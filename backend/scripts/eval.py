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
    """Run retrieval for one case and compute precision/recall/F1."""
    description = case["description"]
    expected_regions: Set[str] = set(case.get("expected_regions", []))
    expected_categories: Set[str] = {c.lower() for c in case.get("expected_categories", [])}

    ctx = rag_service.retrieve_context(
        description,
        intra_country_focus=case.get("intra_country_focus", False),
        focus_country=case.get("focus_country"),
        use_live_feeds=use_gdelt,  # may not be implemented yet — caller can ignore
    ) if "use_live_feeds" in rag_service.retrieve_context.__code__.co_varnames else \
        rag_service.retrieve_context(
            description,
            intra_country_focus=case.get("intra_country_focus", False),
            focus_country=case.get("focus_country"),
        )

    risks = ctx.get("risks", [])
    retrieved_count = len(risks)

    # True positives: retrieved risks whose region matches an expected region.
    # We also union retrieved categories to score category coverage.
    tp_regions: Set[str] = set()
    retrieved_categories: Set[str] = set()
    matched_retrieved = 0

    for r in risks:
        retrieved_categories.add(_normalize(r.get("category", "")))
        # Try region first, then country (intra-country risks have a country field)
        if _region_matches(r.get("region", ""), expected_regions):
            matched_retrieved += 1
            tp_regions.add(_normalize(r.get("region", "")))
        elif _region_matches(r.get("country", ""), expected_regions):
            matched_retrieved += 1
            tp_regions.add(_normalize(r.get("country", "")))

    # Recall: how many of the expected regions are covered by at least one retrieved risk?
    covered_expected: Set[str] = set()
    for exp in expected_regions:
        for r in risks:
            if (_region_matches(r.get("region", ""), {exp})
                    or _region_matches(r.get("country", ""), {exp})):
                covered_expected.add(exp)
                break

    precision = matched_retrieved / retrieved_count if retrieved_count else 0.0
    recall = len(covered_expected) / len(expected_regions) if expected_regions else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    category_coverage = (
        len(expected_categories & retrieved_categories) / len(expected_categories)
        if expected_categories else 0.0
    )

    return {
        "id": case["id"],
        "description": description[:60] + ("…" if len(description) > 60 else ""),
        "retrieved": retrieved_count,
        "true_positives": matched_retrieved,
        "expected_regions": len(expected_regions),
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
    print(f"  {'CASE':<26} {'RTRV':>5} {'TP':>4} {'P':>7} {'R':>7} {'F1':>7} {'CAT':>6}")
    print("  " + "-" * 84)
    for r in results:
        print(
            f"  {r['id']:<26} {r['retrieved']:>5} {r['true_positives']:>4} "
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
