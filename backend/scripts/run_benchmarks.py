"""
SupplyChainIQ — Groq Performance Benchmarking Suite
====================================================
Run from the `backend/` directory:
    python3 scripts/run_benchmarks.py

Reads your Groq API key from the local encrypted vault (no .env needed),
then fires real API calls to measure system performance.
"""

import sys
import os
import time
import io
import statistics
import json
from pathlib import Path
from datetime import datetime

# ── Path setup (so we can import from app/) ──────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import httpx
import pandas as pd

# ── 1. Pull Groq key from the encrypted vault ─────────────────────────────────
print("=" * 60)
print("  SupplyChainIQ — Live Performance Benchmark (Groq Only)")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print()

print("🔑 Reading Groq API key from local vault...")
try:
    import sqlite3
    from app.services.key_vault import key_vault

    # Auto-discover the user_id that has a Groq key stored
    vault_db = BACKEND_DIR / "data" / "vault.db"
    conn = sqlite3.connect(str(vault_db))
    row = conn.execute(
        "SELECT user_id FROM api_keys WHERE provider = 'groq' LIMIT 1"
    ).fetchone()
    conn.close()

    if not row:
        print("❌ No Groq key found in vault.")
        print("   → Open the app at http://localhost:3000")
        print("   → Go to Setup, select Groq, and save your key.")
        sys.exit(1)

    user_id = row[0]
    GROQ_KEY = key_vault.get_key(user_id, "groq")
    if not GROQ_KEY:
        print(f"❌ Found key record for user {user_id!r} but failed to decrypt it.")
        sys.exit(1)
    print(f"   ✅ Key found for user {user_id!r}: {GROQ_KEY[:8]}***...{GROQ_KEY[-4:]}")
except Exception as e:
    print(f"❌ Vault error: {e}")
    sys.exit(1)

# ── 2. Load RAG service ───────────────────────────────────────────────────────
print()
print("📚 Loading RAG service...")
try:
    from app.services.rag_service import rag_service as _rag
    retrieve_context = _rag.retrieve_context
    format_context_for_llm = _rag.format_context_for_llm
    print("   ✅ RAG service loaded.")
except Exception as e:
    print(f"❌ RAG service load error: {e}")
    sys.exit(1)

# ── 3. Test prompts ───────────────────────────────────────────────────────────
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # Groq free tier — fast, low-latency

SYSTEM_PROMPT = (
    "You are SupplyChainIQ. Analyze the supply chain and respond with valid JSON: "
    '{"risk_nodes":[{"node":"string","risk_level":"High","cause":"string",'
    '"recommended_action":"string","confidence_score":0.85,"category":"geopolitical"}],'
    '"overall_risk_level":"High","summary":"string","follow_up_suggestions":["string"]}'
)

TEST_CASES = [
    {
        "name": "Simple Chain (1 region)",
        "desc": "I source CPUs from TSMC in Taiwan and sell to customers in London.",
    },
    {
        "name": "Complex Chain (4 regions)",
        "desc": (
            "I run a high-end laptop assembly line. CPUs from TSMC in Taiwan, "
            "display panels from LG in South Korea, magnesium casings from a factory "
            "in Shenzhen. Everything ships via the Port of Singapore to Rotterdam."
        ),
    },
    {
        "name": "Food & Beverage Chain",
        "desc": (
            "I operate a premium coffee brand in London. We source beans from Ethiopia "
            "and Brazil, process them in Djibouti, ship via the Red Sea to a roasting "
            "plant in Trieste, then truck to our UK distribution centre."
        ),
    },
]

DEMO_CSV = BACKEND_DIR.parent / "demo_files" / "supplier_list.csv"
# Fallback inline CSV if file is inaccessible
INLINE_CSV = b"""Supplier_ID,Supplier_Name,Country,Component,Tier,Lead_Time_Days,Annual_Value_USD,Single_Source
SUP-001,TSMC,Taiwan,Advanced Semiconductors (5nm),1,90,42000000,Yes
SUP-002,Samsung SDI,South Korea,Lithium-Ion Battery Cells,1,60,18500000,No
SUP-003,Shenzhen Foxconn,China,PCB Assembly,2,45,9200000,No
SUP-004,Daikin Vietnam,Vietnam,Compressor Units,2,55,4100000,No
SUP-005,Infineon Germany,Germany,Power Management ICs,1,75,7800000,Yes"""

# ── 4. Benchmark helpers ──────────────────────────────────────────────────────

