"""
REST API routes for session management and audio serving
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
import logging
import os
import numpy as np

from app.api.models import (
    SessionStartRequest,
    SessionStartResponse,
    SessionStopRequest,
    SessionStopResponse,
    SessionStatus,
)
from app.api.session_manager import session_manager
from app.pipeline.pipeline_runner import get_pipeline_runner
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/session/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """
    Start a new voice interaction session
    Initializes session state and begins listening
    """
    try:
        # Resume existing session from DB or create a new one
        session = await session_manager.resume_or_create_session(
            session_id=request.session_id or "",
            language=request.language,
            mode=request.mode
        )

        logger.info(
            f"Session started: {session.session_id}, "
            f"Status: {session.status}"
        )

        return SessionStartResponse(
            session_id=session.session_id,
            status=session.status
        )

    except Exception as e:
        logger.error(f"Error starting session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {str(e)}"
        )


@router.post("/session/stop", response_model=SessionStopResponse)
async def stop_session(request: SessionStopRequest, background_tasks: BackgroundTasks):
    """
    Stop the current session turn
    Triggers audio processing pipeline
    """
    try:
        # Get session
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {request.session_id}"
            )

        # Check if session is in listening state
        if session.status != SessionStatus.LISTENING:
            logger.warning(
                f"Session {request.session_id} not in listening state: {session.status}"
            )

        # Update status to processing
        session.status = SessionStatus.PROCESSING

        logger.info(
            f"Session stopped: {session.session_id}, "
            f"Status: {session.status}, "
            f"Turn: {session.current_turn.turn_id if session.current_turn else 'None'}"
        )

        # For POC: Generate test audio (simulating user speech)
        # In production, this would come from actual microphone capture
        # Generate 3 seconds of test audio (will be processed by VAD/STT)
        sample_rate = settings.AUDIO_SAMPLE_RATE
        duration = 3.0
        test_audio = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.1

        # Trigger pipeline processing in background
        pipeline_runner = get_pipeline_runner()
        background_tasks.add_task(
            pipeline_runner.process_session_audio,
            request.session_id,
            test_audio,
            sample_rate
        )

        logger.info(f"Pipeline processing queued for session {request.session_id}")

        return SessionStopResponse(
            session_id=session.session_id,
            status=session.status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop session: {str(e)}"
        )


@router.get("/audio/{session_id}/{turn_id}.wav")
async def get_audio(session_id: str, turn_id: str):
    """
    Serve synthesized audio file for a specific turn
    """
    try:
        # Construct audio file path
        audio_path = os.path.join(
            settings.AUDIO_DIR,
            session_id,
            f"{turn_id}.wav"
        )

        # Check if file exists
        if not os.path.exists(audio_path):
            logger.warning(f"Audio file not found: {audio_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audio file not found for session {session_id}, turn {turn_id}"
            )

        logger.info(f"Serving audio file: {audio_path}")

        # Serve the WAV file
        return FileResponse(
            audio_path,
            media_type="audio/wav",
            filename=f"{turn_id}.wav"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving audio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve audio: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Get information about a session (for debugging)
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )

    return {
        "session_id": session.session_id,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "num_turns": len(session.turns),
        "current_turn": session.current_turn.turn_id if session.current_turn else None
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and cleanup resources
    """
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )

    return {"message": f"Session {session_id} deleted successfully"}
