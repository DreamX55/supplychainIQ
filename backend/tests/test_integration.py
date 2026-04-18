"""
Integration tests for SupplyChainIQ.

Covers the full critical-path demo flow end-to-end using FastAPI's
TestClient: personas → alerts → analyze → scenario → followup → replay →
history → key vault → error paths.

All tests use the mock LLM provider so they run offline with zero cost
and produce deterministic output. The mock-provider regression
assertions below catch the two bugs the post-Phase-5 audit found:

  1. RAG-context token bleed into mock keyword matching (electronics
     persona must NOT produce a Red Sea risk, must NOT have spurious
     EU/Suez graph nodes).
  2. "us" substring matching "consumer" (the word 'consumer' alone
     must NOT trigger a US destination node).

Run:
    cd backend && python -m pytest tests/ -v
  or:
    cd backend && python tests/test_integration.py
"""

import json
import logging
import sys
from pathlib import Path

# Silence provider-fallback warnings — they're expected noise when the
# router chain falls through to mock (e.g. env blocks Groq's api host).
logging.getLogger("supplychainiq").setLevel(logging.ERROR)
logging.getLogger("supplychainiq.router").setLevel(logging.ERROR)

# Make the backend package importable whether run via pytest or directly
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


HELIX_DESCRIPTION = (
    "We manufacture consumer electronics. Our advanced semiconductors come "
    "from Taiwan (TSMC and partners), passive components from China, final "
    "assembly happens in Vietnam, and finished goods are transshipped through "
    "Singapore to the US West Coast. We have a 12-week production cycle and "
    "a high single-source dependency on Taiwan for our most expensive BoM "
    "line items. Geopolitical risk is our biggest unknown."
)


# Wipe the demo SQLite DB once at module load so runs are reproducible.
# We can't delete it per-test because SQLAlchemy's global engine caches
# open connection handles — deleting the file mid-run corrupts state.
# Tests use distinct X-User-ID values for isolation instead.
_DB_PATH = _BACKEND_ROOT / "data" / "supplychainiq.db"
if _DB_PATH.exists():
    _DB_PATH.unlink()


def _new_client() -> TestClient:
    return TestClient(app)


def _hdrs(user_id: str = "integration_tester") -> dict:
    return {"X-User-ID": user_id}


# ----------------------------------------------------------------------
# Critical-path demo flow
# ----------------------------------------------------------------------

