"""
Pipeline Runner - Integrates voice pipeline with API
Handles async execution and WebSocket event broadcasting
"""
import asyncio
import logging
import numpy as np
from typing import Optional
import os

from app.pipeline.voice_pipeline import get_pipeline
from app.api.session_manager import session_manager
from app.api.ws import connection_manager
from app.api.models import SessionStatus
from app.config import settings
from app.utils.audio_io import save_wav

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Runs voice pipeline and broadcasts events"""

    def __init__(self):
        """Initialize pipeline runner"""
        self.pipeline = get_pipeline()
        logger.info("Pipeline runner initialized")

    async def process_session_audio(
        self,
        session_id: str,
        audio: np.ndarray,
        sample_rate: int = None
    ) -> bool:
        """
        Process audio for a session through the complete pipeline

        Args:
            session_id: Session ID
            audio: Audio data
            sample_rate: Sample rate in Hz

        Returns:
            True if successful, False otherwise
        """
        if sample_rate is None:
            sample_rate = settings.AUDIO_SAMPLE_RATE

        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return False

        if not session.current_turn:
            logger.error(f"No current turn for session: {session_id}")
            return False

        turn_id = session.current_turn.turn_id

        try:
            logger.info(f"Processing audio for session {session_id}, turn {turn_id}")

            # Broadcast state: thinking
            await connection_manager.broadcast_state(
                session_id,
                SessionStatus.PROCESSING,
                turn_id
            )
            session.status = SessionStatus.PROCESSING

            # Get conversation context
            context = session.get_context(num_turns=settings.LLM_CONTEXT_TURNS)

            # Run pipeline (this is CPU-bound, but we'll run it in the event loop for now)
            # In production, you might want to run this in a thread pool
            result = await asyncio.to_thread(
                self.pipeline.process,
                audio,
                sample_rate,
                context
            )

            # Check for errors
            if result.get("error"):
                error_msg = result["error"]
                logger.error(f"Pipeline error: {error_msg}")

                await connection_manager.broadcast_error(
                    session_id,
                    "PIPELINE_ERROR",
                    error_msg,
                    turn_id
                )

                session.status = SessionStatus.ERROR
                return False

            # Extract results
            transcript = result.get("transcript")
            reply_text = result.get("reply_text")
            route = result.get("route")
            processing_time = result.get("processing_time_ms", 0)

            logger.info(
                f"Pipeline complete: transcript='{transcript}', "
                f"reply='{reply_text}', route={route}, time={processing_time}ms"
            )

            # Update session turn
            session.current_turn.transcript = transcript
            session.current_turn.reply_text = reply_text
            session.current_turn.processing_time_ms = processing_time

            # Broadcast transcript
            if transcript:
                await connection_manager.broadcast_transcript(
                    session_id,
                    transcript,
                    turn_id,
                    partial=False
                )

            # Broadcast reply text
            if reply_text:
                await connection_manager.broadcast_reply_text(
                    session_id,
                    reply_text,
                    turn_id
                )

            # Generate audio using TTS
            audio_path = await self._generate_audio_placeholder(
                session_id,
                turn_id,
                reply_text
            )

            if audio_path:
                session.current_turn.audio_path = audio_path

                # Get actual audio duration
                from app.utils.wav_utils import get_wav_duration
                duration_sec = await asyncio.to_thread(get_wav_duration, audio_path)
                duration_ms = int(duration_sec * 1000)

                # Broadcast audio ready
                audio_url = f"http://{settings.SERVICE_HOST}:{settings.SERVICE_PORT}/api/audio/{session_id}/{turn_id}.wav"

                await connection_manager.broadcast_audio_ready(
                    session_id,
                    turn_id,
                    audio_url,
                    duration_ms=duration_ms
                )

                # Update state to speaking
                await connection_manager.broadcast_state(
                    session_id,
                    SessionStatus.SPEAKING,
                    turn_id
                )
                session.status = SessionStatus.SPEAKING

            # Complete turn
            session.complete_turn()

            # After a brief moment, go back to idle
            await asyncio.sleep(0.5)
            await connection_manager.broadcast_state(
                session_id,
                SessionStatus.IDLE,
                None
            )
            session.status = SessionStatus.IDLE

            logger.info(f"Session {session_id} turn {turn_id} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error processing session audio: {e}", exc_info=True)

            await connection_manager.broadcast_error(
                session_id,
                "PROCESSING_ERROR",
                str(e),
                turn_id
            )

            session.status = SessionStatus.ERROR
            return False

    async def _generate_audio_placeholder(
        self,
        session_id: str,
        turn_id: str,
        text: str
    ) -> Optional[str]:
        """
        Generate audio file using TTS

        Args:
            session_id: Session ID
            turn_id: Turn ID
            text: Text to synthesize

        Returns:
            Path to audio file or None
        """
        try:
            # Create session audio directory
            audio_dir = os.path.join(settings.AUDIO_DIR, session_id)
            os.makedirs(audio_dir, exist_ok=True)

            audio_path = os.path.join(audio_dir, f"{turn_id}.wav")

            # Import TTS processor (ElevenLabs for high-quality cloud TTS)
            from app.pipeline.processors.tts_elevenlabs import ElevenLabsTTSProcessor

            # Create TTS processor (will be cached in future)
            # Using Rachel - clear, friendly female voice for kids
            tts = ElevenLabsTTSProcessor(voice=settings.ELEVENLABS_VOICE)

            # Synthesize speech (run in thread pool as it's CPU-intensive)
            success = await asyncio.to_thread(tts.synthesize, text, audio_path)

            if success:
                logger.info(f"Generated TTS audio: {audio_path}")
                return audio_path
            else:
                logger.error("TTS synthesis failed")
                return None

        except Exception as e:
            logger.error(f"Error generating TTS audio: {e}", exc_info=True)
            return None


# Global pipeline runner instance
_runner_instance = None


def get_pipeline_runner() -> PipelineRunner:
    """Get or create global pipeline runner instance"""
    global _runner_instance

    if _runner_instance is None:
        _runner_instance = PipelineRunner()

    return _runner_instance


async def process_audio_stream(session_id: str, audio_data: bytes):
    """
    Process audio received from WebSocket stream

    Args:
        session_id: Session ID
        audio_data: Raw audio bytes (WebM format from browser)
    """
    import tempfile
    import soundfile as sf
    import subprocess

    logger.info(f"Processing audio stream for session {session_id}: {len(audio_data)} bytes")

    try:
        # Write raw audio to temp file
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
            temp_webm.write(audio_data)
            temp_webm_path = temp_webm.name

        # Create temp WAV file path
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()

        # Convert WebM to WAV using ffmpeg directly
        logger.info("Converting WebM to WAV using ffmpeg...")

        # ffmpeg command: convert to mono, 16kHz WAV
        cmd = [
            'ffmpeg',
            '-i', temp_webm_path,  # Input file
            '-ar', '16000',        # Sample rate 16kHz
            '-ac', '1',            # Mono (1 channel)
            '-y',                  # Overwrite output file
            temp_wav_path          # Output file
        ]

        # Run ffmpeg (in thread to not block event loop)
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr}")
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

        logger.info("Conversion complete")

        # Read WAV file into numpy array
        audio, sample_rate = sf.read(temp_wav_path, dtype='float32')

        logger.info(f"Converted audio: {len(audio)} samples at {sample_rate}Hz")

        # Clean up temp files
        try:
            os.unlink(temp_webm_path)
            os.unlink(temp_wav_path)
        except:
            pass

        # Process through pipeline
        runner = get_pipeline_runner()
        await runner.process_session_audio(session_id, audio, sample_rate)

    except FileNotFoundError as e:
        logger.error(f"ffmpeg not found: {e}")

        # Send error to client
        await connection_manager.broadcast_error(
            session_id,
            "FFMPEG_NOT_FOUND",
            "ffmpeg is required for audio conversion. Please install ffmpeg and add it to PATH."
        )

        await connection_manager.broadcast_state(
            session_id,
            SessionStatus.IDLE
        )

        raise

    except Exception as e:
        logger.error(f"Error processing audio stream: {e}", exc_info=True)

        # Send error to client
        await connection_manager.broadcast_error(
            session_id,
            "AUDIO_CONVERSION_ERROR",
            f"Failed to convert audio: {str(e)}"
        )

        await connection_manager.broadcast_state(
            session_id,
            SessionStatus.IDLE
        )

        raise
