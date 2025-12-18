"""
Database configuration and session management for Company Search.
Uses SQLAlchemy 2.0 with async support (asyncpg driver).

Render.com compatibility:
- Automatically converts postgres:// to postgresql+asyncpg://
- Uses NullPool for serverless compatibility
- Graceful handling when DATABASE_URL not set (allows /extract to work)
"""

import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarativebase
from sqlalchemy.pool import NullPool

# ============================================================================
# Configuration
# ============================================================================

# Get DATABASE_URL from environment
# Format: postgresql+asyncpg://user:password@host:port/database
DATABASE_URL = os.getenv("DATABASE_URL")

# For local development or when database not needed, allow running without it
if not DATABASE_URL:
    print("⚠️  WARNING: DATABASE_URL not set. Conversational features will be disabled.")
    print("   The /extract endpoint will still work, but /api/v1/conversations/* will not.")
    DATABASE_URL = None
else:
    # Convert postgres:// to postgresql+asyncpg:// (Render provides postgres://)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ============================================================================
# SQLAlchemy Setup
# ============================================================================

# Create async engine only if DATABASE_URL is set
engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None

if DATABASE_URL:
    # Create async engine
    # - pool_pre_ping: Check connection health before using
    # - echo: Set to True for SQL query logging (development)
    # - NullPool: For serverless/Render environments to avoid connection pooling issues
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True for debugging SQL queries
        pool_pre_ping=True,
        poolclass=NullPool,  # Disable pooling for serverless compatibility
    )

    # Create async session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

# ============================================================================
# Base Model
# ============================================================================

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

# ============================================================================
# Dependency Injection
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession: Database session

    Raises:
        RuntimeError: If DATABASE_URL not configured
    """
    if not AsyncSessionLocal:
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL environment variable.\n"
            "To use conversational features, add a PostgreSQL database on Render."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# ============================================================================
# Database Initialization
# ============================================================================

async def init_db():
    """
    Initialize database tables.
    Creates all tables defined in models.

    Note: In production, use Alembic migrations instead.
    This is mainly for development/testing.
    """
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        print("⚠️  Skipping database initialization (DATABASE_URL not set)")

async def close_db():
    """
    Close database engine.
    Call this on application shutdown.
    """
    if engine:
        await engine.dispose()

def is_database_configured() -> bool:
    """
    Check if database is configured and available.

    Returns:
        bool: True if DATABASE_URL is set and engine created
    """
    return engine is not None
