"""
Proactive Engine — Makes Whiskers the cat behave like a living animal.

Two background loops per session:
  Layer 1 (passive_sound_loop): Sends cat.sound events at short random intervals
  Layer 2 (proactive_speech_loop): Generates LLM text + TTS audio at longer intervals
  Layer 3 (mood_tick_loop): Checks mood transitions every 60s
"""
import asyncio
import logging
import os
import uuid
from typing import Optional

from app.personality.cat_mood import CatMood, MoodManager
from app.personality.cat_prompts import get_proactive_prompt, get_context_note
from app.config import settings

logger = logging.getLogger(__name__)


class ProactiveEngine:
    """Per-session engine driving Whiskers's proactive cat behavior."""

    def __init__(self, session_id: str, mood_manager: MoodManager):
        self.session_id = session_id
        self.mood_manager = mood_manager
        self._passive_task: Optional[asyncio.Task] = None
        self._proactive_task: Optional[asyncio.Task] = None
        self._mood_task: Optional[asyncio.Task] = None
        self._paused = False
        self._running = False

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._passive_task = asyncio.create_task(self._passive_sound_loop())
        self._proactive_task = asyncio.create_task(self._proactive_speech_loop())
        self._mood_task = asyncio.create_task(self._mood_tick_loop())
        logger.info(f"ProactiveEngine started for session {self.session_id}")

    def stop(self) -> None:
        self._running = False
        for task in [self._passive_task, self._proactive_task, self._mood_task]:
            if task and not task.done():
                task.cancel()
        logger.info(f"ProactiveEngine stopped for session {self.session_id}")

    def pause(self) -> None:
        """Pause while user is actively speaking/processing."""
        self._paused = True

    def resume(self) -> None:
        """Resume after the cat finishes responding."""
        self._paused = False

    # ──────────────────────────────────────────────
    # Helper
    # ──────────────────────────────────────────────

    def _session_is_idle(self) -> bool:
        from app.api.session_manager import session_manager
        from app.api.models import SessionStatus
        session = session_manager.get_session(self.session_id)
        return bool(session and session.status == SessionStatus.IDLE)

    # ──────────────────────────────────────────────
    # Background Loops
    # ──────────────────────────────────────────────

    async def _passive_sound_loop(self) -> None:
        """Emit random cat sounds at short random intervals."""
        await asyncio.sleep(15)  # Brief startup grace period
        while self._running:
            try:
                interval = self.mood_manager.get_passive_sound_interval()
                await asyncio.sleep(interval)
                if not self._running:
                    break
                if self._paused or not self._session_is_idle():
                    continue
                sound_name = self.mood_manager.get_passive_sound()
                await self._broadcast_cat_sound(sound_name)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.session_id}] Passive sound loop error: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _proactive_speech_loop(self) -> None:
        """Generate LLM+TTS proactive speech at longer random intervals."""
        await asyncio.sleep(30)  # Longer startup delay
        while self._running:
            try:
                interval = self.mood_manager.get_proactive_interval()
                await asyncio.sleep(interval)
                if not self._running:
                    break
                if self._paused or not self._session_is_idle():
                    continue
                await self._trigger_proactive_speech()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.session_id}] Proactive speech loop error: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def _mood_tick_loop(self) -> None:
        """Check mood transitions every 60 seconds."""
        while self._running:
            try:
                await asyncio.sleep(60)
                if not self._running:
                    break
                new_mood = self.mood_manager.tick()
                if new_mood is not None:
                    await self._broadcast_cat_mood_change(new_mood)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.session_id}] Mood tick loop error: {e}", exc_info=True)

    # ──────────────────────────────────────────────
    # Proactive Speech Generation
    # ──────────────────────────────────────────────

    async def _trigger_proactive_speech(self) -> None:
        from app.api.session_manager import session_manager
        from app.api.models import SessionStatus

        session = session_manager.get_session(self.session_id)
        if not session:
            return

        mood = self.mood_manager.current_mood
        context = session.get_context(num_turns=3)
        system_prompt = get_proactive_prompt(mood) + get_context_note(context)

        logger.info(f"[{self.session_id}] Triggering proactive speech — mood={mood}")

        try:
            # Keep the session alive in the cleanup check — proactive speech
            # counts as activity even without user input.
            from datetime import datetime
            session.updated_at = datetime.utcnow()

            # Mark session as speaking so other triggers don't fire
            session.status = SessionStatus.SPEAKING
            await self._broadcast_cat_state("speaking")

            # Generate text (LLM call in thread)
            text = await asyncio.to_thread(self._call_llm, system_prompt)
            if not text:
                session.status = SessionStatus.IDLE
                await self._broadcast_cat_state("idle")
                return

            # Generate TTS
            audio_path = await self._synthesize_tts(text)
            if not audio_path:
                session.status = SessionStatus.IDLE
                await self._broadcast_cat_state("idle")
                return

            # Apply cat voice pitch shift
            if settings.CAT_VOICE_PITCH_SEMITONES != 0.0:
                from app.utils.audio_pitch import pitch_shift_wav_inplace
                await asyncio.to_thread(
                    pitch_shift_wav_inplace, audio_path, settings.CAT_VOICE_PITCH_SEMITONES
                )

            # Get duration
            from app.utils.wav_utils import get_wav_info
            wav_info = await asyncio.to_thread(get_wav_info, audio_path)
            duration_ms = int(wav_info.get("duration", 2.0) * 1000)

            # Build URL
            filename = os.path.basename(audio_path)
            base_url = settings.PUBLIC_URL or f"http://{settings.SERVICE_HOST}:{settings.SERVICE_PORT}"
            audio_url = f"{base_url}/api/audio/{self.session_id}/{filename}"

            # Broadcast to frontend
            await self._broadcast_cat_proactive(text, audio_url, duration_ms, mood)

            # Wait for audio to finish + 1s buffer, then restore idle
            await asyncio.sleep((duration_ms / 1000.0) + 1.0)

        except Exception as e:
            logger.error(f"[{self.session_id}] Proactive speech failed: {e}", exc_info=True)
        finally:
            session = session_manager.get_session(self.session_id)
            if session and session.status == SessionStatus.SPEAKING:
                session.status = SessionStatus.IDLE
                await self._broadcast_cat_state("idle")

    def _call_llm(self, system_prompt: str) -> Optional[str]:
        """
        Synchronous LLM call for proactive text generation.

        Tries Claude first (fast), falls back to Ollama on any error.
        Uses a minimal trigger prompt — the full personality lives in the system prompt.
        """
        prompt = "..."  # The system prompt carries all context

        # ── Try Claude first ────────────────────────────────────────────────
        if settings.ANTHROPIC_API_KEY:
            try:
                from app.pipeline.processors.llm_claude import ClaudeLLMProcessor
                sentences = list(
                    ClaudeLLMProcessor().generate_sentences_stream(
                        prompt, context=None, system_prompt=system_prompt
                    )
                )
                if sentences:
                    return " ".join(sentences)
            except Exception as exc:
                logger.warning(
                    f"[{self.session_id}] Proactive Claude failed "
                    f"({type(exc).__name__}), falling back to Ollama"
                )

        # ── Fallback: Ollama ─────────────────────────────────────────────────
        try:
            from app.pipeline.processors.llm_ollama import OllamaLLMProcessor
            return OllamaLLMProcessor().generate(
                prompt=prompt, system_prompt=system_prompt
            )
        except Exception as exc:
            logger.error(f"[{self.session_id}] Proactive Ollama failed: {exc}")
            return None

    async def _synthesize_tts(self, text: str) -> Optional[str]:
        """Generate TTS audio and return the file path."""
        try:
            from app.pipeline.pipeline_runner import _create_tts_processor
            audio_dir = os.path.join(settings.AUDIO_DIR, self.session_id)
            os.makedirs(audio_dir, exist_ok=True)
            proactive_id = f"proactive_{uuid.uuid4().hex[:8]}.wav"
            audio_path = os.path.join(audio_dir, proactive_id)
            tts = _create_tts_processor()
            success = await asyncio.to_thread(tts.synthesize, text, audio_path)
            return audio_path if success else None
        except Exception as e:
            logger.error(f"[{self.session_id}] Proactive TTS failed: {e}")
            return None

    # ──────────────────────────────────────────────
    # Broadcast Helpers
    # ──────────────────────────────────────────────

    async def _broadcast_cat_sound(self, sound_name: str) -> None:
        try:
            from app.api.ws import connection_manager
            await connection_manager.broadcast_cat_sound(
                self.session_id, sound_name, self.mood_manager.current_mood.value
            )
        except Exception as e:
            logger.debug(f"[{self.session_id}] Could not broadcast cat.sound: {e}")

    async def _broadcast_cat_proactive(
        self, text: str, audio_url: str, duration_ms: int, mood: CatMood
    ) -> None:
        try:
            from app.api.ws import connection_manager
            await connection_manager.broadcast_cat_proactive(
                self.session_id, text, audio_url, duration_ms, mood.value
            )
        except Exception as e:
            logger.debug(f"[{self.session_id}] Could not broadcast cat.proactive: {e}")

    async def _broadcast_cat_mood_change(self, new_mood: CatMood) -> None:
        try:
            from app.api.ws import connection_manager
            await connection_manager.broadcast_cat_mood_change(
                self.session_id, new_mood.value
            )
        except Exception as e:
            logger.debug(f"[{self.session_id}] Could not broadcast cat.mood_change: {e}")

    async def _broadcast_cat_state(self, state: str) -> None:
        try:
            from app.api.ws import connection_manager
            await connection_manager.broadcast_cat_state(self.session_id, state)
        except Exception as e:
            logger.debug(f"[{self.session_id}] Could not broadcast cat.state: {e}")
