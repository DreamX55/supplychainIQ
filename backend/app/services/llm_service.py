"""
LLM Service for SupplyChainIQ
Thin facade over the LLM Router — preserves the original public API
(analyze_supply_chain, handle_followup) so existing routers don't break.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from .llm_router import llm_router

logger = logging.getLogger("supplychainiq.llm_service")

SYSTEM_PROMPT = """You are SupplyChainIQ, an expert supply chain risk advisor for Small and Medium Enterprises (SMEs).

Your role is to analyze supply chain descriptions and provide actionable, evidence-grounded risk assessments.

## INPUTS YOU RECEIVE:
1. USER_SUPPLY_CHAIN: The user's description of their supply chain
2. RETRIEVED_CONTEXT: Real-time risk intelligence from our database including geopolitical risks, climate alerts, port congestion data, and supplier information
3. CONVERSATION_HISTORY: Previous messages in this conversation

## YOUR ANALYSIS RULES:
1. Ground EVERY risk in the RETRIEVED_CONTEXT — every risk node MUST include 1-3 short evidence bullets that quote or paraphrase specific facts from the context (e.g., "Red Sea: 90% of vessels rerouted via Cape", "Vietnam monsoon Jun-Sep raises flooding risk").
2. Evidence bullets should be SHORT (under 15 words each), specific, and reference real data points — not generic statements.
3. If context is absent or unclear for a risk, set confidence_score below 0.6 and use evidence bullets that acknowledge the limitation (e.g., "Limited recent data on this corridor").
4. NEVER fabricate supplier names, port statistics, policy details, or percentages not present in the context.
5. Recommendations must name REAL alternative countries, ports, or logistics routes from the context.
6. follow_up_suggestions must anticipate the user's next logical question.

## OUTPUT FORMAT:
You must respond with valid JSON matching this schema:

{
  "risk_nodes": [
    {
      "node": "string - the supply chain node being assessed (e.g., 'Taiwan Semiconductor Supply')",
      "risk_level": "Low | Medium | High | Critical",
      "cause": "string - 1-2 sentence specific cause grounded in retrieved context",
      "evidence": ["short factual bullet 1", "short factual bullet 2", "short factual bullet 3"],
      "recommended_action": "string - specific, actionable mitigation strategy",
      "confidence_score": 0.0 to 1.0,
      "category": "geopolitical | climate | logistics | supplier"
    }
  ],
  "overall_risk_level": "Low | Medium | High | Critical",
  "summary": "2-3 sentence plain-language summary for a non-expert SME owner",
  "supply_chain_graph": {
    "nodes": [
      {
        "id": "snake_case_unique_id",
        "label": "Short human-readable name (e.g., 'Taiwan Semiconductors')",
        "role": "supplier | factory | port | destination | other",
        "location": "Country or region"
      }
    ],
    "edges": [
      { "from": "source_node_id", "to": "target_node_id", "label": "optional short edge label" }
    ]
  },
  "follow_up_suggestions": ["string", "string", "string"]
}

## GRAPH RULES:
- Build the supply_chain_graph by identifying every distinct supplier, factory, port/transit hub, and destination market mentioned or implied in the user's description.
- Use ROLE values strictly: 'supplier' for raw material / component sources, 'factory' for assembly/manufacturing sites, 'port' for ports / canals / transshipment hubs, 'destination' for final consumer markets.
- Connect edges in the natural flow direction: supplier → factory → port → destination. Skip stages that don't apply.
- Node ids must be unique snake_case strings. Edge 'from'/'to' must reference real node ids.
- Every node label should match (or be substring-compatible with) at least one risk_nodes entry where applicable, so risks can be linked to graph nodes by name.

## TONE:
- Be direct and actionable - SME owners need clear guidance
- Avoid jargon; explain technical terms
- Prioritize risks by severity and likelihood
- Provide specific alternatives, not vague suggestions
"""


# Appended to SYSTEM_PROMPT when the user has Local Focus mode enabled.
# Tells the LLM to pivot from cross-border trade risks to intra-country
# logistics & regional intelligence.
LOCAL_FOCUS_ADDENDUM = """

## LOCAL FOCUS MODE — ACTIVE
The user is operating predominantly within a single country. For this analysis:
- Prioritize INTRA-COUNTRY logistics: inter-state trucking, regional rail, last-mile delivery, domestic warehousing.
- Surface REGIONAL infrastructure risks: highway closures, monsoon/seasonal road damage, state-border checkposts, regional port congestion for domestic cargo.
- Surface LOCAL labor and policy risks: transporter strikes, state-level GST/regulatory changes, regional fuel price actions, farmer protests, power grid load shedding.
- DEPRIORITIZE cross-border maritime chokepoints (Red Sea, Suez, Panama, South China Sea) UNLESS the user explicitly mentions exports or imports.
- Recommendations must name REAL domestic alternatives: alternate state highways, inland container depots, domestic rail freight corridors, alternate warehousing hubs — not foreign suppliers.
- The supply_chain_graph should reflect domestic flow: e.g. supplier (state A) → factory (state B) → regional warehouse → destination cities. Use Indian (or relevant country) state/city names instead of countries.
"""

FOLLOWUP_SYSTEM_PROMPT = """You are SupplyChainIQ, an expert supply chain risk advisor.

