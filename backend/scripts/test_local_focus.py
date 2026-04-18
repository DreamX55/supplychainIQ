"""
Local Focus mode verification script.

Fires the same supply-chain prompt twice through the RAG layer —
once with intra_country_focus OFF and once with it ON — and prints
the top retrieved risks side-by-side so you can confirm the pivot
from cross-border maritime risks to intra-country logistics risks.

Run from the backend/ directory:
    python -m scripts.test_local_focus
"""
from app.services.rag_service import rag_service


PROMPT = (
    "We are a textile manufacturer. We source cotton from Tamil Nadu, "
    "weave and dye in Maharashtra, and truck finished goods to retail "
    "warehouses in Mumbai, Delhi, and Bangalore."
)


def _print_risks(label: str, risks):
    print(f"\n{'=' * 72}")
    print(f"  {label}")
    print('=' * 72)
    if not risks:
        print("  (no risks returned)")
        return
    for i, r in enumerate(risks[:6], 1):
        title = r['title'][:55]
        region = str(r.get('region', ''))[:18]
        category = r['category'][:12]
        score = r['relevance_score']
        level = r['risk_level']
        print(f"  {i}. [{level:8s}] {title:55s}")
        print(f"      region={region:18s} cat={category:12s} score={score:.2f}")


def main():
    print(f"PROMPT: {PROMPT}")

    ctx_off = rag_service.retrieve_context(PROMPT)
    _print_risks("LOCAL FOCUS = OFF (global trade lens)", ctx_off['risks'])

    ctx_on = rag_service.retrieve_context(
        PROMPT,
        intra_country_focus=True,
        focus_country="India",
    )
    _print_risks("LOCAL FOCUS = ON  (India intra-country lens)", ctx_on['risks'])

    print()
    print(f"  shipping_alternatives  OFF={len(ctx_off['shipping_alternatives'])}  "
          f"ON={len(ctx_on['shipping_alternatives'])}  (ON should be 0)")

    # Pass/fail signal
    off_top_region = (ctx_off['risks'][0].get('region', '') if ctx_off['risks'] else '').lower()
    on_top_country = (ctx_on['risks'][0].get('country', '') if ctx_on['risks'] else '').lower()
    print()
    if on_top_country == "india" and off_top_region != on_top_country:
        print("  PASS — Local Focus successfully pivoted the top result to India.")
    else:
        print("  FAIL — Local Focus did not pivot the top result. Check rerank weights.")


if __name__ == "__main__":
    main()
