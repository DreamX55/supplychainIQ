"""
Secure API Key Vault for SupplyChainIQ

Provides Fernet-encrypted storage for per-user LLM API keys.
Keys are encrypted at rest in SQLite; the master encryption key
is derived from VAULT_MASTER_KEY env var (auto-generated if absent).

Design decisions:
  - SQLite for simplicity (hackathon scope) — swap to PostgreSQL later
  - Fernet (AES-128-CBC + HMAC-SHA256) — symmetric, fast, built into cryptography lib
  - Per-user isolation via user_id column
  - Keys are never logged or returned in full — only masked previews
"""

import os
import sqlite3
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("supplychainiq.vault")

# Where the SQLite database lives
DB_DIR = Path(os.getenv("VAULT_DB_DIR", "data"))
DB_PATH = DB_DIR / "vault.db"


def _get_or_create_master_key() -> bytes:
    """
    Get the Fernet master key from env, or generate and persist one.
    In production, this should come from a secrets manager (AWS SSM, Vault, etc).
    For the hackathon, we auto-generate and store in a file.
    """
    env_key = os.getenv("VAULT_MASTER_KEY", "")
    if env_key:
        return env_key.encode()

    key_file = DB_DIR / ".vault_key"
    if key_file.exists():
        return key_file.read_bytes().strip()

    # First run — generate a new key
    DB_DIR.mkdir(parents=True, exist_ok=True)
    new_key = Fernet.generate_key()
    key_file.write_bytes(new_key)
    # Restrict permissions (best-effort on all platforms)
    try:
        key_file.chmod(0o600)
    except OSError:
        pass
    logger.info("Generated new vault master key")
    return new_key


class KeyVault:
    """
    Encrypted API key storage with per-user isolation.

    Usage:
        vault = KeyVault()
        vault.store_key("user-123", "claude", "sk-ant-xxx")
        key = vault.get_key("user-123", "claude")    # returns decrypted key
        vault.delete_key("user-123", "claude")
        providers = vault.list_providers("user-123")  # ["claude", "gemini"]
    """

    # Supported provider names — validated on store
    VALID_PROVIDERS = {"claude", "openai", "gemini", "groq"}

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        master_key = _get_or_create_master_key()
        self._fernet = Fernet(master_key)

        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store_key(self, user_id: str, provider: str, api_key: str) -> None:
        """
        Encrypt and store an API key.
        Overwrites any existing key for the same user+provider.
        """
        provider = provider.lower().strip()
        if provider not in self.VALID_PROVIDERS:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Valid: {', '.join(sorted(self.VALID_PROVIDERS))}"
            )

        if not api_key or len(api_key) < 8:
            raise ValueError("API key must be at least 8 characters")

        encrypted = self._fernet.encrypt(api_key.encode()).decode()
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    INSERT INTO api_keys (user_id, provider, encrypted_key, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, provider)
                    DO UPDATE SET encrypted_key = excluded.encrypted_key,
                                  updated_at = excluded.updated_at
                    """,
                    (user_id, provider, encrypted, now, now),
                )
                conn.commit()
            finally:
                conn.close()

        logger.info(f"Stored key for user={user_id} provider={provider}")

    def get_key(self, user_id: str, provider: str) -> Optional[str]:
        """
        Retrieve and decrypt an API key.
        Returns None if no key is stored for this user+provider.
        """
        provider = provider.lower().strip()
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT encrypted_key FROM api_keys WHERE user_id = ? AND provider = ?",
                    (user_id, provider),
                ).fetchone()
            finally:
                conn.close()

        if not row:
            return None

        try:
            return self._fernet.decrypt(row[0].encode()).decode()
        except InvalidToken:
            logger.error(
                f"Failed to decrypt key for user={user_id} provider={provider} "
                "(master key may have changed)"
            )
            return None

    def delete_key(self, user_id: str, provider: str) -> bool:
        """Delete a stored key. Returns True if a key was deleted."""
        provider = provider.lower().strip()
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute(
                    "DELETE FROM api_keys WHERE user_id = ? AND provider = ?",
                    (user_id, provider),
                )
                conn.commit()
                deleted = cursor.rowcount > 0
            finally:
                conn.close()

        if deleted:
            logger.info(f"Deleted key for user={user_id} provider={provider}")
        return deleted

    def list_providers(self, user_id: str) -> List[str]:
        """List provider names that have stored keys for this user."""
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT provider FROM api_keys WHERE user_id = ? ORDER BY provider",
                    (user_id,),
                ).fetchall()
            finally:
                conn.close()
        return [r[0] for r in rows]

    def get_key_info(self, user_id: str, provider: str) -> Optional[Dict]:
        """
        Get metadata about a stored key (without exposing the full key).
        Returns masked preview like "sk-ant-***...xyz".
        """
        provider = provider.lower().strip()
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT encrypted_key, created_at, updated_at FROM api_keys "
                    "WHERE user_id = ? AND provider = ?",
                    (user_id, provider),
                ).fetchone()
            finally:
                conn.close()

        if not row:
            return None

        try:
            decrypted = self._fernet.decrypt(row[0].encode()).decode()
            masked = self._mask_key(decrypted)
        except InvalidToken:
            masked = "***DECRYPT_ERROR***"

        return {
            "provider": provider,
            "key_preview": masked,
            "created_at": row[1],
            "updated_at": row[2],
        }

    def delete_all_keys(self, user_id: str) -> int:
        """Delete all stored keys for a user. Returns count deleted."""
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute(
                    "DELETE FROM api_keys WHERE user_id = ?", (user_id,)
                )
                conn.commit()
                count = cursor.rowcount
            finally:
                conn.close()
        logger.info(f"Deleted {count} keys for user={user_id}")
        return count

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        """Create a new connection (SQLite is thread-safe with proper locking)."""
        return sqlite3.connect(str(self._db_path))

    def _init_db(self) -> None:
        """Create the keys table if it doesn't exist."""
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    user_id    TEXT NOT NULL,
                    provider   TEXT NOT NULL,
                    encrypted_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, provider)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)"
            )
            conn.commit()
        finally:
            conn.close()
        logger.info(f"Vault database initialized at {self._db_path}")

    @staticmethod
    def _mask_key(key: str) -> str:
        """Mask an API key for safe display: show first 8 and last 4 chars."""
        if len(key) <= 12:
            return key[:4] + "***"
        return key[:8] + "***..." + key[-4:]


# Singleton
key_vault = KeyVault()
