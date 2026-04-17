"""
Tests for SupplyChainIQ Multi-LLM Abstraction Layer (Sub-Task 1.1)
"""

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.services.llm_providers import (
    LLMProvider, BaseLLMProvider, ClaudeProvider, OpenAIProvider,
    GeminiProvider, MockProvider,
)
from backend.app.services.llm_router import LLMRouter
from backend.app.services.llm_service import LLMService


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


SAMPLE_SYSTEM = "You are a test assistant."
SAMPLE_MSGS = [{"role": "user", "content": "We source chips from Taiwan and ship via Singapore to the US."}]

VALID_JSON = json.dumps({
    "risk_nodes": [{"node": "Taiwan Supply", "risk_level": "High",
                    "cause": "Geopolitical tensions", "recommended_action": "Diversify",
                    "confidence_score": 0.85, "category": "geopolitical"}],
    "overall_risk_level": "High",
    "summary": "Significant geopolitical risk.",
    "follow_up_suggestions": ["What alternatives?"],
})


# === Provider Availability ===

class TestProviderAvailability:
    def test_mock_always_available(self):
        assert MockProvider().is_available() is True

    def test_claude_unavailable_without_key(self):
        os.environ["ANTHROPIC_API_KEY"] = ""
        assert ClaudeProvider().is_available() is False

    def test_claude_available_with_key(self):
        os.environ["ANTHROPIC_API_KEY"] = "sk-test"
        assert ClaudeProvider().is_available() is True
        os.environ["ANTHROPIC_API_KEY"] = ""

    def test_openai_unavailable_without_key(self):
        os.environ["OPENAI_API_KEY"] = ""
        assert OpenAIProvider().is_available() is False

    def test_gemini_unavailable_without_key(self):
        os.environ["GEMINI_API_KEY"] = ""
        assert GeminiProvider().is_available() is False


# === JSON Extraction ===

class TestJSONExtraction:
    def test_plain_json(self):
        result = BaseLLMProvider._extract_json(VALID_JSON)
        assert "risk_nodes" in result

    def test_json_with_markdown_fence(self):
        text = f"```json\n{VALID_JSON}\n```"
        result = BaseLLMProvider._extract_json(text)
        assert "risk_nodes" in result

    def test_json_with_preamble(self):
        text = f"Here is the analysis:\n\n{VALID_JSON}\n\nHope this helps!"
        result = BaseLLMProvider._extract_json(text)
        assert result["overall_risk_level"] == "High"

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON object found"):
            BaseLLMProvider._extract_json("Just plain text.")

    def test_invalid_json_raises(self):
        with pytest.raises((ValueError, json.JSONDecodeError)):
            BaseLLMProvider._extract_json("{broken: !!!}")


# === Mock Provider ===

class TestMockProvider:
    def test_taiwan_chips(self):
        result = run(MockProvider().generate(SAMPLE_SYSTEM, SAMPLE_MSGS))
        names = [n["node"] for n in result["risk_nodes"]]
        assert "Taiwan Semiconductor Supply" in names

    def test_singapore_detection(self):
        result = run(MockProvider().generate(SAMPLE_SYSTEM, SAMPLE_MSGS))
        names = [n["node"] for n in result["risk_nodes"]]
        assert "Singapore Transshipment Hub" in names

    def test_us_detection(self):
        result = run(MockProvider().generate(SAMPLE_SYSTEM, SAMPLE_MSGS))
        names = [n["node"] for n in result["risk_nodes"]]
        assert "US Destination Logistics" in names

    def test_generic_fallback(self):
        msgs = [{"role": "user", "content": "I have a supply chain."}]
        result = run(MockProvider().generate(SAMPLE_SYSTEM, msgs))
        assert result["risk_nodes"][0]["node"] == "General Supply Chain"

    def test_schema_complete(self):
        result = run(MockProvider().generate(SAMPLE_SYSTEM, SAMPLE_MSGS))
        for key in ["risk_nodes", "overall_risk_level", "summary", "follow_up_suggestions"]:
            assert key in result
        for node in result["risk_nodes"]:
            for k in ["node", "risk_level", "cause", "recommended_action", "confidence_score", "category"]:
                assert k in node

    def test_overall_matches_max(self):
        result = run(MockProvider().generate(SAMPLE_SYSTEM, SAMPLE_MSGS))
        levels = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
        max_l = max(levels[n["risk_level"]] for n in result["risk_nodes"])
        rev = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
        assert result["overall_risk_level"] == rev[max_l]

    def test_red_sea_critical(self):
        msgs = [{"role": "user", "content": "We ship through the Red Sea to Europe."}]
        result = run(MockProvider().generate(SAMPLE_SYSTEM, msgs))
        red_sea = [n for n in result["risk_nodes"] if n["node"] == "Red Sea Shipping Route"]
        assert len(red_sea) == 1
        assert red_sea[0]["risk_level"] == "Critical"


