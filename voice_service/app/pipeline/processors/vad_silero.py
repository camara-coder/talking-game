"""
Voice Activity Detection (VAD) Processor — Silero VAD
Neural network-based VAD replacing legacy webrtcvad.
Better accuracy on children's voices, background noise, and edge cases.
"""
import torch
import numpy as np
import logging
from typing import Optional

from silero_vad import load_silero_vad, get_speech_timestamps

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level model cache (loaded once, reused across instances)
_silero_model = None


def _get_silero_model():
    """Load Silero VAD model (cached singleton)."""
    global _silero_model
    if _silero_model is None:
        logger.info("Loading Silero VAD model...")
        _silero_model = load_silero_vad()
        logger.info("Silero VAD model loaded successfully")
    return _silero_model


class SileroVADProcessor:
    """Voice Activity Detection processor using Silero VAD (neural network)"""

    def __init__(
        self,
        sample_rate: int = None,
        threshold: float = None,
        min_speech_duration_ms: int = None,
        min_silence_duration_ms: int = None,
        speech_pad_ms: int = None,
    ):
        """
        Initialize Silero VAD processor.

        Args:
            sample_rate: Audio sample rate in Hz (must be 8000 or 16000)
            threshold: Speech probability threshold (0.0-1.0). Lower = more
                       sensitive, catches quieter speech but more false positives.
                       Default 0.35 is tuned for children's variable volume.
            min_speech_duration_ms: Minimum speech segment duration to keep.
                                    Filters out clicks and pops. Default 250ms.
            min_silence_duration_ms: How long silence must last to split segments.
                                     Default 150ms — generous for children who
                                     pause mid-sentence.
            speech_pad_ms: Padding added before/after each speech segment.
                           Prevents clipping first/last phonemes. Default 60ms.
        """
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self.threshold = threshold or getattr(settings, 'SILERO_VAD_THRESHOLD', 0.35)
        self.min_speech_duration_ms = min_speech_duration_ms or getattr(
            settings, 'SILERO_VAD_MIN_SPEECH_MS', 250
        )
        self.min_silence_duration_ms = min_silence_duration_ms or getattr(
            settings, 'SILERO_VAD_MIN_SILENCE_MS', 150
        )
        self.speech_pad_ms = speech_pad_ms or getattr(
            settings, 'SILERO_VAD_SPEECH_PAD_MS', 60
        )

        # Validate sample rate (Silero VAD supports 8000 and 16000)
        if self.sample_rate not in [8000, 16000]:
            raise ValueError(
                f"Silero VAD requires sample_rate 8000 or 16000, got {self.sample_rate}"
            )

        # Load model (cached globally)
        self.model = _get_silero_model()

        logger.info(
            f"Silero VAD initialized: sample_rate={self.sample_rate}Hz, "
            f"threshold={self.threshold}, "
            f"min_speech={self.min_speech_duration_ms}ms, "
            f"min_silence={self.min_silence_duration_ms}ms, "
            f"speech_pad={self.speech_pad_ms}ms"
        )

    def process(self, audio: np.ndarray) -> Optional[np.ndarray]:
        """
        Process audio and extract speech segments.

        Same interface as the old VADProcessor — takes float32 audio,
        returns trimmed float32 audio with only speech, or None.

        Args:
            audio: Audio data as float32 numpy array, range [-1.0, 1.0]

        Returns:
            Trimmed audio containing only speech, or None if no speech detected
        """
        logger.info(f"Processing audio with Silero VAD: {len(audio)} samples "
                     f"({len(audio) / self.sample_rate:.2f}s)")

        # Convert numpy float32 to torch tensor (Silero requires this)
        audio_tensor = torch.from_numpy(audio).float()

        # Ensure 1D (mono)
        if audio_tensor.dim() > 1:
            audio_tensor = audio_tensor.squeeze()

        # Get speech timestamps (sample indices)
        try:
            speech_timestamps = get_speech_timestamps(
                audio_tensor,
                self.model,
                sampling_rate=self.sample_rate,
                threshold=self.threshold,
                min_speech_duration_ms=self.min_speech_duration_ms,
                min_silence_duration_ms=self.min_silence_duration_ms,
                speech_pad_ms=self.speech_pad_ms,
                return_seconds=False,  # Return sample indices, not seconds
            )
        except Exception as e:
            logger.error(f"Silero VAD processing failed: {e}", exc_info=True)
            # Fallback: return original audio rather than losing the utterance
            logger.warning("Returning unprocessed audio as fallback")
            return audio

        if not speech_timestamps:
            logger.warning("No speech detected by Silero VAD")
            return None

        # Log detected segments
        for i, segment in enumerate(speech_timestamps):
            start_sec = segment['start'] / self.sample_rate
            end_sec = segment['end'] / self.sample_rate
            logger.debug(f"Speech segment {i}: {start_sec:.2f}s - {end_sec:.2f}s")

        # Extract and concatenate all speech segments
        speech_chunks = []
        for segment in speech_timestamps:
            start = segment['start']
            end = segment['end']
            speech_chunks.append(audio[start:end])

        speech_audio = np.concatenate(speech_chunks)

        logger.info(
            f"Silero VAD complete: {len(audio)} -> {len(speech_audio)} samples "
            f"({len(speech_audio) / self.sample_rate:.2f}s), "
            f"{len(speech_timestamps)} segment(s)"
        )

        return speech_audio
