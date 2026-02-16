"""
Speech-to-Text (STT) Processor using Moonshine (Useful Sensors).
Lightweight, CPU-optimized ASR with built-in streaming and VAD support.
"""
import logging
import os
from typing import Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

_moonshine_transcriber = None

# Map config model names to (model_name, ModelArch) pairs.
# Available English models: tiny-en, base-en,
# tiny-streaming-en, small-streaming-en, medium-streaming-en
_MODEL_MAP = {
    "tiny": ("tiny-en", "TINY"),
    "base": ("base-en", "BASE"),
    "tiny-streaming": ("tiny-streaming-en", "TINY_STREAMING"),
    "small-streaming": ("small-streaming-en", "SMALL_STREAMING"),
    "medium-streaming": ("medium-streaming-en", "MEDIUM_STREAMING"),
}


def _get_moonshine_transcriber():
    global _moonshine_transcriber
    if _moonshine_transcriber is not None:
        return _moonshine_transcriber

    model_key = settings.MOONSHINE_MODEL_NAME.lower()
    logger.info(f"Loading Moonshine model: {model_key}")

    try:
        from moonshine_voice import Transcriber, get_model_path, ModelArch
    except ImportError as e:
        raise ImportError(
            "moonshine-voice is required for Moonshine STT. "
            "Install with: pip install moonshine-voice"
        ) from e

    entry = _MODEL_MAP.get(model_key)
    if entry is None:
        valid = ", ".join(sorted(_MODEL_MAP.keys()))
        raise ValueError(
            f"Unknown MOONSHINE_MODEL_NAME '{model_key}'. "
            f"Supported: {valid}"
        )

    model_name, arch_name = entry
    model_arch = ModelArch[arch_name]

    model_path = str(get_model_path(model_name))
    logger.info(f"Moonshine model path: {model_path}, arch: {arch_name}")

    _moonshine_transcriber = Transcriber(
        model_path=model_path,
        model_arch=model_arch,
    )
    logger.info(f"Moonshine model loaded: {model_name}")
    return _moonshine_transcriber


class MoonshineSTTProcessor:
    """
    Moonshine STT processor for lightweight, CPU-optimized speech recognition.
    Supports tiny (34M), base, small-streaming (123M), and medium-streaming (245M) models.
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

            # transcribe_without_streaming accepts List[float] and sample_rate
            audio_list = audio.astype(np.float32).tolist()
            transcript = self.transcriber.transcribe_without_streaming(
                audio_list, sample_rate
            )

            # Transcript has .lines, each with .text
            if not transcript or not transcript.lines:
                logger.warning("Transcription returned no lines")
                return None

            text = " ".join(
                line.text for line in transcript.lines if line.text
            ).strip()

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
