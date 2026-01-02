"""
Text-to-Speech (TTS) Processor using ElevenLabs API
High-quality cloud-based TTS for fast, natural-sounding speech
"""
import os
import logging
import asyncio
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class ElevenLabsTTSProcessor:
    """
    ElevenLabs TTS processor using the official elevenlabs Python SDK
    Provides high-quality, natural-sounding speech synthesis via cloud API
    """

    def __init__(self, voice: str = "Rachel"):
        """
        Initialize ElevenLabs TTS processor

        Args:
            voice: Voice identifier (default: Rachel - clear, friendly female)
                   Popular kid-friendly voices:
                   - Rachel: Clear, friendly female
                   - Bella: Warm, gentle female
                   - Antoni: Friendly male
                   - Josh: Clear male
        """
        logger.info(f"Initializing ElevenLabs TTS processor with voice: {voice}")

        try:
            from elevenlabs.client import ElevenLabs
        except ImportError:
            raise ImportError(
                "elevenlabs is required for ElevenLabs TTS. "
                "Install with: pip install elevenlabs"
            )

        # Get API key from settings
        api_key = settings.ELEVENLABS_API_KEY
        if not api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY is required. "
                "Set it in your .env file or environment variables. "
                "Get your API key from: https://elevenlabs.io"
            )

        # Initialize ElevenLabs client
        self.client = ElevenLabs(api_key=api_key)
        self.voice = voice
        self.model = settings.ELEVENLABS_MODEL

        logger.info("ElevenLabs TTS processor initialized successfully")

    async def synthesize_async(self, text: str, output_path: str) -> bool:
        """
        Synthesize text to audio file (async)

        Args:
            text: Text to synthesize
            output_path: Path to save audio file (WAV format)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Synthesizing text: '{text}'")

        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Generate speech using ElevenLabs API
            logger.info("Calling ElevenLabs API...")

            # Call the API (returns an iterator of audio chunks)
            # Using PCM format for WAV output
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice,
                model_id=self.model,
                output_format="pcm_24000"
            )

            # Collect all audio chunks
            audio_chunks = []
            for chunk in audio_generator:
                if chunk:
                    audio_chunks.append(chunk)

            # Combine all chunks into a single audio file
            audio_data = b''.join(audio_chunks)

            # Convert raw PCM data to WAV file with proper headers
            # ElevenLabs PCM format: 24000 Hz, mono, 16-bit
            import wave
            import numpy as np

            # Convert bytes to numpy array (16-bit PCM)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Write as WAV file with proper headers
            with wave.open(output_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(24000)  # 24kHz
                wav_file.writeframes(audio_array.tobytes())

            # Get file info
            file_size = os.path.getsize(output_path)

            # Estimate duration (ElevenLabs typically outputs MP3 at ~128kbps)
            # For more accurate duration, we'd need to parse the audio file
            estimated_duration = file_size / 16000  # Rough estimate

            logger.info(
                f"TTS complete: {output_path} "
                f"({file_size} bytes, ~{estimated_duration:.2f}s)"
            )
            return True

        except Exception as e:
            logger.error(f"Error during TTS synthesis: {e}", exc_info=True)

            # Check for common errors
            if "invalid_api_key" in str(e).lower():
                logger.error(
                    "Invalid API key. Please check your ELEVENLABS_API_KEY. "
                    "Get your API key from: https://elevenlabs.io"
                )
            elif "quota_exceeded" in str(e).lower():
                logger.error(
                    "ElevenLabs quota exceeded. "
                    "You may need to upgrade your plan or wait for quota reset."
                )

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
        # Always create a new event loop when running in a thread pool
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.synthesize_async(text, output_path))
                return result
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in synchronous wrapper: {e}", exc_info=True)
            return False


# Alias for backward compatibility
TTSProcessor = ElevenLabsTTSProcessor