def call_groq(description: str, context: str) -> tuple[dict, float]:
    """Fire one Groq request. Returns (parsed_json, elapsed_seconds)."""
    user_msg = (
        f"## SUPPLY CHAIN:\n{description}\n\n"
        f"## CONTEXT:\n{context}\n\n"
        "Respond with JSON only."
    )
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }
    t0 = time.perf_counter()
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_KEY}",
                     "Content-Type": "application/json"},
            json=payload,
        )
    elapsed = time.perf_counter() - t0
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    # Try to parse the JSON from the response
    try:
        parsed = json.loads(raw)
    except Exception:
        # Extract JSON block if wrapped in markdown
        import re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = json.loads(m.group()) if m else {"raw": raw}
    return parsed, elapsed


def bench_rag(description: str) -> float:
    """Measure RAG retrieval + formatting time (pure Python, no network)."""
    t0 = time.perf_counter()
    ctx = retrieve_context(description)
    format_context_for_llm(ctx)
    return time.perf_counter() - t0


def bench_csv_parse_bytes(content: bytes) -> tuple[int, float]:
    """Measure CSV file ingestion time from raw bytes."""
    t0 = time.perf_counter()
    df = pd.read_csv(io.BytesIO(content))
    text = df.to_string(index=False)
    elapsed = time.perf_counter() - t0
    return len(text), elapsed

# ── 5. Run benchmarks ─────────────────────────────────────────────────────────

results = []

# --- RAG Retrieval ---
print()
print("─" * 60)
print("  BENCHMARK 1 of 5 — RAG Retrieval Speed")
print("─" * 60)
rag_times = []
for tc in TEST_CASES:
    t = bench_rag(tc["desc"])
    rag_times.append(t)
    print(f"   {tc['name']:<30} {t*1000:.1f} ms")
results.append({
    "metric": "RAG Retrieval (in-memory)",
    "runs": len(rag_times),
    "mean_ms": statistics.mean(rag_times) * 1000,
    "min_ms":  min(rag_times) * 1000,
    "max_ms":  max(rag_times) * 1000,
})

# --- File Ingestion ---
print()
print("─" * 60)
print("  BENCHMARK 2 of 5 — CSV File Ingestion Speed")
print("─" * 60)
try:
    try:
        with open(DEMO_CSV, "rb") as f:
            csv_bytes = f.read()
        csv_label = f"supplier_list.csv (from demo_files)"
    except (PermissionError, FileNotFoundError):
        csv_bytes = INLINE_CSV
        csv_label = "supplier_list.csv (5-supplier inline sample)"
    chars, t = bench_csv_parse_bytes(csv_bytes)
    print(f"   {csv_label}")
    print(f"   → {chars:,} chars parsed in {t*1000:.1f} ms")
    results.append({
        "metric": "CSV File Parse & DataFrame Conversion",
        "runs": 1,
        "mean_ms": t * 1000,
        "min_ms":  t * 1000,
        "max_ms":  t * 1000,
    })
except Exception as e:
    print(f"   ⚠️  CSV benchmark failed: {e}")

# --- LLM Analysis Calls ---
print()
print("─" * 60)
print("  BENCHMARK 3–5 of 5 — Live Groq LLM Analysis")
print("─" * 60)
print("  (Sending real API requests — this may take 30-60 seconds...)")
print()

llm_results_by_case = []
for i, tc in enumerate(TEST_CASES):
    print(f"   [{i+1}/3] {tc['name']}...")
    ctx = format_context_for_llm(retrieve_context(tc["desc"]))
    try:
        parsed, elapsed = call_groq(tc["desc"], ctx)
        risk_count = len(parsed.get("risk_nodes", []))
        overall = parsed.get("overall_risk_level", "?")
        print(f"         ✅  {elapsed:.2f}s | {risk_count} risks | Overall: {overall}")
        llm_results_by_case.append({
            "name": tc["name"],
            "elapsed": elapsed,
            "risks": risk_count,
            "overall": overall,
        })
    except Exception as e:
        print(f"         ❌  Failed: {e}")

