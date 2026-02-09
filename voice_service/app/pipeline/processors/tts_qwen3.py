"""
Text-to-Speech (TTS) Processor using Qwen3-TTS
Local, open-source neural TTS with streaming-capable models.
"""
import logging
import os
from typing import Optional

import numpy as np
import soundfile as sf
import torch

from app.config import settings

logger = logging.getLogger(__name__)

_qwen_model = None
_qwen_model_id = None


def _get_torch_dtype(dtype_name: str):
    name = (dtype_name or "").lower()
    if name in ("bf16", "bfloat16"):
        return torch.bfloat16
    if name in ("fp16", "float16", "half"):
        return torch.float16
    return torch.float32


def _get_qwen_model():
    global _qwen_model, _qwen_model_id
    model_id = settings.QWEN_TTS_MODEL_ID
    if _qwen_model is None or _qwen_model_id != model_id:
        logger.info(f"Loading Qwen3-TTS model: {model_id}")
        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError as e:
            raise ImportError(
                "qwen-tts is required for Qwen3-TTS. "
                "Install with: pip install qwen-tts"
            ) from e

        dtype = _get_torch_dtype(settings.QWEN_TTS_DTYPE)
        kwargs = {
            "device_map": settings.QWEN_TTS_DEVICE,
            "dtype": dtype,
        }
        if settings.QWEN_TTS_ATTN_IMPL:
            kwargs["attn_implementation"] = settings.QWEN_TTS_ATTN_IMPL

        _qwen_model = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
        _qwen_model_id = model_id
        logger.info("Qwen3-TTS model loaded successfully")
    return _qwen_model


class Qwen3TTSProcessor:
    """
    Qwen3-TTS processor for local speech synthesis
    """

    def __init__(self):
        self.model = _get_qwen_model()
        self.language = settings.QWEN_TTS_LANGUAGE
        self.speaker = settings.QWEN_TTS_SPEAKER
        self.instruction = settings.QWEN_TTS_INSTRUCTION

        # Validate speaker if available
        try:
            speakers = self.model.get_supported_speakers()
            if not self.speaker or self.speaker.lower() == "auto":
                self.speaker = speakers[0]
            elif self.speaker not in speakers:
                logger.warning(
                    f"Speaker '{self.speaker}' not supported. "
                    f"Using default '{speakers[0]}'"
                )
                self.speaker = speakers[0]
        except Exception:
            # Some variants may not expose speaker list
            pass

        logger.info(
            f"Qwen3-TTS initialized: model={settings.QWEN_TTS_MODEL_ID}, "
            f"language={self.language}, speaker={self.speaker}"
        )

    def _generate(self, text: str):
        model_id = settings.QWEN_TTS_MODEL_ID
        language = self.language if self.language and self.language.lower() != "auto" else "Auto"
        instruct = self.instruction if self.instruction else None

        if "VoiceDesign" in model_id:
            return self.model.generate_voice_design(
                text=text,
                language=language,
                instruct=instruct or "Warm, friendly voice for a young child.",
            )
        if "CustomVoice" in model_id:
            return self.model.generate_custom_voice(
                text=text,
                language=language,
                speaker=self.speaker,
                instruct=instruct,
            )
        raise ValueError(
            "QWEN_TTS_MODEL_ID must be a VoiceDesign or CustomVoice variant. "
            "Base variants require voice cloning inputs and are not supported yet."
        )

    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Synthesize text to a WAV file.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file
        """
        logger.info(f"Synthesizing text with Qwen3-TTS: '{text}'")

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            wavs, sample_rate = self._generate(text)

            if not wavs or sample_rate is None:
                logger.error("Qwen3-TTS returned no audio")
                return False

            audio = wavs[0]
            if isinstance(audio, torch.Tensor):
                audio = audio.detach().cpu().numpy()
            audio = np.asarray(audio, dtype=np.float32)

            sf.write(output_path, audio, sample_rate)

            file_size = os.path.getsize(output_path)
            duration = len(audio) / float(sample_rate)
            logger.info(
                f"TTS complete: {output_path} "
                f"({file_size} bytes, {duration:.2f}s)"
            )
            return True

        except Exception as e:
            logger.error(f"Error during Qwen3-TTS synthesis: {e}", exc_info=True)
            return False


# Alias for backward compatibility
TTSProcessor = Qwen3TTSProcessor
