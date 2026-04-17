"""
SupplyChainIQ retrieval eval harness.

Scores the RAG layer (not the LLM) against 10 hand-labeled supply chain
test cases. We measure retrieval quality because:

  1. The LLM's output is bounded by what the RAG layer surfaces — if
     the right risks aren't retrieved, the LLM can't reason about them.
  2. Retrieval is deterministic, repeatable, and costs nothing to run.
  3. LLM evaluation is non-deterministic, costs API credits, and would
     require a separate judge model — overkill for a hackathon eval.

Metrics:
  - Precision: of risks retrieved, what fraction matched the expected
    regions for that case.
  - Recall: of expected regions, what fraction were covered by at least
    one retrieved risk.
  - F1: harmonic mean.
  - Category coverage: did the retrieval surface every expected category?

Usage:
    cd backend
    python -m scripts.eval

Optional flag:
    python -m scripts.eval --gdelt    # also include the live GDELT feed
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

from app.services.rag_service import rag_service


CASES_FILE = Path(__file__).parent / "eval_cases.json"


def _load_cases() -> List[Dict[str, Any]]:
    data = json.loads(CASES_FILE.read_text())
    return data["cases"]


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _region_matches(retrieved_region: str, expected_regions: Set[str]) -> bool:
    """
    A retrieved risk counts as a match if its region is contained in,
    or contains, any of the expected regions (case-insensitive substring).
    Substring matching handles 'India' vs 'Tamil Nadu' (parent country)
    and 'Red Sea' vs 'Red Sea Shipping' style variants.
    """
    r = _normalize(retrieved_region)
    if not r:
        return False
    for exp in expected_regions:
        e = _normalize(exp)
        if not e:
            continue
        if r == e or r in e or e in r:
            return True
    return False


def _score_case(case: Dict[str, Any], use_gdelt: bool = False) -> Dict[str, Any]:
    """
    Score one test case using retrieval-quality metrics that match what
    we actually care about: did the top-K results cover every expected
    region, and did the slots we used pull their weight?

    Metrics:
      - Recall: fraction of expected regions covered by ANY retrieved risk.
        This is the headline number — "did we find the things we needed?"
      - Coverage precision: of the retrieval slots we *could have* used
        productively, how many did? Defined as
            min(slots_with_a_match, expected_count) / min(K, expected_count)
        This avoids penalizing extra-but-relevant context: if the user
        had 3 expected regions and we returned 8 risks where 3 of them
        matched, that's 100% useful — not 38%. The other 5 are bonus
        context the LLM can use, not errors.
      - F1: harmonic mean of recall and coverage precision.
      - Category coverage: fraction of expected categories surfaced.
    """
    description = case["description"]
    expected_regions: Set[str] = set(case.get("expected_regions", []))
    expected_categories: Set[str] = {c.lower() for c in case.get("expected_categories", [])}

    ctx = rag_service.retrieve_context(
        description,
        intra_country_focus=case.get("intra_country_focus", False),
        focus_country=case.get("focus_country"),
        use_live_feeds=use_gdelt,
    ) if "use_live_feeds" in rag_service.retrieve_context.__code__.co_varnames else \
        rag_service.retrieve_context(
            description,
            intra_country_focus=case.get("intra_country_focus", False),
            focus_country=case.get("focus_country"),
        )

    risks = ctx.get("risks", [])
    retrieved_count = len(risks)

    # Walk the retrieved risks once and accumulate:
    #   - covered_expected: which expected regions got at least one hit
    #   - useful_slots: distinct retrieved positions that matched something
    #   - retrieved_categories: union of all category labels we surfaced
    covered_expected: Set[str] = set()
    useful_slots = 0
    retrieved_categories: Set[str] = set()

    for r in risks:
        retrieved_categories.add(_normalize(r.get("category", "")))
        matched_this_slot = False
        for exp in expected_regions:
            if (_region_matches(r.get("region", ""), {exp})
                    or _region_matches(r.get("country", ""), {exp})):
                covered_expected.add(exp)
                matched_this_slot = True
        if matched_this_slot:
            useful_slots += 1

    expected_count = len(expected_regions)
    recall = len(covered_expected) / expected_count if expected_count else 0.0

    # Coverage precision: useful slots / min(K, expected). The denominator
    # is "the most useful slots we COULD have filled" — we don't punish
    # K=8 retrieval when there are only 3 things to find.
    cap = min(retrieved_count, expected_count) if expected_count else retrieved_count
    precision = (min(useful_slots, expected_count) / cap) if cap else 0.0

    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    category_coverage = (
        len(expected_categories & retrieved_categories) / len(expected_categories)
        if expected_categories else 0.0
    )

    return {
        "id": case["id"],
        "description": description[:60] + ("…" if len(description) > 60 else ""),
        "retrieved": retrieved_count,
        "useful_slots": useful_slots,
        "expected_regions": expected_count,
        "covered_expected": len(covered_expected),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "category_coverage": category_coverage,
        "missed_regions": sorted(expected_regions - covered_expected),
    }


def _print_scoreboard(results: List[Dict[str, Any]], label: str):
    print()
    print("=" * 88)
    print(f"  RESULTS — {label}")
    print("=" * 88)
    print(f"  {'CASE':<26} {'RTRV':>5} {'USE':>4} {'P':>7} {'R':>7} {'F1':>7} {'CAT':>6}")
    print("  " + "-" * 84)
    for r in results:
        print(
            f"  {r['id']:<26} {r['retrieved']:>5} {r['useful_slots']:>4} "
            f"{r['precision']:>6.0%} {r['recall']:>6.0%} {r['f1']:>6.0%} "
            f"{r['category_coverage']:>5.0%}"
        )

    n = len(results)
    avg_p = sum(r["precision"] for r in results) / n
    avg_r = sum(r["recall"] for r in results) / n
    avg_f1 = sum(r["f1"] for r in results) / n
    avg_cat = sum(r["category_coverage"] for r in results) / n
    print("  " + "-" * 84)
    print(f"  {'AVERAGE':<26} {'':>5} {'':>4} {avg_p:>6.0%} {avg_r:>6.0%} {avg_f1:>6.0%} {avg_cat:>5.0%}")
    print()
    print(f"  Mean precision:        {avg_p:.1%}")
    print(f"  Mean recall:           {avg_r:.1%}")
    print(f"  Mean F1:               {avg_f1:.1%}")
    print(f"  Mean category coverage: {avg_cat:.1%}")

    # Failure summary
    misses = [r for r in results if r["missed_regions"]]
    if misses:
        print()
        print(f"  Cases with missed regions ({len(misses)}/{n}):")
        for r in misses:
            print(f"    {r['id']}: missed {r['missed_regions']}")

    return {"precision": avg_p, "recall": avg_r, "f1": avg_f1, "category": avg_cat}


def main():
    parser = argparse.ArgumentParser(description="SupplyChainIQ retrieval eval")
    parser.add_argument(
        "--gdelt",
        action="store_true",
        help="Also score with GDELT live feed enabled (if available)",
    )
    args = parser.parse_args()

    cases = _load_cases()
    print(f"Loaded {len(cases)} test cases from {CASES_FILE.name}")

    # Always run mock-only first as the baseline
    print("\nRunning baseline (mock data only)...")
    mock_results = [_score_case(c, use_gdelt=False) for c in cases]
    mock_summary = _print_scoreboard(mock_results, "MOCK DATA ONLY")

    if args.gdelt:
        print("\nRunning with live GDELT feed...")
        try:
            gdelt_results = [_score_case(c, use_gdelt=True) for c in cases]
            gdelt_summary = _print_scoreboard(gdelt_results, "MOCK + GDELT LIVE FEED")

            print()
            print("=" * 88)
            print("  LIFT FROM LIVE FEED")
            print("=" * 88)
            for k in ("precision", "recall", "f1", "category"):
                delta = gdelt_summary[k] - mock_summary[k]
                arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "—")
                print(f"  {k:<20} {mock_summary[k]:.1%} → {gdelt_summary[k]:.1%}  ({arrow} {abs(delta):.1%})")
        except Exception as e:
            print(f"  GDELT eval failed: {e}")
            print("  (This is fine if --gdelt was passed before the live feed was wired in)")


if __name__ == "__main__":
    main()
