"""
API Keys Router for SupplyChainIQ
CRUD endpoints for managing per-user encrypted LLM API keys.

Uses X-User-ID header for user identification (Sub-Task 1.3 will add
proper multi-user auth; for now this is the foundation).
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from ..services.key_vault import key_vault

router = APIRouter(prefix="/api/v1/keys", tags=["api-keys"])

# Default user ID when no header is provided (single-user demo mode)
DEFAULT_USER = "default"


# ------------------------------------------------------------------
# Request/Response Models
# ------------------------------------------------------------------

class StoreKeyRequest(BaseModel):
    """Request to store an API key"""
    provider: str = Field(
        ...,
        description="LLM provider name: claude, openai, or gemini",
        examples=["claude"],
    )
    api_key: str = Field(
        ...,
        description="The API key to store (will be encrypted at rest)",
        min_length=8,
    )


class KeyInfoResponse(BaseModel):
    """Info about a stored key (key is masked)"""
    provider: str
    key_preview: str
    created_at: str
    updated_at: str


class KeyListResponse(BaseModel):
    """List of stored providers"""
    user_id: str
    providers: List[str]
    available_providers: List[str]


class DeleteResponse(BaseModel):
    """Deletion confirmation"""
    deleted: bool
    provider: Optional[str] = None
    count: Optional[int] = None


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------

def _get_user_id(x_user_id: Optional[str]) -> str:
    """Extract user ID from header or use default."""
    return x_user_id.strip() if x_user_id else DEFAULT_USER


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/store", response_model=KeyInfoResponse)
async def store_api_key(
    body: StoreKeyRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """
    Store an encrypted API key for an LLM provider.
    Overwrites any existing key for the same provider.
    """
    user_id = _get_user_id(x_user_id)

    try:
        key_vault.store_key(user_id, body.provider, body.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    info = key_vault.get_key_info(user_id, body.provider)
    if not info:
        raise HTTPException(status_code=500, detail="Key stored but retrieval failed")

    return KeyInfoResponse(**info)


@router.get("/list", response_model=KeyListResponse)
async def list_keys(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """
    List all providers that have stored keys for the current user.
    Also returns which providers are globally available (env vars).
    """
    user_id = _get_user_id(x_user_id)
    providers = key_vault.list_providers(user_id)

    # Import here to avoid circular deps
    from ..services.llm_service import llm_service
    available = llm_service.get_available_providers()

    return KeyListResponse(
        user_id=user_id,
        providers=providers,
        available_providers=available,
    )


@router.get("/info/{provider}", response_model=KeyInfoResponse)
async def get_key_info(
    provider: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """
    Get metadata about a stored key (masked preview, timestamps).
    Never returns the full key.
    """
    user_id = _get_user_id(x_user_id)
    info = key_vault.get_key_info(user_id, provider)

    if not info:
        raise HTTPException(
            status_code=404,
            detail=f"No key stored for provider '{provider}'",
        )

    return KeyInfoResponse(**info)


@router.delete("/delete/{provider}", response_model=DeleteResponse)
async def delete_key(
    provider: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Delete a stored API key for a specific provider."""
    user_id = _get_user_id(x_user_id)
    deleted = key_vault.delete_key(user_id, provider)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No key found for provider '{provider}'",
        )

    return DeleteResponse(deleted=True, provider=provider)


@router.delete("/delete-all", response_model=DeleteResponse)
async def delete_all_keys(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Delete all stored API keys for the current user."""
    user_id = _get_user_id(x_user_id)
    count = key_vault.delete_all_keys(user_id)
    return DeleteResponse(deleted=count > 0, count=count)
