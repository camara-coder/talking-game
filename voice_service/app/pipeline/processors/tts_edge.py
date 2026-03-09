"""
Text-to-Speech (TTS) Processor using Edge TTS
Cloud-compatible TTS using Microsoft Edge's speech service

edge-tts outputs MP3 bytes internally. This processor saves a temporary
MP3, converts it to WAV via ffmpeg subprocess, then removes the temp file.
ffmpeg is already a project dependency (used elsewhere in the audio pipeline).
"""
import asyncio
import logging
import os
import subprocess
import tempfile
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EdgeTTSProcessor:
    """Text-to-Speech processor using Edge TTS (Microsoft Edge cloud TTS)"""

    def __init__(self, voice: str = None):
        """
        Initialize Edge TTS processor

        Args:
            voice: SSML voice name. Defaults to settings.EDGE_TTS_VOICE.
                   Good cartoon-cat voices for kids:
                   - en-US-AriaNeural      (bright, enthusiastic female)
                   - en-US-JennyNeural     (warm, friendly female)
                   - en-US-AnaNeural       (child voice — youngest, playful)
                   - en-GB-MaisieNeural    (British child voice)
        """
        self.voice = voice or settings.EDGE_TTS_VOICE
        logger.info(f"Edge TTS processor initialized with voice: {self.voice}")

    async def synthesize_async(self, text: str, output_path: str) -> bool:
        """
        Synthesize text to a WAV file (async).

        edge-tts natively produces MP3; this method saves a temporary MP3
        then converts it to WAV using ffmpeg before returning.

        Args:
            text: Text to synthesize
            output_path: Destination WAV file path

        Returns:
            True if successful, False otherwise
        """
        try:
            import edge_tts
        except ImportError:
            logger.error(
                "edge-tts is not installed. "
                "Add it to requirements.txt: edge-tts>=6.1.9"
            )
            return False

        logger.info(f"Edge TTS synthesizing: '{text}' → {output_path}")

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # edge-tts produces MP3 data.  Save to a temp file, then
            # convert to WAV with ffmpeg.
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_mp3 = tmp.name

            try:
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(tmp_mp3)

                # Verify MP3 was written
                if not os.path.exists(tmp_mp3) or os.path.getsize(tmp_mp3) == 0:
                    logger.error("edge-tts produced no output")
                    return False

                # Convert MP3 → WAV (mono, 24 kHz, PCM-16)
                cmd = [
                    "ffmpeg", "-y",
                    "-i", tmp_mp3,
                    "-ar", "24000",
                    "-ac", "1",
                    "-sample_fmt", "s16",
                    output_path,
                ]
                proc = await asyncio.to_thread(
                    subprocess.run, cmd,
                    capture_output=True, timeout=30
                )
                if proc.returncode != 0:
                    logger.error(
                        f"ffmpeg conversion failed (rc={proc.returncode}): "
                        f"{proc.stderr.decode(errors='replace')}"
                    )
                    return False

            finally:
                # Always remove temp MP3
                try:
                    os.unlink(tmp_mp3)
                except OSError:
                    pass

            file_size = os.path.getsize(output_path)
            logger.info(f"Edge TTS complete: {output_path} ({file_size} bytes)")
            return True

        except Exception as e:
            logger.error(f"Error during Edge TTS synthesis: {e}", exc_info=True)
            return False

    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Synchronous wrapper for synthesize_async.

        Runs the async coroutine in a fresh event loop so it can be
        called from a ThreadPoolExecutor (asyncio.to_thread).
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.synthesize_async(text, output_path))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in synchronous wrapper: {e}", exc_info=True)
            return False

    @staticmethod
    async def list_voices():
        """List all available Edge TTS voices"""
        import edge_tts
        voices = await edge_tts.list_voices()
        for v in voices:
            logger.info(
                f"  {v['ShortName']} - {v['Gender']} "
                f"({v['Locale']}) - {v['FriendlyName']}"
            )
        return voices


# Alias for backward compatibility
TTSProcessor = EdgeTTSProcessor