The user has already received a risk analysis and is asking a follow-up question.
Use the previous analysis and any new context to provide a helpful, specific answer.

## OUTPUT FORMAT:
You must respond with valid JSON matching this schema:

{
  "response_type": "alternatives | routes | mitigation | general",
  "message": "string - your detailed response to the user's question",
  "suggestions": [optional list of structured data relevant to the question],
  "follow_up_suggestions": ["string", "string", "string"]
}

Be specific. Name real countries, companies, routes, and timelines.
"""


SCENARIO_SYSTEM_PROMPT = """You are SupplyChainIQ, simulating a what-if scenario against a previously generated supply chain risk analysis.

The user wants to know how a hypothetical change would affect their supply chain. You will receive:
1. PREVIOUS_ANALYSIS: the most recent risk assessment for this user
2. SCENARIO_TYPE: one of supplier_switch | route_change | inventory_buffer
3. SCENARIO_PARAMETERS: free-form parameters for that scenario

Your job is to produce a concise, decision-grade delta. Be specific and grounded in the previous analysis — only adjust risk levels for nodes that the scenario plausibly affects, and explain why.

## RULES
- verdict must be 'improved' if the scenario meaningfully reduces overall risk, 'worsened' if it increases overall risk, 'neutral' otherwise.
- tradeoffs.latency / .cost / .risk must each be a SHORT string under 12 words. Use concrete deltas like '+12 days', '+15% freight', 'Critical → Medium for chip supply'. Use 'unchanged' if there's no meaningful change in that dimension.
- before / after snapshots must reference the SAME node names where possible so the UI can pair them. List ONLY the nodes the scenario actually changes (1-4 nodes), not the full analysis.
- after.affected_nodes[].delta_explanation should be 1 short sentence justifying the new risk level.
- narrative should be 2-3 sentences in plain language for an SME owner.

## OUTPUT FORMAT
You must respond with valid JSON matching this schema:

