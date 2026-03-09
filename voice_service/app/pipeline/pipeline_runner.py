"""
Pipeline Runner - Integrates voice pipeline with API
Handles async execution and WebSocket event broadcasting

Response latency strategy (fastest → slowest):
  1. Pool fast-path  — pre-baked cat phrase, no LLM (~100 ms total after STT)
  2. Streaming LLM   — sentence-level TTS; first audio sent before full reply done
  3. (legacy batch)  — kept only as fallback; not reached in normal operation
"""
import asyncio
import logging
import numpy as np
from typing import Optional
import os
import time

from app.pipeline.voice_pipeline import get_pipeline
from app.api.session_manager import session_manager
from app.api.ws import connection_manager
from app.api.models import SessionStatus
from app.config import settings
from app.utils.audio_io import save_wav

logger = logging.getLogger(__name__)


def _collect_sentences(prompt: str, context: list, system_prompt: str) -> list[str]:
    """
    Generate LLM sentences with Claude as primary and Ollama as fallback.

    Tries Claude (claude-haiku-4-5) first — ~5-10× faster than local CPU
    inference.  Falls back to the Ollama 0.5b model if:
      - ANTHROPIC_API_KEY is not set
      - API credits are exhausted / any Anthropic API error

    Called via asyncio.to_thread so it doesn't block the event loop.
    """
    # ── Try Claude first ────────────────────────────────────────────────────
    if settings.ANTHROPIC_API_KEY:
        try:
            from app.pipeline.processors.llm_claude import ClaudeLLMProcessor
            sentences = list(
                ClaudeLLMProcessor().generate_sentences_stream(prompt, context, system_prompt)
            )
            if sentences:
                logger.info(f"Claude replied with {len(sentences)} sentence(s)")
                return sentences
        except Exception as exc:
            logger.warning(
                f"Claude unavailable ({type(exc).__name__}: {exc}), "
                "falling back to Ollama"
            )

    # ── Fallback: local Ollama ──────────────────────────────────────────────
    logger.info("Using Ollama fallback for LLM")
    from app.pipeline.processors.llm_ollama import OllamaLLMProcessor
    return list(OllamaLLMProcessor().generate_sentences_stream(prompt, context, system_prompt))


