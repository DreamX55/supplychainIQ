"""
Authentication router.

Endpoints:
  POST /api/v1/auth/register  — create a new account
  POST /api/v1/auth/login     — exchange email+password for a JWT
  GET  /api/v1/auth/me        — return the current user (requires JWT)
"""
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import get_db, UserDB
from ..services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

logger = logging.getLogger("supplychainiq.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ----------------------------------------------------------------------
# Request / response models
# ----------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    company_name: Optional[str] = None
    company_type: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    company_name: Optional[str] = None
    company_type: Optional[str] = None


class MeResponse(BaseModel):
    user_id: str
    email: Optional[str] = None
    company_name: Optional[str] = None
    company_type: Optional[str] = None


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------

@router.post("/register", response_model=AuthResponse)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    # Reject if email already exists
    existing = await db.execute(select(UserDB).where(UserDB.email == payload.email))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = UserDB(
        user_id=f"user_{uuid.uuid4().hex[:12]}",
        email=payload.email,
        password_hash=hash_password(payload.password),
        company_name=payload.company_name,
        company_type=payload.company_type,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        logger.exception("Registration failed")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

    token = create_access_token(user.user_id, user.email)
    return AuthResponse(
        access_token=token,
        user_id=user.user_id,
        email=user.email,
        company_name=user.company_name,
        company_type=user.company_type,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    result = await db.execute(select(UserDB).where(UserDB.email == payload.email))
    user = result.scalars().first()

    # Constant-ish-time failure: always run verify_password even when the
    # user doesn't exist, so timing can't distinguish "no such user" from
    # "wrong password".
    stored_hash = user.password_hash if user else "$2b$12$invalidinvalidinvalidinvalidinvalidinvalidinvalidinvali"
    if not verify_password(payload.password, stored_hash) or not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user.user_id, user.email)
    return AuthResponse(
        access_token=token,
        user_id=user.user_id,
        email=user.email,
        company_name=user.company_name,
        company_type=user.company_type,
    )


@router.get("/me", response_model=MeResponse)
async def me(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    result = await db.execute(select(UserDB).where(UserDB.user_id == payload["sub"]))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        company_name=user.company_name,
        company_type=user.company_type,
    )
