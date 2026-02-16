"""
Speech-to-Text (STT) Processor using Moonshine (Useful Sensors).
Lightweight, CPU-optimized ASR with built-in streaming and VAD support.
"""
import logging
import tempfile
from typing import Optional

import numpy as np
import soundfile as sf

from app.config import settings

logger = logging.getLogger(__name__)

_moonshine_transcriber = None


def _get_moonshine_transcriber():
    global _moonshine_transcriber
    if _moonshine_transcriber is None:
        model_name = settings.MOONSHINE_MODEL_NAME
        logger.info(f"Loading Moonshine model: {model_name}")
        try:
            from moonshine_voice import Transcriber
        except ImportError as e:
            raise ImportError(
                "moonshine-voice is required for Moonshine STT. "
                "Install with: pip install moonshine-voice"
            ) from e

        _moonshine_transcriber = Transcriber(model_name=model_name)
        logger.info(f"Moonshine model loaded: {model_name}")
    return _moonshine_transcriber


class MoonshineSTTProcessor:
    """
    Moonshine STT processor for lightweight, CPU-optimized speech recognition.
    Supports tiny (34M), small (123M), and medium (245M) streaming models.
    """

    def __init__(self):
        self.transcriber = _get_moonshine_transcriber()

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """
        Transcribe audio using Moonshine.

        Args:
            audio: Audio data as float32 numpy array
            sample_rate: Sample rate in Hz (16000 expected)

        Returns:
            Transcribed text or None
        """
        try:
            if len(audio) == 0:
                return None

            duration = len(audio) / sample_rate
            logger.info(
                f"Transcribing audio with Moonshine: "
                f"{len(audio)} samples, {duration:.2f}s"
            )

            # Moonshine expects a WAV file path or audio array at 16kHz
            # Write to temp file for compatibility with the Transcriber API
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
                sf.write(temp_path, audio, sample_rate, subtype="PCM_16")

            try:
                text = self.transcriber.transcribe(temp_path)
                if isinstance(text, list):
                    text = " ".join(text)
                text = text.strip() if text else ""
            finally:
                try:
                    import os
                    os.unlink(temp_path)
                except Exception:
                    pass

            if text:
                logger.info(f"Transcription complete: '{text}'")
                return text
            logger.warning("Transcription returned empty text")
            return None

        except Exception as e:
            logger.error(f"Error during Moonshine transcription: {e}", exc_info=True)
            return None


# Alias for backward compatibility
STTProcessor = MoonshineSTTProcessor
