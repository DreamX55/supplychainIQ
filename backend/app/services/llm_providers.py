"""
LLM Provider Abstraction Layer for SupplyChainIQ
Supports Claude, OpenAI, Gemini, and Mock providers with unified interface.

Each provider normalizes its response into a standard dict matching the
RiskAnalysisResponse schema so the router doesn't care which LLM answered.
"""

import os
import re
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum

import httpx

logger = logging.getLogger("supplychainiq.llm")


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    GROQ = "groq"
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    MOCK = "mock"


class BaseLLMProvider(ABC):
    """
    Abstract base for all LLM providers.
    Subclasses implement _call_api(); the base handles JSON extraction
    and response normalization.
    """

    provider_name: str = "base"

    @abstractmethod
    async def _call_api(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        """
        Send messages to the provider and return the raw text response.
        Raises on failure — the router handles fallback.
        """
        ...

    def is_available(self) -> bool:
        """Check whether this provider has a valid API key configured."""
        return True

    async def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Call the provider and parse its JSON response.
        Returns the parsed dict or raises ValueError on parse failure.
        """
        raw = await self._call_api(system_prompt, messages)
        return self._extract_json(raw)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """
        Extract the first JSON object from a text blob.
        LLMs sometimes wrap JSON in markdown fences — we handle that.
        """
        # Strip markdown fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Find the outermost { ... }
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end <= start:
            raise ValueError(f"No JSON object found in LLM response (length={len(text)})")

        return json.loads(cleaned[start:end])


# ======================================================================
# Claude (Anthropic) Provider
# ======================================================================

class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider via Messages API"""

    provider_name = "claude"

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.max_tokens = 4096

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def _call_api(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "system": system_prompt,
                    "messages": messages,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]


# ======================================================================
# OpenAI Provider
# ======================================================================

class OpenAIProvider(BaseLLMProvider):
    """OpenAI ChatCompletion provider (GPT-4o / GPT-4-turbo)"""

    provider_name = "openai"

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.max_tokens = 4096

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def _call_api(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        # OpenAI expects system as a message, not a separate param
        oai_messages = [{"role": "system", "content": system_prompt}]
        oai_messages.extend(messages)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "messages": oai_messages,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


# ======================================================================
# Groq Provider — fast OSS-model inference, OpenAI-compatible API
# ======================================================================

class GroqProvider(BaseLLMProvider):
    """
    Groq provider — uses an OpenAI-compatible chat/completions endpoint.
    Default model is llama-3.3-70b-versatile (fast, cheap, JSON-capable).
    Primary live provider for the hackathon demo.
    """

    provider_name = "groq"

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.max_tokens = 4096

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def _call_api(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        groq_messages = [{"role": "system", "content": system_prompt}]
        groq_messages.extend(messages)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "messages": groq_messages,
                    "temperature": 0.3,
                    # Force JSON output — Groq supports OpenAI's response_format
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


# ======================================================================
# Gemini (Google) Provider — Free Tier
# ======================================================================

class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider via generateContent REST API (free tier)"""

    provider_name = "gemini"

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def _call_api(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        # Gemini REST: system instruction + contents
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

        # Map messages to Gemini format (role: user/model)
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload: Dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4096,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        url,
                        headers={"Content-Type": "application/json"},
                        json=payload,
                    )
                    if resp.status_code == 429:
                        logger.warning(f"Gemini API Rate Limited (429). Attempt {attempt + 1}. Retrying in {2 ** attempt}s...")
                        await asyncio.sleep(2 ** attempt)
                        continue
                        
                    resp.raise_for_status()
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise e
        return "" # Should not reach here if raise_for_status is used correctly


# ======================================================================
# Mock Provider — deterministic, zero-cost, always available
# ======================================================================

class MockProvider(BaseLLMProvider):
    """
    Hardcoded mock provider for demo / no-API-key scenarios.
    Mirrors the original _generate_mock_response logic from llm_service.py.
    """

    provider_name = "mock"

    def is_available(self) -> bool:
        return True  # always available as fallback

    async def _call_api(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        # Not used — generate() is overridden
        raise NotImplementedError

    async def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Override generate() directly since we don't need to call an API.
        Dispatches to scenario / followup / analysis builders based on
        sentinel markers in the user message.
        """
        # Find the last user message
        user_text = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_text = msg["content"]
                break

        if "## SCENARIO SIMULATION" in user_text:
            return MockProvider._build_mock_scenario(user_text)

        # IMPORTANT: only run keyword matching against the user's actual
        # description, not the full assembled message. Otherwise RAG context
        # tokens like "Red Sea" or "Eastern European" leak into the matcher
        # and produce spurious risks.
        clean_desc = MockProvider._extract_user_description(user_text)
        return self._build_mock_analysis(clean_desc)

    @staticmethod
    def _extract_user_description(user_text: str) -> str:
        """
        Pull just the user's supply-chain description out of the assembled
        message that llm_service builds. Falls back to the full text if no
        sentinel header is present (preserves direct-call backward compat).
        """
        if not user_text:
            return ""
        marker = "## USER SUPPLY CHAIN DESCRIPTION:"
        idx = user_text.find(marker)
        if idx < 0:
            return user_text
        body = user_text[idx + len(marker):]
        # Stop at the next ## header (e.g. "## RETRIEVED RISK INTELLIGENCE")
        next_header = body.find("\n##")
        if next_header >= 0:
            body = body[:next_header]
        return body.strip()

    @staticmethod
    def _build_mock_scenario(user_text: str) -> Dict[str, Any]:
        """
        Deterministic scenario delta for demo mode. Parses the scenario
        type and parameters out of the marker block and returns a
        coherent before/after story for known patterns.
        """
        import re

        type_match = re.search(r"## SCENARIO_TYPE:\s*(\S+)", user_text)
        scenario_type = (type_match.group(1) if type_match else "").strip().lower()

        # Extract parameters JSON block (best-effort)
        params: Dict[str, Any] = {}
        try:
            params_match = re.search(
                r"## SCENARIO_PARAMETERS:\s*(\{.*?\})\s*\n\s*## ",
                user_text,
                re.DOTALL,
            )
            if params_match:
                params = json.loads(params_match.group(1))
        except Exception:
            params = {}

        text_lower = user_text.lower()

        # ----- supplier_switch -----
        if scenario_type == "supplier_switch":
            from_node = str(params.get("from_node") or params.get("from") or "current supplier")
            to_country = str(params.get("to_country") or params.get("to") or "alternative country")
            return {
                "scenario_label": f"Switch sourcing from {from_node} to {to_country}",
                "verdict": "improved",
                "narrative": (
                    f"Switching {from_node} sourcing to {to_country} reduces single-source "
                    "geopolitical exposure. Expect a 6-8 week qualification cycle and modest "
                    "cost premium, offset by significantly lower disruption risk."
                ),
                "tradeoffs": {
                    "latency": "+5 to 10 days lead time",
                    "cost": "+10-15% unit cost",
                    "risk": "Critical → Medium for affected node",
                },
                "before": {
                    "overall_risk_level": "High",
                    "affected_nodes": [
                        {"node": from_node, "risk_level": "Critical"},
                    ],
                },
                "after": {
                    "overall_risk_level": "Medium",
                    "affected_nodes": [
                        {
                            "node": f"{to_country} ({from_node.split()[0] if from_node else 'alt'})",
                            "risk_level": "Medium",
                            "delta_explanation": (
                                "Lower geopolitical exposure but 6-8 week supplier qualification required."
                            ),
                        },
                    ],
                },
            }

        # ----- route_change -----
        if scenario_type == "route_change":
            from_route = str(params.get("from_route") or params.get("from") or "current route")
            to_route = str(params.get("to_route") or params.get("to") or "alternative route")
            return {
                "scenario_label": f"Reroute from {from_route} to {to_route}",
                "verdict": "neutral",
                "narrative": (
                    f"Switching from {from_route} to {to_route} sidesteps the active disruption "
                    "but adds significant transit time and freight cost. Recommended only for "
                    "shipments where in-transit risk outweighs the delay."
                ),
                "tradeoffs": {
                    "latency": "+10 to 14 days transit",
                    "cost": "+150-250% freight",
                    "risk": "Critical → Low for in-transit risk",
                },
                "before": {
                    "overall_risk_level": "Critical",
                    "affected_nodes": [
                        {"node": f"{from_route} Shipping", "risk_level": "Critical"},
                    ],
                },
                "after": {
                    "overall_risk_level": "Medium",
                    "affected_nodes": [
                        {
                            "node": f"{to_route} Shipping",
                            "risk_level": "Low",
                            "delta_explanation": (
                                "Avoids active threat zone, but freight cost and transit time spike."
                            ),
                        },
                    ],
                },
            }

        # ----- inventory_buffer -----
        if scenario_type == "inventory_buffer":
            try:
                days = int(params.get("buffer_days") or params.get("days") or 30)
            except Exception:
                days = 30
            return {
                "scenario_label": f"Add {days}-day inventory buffer for critical inputs",
                "verdict": "improved",
                "narrative": (
                    f"Holding an additional {days} days of safety stock for the most exposed "
                    "inputs absorbs short-term disruptions without changing your sourcing or "
                    "routing strategy. Working capital and warehousing cost rise modestly."
                ),
                "tradeoffs": {
                    "latency": "Unchanged",
                    "cost": f"+{max(2, days // 6)}% working capital",
                    "risk": "High → Medium for buffered inputs",
                },
                "before": {
                    "overall_risk_level": "High",
                    "affected_nodes": [
                        {"node": "Critical Input Supply", "risk_level": "High"},
                    ],
                },
                "after": {
                    "overall_risk_level": "Medium",
                    "affected_nodes": [
                        {
                            "node": "Critical Input Supply",
                            "risk_level": "Medium",
                            "delta_explanation": (
                                f"{days}-day buffer absorbs typical disruption windows without "
                                "supplier changes."
                            ),
                        },
                    ],
                },
            }

        # ----- generic fallback -----
        return {
            "scenario_label": "Generic scenario simulation",
            "verdict": "neutral",
            "narrative": (
                "This scenario shifts your risk profile in a specific direction. "
                "Without more parameter detail, the system can't quantify the tradeoff "
                "precisely — try a more specific supplier switch, route change, or buffer."
            ),
            "tradeoffs": {
                "latency": "Unchanged",
                "cost": "Unchanged",
                "risk": "Unchanged",
            },
            "before": {
                "overall_risk_level": "Medium",
                "affected_nodes": [],
            },
            "after": {
                "overall_risk_level": "Medium",
                "affected_nodes": [],
            },
        }

    # ==================================================================
    # Declarative mock patterns — single source of truth for both the
    # analysis builder and the graph builder. Adding a new country or
    # corridor is a one-entry append.
    #
    # Each entry may specify:
    #   id           — unique slug (required)
    #   keywords     — list of lowercase substrings, OR
    #   regex        — a raw regex pattern string (used for word-bounded
    #                  matches like 'us' that would otherwise be too loose)
    #   require_any  — optional extra list of substrings, AT LEAST ONE
    #                  of which must ALSO be present (used for
    #                  "Taiwan AND (chip|semiconductor)" style gating)
    #   risk         — optional risk-node dict contributed to the brief
    #   graph_node   — optional graph-node dict contributed to the chain
    # ==================================================================
    _MOCK_PATTERNS: List[Dict[str, Any]] = [
        # --- Suppliers ---------------------------------------------------
        {
            "id": "taiwan_semis",
            "keywords": ["taiwan"],
            "require_any": ["chip", "semiconductor"],
            "risk": {
                "node": "Taiwan Semiconductor Supply",
                "risk_level": "High",
                "cause": "Geopolitical tensions in Taiwan Strait region affecting semiconductor exports. Military exercises and diplomatic disputes create supply uncertainty.",
                "evidence": [
                    "Taiwan produces ~60% of global semiconductors and 90% of advanced chips",
                    "PLA naval exercises near Taiwan Strait increased 35% YoY",
                    "TSMC export licensing under review by multiple jurisdictions",
                ],
                "recommended_action": "Diversify semiconductor sourcing to South Korea (Samsung, SK Hynix) or Japan (Renesas, Kioxia). Consider building 6-month safety stock for critical components.",
                "confidence_score": 0.89,
                "category": "geopolitical",
            },
            "graph_node": {"id": "taiwan_semis", "label": "Taiwan Semiconductors", "role": "supplier", "location": "Taiwan"},
        },
        {
            "id": "china_components",
            "keywords": ["china"],
            "graph_node": {"id": "china_components", "label": "China Components", "role": "supplier", "location": "China"},
        },
        {
            "id": "bangladesh_textiles",
            "keywords": ["bangladesh"],
            "graph_node": {"id": "bangladesh_textiles", "label": "Bangladesh Textiles", "role": "supplier", "location": "Bangladesh"},
        },
        {
            "id": "india_inputs",
            "keywords": ["india"],
            "graph_node": {"id": "india_inputs", "label": "India Inputs", "role": "supplier", "location": "India"},
        },

        # --- Factories / assembly ---------------------------------------
        {
            "id": "vietnam",
            "keywords": ["vietnam"],
            "risk": {
                "node": "Vietnam Manufacturing Hub",
                "risk_level": "Medium",
                "cause": "Monsoon season (June-September) creates flooding risks. Power grid reliability improving but occasional disruptions occur.",
                "evidence": [
                    "Northern Vietnam monsoon season runs June through September",
                    "2023 EVN power rationing affected industrial parks for 2-3 weeks",
                    "Hai Phong port saw 12-day delays during 2024 typhoon season",
                ],
                "recommended_action": "Establish backup assembly capacity in Thailand or Malaysia. Ensure suppliers have flood mitigation measures in place.",
                "confidence_score": 0.82,
                "category": "climate",
            },
            "graph_node": {"id": "vietnam_assembly", "label": "Vietnam Assembly", "role": "factory", "location": "Vietnam"},
        },
        {
            "id": "thailand",
            "keywords": ["thailand"],
            "graph_node": {"id": "thailand_assembly", "label": "Thailand Assembly", "role": "factory", "location": "Thailand"},
        },
        {
            "id": "malaysia",
            "keywords": ["malaysia"],
            "graph_node": {"id": "malaysia_assembly", "label": "Malaysia Assembly", "role": "factory", "location": "Malaysia"},
        },
        {
            "id": "mexico",
            "keywords": ["mexico"],
            "graph_node": {"id": "mexico_assembly", "label": "Mexico Assembly", "role": "factory", "location": "Mexico"},
        },

        # --- Ports / transit --------------------------------------------
        {
            "id": "singapore",
            "keywords": ["singapore"],
            "risk": {
                "node": "Singapore Transshipment Hub",
                "risk_level": "Medium",
                "cause": "Red Sea crisis has increased vessel diversions to Singapore, causing container dwell times to increase by 40%. Transshipment delays of 3-5 days reported.",
                "evidence": [
                    "Container dwell times up ~40% vs 2023 baseline",
                    "Average transshipment delay: 3-5 days reported by MPA",
                    "Port Klang and Tanjung Pelepas absorbing overflow traffic",
                ],
                "recommended_action": "Consider direct shipping routes where possible. Build buffer time into delivery schedules. Evaluate Port Klang (Malaysia) as alternative.",
                "confidence_score": 0.88,
                "category": "logistics",
            },
            "graph_node": {"id": "singapore_port", "label": "Singapore Hub", "role": "port", "location": "Singapore"},
        },
        {
            "id": "suez_corridor",
            "keywords": ["red sea", "suez"],
            # Risk lives on the dedicated red_sea_europe pattern below;
            # this entry just contributes the graph node.
            "graph_node": {"id": "suez_corridor", "label": "Suez / Red Sea Corridor", "role": "port", "location": "Red Sea"},
        },
        {
            "id": "panama",
            "keywords": ["panama"],
            "graph_node": {"id": "panama_corridor", "label": "Panama Canal", "role": "port", "location": "Panama"},
        },

        # --- Destinations ------------------------------------------------
        {
            "id": "us_market",
            # Word-bounded so "consumer" / "discuss" don't falsely trigger.
            "regex": r"\b(us|usa|united states|america)\b",
            "risk": {
                "node": "US Destination Logistics",
                "risk_level": "Low",
                "cause": "US West Coast ports operating normally. Labor agreements in place through 2028. Average container dwell time at 2.5 days.",
                "evidence": [
                    "ILWU-PMA contract ratified, valid through 2028",
                    "LA/Long Beach average dwell time: 2.5 days",
                    "Prince Rupert (Canada) viable contingency for fast clearance",
                ],
                "recommended_action": "Maintain current routing. Consider Prince Rupert (Canada) as contingency for faster clearance if congestion increases.",
                "confidence_score": 0.91,
                "category": "logistics",
            },
            "graph_node": {"id": "us_market", "label": "US Market", "role": "destination", "location": "United States"},
        },
        {
            "id": "eu_market",
            "keywords": ["europe", "germany", "european"],
            "graph_node": {"id": "eu_market", "label": "European Market", "role": "destination", "location": "Europe"},
        },

        # --- Route-wide risk (no graph node — covered by suez_corridor) ---
        {
            "id": "red_sea_route",
            "keywords": ["europe", "red sea", "suez"],
            "risk": {
                "node": "Red Sea Shipping Route",
                "risk_level": "Critical",
                "cause": "Houthi attacks on commercial vessels have forced major shipping lines to reroute around Cape of Good Hope, adding 10-14 days transit time and 200-300% higher freight costs.",
                "evidence": [
                    "Maersk, MSC, CMA CGM all rerouting via Cape of Good Hope",
                    "Asia-Europe transit time: +10 to +14 days vs Suez",
                    "Spot freight rates up 200-300% on Asia-Europe lane",
                ],
                "recommended_action": "Immediate: Reroute via Cape of Good Hope. Medium-term: Evaluate air freight for high-value cargo. Consider nearshoring to Poland for European market.",
                "confidence_score": 0.95,
                "category": "geopolitical",
            },
        },
    ]

    _GENERIC_RISK: Dict[str, Any] = {
        "node": "General Supply Chain",
        "risk_level": "Medium",
        "cause": "Global supply chain volatility remains elevated due to ongoing geopolitical tensions, climate events, and logistics disruptions.",
        "evidence": [
            "Global Supply Chain Pressure Index remains above 2019 baseline",
            "Average lead times still 25% longer than pre-2020 levels",
            "Insurance premiums for ocean freight elevated across major lanes",
        ],
        "recommended_action": "Conduct detailed supply chain mapping. Identify single-source dependencies. Build strategic inventory buffers for critical materials.",
        "confidence_score": 0.75,
        "category": "supplier",
    }

    _GENERIC_GRAPH_NODES: List[Dict[str, Any]] = [
        {"id": "generic_supplier", "label": "Primary Supplier", "role": "supplier", "location": "Origin"},
        {"id": "generic_factory", "label": "Assembly Plant", "role": "factory", "location": "Region"},
        {"id": "generic_port", "label": "Transit Hub", "role": "port", "location": "Port"},
        {"id": "generic_dest", "label": "Target Market", "role": "destination", "location": "Destination"},
    ]

    @staticmethod
    def _pattern_matches(pattern: Dict[str, Any], desc: str) -> bool:
        """Return True if a mock pattern fires against the lowercased desc."""
        if "regex" in pattern:
            if not re.search(pattern["regex"], desc):
                return False
        elif "keywords" in pattern:
            if not any(k in desc for k in pattern["keywords"]):
                return False
        else:
            return False
        require_any = pattern.get("require_any")
        if require_any and not any(k in desc for k in require_any):
            return False
        return True

    @staticmethod
    def _build_mock_analysis(text: str) -> Dict[str, Any]:
        """Keyword-driven mock response using the shared _MOCK_PATTERNS table."""
        desc = text.lower()

        risk_nodes: List[Dict[str, Any]] = []
        for p in MockProvider._MOCK_PATTERNS:
            if MockProvider._pattern_matches(p, desc) and p.get("risk"):
                risk_nodes.append(p["risk"])

        if not risk_nodes:
            risk_nodes.append(MockProvider._GENERIC_RISK)

        # Determine overall risk
        level_map = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
        max_risk = max(level_map.get(r["risk_level"], 2) for r in risk_nodes)
        overall_map = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}

        high_risks = [r for r in risk_nodes if r["risk_level"] in ("High", "Critical")]
        if high_risks:
            summary = (
                f"Your supply chain faces {len(high_risks)} significant risk(s). "
                f"The most critical is {high_risks[0]['node']} due to "
                f"{high_risks[0]['cause'].split('.')[0]}. "
                "Immediate action recommended to mitigate potential disruptions."
            )
        else:
            summary = (
                "Your supply chain shows moderate risk levels. "
                "No critical threats detected, but ongoing monitoring and contingency planning advised. "
                "Consider diversifying suppliers to build additional resilience."
            )

        return {
            "risk_nodes": risk_nodes,
            "overall_risk_level": overall_map[max_risk],
            "summary": summary,
            "supply_chain_graph": MockProvider._build_mock_graph(desc),
            "follow_up_suggestions": [
                "What alternative suppliers should I consider?",
                "How can I reduce single-source dependencies?",
                "What contingency routes are available?",
            ],
        }

    @staticmethod
    def _build_mock_graph(desc: str) -> Dict[str, Any]:
        """
        Build a deterministic supply chain graph from the lowercased
        description using the shared _MOCK_PATTERNS table. Each pattern
        that fires may contribute a graph node; patterns without a
        graph_node contribute nothing here.
        """
        nodes: List[Dict[str, Any]] = []
        seen = set()

        for p in MockProvider._MOCK_PATTERNS:
            if not MockProvider._pattern_matches(p, desc):
                continue
            gn = p.get("graph_node")
            if not gn or gn["id"] in seen:
                continue
            seen.add(gn["id"])
            nodes.append(dict(gn))  # defensive copy so downstream mutation is safe

        # Fallback: a generic 4-node chain so the graph always has something
        if not nodes:
            nodes = [dict(n) for n in MockProvider._GENERIC_GRAPH_NODES]

        # Build edges by connecting consecutive role columns (any-to-any)
        role_order = ["supplier", "factory", "port", "destination"]
        by_role: Dict[str, List[str]] = {r: [] for r in role_order}
        for n in nodes:
            by_role.setdefault(n["role"], []).append(n["id"])

        edges: List[Dict[str, Any]] = []
        active_roles = [r for r in role_order if by_role.get(r)]
        for a, b in zip(active_roles, active_roles[1:]):
            for s in by_role[a]:
                for t in by_role[b]:
                    edges.append({"from": s, "to": t})

        return {"nodes": nodes, "edges": edges}
