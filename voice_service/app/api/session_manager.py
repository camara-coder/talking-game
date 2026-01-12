"""
Session Manager - Handles session state and lifecycle
"""
from typing import Dict, Optional
import asyncio
import logging
from datetime import datetime, timedelta

from app.api.models import Session, SessionStatus, Turn
from app.config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages active sessions and their lifecycle"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._db_enabled = settings.ENABLE_DB_PERSISTENCE
        logger.info(f"Database persistence: {'enabled' if self._db_enabled else 'disabled'}")

    async def start(self):
        """Start session manager background tasks"""
        logger.info("Session Manager started")
        self._cleanup_task = asyncio.create_task(self._cleanup_sessions())

    async def stop(self):
        """Stop session manager and cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Session Manager stopped")

    def create_session(self, session_id: Optional[str] = None, language: str = "en", mode: str = "ptt") -> Session:
        """Create a new session"""
        session = Session(language=language, mode=mode)
        if session_id:
            session.session_id = session_id

        # Check max concurrent sessions
        if len(self.sessions) >= settings.MAX_CONCURRENT_SESSIONS:
            logger.warning(f"Max concurrent sessions reached: {settings.MAX_CONCURRENT_SESSIONS}")
            # Remove oldest idle session
            self._remove_oldest_idle_session()

        self.sessions[session.session_id] = session
        logger.info(f"Session created: {session.session_id}")

        # Persist to database (async background task)
        if self._db_enabled:
            asyncio.create_task(self._persist_session(session))

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session deleted: {session_id}")
            return True
        return False

    def update_session_status(self, session_id: str, status: SessionStatus) -> bool:
        """Update session status"""
        session = self.get_session(session_id)
        if session:
            session.status = status
            session.updated_at = datetime.utcnow()
            return True
        return False

    def _remove_oldest_idle_session(self):
        """Remove the oldest idle session"""
        idle_sessions = [
            (sid, s) for sid, s in self.sessions.items()
            if s.status == SessionStatus.IDLE
        ]
        if idle_sessions:
            # Sort by updated_at
            oldest = min(idle_sessions, key=lambda x: x[1].updated_at)
            self.delete_session(oldest[0])

    async def _cleanup_sessions(self):
        """Background task to cleanup expired sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                now = datetime.utcnow()
                timeout = timedelta(seconds=settings.SESSION_TIMEOUT_SECONDS)

                expired = [
                    session_id
                    for session_id, session in self.sessions.items()
                    if (now - session.updated_at) > timeout
                ]

                for session_id in expired:
                    logger.info(f"Cleaning up expired session: {session_id}")
                    self.delete_session(session_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}", exc_info=True)

    async def resume_or_create_session(self, session_id: str, language: str = "en", mode: str = "ptt") -> Session:
        """Resume existing session from DB or create new one

        Args:
            session_id: Session ID to resume or create
            language: Language code (default: "en")
            mode: Interaction mode (default: "ptt")

        Returns:
            Session object (either resumed from DB or newly created)
        """
        # Check in-memory cache first
        if session_id in self.sessions:
            logger.info(f"Session found in memory: {session_id}")
            return self.sessions[session_id]

        # Try to load from database
        if self._db_enabled:
            try:
                from app.db.session import get_db_session
                from app.db.repositories.session_repository import SessionRepository
                from app.db.repositories.turn_repository import TurnRepository
                from app.api.models import Session

                async with get_db_session() as db_session:
                    session_repo = SessionRepository(db_session)
                    turn_repo = TurnRepository(db_session)

                    db_session_obj = await session_repo.get_by_id(session_id)
                    if db_session_obj:
                        # Load turns (limit to 50 most recent)
                        db_turns = await turn_repo.get_by_session(session_id, limit=50)

                        # Reconstruct session
                        session = Session.from_db(db_session_obj, db_turns)

                        # Add to in-memory cache
                        self.sessions[session_id] = session
                        logger.info(f"Session resumed from DB: {session_id} ({len(session.turns)} turns)")
                        return session
            except Exception as e:
                logger.error(f"Failed to resume session from DB: {e}", exc_info=True)

        # Create new session
        logger.info(f"Creating new session: {session_id}")
        return self.create_session(session_id=session_id, language=language, mode=mode)

    async def _persist_session(self, session: Session) -> None:
        """Persist session to database (async background task)

        Args:
            session: Session object to persist
        """
        try:
            from app.db.session import get_db_session
            from app.db.repositories.session_repository import SessionRepository

            async with get_db_session() as db_session:
                repo = SessionRepository(db_session)
                db_model = session.to_db()
                await repo.create(db_model)
                logger.debug(f"Session persisted to DB: {session.session_id}")
        except Exception as e:
            logger.error(f"Failed to persist session: {e}", exc_info=True)

    async def persist_turn(self, session_id: str, turn: "Turn") -> None:
        """Persist a completed turn to database

        Args:
            session_id: Session ID the turn belongs to
            turn: Turn object to persist
        """
        if not self._db_enabled:
            return

        try:
            from app.db.session import get_db_session
            from app.db.repositories.turn_repository import TurnRepository

            async with get_db_session() as db_session:
                repo = TurnRepository(db_session)
                db_turn = turn.to_db()
                db_turn.session_id = session_id
                await repo.create(db_turn)
                logger.debug(f"Turn persisted to DB: {turn.turn_id}")
        except Exception as e:
            logger.error(f"Failed to persist turn: {e}", exc_info=True)


# Global session manager instance
session_manager = SessionManager()
