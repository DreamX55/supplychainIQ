"""
Authentication service.

Handles password hashing (bcrypt directly — passlib's bcrypt wrapper has
known incompat issues with bcrypt >= 4.1) and JWT issuance/verification.
Kept deliberately small and self-contained — no global state besides the
constants below.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

# JWT secret. In production this MUST come from env. We default to a
# static value only so the demo runs without configuration — the secret
# should be rotated for any real deployment.
JWT_SECRET = os.getenv("SUPPLYCHAINIQ_JWT_SECRET", "dev-only-change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# bcrypt has a hard 72-byte limit on input. Truncate (don't error) so a
# user with a long passphrase still gets a deterministic hash.
_BCRYPT_MAX = 72


def _to_bytes(s: str) -> bytes:
    b = s.encode("utf-8")
    return b[:_BCRYPT_MAX]


def hash_password(plain: str) -> str:
    """Bcrypt-hash a plaintext password. Returns the hash as a UTF-8 string."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(_to_bytes(plain), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time check of plaintext against a bcrypt hash."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: Optional[str] = None) -> str:
    """Issue a signed JWT for the given user_id."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT. Returns the payload dict on success,
    or None on any failure (expired, malformed, bad signature).
    """
    if not token:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None
