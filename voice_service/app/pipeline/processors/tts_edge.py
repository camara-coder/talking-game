"""
Text-to-Speech (TTS) Processor using Edge TTS
Cloud-compatible TTS using Microsoft Edge's speech service
"""
import edge_tts
import asyncio
import logging
import os
from typing import Optional

from app.config import settings
from app.utils.wav_utils import get_wav_duration

logger = logging.getLogger(__name__)


class EdgeTTSProcessor:
    """Text-to-Speech processor using Edge TTS (Microsoft Edge cloud TTS)"""

    def __init__(self, voice: str = "en-US-AriaNeural"):
        """
        Initialize Edge TTS processor

        Args:
            voice: Voice to use (default: en-US-AriaNeural - female, friendly)
                   Other good options for kids:
                   - en-US-JennyNeural (female, warm)
                   - en-US-GuyNeural (male, friendly)
                   - en-GB-SoniaNeural (British female)
        """
        logger.info(f"Initializing Edge TTS processor with voice: {voice}")
        self.voice = voice
        logger.info("Edge TTS processor initialized successfully")

    async def synthesize_async(self, text: str, output_path: str) -> bool:
        """
        Synthesize text to audio file (async)

        Args:
            text: Text to synthesize
            output_path: Path to save audio file

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Synthesizing text: '{text}'")

        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Create TTS communicator
            communicate = edge_tts.Communicate(text, self.voice)

            # Save to file
            await communicate.save(output_path)

            # Verify file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)

                # Try to get duration (edge-tts outputs mp3, we may need to convert)
                try:
                    duration = get_wav_duration(output_path)
                except:
                    # If it's mp3, estimate duration from file size
                    # Rough estimate: 128kbps mp3 = ~16KB per second
                    duration = file_size / 16000

                logger.info(
                    f"TTS complete: {output_path} "
                    f"({file_size} bytes, ~{duration:.2f}s)"
                )
                return True
            else:
                logger.error(f"TTS file was not created: {output_path}")
                return False

        except Exception as e:
            logger.error(f"Error during TTS synthesis: {e}", exc_info=True)
            return False

    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Synchronous wrapper for synthesize_async

        Args:
            text: Text to synthesize
            output_path: Path to save audio file

        Returns:
            True if successful, False otherwise
        """
        # Run async function in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create new loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.synthesize_async(text, output_path))
                loop.close()
            else:
                result = loop.run_until_complete(self.synthesize_async(text, output_path))
            return result
        except Exception as e:
            logger.error(f"Error in synchronous wrapper: {e}", exc_info=True)
            return False

    @staticmethod
    async def list_voices():
        """List all available Edge TTS voices"""
        voices = await edge_tts.list_voices()
        logger.info(f"Available Edge TTS voices ({len(voices)}):")
        for voice in voices:
            logger.info(
                f"  {voice['ShortName']} - {voice['Gender']} "
                f"({voice['Locale']}) - {voice['FriendlyName']}"
            )
        return voices


# Alias for backward compatibility
TTSProcessor = EdgeTTSProcessor
