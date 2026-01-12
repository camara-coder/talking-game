"""30-day data retention cleanup task"""
import asyncio
import logging
import os
import shutil
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)


async def cleanup_old_data_task() -> None:
    """Background task to delete sessions and audio older than retention period

    This task runs continuously, sleeping for CLEANUP_INTERVAL_HOURS between runs.
    It deletes:
    1. Database records (sessions and turns) older than DATA_RETENTION_DAYS
    2. Associated audio files from disk

    The task gracefully handles cancellation and errors.
    """
    logger.info(
        f"Cleanup task started: will delete data older than {settings.DATA_RETENTION_DAYS} days, "
        f"running every {settings.CLEANUP_INTERVAL_HOURS} hours"
    )

    while True:
        try:
            # Sleep for configured interval (default: 24 hours)
            await asyncio.sleep(settings.CLEANUP_INTERVAL_HOURS * 3600)

            if not settings.ENABLE_DB_PERSISTENCE:
                logger.debug("Database persistence disabled, skipping cleanup")
                continue

            cutoff_date = datetime.utcnow() - timedelta(days=settings.DATA_RETENTION_DAYS)
            logger.info(f"Starting cleanup: deleting data older than {cutoff_date}")

            from app.db.session import get_db_session
            from app.db.repositories.session_repository import SessionRepository

            async with get_db_session() as db_session:
                repo = SessionRepository(db_session)

                # Get expired sessions
                expired = await repo.get_expired_sessions(cutoff_date)
                logger.info(f"Found {len(expired)} expired sessions to delete")

                if not expired:
                    logger.info("No expired sessions found, cleanup complete")
                    continue

                # Delete audio files first
                audio_deleted = 0
                for session in expired:
                    audio_dir = os.path.join(settings.AUDIO_DIR, session.session_id)
                    if os.path.exists(audio_dir):
                        try:
                            shutil.rmtree(audio_dir)
                            audio_deleted += 1
                            logger.debug(f"Deleted audio directory: {audio_dir}")
                        except Exception as e:
                            logger.error(f"Failed to delete audio directory {audio_dir}: {e}")

                logger.info(f"Deleted {audio_deleted} audio directories")

                # Delete from database (cascades to turns)
                deleted_count = 0
                for session in expired:
                    try:
                        if await repo.delete(session.session_id):
                            deleted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete session {session.session_id}: {e}")

                logger.info(f"Cleanup completed: deleted {deleted_count} sessions from database")

        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled, shutting down")
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}", exc_info=True)
            # Continue running despite errors
            await asyncio.sleep(60)  # Wait 1 minute before retrying
