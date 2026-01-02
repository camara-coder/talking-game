"""
Session Manager - Handles session state and lifecycle
"""
from typing import Dict, Optional
import asyncio
import logging
from datetime import datetime, timedelta

from app.api.models import Session, SessionStatus
from app.config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages active sessions and their lifecycle"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

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


# Global session manager instance
session_manager = SessionManager()
