"""Database session factory"""
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.db.base import get_engine
import logging

logger = logging.getLogger(__name__)

# Global session maker
async_session_maker: Optional[async_sessionmaker] = None


def init_session_factory() -> bool:
    """Initialize the async session factory

    Must be called after init_db() to set up the session maker

    Returns:
        True if successful, False otherwise
    """
    global async_session_maker

    engine = get_engine()
    if not engine:
        logger.error("Cannot initialize session factory: database engine not initialized")
        return False

    try:
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False  # Keep objects accessible after commit
        )
        logger.info("Database session factory initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize session factory: {e}", exc_info=True)
        return False


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for operations

    Usage:
        async with get_db_session() as session:
            # perform database operations
            result = await session.execute(query)

    Yields:
        AsyncSession instance

    Raises:
        RuntimeError: If session factory not initialized
    """
    if not async_session_maker:
        raise RuntimeError("Database session factory not initialized. Call init_session_factory() first.")

    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}", exc_info=True)
            await session.rollback()
            raise
        finally:
            await session.close()
