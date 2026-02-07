"""
Noise Reduction Processor
Applies spectral gating noise reduction to improve VAD and STT accuracy.
Runs on the full accumulated audio BEFORE VAD processing.
"""
import numpy as np
import noisereduce as nr
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class NoiseReducer:
    """Server-side noise reduction using spectral gating"""

    def __init__(
        self,
        sample_rate: int = None,
        prop_decrease: float = None,
        stationary: bool = False,
    ):
        """
        Initialize noise reducer.

        Args:
            sample_rate: Audio sample rate in Hz
            prop_decrease: How much to reduce noise (0.0-1.0).
                           0.0 = no reduction, 1.0 = maximum reduction.
                           Default 0.6 is conservative — removes noise without
                           distorting children's higher-pitched voices.
            stationary: If True, assumes noise is constant (fan, hum).
                        If False, handles non-stationary noise too (TV, voices).
                        Default False for children's environments.
        """
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self.prop_decrease = prop_decrease or getattr(
            settings, 'NOISE_REDUCE_PROP_DECREASE', 0.6
        )
        self.stationary = stationary

        logger.info(
            f"NoiseReducer initialized: sample_rate={self.sample_rate}Hz, "
            f"prop_decrease={self.prop_decrease}, stationary={self.stationary}"
        )

    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Reduce noise in audio.

        IMPORTANT: This always returns audio (never None). Even if noise reduction
        fails, it returns the original audio unchanged. This ensures the pipeline
        never breaks at this stage.

        Args:
            audio: Audio data as float32 numpy array, range [-1.0, 1.0]

        Returns:
            Noise-reduced audio as float32 numpy array
        """
        if len(audio) == 0:
            return audio

        logger.info(f"Applying noise reduction: {len(audio)} samples "
                     f"({len(audio) / self.sample_rate:.2f}s)")

        try:
            # Calculate input RMS for logging
            input_rms = np.sqrt(np.mean(audio ** 2))

            reduced = nr.reduce_noise(
                y=audio,
                sr=self.sample_rate,
                stationary=self.stationary,
                prop_decrease=self.prop_decrease,
                n_fft=512,
                win_length=256,
                hop_length=128,
            )

            # Ensure output stays in valid range
            reduced = np.clip(reduced, -1.0, 1.0).astype(np.float32)

            # Calculate output RMS for logging
            output_rms = np.sqrt(np.mean(reduced ** 2))
            reduction_db = 0.0
            if input_rms > 0 and output_rms > 0:
                reduction_db = 20 * np.log10(output_rms / input_rms)

            logger.info(
                f"Noise reduction complete: RMS {input_rms:.4f} -> {output_rms:.4f} "
                f"({reduction_db:+.1f} dB)"
            )

            return reduced

        except Exception as e:
            logger.error(f"Noise reduction failed: {e}", exc_info=True)
            logger.warning("Returning original audio without noise reduction")
            return audio
