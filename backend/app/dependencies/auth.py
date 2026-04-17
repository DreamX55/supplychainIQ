"""
Authentication dependencies.
Extracts the X-User-ID header and provisions the user if they don't exist.
"""
from typing import Optional
from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import get_db, UserDB

DEFAULT_USER_ID = "guest"

async def get_current_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract the basic user ID string"""
    user_id = x_user_id.strip() if x_user_id and x_user_id.strip() else DEFAULT_USER_ID
    return user_id

async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> UserDB:
    """
    Get the user profile from the database, creating a placeholder
    Guest profile if they don't exist yet.
    """
    result = await db.execute(select(UserDB).where(UserDB.user_id == user_id))
    user = result.scalars().first()
    
    if not user:
        # Auto-provision
        user = UserDB(
            user_id=user_id,
            company_name="Guest" if user_id == DEFAULT_USER_ID else None,
            company_type=None
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to provision user: {str(e)}")
            
    return user
