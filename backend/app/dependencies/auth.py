"""
Authentication dependencies.

Resolves the current user from one of two sources, in order:
  1. `Authorization: Bearer <jwt>` — issued by /api/v1/auth/login
  2. `X-User-ID: <id>`              — legacy guest path, auto-provisioned

This lets the app run a real multi-tenant login flow while still
supporting the one-click guest demo path so judges don't have to register.
"""
from typing import Optional
from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import get_db, UserDB
from ..services.auth_service import decode_access_token

DEFAULT_USER_ID = "guest"


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> str:
    """
    Resolve the current user_id. Prefers a valid JWT in Authorization;
    falls back to X-User-ID; falls back to DEFAULT_USER_ID.
    """
    # 1. JWT path
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            return str(payload["sub"])
        # If a token was provided but is invalid/expired, refuse rather
        # than silently dropping to guest. That would mask bugs and let
        # an expired session look like a fresh anonymous one.
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    # 2. Legacy guest header path
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    # 3. Anonymous guest
    return DEFAULT_USER_ID


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserDB:
    """
    Get the user profile from the database, creating a placeholder
    Guest profile if they don't exist yet (legacy / guest path only).
    """
    result = await db.execute(select(UserDB).where(UserDB.user_id == user_id))
    user = result.scalars().first()

    if not user:
        # Auto-provision — this only happens for guest / X-User-ID flows.
        # Real registered users always already exist by the time we get here.
        user = UserDB(
            user_id=user_id,
            company_name="Guest" if user_id == DEFAULT_USER_ID else None,
            company_type=None,
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to provision user: {str(e)}")

    return user
