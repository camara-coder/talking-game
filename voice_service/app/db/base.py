"""Database engine and base setup"""
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import declarative_base
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()

_engine: Optional[AsyncEngine] = None


async def init_db(database_url: str, pool_size: int = 10, max_overflow: int = 20, echo: bool = False) -> Optional[AsyncEngine]:
    """Initialize database engine

    Args:
        database_url: PostgreSQL connection URL (must use asyncpg driver)
        pool_size: Number of connections to maintain in the pool
        max_overflow: Maximum overflow connections
        echo: Enable SQLAlchemy query logging

    Returns:
        AsyncEngine instance or None if database_url is empty
    """
    global _engine

    if not database_url:
        logger.warning("DATABASE_URL not set, DB persistence disabled")
        return None

    try:
        _engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=echo
        )
        logger.info("Database engine initialized")
        return _engine
    except Exception as e:
        logger.error(f"Failed to initialize database engine: {e}", exc_info=True)
        return None


async def close_db() -> None:
    """Close database connections"""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database connections closed")


def get_engine() -> Optional[AsyncEngine]:
    """Get the database engine instance

    Returns:
        AsyncEngine instance or None if not initialized
    """
    return _engine