# === Router Fallback ===

class TestRouterFallback:
    def test_falls_back_to_mock(self):
        router = LLMRouter()
        result = run(router.generate(SAMPLE_SYSTEM, SAMPLE_MSGS))
        assert result["provider_used"] == "mock"
        assert result["is_mock"] is True
        assert "risk_nodes" in result["data"]

    def test_preferred_provider_first(self):
        router = LLMRouter()
        chain = router._build_chain("openai")
        assert chain[0] == LLMProvider.OPENAI
        assert chain[-1] == LLMProvider.MOCK

    def test_unknown_preferred_ignored(self):
        router = LLMRouter()
        chain = router._build_chain("nonexistent")
        assert chain[0] == LLMProvider.CLAUDE
        assert chain[-1] == LLMProvider.MOCK

    def test_mock_always_last(self):
        router = LLMRouter()
        for pref in [None, "claude", "openai", "gemini", "mock"]:
            chain = router._build_chain(pref)
            assert chain[-1] == LLMProvider.MOCK

    def test_errors_collected(self):
        router = LLMRouter()

        class FailProvider(BaseLLMProvider):
            provider_name = "fail"
            def is_available(self): return True
            async def _call_api(self, sp, msgs): raise RuntimeError("boom")

        router._providers[LLMProvider.CLAUDE] = FailProvider()
        result = run(router.generate(SAMPLE_SYSTEM, SAMPLE_MSGS))
        assert result["provider_used"] == "mock"
        errs = [e for e in result["errors"] if e["provider"] == "claude"]
        assert len(errs) == 1
        assert "boom" in errs[0]["error"]

    def test_uses_real_provider(self):
        router = LLMRouter()

        class FakeClaude(BaseLLMProvider):
            provider_name = "claude"
            def is_available(self): return True
            async def _call_api(self, sp, msgs): return VALID_JSON

        router._providers[LLMProvider.CLAUDE] = FakeClaude()
        result = run(router.generate(SAMPLE_SYSTEM, SAMPLE_MSGS))
        assert result["provider_used"] == "claude"
        assert result["is_mock"] is False

    def test_skips_bad_schema(self):
        router = LLMRouter()

        class BadSchema(BaseLLMProvider):
            provider_name = "claude"
            def is_available(self): return True
            async def _call_api(self, sp, msgs): return json.dumps({"bad": "data"})

        router._providers[LLMProvider.CLAUDE] = BadSchema()
        result = run(router.generate(SAMPLE_SYSTEM, SAMPLE_MSGS))
        assert result["provider_used"] == "mock"
        assert len(result["errors"]) >= 1


# === LLMService Backward Compat ===

class TestLLMServiceCompat:
    def test_analyze_returns_expected_keys(self):
        svc = LLMService()
        result = run(svc.analyze_supply_chain(
            supply_chain_description="Chips from Taiwan to the US.",
            retrieved_context="## CONTEXT\nNone.",
        ))
        for key in ["risk_nodes", "overall_risk_level", "summary", "follow_up_suggestions", "_meta"]:
            assert key in result
        assert result["_meta"]["provider_used"] == "mock"
        assert result["_meta"]["is_mock"] is True

    def test_followup_alternatives(self):
        svc = LLMService()
        result = run(svc.handle_followup(
            question="What alternative suppliers?",
            previous_analysis={}, retrieved_context="",
        ))
        assert result["response_type"] == "alternatives"
        assert "message" in result

    def test_followup_routes(self):
        svc = LLMService()
        result = run(svc.handle_followup(
            question="What shipping routes?",
            previous_analysis={}, retrieved_context="",
        ))
        assert result["response_type"] == "routes"

    def test_followup_generic(self):
        svc = LLMService()
        result = run(svc.handle_followup(
            question="Tell me more",
            previous_analysis={}, retrieved_context="",
        ))
        assert result["response_type"] == "general"

    def test_get_available_providers(self):
        svc = LLMService()
        providers = svc.get_available_providers()
        assert "mock" in providers
        assert isinstance(providers, list)


# === Enum ===

class TestLLMProviderEnum:
    def test_values(self):
        assert LLMProvider.CLAUDE.value == "claude"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.GEMINI.value == "gemini"
        assert LLMProvider.MOCK.value == "mock"

    def test_from_string(self):
        assert LLMProvider("claude") == LLMProvider.CLAUDE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
