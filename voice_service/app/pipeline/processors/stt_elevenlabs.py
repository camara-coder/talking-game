"""
Speech-to-Text (STT) Processor using ElevenLabs Scribe API
High-accuracy cloud-based speech recognition
"""
import logging
import tempfile
import numpy as np
import soundfile as sf
from typing import Optional
from io import BytesIO

from app.config import settings

logger = logging.getLogger(__name__)


class ElevenLabsSTTProcessor:
    """
    ElevenLabs Scribe API processor for speech-to-text
    Provides highly accurate speech recognition via cloud API
    """

    def __init__(self):
        """Initialize ElevenLabs STT processor"""
        logger.info("Initializing ElevenLabs STT processor")

        try:
            from elevenlabs.client import ElevenLabs
        except ImportError:
            raise ImportError(
                "elevenlabs is required for ElevenLabs STT. "
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
        self.model = settings.ELEVENLABS_STT_MODEL
        self.language = settings.STT_LANGUAGE

        logger.info(f"ElevenLabs STT processor initialized: model={self.model}, language={self.language}")

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> Optional[str]:
        """
        Transcribe audio to text using ElevenLabs Scribe API

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz

        Returns:
            Transcribed text (or None if failed)
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"Transcribing audio: {len(audio)} samples, {len(audio)/sample_rate:.2f}s")

            # Create temporary WAV file for upload
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name

                # Write audio to WAV file
                sf.write(temp_path, audio, sample_rate, subtype='PCM_16')

                # Read the file into BytesIO for API upload
                with open(temp_path, 'rb') as audio_file:
                    audio_data = BytesIO(audio_file.read())

            # Clean up temp file
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

            # Convert language code format
            # ElevenLabs uses 3-letter codes like "eng", "spa", etc.
            language_code = None
            if self.language:
                # Map common 2-letter codes to 3-letter codes
                lang_map = {
                    "en": "eng",
                    "es": "spa",
                    "fr": "fra",
                    "de": "deu",
                    "it": "ita",
                    "pt": "por",
                    "pl": "pol",
                    "nl": "nld",
                    "ja": "jpn",
                    "zh": "cmn",
                    "ko": "kor",
                    "ar": "ara",
                    "hi": "hin",
                    "ru": "rus",
                    "tr": "tur",
                }
                language_code = lang_map.get(self.language, None)

            # Call ElevenLabs Scribe API
            transcription = self.client.speech_to_text.convert(
                file=audio_data,
                model_id=self.model,
                language_code=language_code,  # None will auto-detect
                tag_audio_events=False,  # Don't need laughter/applause tags for kid game
                diarize=False,  # Don't need speaker identification
            )

            processing_time = time.time() - start_time

            # Extract text from response
            # The response has a 'text' attribute
            text = transcription.text.strip() if hasattr(transcription, 'text') else str(transcription).strip()

            if text:
                logger.info(
                    f"Transcription complete: '{text}' "
                    f"({processing_time:.2f}s)"
                )
                return text
            else:
                logger.warning("Transcription returned empty text")
                return None

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error during transcription: {e}", exc_info=True)

            # Check for common errors
            if "invalid_api_key" in str(e).lower():
                logger.error(
                    "Invalid API key. Please check your ELEVENLABS_API_KEY. "
                    "Get your API key from: https://elevenlabs.io"
                )
            elif "quota" in str(e).lower() or "limit" in str(e).lower():
                logger.error(
                    "ElevenLabs quota exceeded. "
                    "You may need to add credits or upgrade your plan."
                )

            return None


# Alias for backward compatibility
STTProcessor = ElevenLabsSTTProcessor
