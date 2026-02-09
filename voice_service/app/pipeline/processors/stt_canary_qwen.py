"""
Speech-to-Text (STT) Processor using NVIDIA Canary-Qwen-2.5B (NeMo).
"""
import logging
import tempfile
from typing import Optional

import numpy as np
import soundfile as sf
import torch

from app.config import settings

logger = logging.getLogger(__name__)

_canary_model = None


def _get_device():
    device = settings.CANARY_QWEN_DEVICE
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return device


def _get_canary_model():
    global _canary_model
    if _canary_model is None:
        logger.info(f"Loading Canary-Qwen model: {settings.CANARY_QWEN_MODEL_ID}")
        try:
            from nemo.collections.speechlm2.models import SALM
        except ImportError as e:
            raise ImportError(
                "nemo_toolkit is required for Canary-Qwen STT. "
                "Install with: pip install nemo_toolkit[asr,tts] @ git+https://github.com/NVIDIA/NeMo.git"
            ) from e

        device = _get_device()
        _canary_model = SALM.from_pretrained(settings.CANARY_QWEN_MODEL_ID)
        _canary_model.to(device)
        _canary_model.eval()
        logger.info(f"Canary-Qwen model loaded on {device}")
    return _canary_model


class CanaryQwenSTTProcessor:
    """
    Canary-Qwen-2.5B STT processor (NeMo).
    """

    def __init__(self):
        self.model = _get_canary_model()

    def _build_prompt(self, model, audio_path: str) -> list:
        """
        Build the NeMo Canary prompt with audio locator tag.
        """
        prompt_text = settings.CANARY_QWEN_PROMPT or "Transcribe the following:"
        if model.audio_locator_tag not in prompt_text:
            prompt_text = f"{prompt_text} {model.audio_locator_tag}"
        return [[{"role": "user", "content": prompt_text, "audio": [audio_path]}]]

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """
        Transcribe audio using Canary-Qwen-2.5B.
        """
        try:
            if len(audio) == 0:
                return None

            logger.info(f"Transcribing audio with Canary-Qwen: {len(audio)} samples, {len(audio)/sample_rate:.2f}s")

            # Write audio to temp WAV (Canary expects file path)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                sf.write(temp_path, audio, sample_rate, subtype="PCM_16")

            try:
                model = self.model
                prompt = self._build_prompt(model, temp_path)
                with torch.no_grad():
                    outputs = model.generate(
                        prompts=prompt,
                        max_new_tokens=settings.CANARY_QWEN_MAX_TOKENS,
                        temperature=settings.CANARY_QWEN_TEMPERATURE,
                        top_p=settings.CANARY_QWEN_TOP_P,
                    )
                # Canary returns token ids; decode with tokenizer
                if isinstance(outputs, list) and outputs:
                    token_ids = outputs[0]
                    text = model.tokenizer.ids_to_text(token_ids.cpu()).strip()
                else:
                    text = ""

                if text:
                    logger.info(f"Transcription complete: '{text}'")
                    return text
                logger.warning("Transcription returned empty text")
                return None
            finally:
                try:
                    import os
                    os.unlink(temp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error during Canary-Qwen transcription: {e}", exc_info=True)
            return None


# Alias for backward compatibility
STTProcessor = CanaryQwenSTTProcessor
