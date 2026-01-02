"""
Text-to-Speech (TTS) Processor
Uses pyttsx3 for offline TTS with Windows voices
"""
import pyttsx3
import logging
import os
import tempfile
from typing import Optional

from app.config import settings
from app.utils.wav_utils import get_wav_duration

logger = logging.getLogger(__name__)


class TTSProcessor:
    """Text-to-Speech processor using pyttsx3"""

    def __init__(self, voice_id: Optional[str] = None):
        """
        Initialize TTS processor

        Args:
            voice_id: Optional specific voice ID to use
        """
        logger.info("Initializing TTS processor...")

        # Initialize pyttsx3 engine
        self.engine = pyttsx3.init()

        # Configure voice properties
        voices = self.engine.getProperty('voices')

        # Try to find a kid-friendly voice (typically female, higher pitch)
        # On Windows, this will use SAPI5 voices
        selected_voice = None

        if voice_id:
            # Use specific voice if provided
            for voice in voices:
                if voice.id == voice_id:
                    selected_voice = voice
                    break
        else:
            # Try to find a suitable voice
            # Prefer female voices (often sound friendlier for kids)
            for voice in voices:
                if 'zira' in voice.name.lower() or 'hazel' in voice.name.lower():
                    selected_voice = voice
                    break

            # Fallback to first female voice
            if not selected_voice:
                for voice in voices:
                    if 'female' in voice.name.lower() or voice.gender == 'VoiceGenderFemale':
                        selected_voice = voice
                        break

            # Ultimate fallback to first available voice
            if not selected_voice and voices:
                selected_voice = voices[0]

        if selected_voice:
            self.engine.setProperty('voice', selected_voice.id)
            logger.info(f"Selected voice: {selected_voice.name}")
        else:
            logger.warning("No suitable voice found, using default")

        # Set speech rate (words per minute)
        # Default is ~200, we'll slow it down a bit for kids
        self.engine.setProperty('rate', 160)

        # Set volume (0.0 to 1.0)
        self.engine.setProperty('volume', 0.9)

        logger.info("TTS processor initialized successfully")

    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Synthesize text to audio file

        Args:
            text: Text to synthesize
            output_path: Path to save WAV file

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Synthesizing text: '{text}'")

        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save to file
            self.engine.save_to_file(text, output_path)

            # Run the synthesis
            self.engine.runAndWait()

            # Verify file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                duration = get_wav_duration(output_path)

                logger.info(
                    f"TTS complete: {output_path} "
                    f"({file_size} bytes, {duration:.2f}s)"
                )
                return True
            else:
                logger.error(f"TTS file was not created: {output_path}")
                return False

        except Exception as e:
            logger.error(f"Error during TTS synthesis: {e}", exc_info=True)
            return False

    def get_available_voices(self):
        """
        Get list of available voices

        Returns:
            List of voice objects
        """
        return self.engine.getProperty('voices')

    def list_voices(self):
        """Print available voices for debugging"""
        voices = self.get_available_voices()
        logger.info(f"Available voices ({len(voices)}):")
        for i, voice in enumerate(voices):
            logger.info(
                f"  [{i}] {voice.name} "
                f"(ID: {voice.id}, Languages: {voice.languages})"
            )
