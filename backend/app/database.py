"""
Database configuration and SQLAlchemy ORM models for SupplyChainIQ.
"""
import os
import uuid
from typing import AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Setup the DB path relative to the backend directory
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DB_DIR, 'supplychainiq.db')}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


class UserDB(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    company_name = Column(String, nullable=True)
    company_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    sessions = relationship("SessionDB", back_populates="user", cascade="all, delete-orphan")


class SessionDB(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    description = Column(Text, nullable=True)
    context_data = Column(JSON, nullable=True)  # Stores extracted file contexts
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("UserDB", back_populates="sessions")
    messages = relationship("MessageDB", back_populates="session", cascade="all, delete-orphan")
    analysis_result = relationship("AnalysisResultDB", back_populates="session", uselist=False, cascade="all, delete-orphan")


class MessageDB(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    session = relationship("SessionDB", back_populates="messages")


class AnalysisResultDB(Base):
    __tablename__ = "analysis_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, unique=True)
    risk_nodes = Column(JSON, nullable=False)
    overall_risk_level = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    entities = Column(JSON, nullable=True)
    warning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    session = relationship("SessionDB", back_populates="analysis_result")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get the DB session"""
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
