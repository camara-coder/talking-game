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


class STTProcessor:
    """Speech-to-Text processor using faster-whisper"""

    def __init__(
        self,
        model_size: str = None,
        device: str = None,
        compute_type: str = None
    ):
        """
        Initialize STT processor

        Args:
            model_size: Whisper model size (tiny.en, base.en, small.en, etc.)
            device: Device to run on ("cpu" or "cuda")
            compute_type: Compute type (int8, float16, float32)
        """
        self.model_size = model_size or settings.STT_MODEL_SIZE
        self.device = device or settings.STT_DEVICE
        self.compute_type = compute_type or settings.STT_COMPUTE_TYPE

        logger.info(
            f"Initializing STT: model={self.model_size}, "
            f"device={self.device}, compute={self.compute_type}"
        )

        # Load model (first time will download)
        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type
        )

        logger.info("STT model loaded successfully")

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
            # faster-whisper expects audio in the correct sample rate (16kHz)
            # If audio is not 16kHz, we should resample
            if sample_rate != 16000:
                logger.warning(
                    f"Audio sample rate is {sample_rate}Hz, "
                    "faster-whisper works best with 16kHz"
                )
                # Resample if needed
                from app.utils.audio_io import resample_audio
                audio = resample_audio(audio, sample_rate, 16000)
                sample_rate = 16000

            # Transcribe
            segments, info = self.model.transcribe(
                audio,
                beam_size=settings.STT_BEAM_SIZE,
                language=settings.STT_LANGUAGE,
                vad_filter=False,  # We already did VAD
                condition_on_previous_text=False
            )

            # Collect all segments
            transcript_parts = []
            for segment in segments:
                transcript_parts.append(segment.text)
                logger.debug(
                    f"Segment [{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}"
                )

            # Combine segments
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
