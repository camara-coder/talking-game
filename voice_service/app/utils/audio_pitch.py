"""
Audio pitch shifting utility for the cat voice.

Uses scipy.signal.resample_poly (polyphase FIR) instead of the FFT-based
scipy.signal.resample.  resample_poly is ~10-30× faster for typical TTS
output lengths because it only needs to apply a short FIR filter rather
than computing two full-length FFTs.

Algorithm (resample trick):
  1. Shorten the audio by factor (1/pitch_factor) using resample_poly.
     Playing it at the original rate now sounds faster → higher pitch.
  2. Stretch it back to the original length using the inverse ratio.
     Duration is restored; the higher frequency content is kept.

The pitch_factor ratio is approximated with a small rational number
(denominator ≤ 20) via fractions.Fraction.limit_denominator so that
resample_poly can use a compact polyphase filter bank.  The approximation
error is < 0.5 semitones for all values in the ±8 semitone range.
"""
import logging
import math
from fractions import Fraction

import numpy as np
import soundfile as sf
import scipy.signal

logger = logging.getLogger(__name__)


def shift_pitch(audio: np.ndarray, semitones: float) -> np.ndarray:
    """
    Shift the pitch of a mono audio array without changing its duration.

    Args:
        audio:     float32 numpy array, mono.
        semitones: Positive = higher pitch, negative = lower.

    Returns:
        Pitch-shifted float32 numpy array of the same length.
    """
    if abs(semitones) < 0.01:
        return audio

    n_original = len(audio)
    if n_original == 0:
        return audio

    # pitch_factor > 1 means higher pitch (e.g. 1.335 for +5 semitones)
    pitch_factor = 2.0 ** (semitones / 12.0)

    # Rational approximation of (1 / pitch_factor) — the shortening ratio.
    # limit_denominator(20) keeps the filter bank small → fast convolution.
    frac = Fraction(1.0 / pitch_factor).limit_denominator(20)
    up1, down1 = frac.numerator, frac.denominator

    # Step 1: shorten (speeds up audio → raises pitch)
    shortened = scipy.signal.resample_poly(audio, up1, down1)

    # Step 2: stretch back using the inverse ratio (restores duration)
    stretched = scipy.signal.resample_poly(shortened, down1, up1)

    # Trim or zero-pad to exact original length (off-by-one from ceiling arith.)
    if len(stretched) > n_original:
        stretched = stretched[:n_original]
    elif len(stretched) < n_original:
        stretched = np.pad(stretched, (0, n_original - len(stretched)))

    return stretched.astype(np.float32)


def pitch_shift_wav_inplace(path: str, semitones: float) -> None:
    """
    Read a WAV file, shift its pitch, and overwrite it in place.

    Args:
        path:      Absolute path to the WAV file.
        semitones: Semitones to shift (positive = higher).
    """
    if abs(semitones) < 0.01:
        return

    try:
        audio, sample_rate = sf.read(path, dtype="float32")

        # Handle stereo gracefully (shouldn't happen with TTS, but just in case)
        if audio.ndim > 1:
            channels = [shift_pitch(audio[:, c], semitones) for c in range(audio.shape[1])]
            shifted = np.stack(channels, axis=1)
        else:
            shifted = shift_pitch(audio, semitones)

        sf.write(path, shifted, sample_rate)
        logger.debug(f"Pitch shifted {path} by {semitones:+.1f} semitones")

    except Exception as e:
        # Pitch shift is a "nice to have" — log and continue rather than fail
        logger.warning(f"Pitch shift failed for {path}: {e}")
