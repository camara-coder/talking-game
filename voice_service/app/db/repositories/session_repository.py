"""Repository for session database operations"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import DBSession
import logging

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for CRUD operations on sessions"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, db_session: DBSession) -> DBSession:
        """Create a new session in the database

        Args:
            db_session: DBSession object to persist

        Returns:
            The created DBSession with any database-generated fields populated
        """
        self.session.add(db_session)
        await self.session.commit()
        await self.session.refresh(db_session)
        logger.debug(f"Created session in database: {db_session.session_id}")
        return db_session

    async def get_by_id(self, session_id: str) -> Optional[DBSession]:
        """Retrieve a session by ID

        Args:
            session_id: Unique session identifier

        Returns:
            DBSession if found, None otherwise
        """
        result = await self.session.execute(
            select(DBSession).where(DBSession.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def update(self, db_session: DBSession) -> DBSession:
        """Update an existing session

        Args:
            db_session: DBSession object with updated fields

        Returns:
            The updated DBSession
        """
        merged = await self.session.merge(db_session)
        await self.session.commit()
        logger.debug(f"Updated session in database: {db_session.session_id}")
        return merged

    async def delete(self, session_id: str) -> bool:
        """Delete a session (cascades to turns)

        Args:
            session_id: Unique session identifier

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(DBSession).where(DBSession.session_id == session_id)
        )
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.debug(f"Deleted session from database: {session_id}")
        return deleted

    async def get_expired_sessions(self, cutoff: datetime) -> List[DBSession]:
        """Get sessions older than cutoff date (for cleanup)

        Args:
            cutoff: DateTime threshold for expiration

        Returns:
            List of expired DBSession objects
        """
        result = await self.session.execute(
            select(DBSession).where(DBSession.last_activity_at < cutoff)
        )
        sessions = result.scalars().all()
        logger.debug(f"Found {len(sessions)} expired sessions before {cutoff}")
        return list(sessions)
