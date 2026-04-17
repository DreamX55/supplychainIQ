"""
LLM Router for SupplyChainIQ
Manages provider selection, fallback chains, and response normalization.

Priority chain per request:
  1. User's vault key for preferred provider (if stored)
  2. User's vault keys for other providers
  3. Env-configured providers (global fallback)
  4. Mock (always succeeds)

Fallback on failure: next provider in chain → mock
"""

import os
import logging
from typing import Dict, Any, List, Optional

from .llm_providers import (
    LLMProvider,
    BaseLLMProvider,
    ClaudeProvider,
    OpenAIProvider,
    GeminiProvider,
    GroqProvider,
    MockProvider,
)

logger = logging.getLogger("supplychainiq.router")

# Map provider enum → env var name for that provider's API key
_PROVIDER_ENV_MAP: Dict[LLMProvider, str] = {
    LLMProvider.GROQ: "GROQ_API_KEY",
    LLMProvider.CLAUDE: "ANTHROPIC_API_KEY",
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.GEMINI: "GEMINI_API_KEY",
}


def _make_provider_with_key(provider_enum: LLMProvider, api_key: str) -> BaseLLMProvider:
    """
    Create a fresh provider instance with an explicit API key override.
    Used when a user has stored a key in the vault.
    """
    if provider_enum == LLMProvider.GROQ:
        p = GroqProvider()
        p.api_key = api_key
        return p
    elif provider_enum == LLMProvider.CLAUDE:
        p = ClaudeProvider()
        p.api_key = api_key
        return p
    elif provider_enum == LLMProvider.OPENAI:
        p = OpenAIProvider()
        p.api_key = api_key
        return p
    elif provider_enum == LLMProvider.GEMINI:
        p = GeminiProvider()
        p.api_key = api_key
        return p
    else:
        return MockProvider()


class LLMRouter:
    """
    Routes LLM requests through a prioritized fallback chain.

    Usage:
        router = LLMRouter()
        result = await router.generate(system_prompt, messages, user_id="user-123")
    """

    def __init__(self):
        # Default provider instances (use env-var keys)
        self._providers: Dict[LLMProvider, BaseLLMProvider] = {
            LLMProvider.GROQ: GroqProvider(),
            LLMProvider.CLAUDE: ClaudeProvider(),
            LLMProvider.OPENAI: OpenAIProvider(),
            LLMProvider.GEMINI: GeminiProvider(),
            LLMProvider.MOCK: MockProvider(),
        }

        # Groq is the primary live provider for the hackathon demo —
        # fast, cheap, JSON-mode capable. Others remain as fallbacks.
        self._default_priority = [
            LLMProvider.GROQ,
            LLMProvider.CLAUDE,
            LLMProvider.OPENAI,
            LLMProvider.GEMINI,
            LLMProvider.MOCK,
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_available_providers(self, user_id: Optional[str] = None) -> List[str]:
        """
        Return names of providers that have valid API keys,
        including user-specific vault keys.
        """
        available = set()

        # Env-level providers
        for p in self._default_priority:
            if self._providers[p].is_available():
                available.add(p.value)

        # User vault keys
        if user_id:
            try:
                from .key_vault import key_vault
                for prov_name in key_vault.list_providers(user_id):
                    available.add(prov_name)
            except Exception:
                pass

        # Maintain priority ordering
        return [
            p.value for p in self._default_priority
            if p.value in available
        ]

    async def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        preferred_provider: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response using the best available provider.

        Args:
            system_prompt: System instructions for the LLM.
            messages: Conversation messages (role + content dicts).
            preferred_provider: Optional provider name to try first.
            user_id: If provided, check vault for user-specific API keys.

        Returns:
            {
                "data": <parsed analysis dict>,
                "provider_used": "claude" | "openai" | "gemini" | "mock",
                "is_mock": bool,
                "errors": [<provider errors encountered>]
            }
        """
        chain = self._build_chain(preferred_provider)
        errors: List[Dict[str, str]] = []

        # Build a map of user-specific provider overrides from the vault
        user_providers = self._load_user_providers(user_id) if user_id else {}

        for provider_enum in chain:
            # Prefer user's vault key over env-level provider
            if provider_enum in user_providers:
                provider = user_providers[provider_enum]
            else:
                provider = self._providers[provider_enum]

            if not provider.is_available():
                continue

            try:
                logger.info(f"Trying provider: {provider_enum.value}")
                data = await provider.generate(system_prompt, messages)

                # Validate minimum schema: accept any of the three known
                # response shapes — analysis (risk_nodes), followup (message),
                # or scenario (verdict). Reject anything else as a parse failure.
                if not isinstance(data, dict) or not (
                    "risk_nodes" in data or "message" in data or "verdict" in data
                ):
                    raise ValueError(
                        f"Provider {provider_enum.value} returned an unrecognized response shape"
                    )

                return {
                    "data": data,
                    "provider_used": provider_enum.value,
                    "is_mock": provider_enum == LLMProvider.MOCK,
                    "errors": errors,
                }

            except Exception as exc:
                err_msg = f"{provider_enum.value}: {type(exc).__name__}: {exc}"
                logger.warning(f"Provider failed — {err_msg}")
                errors.append({"provider": provider_enum.value, "error": str(exc)})
                continue

        # Defensive fallback — mock always succeeds
        logger.error("All providers failed including mock — returning empty result")
        return {
            "data": MockProvider._build_mock_analysis(""),
            "provider_used": "mock",
            "is_mock": True,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_user_providers(
        self, user_id: str
    ) -> Dict[LLMProvider, BaseLLMProvider]:
        """
        Load user-specific provider instances from the vault.
        Returns a dict of provider_enum → provider_instance for
        any providers the user has stored keys for.
        """
        overrides: Dict[LLMProvider, BaseLLMProvider] = {}
        try:
            from .key_vault import key_vault
            for prov_name in key_vault.list_providers(user_id):
                try:
                    prov_enum = LLMProvider(prov_name)
                except ValueError:
                    continue
                api_key = key_vault.get_key(user_id, prov_name)
                if api_key:
                    overrides[prov_enum] = _make_provider_with_key(prov_enum, api_key)
        except Exception as exc:
            logger.warning(f"Failed to load vault keys for user={user_id}: {exc}")
        return overrides

    def _build_chain(self, preferred: Optional[str]) -> List[LLMProvider]:
        """
        Build the ordered fallback chain.
        If a preferred provider is specified, it goes first.
        Mock is always last.
        """
        chain = list(self._default_priority)

        if preferred:
            try:
                pref_enum = LLMProvider(preferred.lower())
                # Move preferred to front
                if pref_enum in chain:
                    chain.remove(pref_enum)
                chain.insert(0, pref_enum)
            except ValueError:
                logger.warning(f"Unknown preferred provider: {preferred}")

        # Ensure mock is always last (safety net)
        if LLMProvider.MOCK in chain:
            chain.remove(LLMProvider.MOCK)
        chain.append(LLMProvider.MOCK)

        return chain


# Singleton
llm_router = LLMRouter()
