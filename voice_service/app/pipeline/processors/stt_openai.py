"""
Speech-to-Text (STT) Processor using OpenAI Whisper API
High-accuracy cloud-based speech recognition
"""
import logging
import tempfile
import numpy as np
import soundfile as sf
from typing import Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIWhisperProcessor:
    """
    OpenAI Whisper API processor for speech-to-text
    Provides highly accurate speech recognition via cloud API
    """

    def __init__(self):
        """Initialize OpenAI Whisper processor"""
        logger.info("Initializing OpenAI Whisper STT processor")

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai is required for OpenAI Whisper STT. "
                "Install with: pip install openai"
            )

        # Get API key from settings
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required. "
                "Set it in your .env file or environment variables. "
                "Get your API key from: https://platform.openai.com/api-keys"
            )

        # Initialize OpenAI client
        self.client = OpenAI(api_key=api_key)
        self.model = settings.OPENAI_WHISPER_MODEL
        self.language = settings.STT_LANGUAGE

        logger.info(f"OpenAI Whisper processor initialized: model={self.model}, language={self.language}")

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> Optional[str]:
        """
        Transcribe audio to text using OpenAI Whisper API

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

                # Open file and send to OpenAI Whisper API
                with open(temp_path, 'rb') as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        language=self.language
                    )

            # Clean up temp file
            import os
            try:
                os.unlink(temp_path)
            except:
                pass

            processing_time = time.time() - start_time

            # Extract text from response
            text = transcript.text.strip()

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
                    "Invalid API key. Please check your OPENAI_API_KEY. "
                    "Get your API key from: https://platform.openai.com/api-keys"
                )
            elif "quota" in str(e).lower():
                logger.error(
                    "OpenAI quota exceeded. "
                    "You may need to add credits or upgrade your plan."
                )

            return None


# Alias for backward compatibility
STTProcessor = OpenAIWhisperProcessor