{
  "scenario_label": "Short label, e.g. 'Switch chip sourcing from Taiwan to South Korea'",
  "verdict": "improved | neutral | worsened",
  "narrative": "2-3 sentence prose explanation of the tradeoff",
  "tradeoffs": {
    "latency": "string under 12 words",
    "cost": "string under 12 words",
    "risk": "string under 12 words"
  },
  "before": {
    "overall_risk_level": "Low | Medium | High | Critical",
    "affected_nodes": [
      { "node": "Original node name", "risk_level": "Low | Medium | High | Critical" }
    ]
  },
  "after": {
    "overall_risk_level": "Low | Medium | High | Critical",
    "affected_nodes": [
      {
        "node": "Updated node name",
        "risk_level": "Low | Medium | High | Critical",
        "delta_explanation": "1 short sentence on why this changed"
      }
    ]
  }
}
"""


class LLMService:
    """
    High-level service consumed by the analysis router.
    Delegates all LLM calls to the LLM Router.
    """

    def __init__(self):
        self.router = llm_router

    def get_available_providers(self) -> List[str]:
        """Expose available providers for health / debug endpoints."""
        return self.router.get_available_providers()

    async def analyze_supply_chain(
        self,
        supply_chain_description: str,
        retrieved_context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        preferred_provider: Optional[str] = None,
        user_id: Optional[str] = None,
        local_focus: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze supply chain and return risk assessment dict.
        Returns the same shape as before so analysis.py doesn't break.
        """
        user_message = (
            f"## USER SUPPLY CHAIN DESCRIPTION:\n{supply_chain_description}\n\n"
            f"{retrieved_context}\n\n"
            "Please analyze this supply chain and provide a comprehensive "
            "risk assessment in the specified JSON format."
        )

        # Build system prompt — append local-focus addendum if enabled
        system_prompt = SYSTEM_PROMPT + (LOCAL_FOCUS_ADDENDUM if local_focus else "")

        messages: List[Dict[str, str]] = []

        # Carry forward conversation history (last 6 messages)
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})

        result = await self.router.generate(
            system_prompt=system_prompt,
            messages=messages,
            preferred_provider=preferred_provider,
            user_id=user_id
        )

        analysis = result["data"]
        # Attach metadata so the router/frontend can display provider info
        analysis["_meta"] = {
            "provider_used": result["provider_used"],
            "is_mock": result["is_mock"],
        }

        logger.info(
            f"Analysis complete — provider={result['provider_used']}, "
            f"mock={result['is_mock']}, "
            f"risks={len(analysis.get('risk_nodes', []))}"
        )
        return analysis

    async def handle_followup(
        self,
        question: str,
        previous_analysis: Dict[str, Any],
        retrieved_context: str,
        preferred_provider: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle follow-up questions about a previous analysis.
        """
        user_message = (
            f"## PREVIOUS ANALYSIS:\n{_safe_json(previous_analysis)}\n\n"
            f"## NEW CONTEXT:\n{retrieved_context}\n\n"
            f"## USER QUESTION:\n{question}\n\n"
            "Please respond in the specified JSON format."
        )

        messages = [{"role": "user", "content": user_message}]

        result = await self.router.generate(
            system_prompt=FOLLOWUP_SYSTEM_PROMPT,
            messages=messages,
            preferred_provider=preferred_provider,
            user_id=user_id
        )

        response = result["data"]

        # If mock provider was used and returned analysis format instead of
        # follow-up format, synthesize a basic follow-up response
        if result["is_mock"] and "message" not in response:
            response = _mock_followup(question)

        response["_meta"] = {
            "provider_used": result["provider_used"],
            "is_mock": result["is_mock"],
        }
        return response

    async def simulate_scenario(
        self,
        previous_analysis: Dict[str, Any],
        scenario_type: str,
        parameters: Dict[str, Any],
        preferred_provider: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Simulate a what-if scenario against an existing analysis and
        return a structured delta (verdict + before/after + tradeoffs).
        """
        # The "## SCENARIO SIMULATION" header doubles as a sentinel for
        # the mock provider so it knows to dispatch to scenario logic
        # instead of regular analysis.
        user_message = (
            "## SCENARIO SIMULATION\n"
            f"## SCENARIO_TYPE: {scenario_type}\n"
            f"## SCENARIO_PARAMETERS:\n{_safe_json(parameters)}\n\n"
            f"## PREVIOUS_ANALYSIS:\n{_safe_json(previous_analysis)}\n\n"
            "Produce the scenario delta in the specified JSON format."
        )

        messages = [{"role": "user", "content": user_message}]

        result = await self.router.generate(
            system_prompt=SCENARIO_SYSTEM_PROMPT,
            messages=messages,
            preferred_provider=preferred_provider,
            user_id=user_id,
        )

        scenario = result["data"]
        scenario["_meta"] = {
            "provider_used": result["provider_used"],
            "is_mock": result["is_mock"],
        }
        logger.info(
            f"Scenario complete — type={scenario_type}, "
            f"provider={result['provider_used']}, "
            f"verdict={scenario.get('verdict')}"
        )
        return scenario


def _safe_json(obj: Any) -> str:
    """JSON-serialize with a fallback to str()."""
    try:
        return json.dumps(obj, indent=2, default=str)
    except Exception:
        return str(obj)


def _mock_followup(question: str) -> Dict[str, Any]:
    """Keyword-based mock follow-up for demo mode (matches original behavior)."""
    q = question.lower()

    if "alternative" in q or "supplier" in q:
        return {
            "response_type": "alternatives",
            "message": "Based on your supply chain profile, here are alternative supplier options:",
            "suggestions": [
                {
                    "category": "Semiconductors",
                    "options": [
                        {"country": "South Korea", "companies": "Samsung, SK Hynix", "lead_time": "6-12 months"},
                        {"country": "Japan", "companies": "Renesas, Kioxia", "lead_time": "4-8 months"},
                    ],
                }
            ],
            "follow_up_suggestions": [
                "What are the cost implications of switching suppliers?",
                "How do I evaluate supplier reliability?",
                "What's the best transition strategy?",
            ],
        }

    if "route" in q or "shipping" in q:
        return {
            "response_type": "routes",
            "message": "Here are alternative shipping routes for your supply chain:",
            "suggestions": [
                {"route": "Cape of Good Hope", "transit_time": "40-45 days", "status": "Currently recommended due to Red Sea situation"},
                {"route": "Trans-Pacific + US Rail", "transit_time": "22-28 days", "status": "Good option for US East Coast"},
            ],
            "follow_up_suggestions": [
                "What's the cost impact of longer routes?",
                "How do I negotiate with freight forwarders?",
                "Should I consider air freight?",
            ],
        }

    return {
        "response_type": "general",
        "message": (
            f"Regarding your question about '{question}': Based on the current risk analysis, "
            "I recommend reviewing your supply chain dependencies and considering diversification "
            "strategies. Would you like specific recommendations for any particular aspect?"
        ),
        "follow_up_suggestions": [
            "Show me supplier alternatives",
            "Analyze shipping route options",
            "What are my biggest risks?",
        ],
    }


# Singleton — same interface the rest of the app expects
llm_service = LLMService()