def _create_tts_processor():
    """Create TTS processor based on configured engine."""
    engine = settings.TTS_ENGINE.lower()
    if engine == "pocket":
        from app.pipeline.processors.tts_pocket import PocketTTSProcessor
        return PocketTTSProcessor()
    elif engine == "qwen3":
        from app.pipeline.processors.tts_qwen3 import Qwen3TTSProcessor
        return Qwen3TTSProcessor()
    elif engine == "edge":
        from app.pipeline.processors.tts_edge import EdgeTTSProcessor
        return EdgeTTSProcessor()
    elif engine == "elevenlabs":
        from app.pipeline.processors.tts_elevenlabs import ElevenLabsTTSProcessor
        return ElevenLabsTTSProcessor(voice=settings.ELEVENLABS_VOICE)
    else:
        raise ValueError(
            f"Unknown TTS_ENGINE '{engine}'. "
            f"Supported: 'pocket', 'qwen3', 'edge', 'elevenlabs'"
        )


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
        Process audio for a session through the complete pipeline.

        Flow:
          1. STT + skills routing  (thread)
          2a. Math route           → single TTS, broadcast
          2b. LLM pool fast-path   → single TTS from pre-baked pool, broadcast
          2c. LLM streaming        → sentence-by-sentence TTS + broadcast
        """
        if sample_rate is None:
            sample_rate = settings.AUDIO_SAMPLE_RATE

        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return False

        if not session.current_turn:
            logger.warning(f"No current turn for session {session_id}, creating one as fallback")
            session.start_turn()

        turn_id = session.current_turn.turn_id

        engine = session_manager.get_proactive_engine(session_id)
        if engine:
            engine.pause()

        mood_manager = session_manager.get_mood_manager(session_id)
        if mood_manager:
            mood_manager.on_user_interaction()

        try:
            t_start = time.time()
            logger.info(f"Processing audio for session {session_id}, turn {turn_id}")

            await connection_manager.broadcast_state(
                session_id, SessionStatus.PROCESSING, turn_id
            )
            session.status = SessionStatus.PROCESSING

            # ── Step 1: STT + skills routing ────────────────────────────────
            stt_result = await asyncio.to_thread(
                self.pipeline.transcribe_and_route, audio, sample_rate
            )

            if stt_result.get("error"):
                await connection_manager.broadcast_error(
                    session_id, "PIPELINE_ERROR", stt_result["error"], turn_id
                )
                session.status = SessionStatus.ERROR
                return False

            transcript = stt_result["transcript"]
            route = stt_result["route"]
            math_response = stt_result.get("math_response")

            session.current_turn.transcript = transcript
            logger.info(f"STT done in {(time.time()-t_start)*1000:.0f}ms: '{transcript}'")

            if transcript:
                await connection_manager.broadcast_transcript(
                    session_id, transcript, turn_id, partial=False
                )

            # ── Step 2: Generate reply ───────────────────────────────────────
            context = session.get_context(num_turns=settings.LLM_CONTEXT_TURNS)

            if route == "math" and math_response:
                # Math is deterministic — single TTS, no LLM needed
                reply_sentences = [math_response]
                logger.info("Math route — skipping LLM")

            else:
                # LLM route: try pool fast-path first
                from app.personality.cat_responses import should_use_pool, get_pool_response
                current_mood = mood_manager.current_mood if mood_manager else None

                if current_mood and should_use_pool(transcript):
                    pool_reply = get_pool_response(current_mood, transcript)
                    reply_sentences = [pool_reply]
                    logger.info(f"Pool fast-path: '{pool_reply}'")
                else:
                    # Full LLM path (Claude → Ollama fallback)
                    from app.personality.cat_prompts import get_system_prompt, get_context_note

                    system_prompt = settings.SYSTEM_PROMPT
                    if mood_manager:
                        mode = mood_manager.get_response_mode()
                        system_prompt = (
                            get_system_prompt(mood_manager.current_mood, mode)
                            + get_context_note(context)
                        )
                        logger.info(f"LLM: mood={mood_manager.current_mood}, mode={mode}")

                    reply_sentences = await asyncio.to_thread(
                        _collect_sentences, transcript, context, system_prompt
                    )

            # ── Step 3: TTS + broadcast each sentence ───────────────────────
            full_reply = " ".join(reply_sentences)
            session.current_turn.reply_text = full_reply
            session.current_turn.processing_time_ms = int((time.time() - t_start) * 1000)

            if full_reply:
                await connection_manager.broadcast_reply_text(
                    session_id, full_reply, turn_id
                )

            audio_dir = os.path.join(settings.AUDIO_DIR, session_id)
            os.makedirs(audio_dir, exist_ok=True)
            base_url = (
                settings.PUBLIC_URL
                if settings.PUBLIC_URL
                else f"http://{settings.SERVICE_HOST}:{settings.SERVICE_PORT}"
            )

            any_audio = False
            for seg_idx, sentence in enumerate(reply_sentences):
                if not sentence.strip():
                    continue
                filename = f"{turn_id}_{seg_idx}.wav" if len(reply_sentences) > 1 else f"{turn_id}.wav"
                audio_path = os.path.join(audio_dir, filename)

                tts = _create_tts_processor()
                success = await asyncio.to_thread(tts.synthesize, sentence, audio_path)
                if not success:
                    logger.error(f"TTS failed for segment {seg_idx}")
                    continue

                if settings.CAT_VOICE_PITCH_SEMITONES != 0.0:
                    from app.utils.audio_pitch import pitch_shift_wav_inplace
                    await asyncio.to_thread(
                        pitch_shift_wav_inplace, audio_path, settings.CAT_VOICE_PITCH_SEMITONES
                    )

                from app.utils.wav_utils import get_wav_info
                wav_info = await asyncio.to_thread(get_wav_info, audio_path)
                duration_ms = int(wav_info.get("duration", 0.0) * 1000)
                sample_rate_hz = wav_info.get("sample_rate", settings.TTS_SAMPLE_RATE)

                audio_url = f"{base_url}/api/audio/{session_id}/{filename}"
                await connection_manager.broadcast_audio_ready(
                    session_id, turn_id, audio_url,
                    duration_ms=duration_ms, sample_rate_hz=sample_rate_hz,
                )
                logger.info(
                    f"Segment {seg_idx} ready in {(time.time()-t_start)*1000:.0f}ms: "
                    f"'{sentence}' → {audio_url}"
                )
                any_audio = True

                if seg_idx == 0:
                    # Mark as speaking as soon as the first chunk is ready
                    await connection_manager.broadcast_state(
                        session_id, SessionStatus.SPEAKING, turn_id
                    )
                    session.status = SessionStatus.SPEAKING

            if not any_audio:
                await connection_manager.broadcast_error(
                    session_id, "TTS_ERROR", "Failed to synthesize response audio", turn_id
                )
                await connection_manager.broadcast_state(
                    session_id, SessionStatus.IDLE, turn_id
                )

            session.complete_turn()
            if len(session.turns) > 0:
                asyncio.create_task(
                    session_manager.persist_turn(session_id, session.turns[-1])
                )

            await asyncio.sleep(0.5)
            await connection_manager.broadcast_state(session_id, SessionStatus.IDLE, None)
            session.status = SessionStatus.IDLE

            logger.info(
                f"Turn {turn_id} complete in {(time.time()-t_start)*1000:.0f}ms"
            )
            return True

        except Exception as e:
            logger.error(f"Error processing session audio: {e}", exc_info=True)
            await connection_manager.broadcast_error(
                session_id, "PROCESSING_ERROR", str(e), turn_id
            )
            session.status = SessionStatus.ERROR
            return False

        finally:
            engine = session_manager.get_proactive_engine(session_id)
            if engine:
                engine.resume()



# Global pipeline runner instance
_runner_instance = None


def get_pipeline_runner() -> PipelineRunner:
    """Get or create global pipeline runner instance"""
    global _runner_instance

    if _runner_instance is None:
        _runner_instance = PipelineRunner()

    return _runner_instance


async def process_audio_stream(session_id: str, audio_data: bytes, sample_rate: int = None):
    """
    Process audio received from WebSocket stream

    Args:
        session_id: Session ID
        audio_data: Raw PCM16 audio bytes from browser AudioWorklet
        sample_rate: Actual sample rate from the client's AudioContext.
                     On Android Chrome this may be 44100 or 48000 instead of 16000.
    """
    logger.info(f"Processing audio stream for session {session_id}: {len(audio_data)} bytes")

    try:
        # Convert raw PCM16 bytes to numpy array
        # AudioWorklet sends Int16Array (little-endian, 2 bytes per sample)
        pcm16_data = np.frombuffer(audio_data, dtype=np.int16)

        # Convert PCM16 to float32 in range [-1.0, 1.0]
        audio = pcm16_data.astype(np.float32) / 32768.0

        # Use client-reported sample rate if available, otherwise fall back to config.
        # Android Chrome may capture at 44100/48000Hz instead of the requested 16kHz.
        if sample_rate is None:
            sample_rate = settings.AUDIO_SAMPLE_RATE

        logger.info(f"Converted PCM audio: {len(audio)} samples at {sample_rate}Hz")

        # Resample to 16kHz if needed. The pipeline processors (Silero VAD, noise
        # reducer) are initialized at 16kHz and cannot handle other rates. Android
        # Chrome often captures at 44100 or 48000Hz when the AudioContext can't use
        # the requested 16kHz rate.
        target_rate = settings.AUDIO_SAMPLE_RATE
        if sample_rate != target_rate:
            logger.info(f"Resampling audio from {sample_rate}Hz to {target_rate}Hz for pipeline")
            from app.utils.audio_io import resample_audio
            audio = resample_audio(audio, sample_rate, target_rate)
            sample_rate = target_rate
            logger.info(f"Resampled audio: {len(audio)} samples at {sample_rate}Hz")

        # Process through pipeline
        runner = get_pipeline_runner()
        await runner.process_session_audio(session_id, audio, sample_rate)

    except Exception as e:
        logger.error(f"Error processing audio stream: {e}", exc_info=True)

        # Send error to client
        await connection_manager.broadcast_error(
            session_id,
            "AUDIO_CONVERSION_ERROR",
            f"Failed to process audio: {str(e)}"
        )

        await connection_manager.broadcast_state(
            session_id,
            SessionStatus.IDLE
        )

        raise