def test_full_demo_flow():
    """One big test that walks the entire demo path end-to-end."""
    client = _new_client()
    with client as c:
        # 1. Welcome screen loads personas
        r = c.get("/api/v1/analysis/personas")
        assert r.status_code == 200
        personas = r.json()["personas"]
        assert len(personas) == 3, f"expected 3 personas, got {len(personas)}"

        # 2. Sidebar loads the live-looking alert feed
        r = c.get("/api/v1/analysis/alerts?limit=5")
        assert r.status_code == 200
        assert r.json()["count"] >= 1

        # 3. Pick the electronics persona → run analysis
        helix = next(p for p in personas if p["id"] == "electronics_oem")
        r = c.post(
            "/api/v1/analysis/analyze",
            headers=_hdrs(),
            json={"description": helix["description"]},
        )
        assert r.status_code == 200, r.text
        a = r.json()
        session_id = a["session_id"]

        # --- Bug-regression assertions: mock keyword matching ---
        risk_nodes = a["risk_nodes"]
        assert not any("Red Sea" in rn["node"] for rn in risk_nodes), (
            "BUG REGRESSION: RAG context bleeding into mock matcher produced "
            "a spurious Red Sea risk on an electronics persona."
        )
        assert a["overall_risk_level"] != "Critical", (
            "BUG REGRESSION: overall risk should be High for electronics, "
            "not Critical (Critical comes from the spurious Red Sea leak)."
        )

        graph_nodes = a["supply_chain_graph"]["nodes"]
        assert not any("EU" in n["label"] or "Euro" in n["label"] for n in graph_nodes), (
            "BUG REGRESSION: spurious European Market node in graph."
        )
        assert not any("Suez" in n["label"] for n in graph_nodes), (
            "BUG REGRESSION: spurious Suez corridor node in graph."
        )

        # --- Evidence grounding ---
        for rn in risk_nodes:
            assert rn.get("evidence") and len(rn["evidence"]) >= 3, (
                f"Risk node {rn['node']!r} is missing evidence bullets."
            )

        # --- Provider meta present on the live response ---
        assert a["provider_meta"] is not None
        assert a["provider_meta"]["provider_used"] == "mock"

        # 4. Run all 3 scenario types against the saved analysis
        for stype, params in [
            ("supplier_switch", {"from_node": "Taiwan Semiconductor Supply", "to_country": "South Korea"}),
            ("route_change", {"from_route": "Pacific", "to_route": "Cape of Good Hope"}),
            ("inventory_buffer", {"buffer_days": 45}),
        ]:
            r = c.post(
                "/api/v1/analysis/scenario",
                headers=_hdrs(),
                json={"session_id": session_id, "scenario_type": stype, "parameters": params},
            )
            assert r.status_code == 200, r.text
            s = r.json()
            assert s["verdict"] in ("improved", "neutral", "worsened")
            assert s["tradeoffs"]["latency"]
            assert s["tradeoffs"]["cost"]
            assert s["tradeoffs"]["risk"]
            # The scenario label must bake user parameters back in for specificity
            if stype == "supplier_switch":
                assert "South Korea" in s["scenario_label"]

        # 5. Followup
        r = c.post(
            "/api/v1/analysis/followup",
            headers=_hdrs(),
            json={"session_id": session_id, "question": "What are my biggest risks?"},
        )
        assert r.status_code == 200

        # 6. Replay — every assistant message must parse as JSON so the
        #    frontend can rehydrate the Risk Brief on history load
        r = c.get(f"/api/v1/analysis/session/{session_id}", headers=_hdrs())
        assert r.status_code == 200
        history = r.json()["history"]
        assert len(history) == 4  # 2 user + 2 assistant
        for m in history:
            if m["role"] == "assistant":
                parsed = json.loads(m["content"])
                assert isinstance(parsed, dict)

        # 7. HistoryScreen path
        r = c.get("/api/v1/user/sessions", headers=_hdrs())
        assert r.status_code == 200
        assert len(r.json()["sessions"]) >= 1

        # 8. Key vault store + list
        r = c.post(
            "/api/v1/keys/store",
            headers=_hdrs(),
            json={"provider": "groq", "api_key": "gsk_test123456789"},
        )
        assert r.status_code == 200
        r = c.get("/api/v1/keys/list", headers=_hdrs())
        assert "groq" in r.json()["providers"]

        # 9. Scenario against a nonexistent session → 404
        r = c.post(
            "/api/v1/analysis/scenario",
            headers={"X-User-ID": "ghost_user"},
            json={"session_id": "nonexistent", "scenario_type": "supplier_switch", "parameters": {}},
        )
        assert r.status_code == 404

        # 10. Unsupported file type → 415
        files = {"background_file": ("virus.exe", b"mzheader", "application/octet-stream")}
        r = c.post("/api/v1/analysis/upload-context", headers=_hdrs(), files=files)
        assert r.status_code == 415


# ----------------------------------------------------------------------
# Targeted mock-provider regression tests
# ----------------------------------------------------------------------

def test_consumer_keyword_does_not_trigger_us_node():
    """The word 'consumer' alone must not substring-match 'us'."""
    client = _new_client()
    with client as c:
        r = c.post(
            "/api/v1/analysis/analyze",
            headers=_hdrs("edge_case_user"),
            json={"description": "We sell consumer goods sourced from Vietnam and shipped to Australia."},
        )
        a = r.json()
        assert not any(
            "US" in rn["node"] or "United States" in rn["node"]
            for rn in a["risk_nodes"]
        ), "'consumer' triggered a false US node match"


def test_apparel_persona_is_story_coherent():
    """The apparel persona should pick up Bangladesh, Vietnam, Red Sea, and Europe."""
    client = _new_client()
    with client as c:
        r = c.get("/api/v1/analysis/personas")
        apparel = next(p for p in r.json()["personas"] if p["id"] == "apparel_brand")
        r = c.post(
            "/api/v1/analysis/analyze",
            headers=_hdrs("apparel_tester"),
            json={"description": apparel["description"]},
        )
        a = r.json()
        graph_labels = {n["label"] for n in a["supply_chain_graph"]["nodes"]}
        # Apparel persona explicitly mentions Bangladesh, Vietnam, Suez, Europe
        assert "Bangladesh Textiles" in graph_labels
        assert "Vietnam Assembly" in graph_labels
        assert "European Market" in graph_labels
        # Red Sea risk is the dramatic moment of the apparel demo
        assert any("Red Sea" in rn["node"] for rn in a["risk_nodes"])


# ----------------------------------------------------------------------
# Plain-script entry point
# ----------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        ("full demo flow", test_full_demo_flow),
        ("'consumer' keyword does not trigger US", test_consumer_keyword_does_not_trigger_us_node),
        ("apparel persona is story-coherent", test_apparel_persona_is_story_coherent),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}\n      {e}")
        except Exception as e:  # pragma: no cover
            failed += 1
            print(f"ERROR {name}\n      {type(e).__name__}: {e}")
    print()
    if failed == 0:
        print(f"  ALL {len(tests)} INTEGRATION TESTS PASSED")
        sys.exit(0)
    else:
        print(f"  {failed}/{len(tests)} FAILED")
        sys.exit(1)
