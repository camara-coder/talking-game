"""Repository for turn database operations"""
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import DBTurn
import logging

logger = logging.getLogger(__name__)


class TurnRepository:
    """Repository for CRUD operations on conversation turns"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, db_turn: DBTurn) -> DBTurn:
        """Create a new turn in the database

        Args:
            db_turn: DBTurn object to persist

        Returns:
            The created DBTurn with any database-generated fields populated
        """
        self.session.add(db_turn)
        await self.session.commit()
        await self.session.refresh(db_turn)
        logger.debug(f"Created turn in database: {db_turn.turn_id} for session {db_turn.session_id}")
        return db_turn

    async def get_by_session(self, session_id: str, limit: int = 10) -> List[DBTurn]:
        """Retrieve turns for a session, ordered chronologically

        Args:
            session_id: Unique session identifier
            limit: Maximum number of turns to retrieve (default: 10)

        Returns:
            List of DBTurn objects in chronological order
        """
        result = await self.session.execute(
            select(DBTurn)
            .where(DBTurn.session_id == session_id)
            .order_by(DBTurn.timestamp.desc())  # Most recent first
            .limit(limit)
        )
        turns = result.scalars().all()
        # Reverse to get chronological order (oldest first)
        chronological_turns = list(reversed(turns))
        logger.debug(f"Retrieved {len(chronological_turns)} turns for session {session_id}")
        return chronological_turns
