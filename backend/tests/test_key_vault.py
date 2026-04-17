"""
Tests for SupplyChainIQ Secure API Key Vault (Sub-Task 1.2)

Covers:
  - Encryption/decryption round-trip
  - Per-user key isolation
  - CRUD operations (store, get, delete, list)
  - Key masking
  - Provider validation
  - Key overwrite (upsert) behavior
  - Vault integration with LLM router
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.services.key_vault import KeyVault


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def vault(tmp_path):
    """Create a fresh vault with a temp database for each test."""
    db = tmp_path / "test_vault.db"
    return KeyVault(db_path=db)


# === Encryption Round-Trip ===

class TestEncryptionRoundTrip:
    def test_store_and_retrieve(self, vault):
        vault.store_key("user1", "claude", "sk-ant-test-key-12345678")
        result = vault.get_key("user1", "claude")
        assert result == "sk-ant-test-key-12345678"

    def test_different_providers(self, vault):
        vault.store_key("user1", "claude", "sk-ant-xxx")
        vault.store_key("user1", "openai", "sk-openai-yyy")
        vault.store_key("user1", "gemini", "AIza-gemini-zzz")

        assert vault.get_key("user1", "claude") == "sk-ant-xxx"
        assert vault.get_key("user1", "openai") == "sk-openai-yyy"
        assert vault.get_key("user1", "gemini") == "AIza-gemini-zzz"

    def test_long_key(self, vault):
        long_key = "sk-" + "a" * 200
        vault.store_key("user1", "claude", long_key)
        assert vault.get_key("user1", "claude") == long_key


# === Per-User Isolation ===

class TestUserIsolation:
    def test_users_dont_see_each_others_keys(self, vault):
        vault.store_key("alice", "claude", "alice-key-12345678")
        vault.store_key("bob", "claude", "bob-key-87654321")

        assert vault.get_key("alice", "claude") == "alice-key-12345678"
        assert vault.get_key("bob", "claude") == "bob-key-87654321"

    def test_nonexistent_user_returns_none(self, vault):
        assert vault.get_key("ghost", "claude") is None

    def test_delete_one_user_doesnt_affect_other(self, vault):
        vault.store_key("alice", "claude", "alice-key-12345678")
        vault.store_key("bob", "claude", "bob-key-87654321")

        vault.delete_key("alice", "claude")
        assert vault.get_key("alice", "claude") is None
        assert vault.get_key("bob", "claude") == "bob-key-87654321"


# === CRUD Operations ===

class TestCRUD:
    def test_store_overwrites(self, vault):
        vault.store_key("user1", "claude", "old-key-12345678")
        vault.store_key("user1", "claude", "new-key-87654321")
        assert vault.get_key("user1", "claude") == "new-key-87654321"

    def test_get_nonexistent_returns_none(self, vault):
        assert vault.get_key("user1", "openai") is None

    def test_delete_returns_true(self, vault):
        vault.store_key("user1", "claude", "key-12345678")
        assert vault.delete_key("user1", "claude") is True

    def test_delete_nonexistent_returns_false(self, vault):
        assert vault.delete_key("user1", "claude") is False

    def test_delete_all(self, vault):
        vault.store_key("user1", "claude", "key1-12345678")
        vault.store_key("user1", "openai", "key2-12345678")
        vault.store_key("user1", "gemini", "key3-12345678")

        count = vault.delete_all_keys("user1")
        assert count == 3
        assert vault.list_providers("user1") == []

    def test_list_providers(self, vault):
        vault.store_key("user1", "claude", "key-12345678")
        vault.store_key("user1", "gemini", "key-87654321")

        providers = vault.list_providers("user1")
        assert providers == ["claude", "gemini"]  # alphabetical

    def test_list_empty(self, vault):
        assert vault.list_providers("nobody") == []


# === Key Info & Masking ===

class TestKeyInfo:
    def test_info_returns_masked_key(self, vault):
        vault.store_key("user1", "claude", "sk-ant-api-key-very-long-value")
        info = vault.get_key_info("user1", "claude")

        assert info is not None
        assert info["provider"] == "claude"
        assert "sk-ant-a" in info["key_preview"]  # first 8 chars
        assert "alue" in info["key_preview"]       # last 4 chars
        assert "***" in info["key_preview"]         # masked middle
        assert "created_at" in info
        assert "updated_at" in info

    def test_info_nonexistent_returns_none(self, vault):
        assert vault.get_key_info("user1", "openai") is None

    def test_mask_short_key(self, vault):
        # Short key (<=12 chars) gets simple mask
        masked = vault._mask_key("short123")
        assert masked == "shor***"

    def test_mask_long_key(self, vault):
        masked = vault._mask_key("sk-ant-api-key-12345678")
        assert masked.startswith("sk-ant-a")
        assert masked.endswith("5678")
        assert "***..." in masked


# === Validation ===

class TestValidation:
    def test_invalid_provider_raises(self, vault):
        with pytest.raises(ValueError, match="Unknown provider"):
            vault.store_key("user1", "grok", "key-12345678")

    def test_empty_key_raises(self, vault):
        with pytest.raises(ValueError, match="at least 8"):
            vault.store_key("user1", "claude", "")

    def test_short_key_raises(self, vault):
        with pytest.raises(ValueError, match="at least 8"):
            vault.store_key("user1", "claude", "short")

    def test_provider_case_insensitive(self, vault):
        vault.store_key("user1", "CLAUDE", "key-12345678")
        assert vault.get_key("user1", "claude") == "key-12345678"

    def test_provider_whitespace_trimmed(self, vault):
        vault.store_key("user1", "  openai  ", "key-12345678")
        assert vault.get_key("user1", "openai") == "key-12345678"


# === Router Integration ===

class TestRouterIntegration:
    def test_router_uses_vault_key(self, vault):
        """Verify the router can load user keys from the vault."""
        from backend.app.services.llm_router import LLMRouter
        from backend.app.services.llm_providers import LLMProvider
        import unittest.mock

        vault.store_key("test-user", "claude", "sk-ant-fake-key-12345")

        router = LLMRouter()
        # Patch the import inside _load_user_providers
        with unittest.mock.patch(
            "backend.app.services.key_vault.key_vault", vault
        ):
            overrides = router._load_user_providers("test-user")

        assert LLMProvider.CLAUDE in overrides
        assert overrides[LLMProvider.CLAUDE].api_key == "sk-ant-fake-key-12345"

    def test_router_no_vault_keys_returns_empty(self, vault):
        from backend.app.services.llm_router import LLMRouter
        import unittest.mock

        router = LLMRouter()
        with unittest.mock.patch(
            "backend.app.services.key_vault.key_vault", vault
        ):
            overrides = router._load_user_providers("nonexistent-user")

        assert overrides == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