if llm_results_by_case:
    times = [r["elapsed"] for r in llm_results_by_case]
    results.append({
        "metric": "LLM Analysis — Simple Chain (Groq llama3-8b)",
        "runs": 1,
        "mean_ms": llm_results_by_case[0]["elapsed"] * 1000 if len(llm_results_by_case) > 0 else 0,
        "min_ms":  llm_results_by_case[0]["elapsed"] * 1000 if len(llm_results_by_case) > 0 else 0,
        "max_ms":  llm_results_by_case[0]["elapsed"] * 1000 if len(llm_results_by_case) > 0 else 0,
    })
    results.append({
        "metric": "LLM Analysis — Complex Chain 4 regions (Groq llama3-8b)",
        "runs": 1,
        "mean_ms": llm_results_by_case[1]["elapsed"] * 1000 if len(llm_results_by_case) > 1 else 0,
        "min_ms":  llm_results_by_case[1]["elapsed"] * 1000 if len(llm_results_by_case) > 1 else 0,
        "max_ms":  llm_results_by_case[1]["elapsed"] * 1000 if len(llm_results_by_case) > 1 else 0,
    })
    results.append({
        "metric": "LLM Analysis — Food & Beverage Chain (Groq llama3-8b)",
        "runs": 1,
        "mean_ms": llm_results_by_case[2]["elapsed"] * 1000 if len(llm_results_by_case) > 2 else 0,
        "min_ms":  llm_results_by_case[2]["elapsed"] * 1000 if len(llm_results_by_case) > 2 else 0,
        "max_ms":  llm_results_by_case[2]["elapsed"] * 1000 if len(llm_results_by_case) > 2 else 0,
    })

# ── 6. Print final table ──────────────────────────────────────────────────────
print()
print()
print("=" * 60)
print("  RESULTS — SupplyChainIQ Performance Benchmark")
print(f"  Provider: Groq (llama3-8b-8192)  |  {datetime.now().strftime('%d %b %Y %H:%M')}")
print("=" * 60)
print()

# Markdown table
header = f"| {'Metric':<46} | {'Mean':>8} | {'Min':>8} | {'Max':>8} |"
sep    = f"|{'-'*48}|{'-'*10}|{'-'*10}|{'-'*10}|"
print(header)
print(sep)

for r in results:
    mean = r["mean_ms"]
    mn   = r["min_ms"]
    mx   = r["max_ms"]
    # Format as ms or s depending on magnitude
    def fmt(v):
        if v >= 1000:
            return f"{v/1000:.2f}s"
        return f"{v:.0f}ms"
    row = f"| {r['metric']:<46} | {fmt(mean):>8} | {fmt(mn):>8} | {fmt(mx):>8} |"
    print(row)

print()

# Detailed per-case LLM table
if llm_results_by_case:
    print()
    print("  LLM ANALYSIS — Per Test Case Detail")
    print(f"  | {'Test Case':<36} | {'Time':>7} | {'Risk Nodes':>10} | {'Overall':>8} |")
    print(f"  |{'-'*38}|{'-'*9}|{'-'*12}|{'-'*10}|")
    for r in llm_results_by_case:
        t = r["elapsed"]
        fmt_t = f"{t:.2f}s"
        print(f"  | {r['name']:<36} | {fmt_t:>7} | {r['risks']:>10} | {r['overall']:>8} |")

print()
print("=" * 60)
print("  Copy the table above into your README / presentation.")
print("=" * 60)
print()

# Also write to a file for easy copy-paste
out_path = BACKEND_DIR / "data" / "benchmark_results.md"
with open(out_path, "w") as f:
    f.write(f"# SupplyChainIQ — Validated Performance Benchmarks\n\n")
    f.write(f"**Provider:** Groq (llama3-8b-8192 LPU)  \n")
    f.write(f"**Measured:** {datetime.now().strftime('%d %B %Y at %H:%M IST')}  \n")
    f.write(f"**Environment:** Local development (MacOS, localhost:8005)  \n\n")
    f.write(f"| Metric | Mean | Min | Max |\n")
    f.write(f"|---|---|---|---|\n")
    for r in results:
        def fmt(v):
            if v >= 1000:
                return f"{v/1000:.2f}s"
            return f"{v:.0f}ms"
        f.write(f"| {r['metric']} | {fmt(r['mean_ms'])} | {fmt(r['min_ms'])} | {fmt(r['max_ms'])} |\n")
    if llm_results_by_case:
        f.write(f"\n## LLM Analysis — Per Test Case\n\n")
        f.write(f"| Test Case | Response Time | Risk Nodes Identified | Overall Risk |\n")
        f.write(f"|---|---|---|---|\n")
        for r in llm_results_by_case:
            f.write(f"| {r['name']} | {r['elapsed']:.2f}s | {r['risks']} | {r['overall']} |\n")
    f.write(f"\n> Benchmarks measured by firing real API requests to Groq's LPU inference API.\n")
    f.write(f"> RAG retrieval uses in-memory search over the curated risk knowledge base.\n")

print(f"📄  Full results also saved to: demo_files/benchmark_results.md")
print()
