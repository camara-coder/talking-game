"""
Speech-to-Text (STT) Processor
Uses faster-whisper for audio transcription
"""
from faster_whisper import WhisperModel
import numpy as np
import logging
from typing import Optional
import time

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton — model is loaded once and reused across requests.
# faster-whisper models are large (244MB for small.en) and slow to load;
# reloading on every pipeline instantiation would add multi-second latency
# to every request.
_whisper_model: Optional[WhisperModel] = None


def _get_whisper_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    logger.info(
        f"Loading faster-whisper model: {settings.STT_MODEL_SIZE} "
        f"(device={settings.STT_DEVICE}, compute={settings.STT_COMPUTE_TYPE})"
    )
    _whisper_model = WhisperModel(
        settings.STT_MODEL_SIZE,
        device=settings.STT_DEVICE,
        compute_type=settings.STT_COMPUTE_TYPE,
    )
    logger.info(f"faster-whisper model loaded: {settings.STT_MODEL_SIZE}")
    return _whisper_model


class STTProcessor:
    """Speech-to-Text processor using faster-whisper"""

    def __init__(self):
        self.model = _get_whisper_model()

    def transcribe(self, audio: np.ndarray, sample_rate: int = None) -> Optional[str]:
        """
        Transcribe audio to text

        Args:
            audio: Audio data as float32 numpy array
            sample_rate: Sample rate in Hz

        Returns:
            Transcribed text or None if transcription failed
        """
        if sample_rate is None:
            sample_rate = settings.AUDIO_SAMPLE_RATE

        logger.info(
            f"Transcribing audio: {len(audio)} samples, "
            f"{len(audio) / sample_rate:.2f}s"
        )

        start_time = time.time()

        try:
            # faster-whisper expects 16kHz audio
            if sample_rate != 16000:
                logger.warning(
                    f"Audio sample rate is {sample_rate}Hz, "
                    "faster-whisper works best with 16kHz"
                )
                from app.utils.audio_io import resample_audio
                audio = resample_audio(audio, sample_rate, 16000)
                sample_rate = 16000

            # Transcribe — initial_prompt biases the decoder towards domain
            # vocabulary (cat, fish, pet, meow...) without constraining it.
            segments, info = self.model.transcribe(
                audio,
                beam_size=settings.STT_BEAM_SIZE,
                language=settings.STT_LANGUAGE,
                vad_filter=False,  # We already did VAD
                condition_on_previous_text=False,
                initial_prompt=settings.STT_INITIAL_PROMPT or None,
            )

            # Collect all segments
            transcript_parts = []
            for segment in segments:
                transcript_parts.append(segment.text)
                logger.debug(
                    f"Segment [{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}"
                )

            transcript = " ".join(transcript_parts).strip()
            elapsed_time = time.time() - start_time

            if transcript:
                logger.info(
                    f"Transcription complete: '{transcript}' "
                    f"({elapsed_time:.2f}s, language={info.language}, "
                    f"probability={info.language_probability:.2f})"
                )
                return transcript
            else:
                logger.warning("Transcription returned empty text")
                return None

        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            return None
