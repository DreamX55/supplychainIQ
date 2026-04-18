"""
User Profile and Sessions Router
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import get_db, UserDB, SessionDB, AnalysisResultDB
from ..dependencies import get_current_user
from ..models import UserProfileResponse, UserProfileUpdate, SessionListResponse, SessionSummary

router = APIRouter(prefix="/api/v1/user", tags=["user"])

@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(user: UserDB = Depends(get_current_user)):
    return UserProfileResponse(
        user_id=user.user_id,
        company_name=user.company_name,
        company_type=user.company_type
    )

@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    update_data: UserProfileUpdate,
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if update_data.company_name is not None:
        user.company_name = update_data.company_name
    if update_data.company_type is not None:
        user.company_type = update_data.company_type
        
    await db.commit()
    await db.refresh(user)
    
    return UserProfileResponse(
        user_id=user.user_id,
        company_name=user.company_name,
        company_type=user.company_type
    )

@router.get("/sessions", response_model=SessionListResponse)
async def get_user_sessions(
    user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all past analysis sessions for the current user."""
    stmt = (
        select(SessionDB)
        .where(SessionDB.user_id == user.user_id)
        .order_by(SessionDB.created_at.desc())
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    summaries = []
    for s in sessions:
        # Get the overall risk level if analysis exists
        risk_level = None
        stmt_analysis = select(AnalysisResultDB).where(AnalysisResultDB.session_id == s.id)
        analysis_result = await db.execute(stmt_analysis)
        analysis = analysis_result.scalars().first()
        if analysis:
            risk_level = analysis.overall_risk_level
            
        summaries.append(SessionSummary(
            id=s.id,
            description=s.description or "Document Upload",
            overall_risk_level=risk_level,
            created_at=s.created_at.isoformat()
        ))
        
    return SessionListResponse(sessions=summaries)
