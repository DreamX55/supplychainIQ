"""
RAG Service for SupplyChainIQ
Handles context retrieval from mock vector database
"""

import asyncio
from typing import List, Dict, Any, Optional
from ..data.mock_risk_data import (
    search_risks,
    get_alternatives,
    get_shipping_alternatives,
    get_all_risks
)


class RAGService:
    """
    Retrieval Augmented Generation Service
    In production, this would connect to Pinecone/Chroma
    For demo, uses mock data with keyword matching
    """
    
    def __init__(self):
        self.all_risks = get_all_risks()
    
    def extract_entities(self, supply_chain_description: str) -> Dict[str, List[str]]:
        """
        Extract key entities from supply chain description
        In production, this would use NER or Claude for extraction
        """
        description_lower = supply_chain_description.lower()
        
        # Region detection
        regions = []
        region_keywords = {
            "taiwan": "Taiwan",
            "china": "China",
            "vietnam": "Vietnam",
            "singapore": "Singapore",
            "malaysia": "Malaysia",
            "thailand": "Thailand",
            "india": "India",
            "bangladesh": "Bangladesh",
            "indonesia": "Indonesia",
            "japan": "Japan",
            "korea": "South Korea",
            "us": "United States",
            "usa": "United States",
            "united states": "United States",
            "america": "United States",
            "europe": "Europe",
            "germany": "Germany",
            "mexico": "Mexico",
            "brazil": "Brazil",
            "red sea": "Red Sea",
            "suez": "Suez Canal",
            "panama": "Panama Canal",
            # Indian states / cities — these all imply India for the
            # focus_country auto-inference, and are also tagged as their
            # own regions so intra-country reranking can match them.
            "tamil nadu": "India",
            "chennai": "India",
            "maharashtra": "India",
            "mumbai": "India",
            "pune": "India",
            "delhi": "India",
            "ncr": "India",
            "bangalore": "India",
            "bengaluru": "India",
            "karnataka": "India",
            "gujarat": "India",
            "ahmedabad": "India",
            "mundra": "India",
            "punjab": "India",
            "haryana": "India",
            "uttarakhand": "India",
            "dehradun": "India",
            "assam": "India",
            "guwahati": "India",
            "kerala": "India",
            "hyderabad": "India",
            "kolkata": "India",
        }
        
        for keyword, region in region_keywords.items():
            if keyword in description_lower:
                if region not in regions:
                    regions.append(region)
        
        # Industry detection
        industries = []
        industry_keywords = {
            "chip": "semiconductors",
            "semiconductor": "semiconductors",
            "electronic": "electronics",
            "apparel": "apparel",
            "cloth": "apparel",
            "textile": "apparel",
            "fashion": "apparel",
            "auto": "automotive",
            "car": "automotive",
            "vehicle": "automotive",
            "pharma": "pharmaceutical",
            "drug": "pharmaceutical",
            "medicine": "pharmaceutical",
            "food": "agricultural",
            "agricult": "agricultural",
            "farm": "agricultural",
            "coffee": "agricultural",
            "tech": "electronics",
            "computer": "electronics"
        }
        
        for keyword, industry in industry_keywords.items():
            if keyword in description_lower:
                if industry not in industries:
                    industries.append(industry)
        
        # Transport mode detection
        transport_modes = []
        if any(word in description_lower for word in ["ship", "port", "sea", "ocean", "vessel", "container"]):
            transport_modes.append("maritime")
        if any(word in description_lower for word in ["air", "fly", "cargo", "freight"]):
            transport_modes.append("air")
        if any(word in description_lower for word in ["rail", "train", "railway"]):
            transport_modes.append("rail")
        if any(word in description_lower for word in ["truck", "road", "land"]):
            transport_modes.append("road")
        
        return {
            "regions": regions,
            "industries": industries,
            "transport_modes": transport_modes
        }
    
    def retrieve_context(
        self,
        supply_chain_description: str,
        max_results: int = 8,
        intra_country_focus: bool = False,
        focus_country: Optional[str] = None,
        use_live_feeds: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant risk context based on supply chain description.

        When intra_country_focus is True, the retriever pivots to:
          - boost risks whose `country` or `region` matches focus_country
          - prefer logistics/road/rail risks
          - deprioritize cross-border maritime chokepoints

        When use_live_feeds is True, the retriever also pulls fresh news
        articles from GDELT for the detected regions and merges them
        with the mock corpus before reranking. Falls back silently to
        mock-only on any GDELT error.
        """
        # Extract entities
        entities = self.extract_entities(supply_chain_description)

        # If local mode is on but no explicit focus_country, infer from
        # the first detected region (best-effort).
        if intra_country_focus and not focus_country:
            detected = entities.get("regions") or []
            if detected:
                focus_country = detected[0]

        # Search for relevant risks
        risk_results = search_risks(
            query=supply_chain_description,
            regions=entities.get("regions"),
            categories=None
        )

        # Optionally augment with live GDELT articles for the detected
        # regions. Done here so the reranker can score live + mock
        # uniformly. Synchronous call into an async service via
        # asyncio.run is fine because retrieve_context is itself sync.
        if use_live_feeds:
            live_risks = self._fetch_live_feeds(entities.get("regions") or [], focus_country)
            if live_risks:
                # Live entries get a competitive starter score so they
                # actually surface in the top-N. Region-matched live news
                # is freshness-weighted and should compete with mock data.
                detected_lower = {r.lower() for r in (entities.get("regions") or [])}
                seen_ids = {r.get("id") for r in risk_results}
                for lr in live_risks:
                    if lr.get("id") in seen_ids:
                        continue
                    # Base score 0.85 — slightly below mock keyword hits
                    # but above weak partial matches. +0.15 if the live
                    # article is for a region the user actually mentioned.
                    score = 0.85
                    if str(lr.get("region", "")).lower() in detected_lower:
                        score += 0.15
                    risk_results.append({**lr, "relevance_score": score})

        if intra_country_focus:
            # Safety net: even if the keyword search missed them, inject
            # every intra-country risk for the focus country so the
            # reranker has something to boost. Without this, prompts that
            # describe a chain in pure city/state terms (e.g. "Mumbai →
            # Delhi by truck") return zero India-tagged risks.
            if focus_country:
                from ..data.mock_risk_data import INTRA_COUNTRY_RISKS
                fc_lower = focus_country.lower()
                seen_ids = {r.get("id") for r in risk_results}
                for r in INTRA_COUNTRY_RISKS:
                    if str(r.get("country", "")).lower() == fc_lower and r.get("id") not in seen_ids:
                        risk_results.append({**r, "relevance_score": 0.5})

            risk_results = self._apply_local_focus(risk_results, focus_country)
        else:
            # Re-sort the merged list (mock + live) by relevance before
            # truncating. Without this, GDELT items appended after the
            # already-sorted mock list would always get cut by [:N].
            risk_results.sort(key=lambda r: r.get("relevance_score", 0), reverse=True)

        risk_results = risk_results[:max_results]

        # Get alternative suppliers for detected industries
        alternatives = {}
        for industry in entities.get("industries", []):
            alts = get_alternatives(industry)
            if alts:
                alternatives[industry] = alts

        # Get shipping route alternatives if regions detected.
        # Skipped entirely in local-focus mode — cross-border shipping
        # alternatives are noise when the user is intra-country.
        shipping_alternatives = {}
        if not intra_country_focus:
            regions = entities.get("regions", [])
            if len(regions) >= 2:
                asian_regions = ["Taiwan", "China", "Vietnam", "Singapore", "Malaysia", "Thailand", "Japan", "South Korea", "India"]
                western_regions = ["United States", "Europe", "Germany"]

                origins = [r for r in regions if r in asian_regions]
                destinations = [r for r in regions if r in western_regions]

                for origin in origins[:1]:
                    for dest in destinations[:1]:
                        routes = get_shipping_alternatives(origin, dest)
                        if routes:
                            shipping_alternatives[f"{origin} to {dest}"] = routes

        return {
            "entities": entities,
            "risks": risk_results,
            "alternative_suppliers": alternatives,
            "shipping_alternatives": shipping_alternatives,
            "context_retrieved": True,
            "intra_country_focus": intra_country_focus,
            "focus_country": focus_country,
        }

    # ------------------------------------------------------------------
    # Local-focus reranking
    # ------------------------------------------------------------------
    # Cross-border / maritime chokepoint regions that we want to push DOWN
    # the relevance list when the user is operating intra-country.
    _MARITIME_CHOKEPOINTS = {
        "red sea", "suez canal", "panama canal",
        "south china sea", "strait of hormuz", "strait of malacca",
    }

    def _fetch_live_feeds(
        self,
        regions: List[str],
        focus_country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Pull live news articles from GDELT for the detected regions.
        Returns risk-shaped dicts. Returns [] silently on any error so
        retrieval always degrades gracefully to mock-only.

        Bridges sync->async because retrieve_context is itself sync.
        Uses asyncio.run when no loop is present, or schedules on the
        current loop when called from inside async code.
        """
        try:
            from .gdelt_service import gdelt_service
        except Exception:
            return []

        # Build the region list. Include focus_country if it's not
        # already in the detected regions (the local-focus auto-infer path).
        query_regions = list(regions or [])
        if focus_country and focus_country not in query_regions:
            query_regions.insert(0, focus_country)
        if not query_regions:
            return []

        try:
            # Try the simple path first — this works when retrieve_context
            # is called from sync code (like the eval harness or tests).
            return asyncio.run(gdelt_service.fetch_for_regions(query_regions))
        except RuntimeError:
            # We're inside an existing event loop (FastAPI request).
            # Run the coroutine in a fresh loop on a worker thread so
            # we don't block or conflict with the parent loop.
            import concurrent.futures

            def _runner():
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(
                        gdelt_service.fetch_for_regions(query_regions)
                    )
                finally:
                    loop.close()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                try:
                    return ex.submit(_runner).result(timeout=10.0)
                except Exception:
                    return []
        except Exception:
            return []

    def _apply_local_focus(
        self,
        risks: List[Dict[str, Any]],
        focus_country: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Rerank risks for local-focus mode:
          + boost intra-country risks tagged with the focus_country
          + boost logistics/road/rail items
          - penalize maritime chokepoints
          - penalize geopolitical risks that are inherently cross-border
        """
        focus_lower = (focus_country or "").lower().strip()
        adjusted: List[Dict[str, Any]] = []

        for risk in risks:
            score = float(risk.get("relevance_score", 0.0))
            region_lower = str(risk.get("region", "")).lower()
            country_lower = str(risk.get("country", "")).lower()
            category = str(risk.get("category", "")).lower()
            transport_mode = str(risk.get("transport_mode") or "").lower()

            # Strong boost: this risk is explicitly tagged to the focus country
            if focus_lower and (country_lower == focus_lower or region_lower == focus_lower):
                score += 0.6

            # Boost: domestic-mode transport
            if transport_mode in ("road", "rail"):
                score += 0.25

            # Boost: logistics category in general
            if category == "logistics":
                score += 0.10

            # Penalty: maritime chokepoints — these are cross-border by definition
            if region_lower in self._MARITIME_CHOKEPOINTS:
                score -= 0.7

            # Penalty: geopolitical risks not in the focus country
            if category == "geopolitical" and focus_lower and country_lower != focus_lower and region_lower != focus_lower:
                score -= 0.3

            adjusted.append({**risk, "relevance_score": max(score, 0.0)})

        adjusted.sort(key=lambda r: r["relevance_score"], reverse=True)
        # Drop anything we pushed all the way to zero — it's no longer relevant
        return [r for r in adjusted if r["relevance_score"] > 0.0]

    
    def format_context_for_llm(self, context: Dict[str, Any]) -> str:
        """
        Format retrieved context into a string for LLM prompt
        """
        lines = ["## RETRIEVED RISK INTELLIGENCE CONTEXT\n"]

        # Local focus banner — surfaced first so the LLM can't miss it
        if context.get("intra_country_focus"):
            fc = context.get("focus_country") or "the user's home country"
            lines.append(f"**MODE: LOCAL FOCUS — Country: {fc}**")
            lines.append(
                "Prioritize intra-country logistics (road, rail, regional infrastructure, "
                "local labor actions, monsoon/seasonal disruption, state-level policy). "
                "Treat cross-border maritime chokepoints as low-priority noise unless the "
                "user explicitly mentions exports.\n"
            )

        # Entities
        entities = context.get("entities", {})
        if entities.get("regions"):
            lines.append(f"**Detected Regions:** {', '.join(entities['regions'])}")
        if entities.get("industries"):
            lines.append(f"**Detected Industries:** {', '.join(entities['industries'])}")
        if entities.get("transport_modes"):
            lines.append(f"**Transport Modes:** {', '.join(entities['transport_modes'])}")
        
        lines.append("\n### RELEVANT RISK ALERTS\n")
        
        # Risk alerts
        for risk in context.get("risks", []):
            is_live = risk.get("source") == "gdelt"
            live_tag = " 🔴 LIVE" if is_live else ""
            lines.append(f"**[{risk['risk_level'].upper()}]{live_tag} {risk['title']}** (Region: {risk['region']})")
            lines.append(f"- Category: {risk['category']}")
            lines.append(f"- Description: {risk['description']}")
            lines.append(f"- Affected Industries: {', '.join(risk['affected_industries'])}")
            lines.append(f"- Sources: {', '.join(risk['sources'])}")
            lines.append(f"- Confidence: {risk['confidence']}")
            lines.append(f"- Last Updated: {risk['last_updated']}")
            if is_live and risk.get("url"):
                lines.append(f"- Article URL: {risk['url']}")
            lines.append("")
        
        # Alternative suppliers
        if context.get("alternative_suppliers"):
            lines.append("\n### ALTERNATIVE SUPPLIER OPTIONS\n")
            for industry, suppliers in context["alternative_suppliers"].items():
                lines.append(f"**{industry.title()} Alternatives:**")
                for supplier in suppliers:
                    if "companies" in supplier:
                        lines.append(f"- {supplier['country']}: {', '.join(supplier['companies'])} (Lead time: {supplier['lead_time']})")
                    elif "specialization" in supplier:
                        lines.append(f"- {supplier['country']}: {supplier['specialization']} (Lead time: {supplier['lead_time']})")
                    elif "products" in supplier:
                        lines.append(f"- {supplier['country']}: {', '.join(supplier['products'])} (Lead time: {supplier['lead_time']})")
                lines.append("")
        
        # Shipping alternatives
        if context.get("shipping_alternatives"):
            lines.append("\n### SHIPPING ROUTE ALTERNATIVES\n")
            for route_name, route_info in context["shipping_alternatives"].items():
                lines.append(f"**{route_name}:**")
                lines.append(f"- Primary Route: {route_info.get('primary', 'N/A')} ({route_info.get('transit_time', 'N/A')})")
                if route_info.get("alternatives"):
                    lines.append("- Alternatives:")
                    for alt in route_info["alternatives"]:
                        status = alt.get("status", alt.get("benefit", ""))
                        lines.append(f"  - {alt['route']}: {alt['transit_time']} ({status})")
                lines.append("")
        
        return "\n".join(lines)


# Singleton instance
rag_service = RAGService()
