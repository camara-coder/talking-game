"""
Text-to-Speech (TTS) Processor using Pocket-TTS (Kyutai).
Ultra-lightweight 100M-parameter TTS that runs efficiently on CPU.
"""
import logging
import os
from typing import Optional

import numpy as np
import soundfile as sf

from app.config import settings

logger = logging.getLogger(__name__)

_pocket_model = None
_pocket_voice_state = None


def _get_pocket_model():
    global _pocket_model, _pocket_voice_state
    if _pocket_model is None:
        logger.info("Loading Pocket-TTS model...")
        try:
            from pocket_tts import TTSModel
        except ImportError as e:
            raise ImportError(
                "pocket-tts is required for Pocket-TTS. "
                "Install with: pip install pocket-tts"
            ) from e

        _pocket_model = TTSModel.load_model()

        # Load voice state from configured voice name or WAV file
        voice = settings.POCKET_TTS_VOICE
        logger.info(f"Loading Pocket-TTS voice: {voice}")
        _pocket_voice_state = _pocket_model.get_state_for_audio_prompt(voice)

        logger.info("Pocket-TTS model loaded successfully")
    return _pocket_model, _pocket_voice_state


class PocketTTSProcessor:
    """
    Pocket-TTS processor for ultra-lightweight, CPU-optimized speech synthesis.
    100M parameters, ~200ms first audio chunk, RTF ~0.17 on CPU.
    """

    def __init__(self):
        self.model, self.voice_state = _get_pocket_model()

    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Synthesize text to a WAV file.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Synthesizing text with Pocket-TTS: '{text}'")

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            audio = self.model.generate_audio(self.voice_state, text)

            if audio is None:
                logger.error("Pocket-TTS returned no audio")
                return False

            # Convert to numpy if it's a torch tensor
            audio_np = audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio)
            audio_np = audio_np.astype(np.float32)

            sample_rate = self.model.sample_rate
            sf.write(output_path, audio_np, sample_rate)

            file_size = os.path.getsize(output_path)
            duration = len(audio_np) / float(sample_rate)
            logger.info(
                f"TTS complete: {output_path} "
                f"({file_size} bytes, {duration:.2f}s)"
            )
            return True

        except Exception as e:
            logger.error(f"Error during Pocket-TTS synthesis: {e}", exc_info=True)
            return False


# Alias for backward compatibility
TTSProcessor = PocketTTSProcessor
