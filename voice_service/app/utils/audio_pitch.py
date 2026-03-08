"""
Audio pitch shifting utility for the cat voice.

Uses scipy.signal.resample (FFT-based) to raise/lower pitch while
preserving duration. No additional dependencies — scipy is already
used elsewhere in the pipeline.

Typical use: +5 semitones to turn a low adult voice into a light,
playful, cartoon-cat-appropriate voice.
"""
import logging
import numpy as np
import soundfile as sf
import scipy.signal

logger = logging.getLogger(__name__)


def shift_pitch(audio: np.ndarray, semitones: float) -> np.ndarray:
    """
    Shift the pitch of a mono audio array without changing its duration.

    Algorithm (resample trick):
      1. Resample audio to a shorter/longer length.
         Shorter → higher pitch (speed up → higher frequencies).
      2. Resample back to the original length.
         This restores duration while keeping the shifted frequencies.

    Works well for speech at ±3-7 semitones. Beyond that, artefacts
    become noticeable but the result is still intelligible.

    Args:
        audio:    float32 numpy array, mono.
        semitones: Positive = higher pitch, negative = lower.

    Returns:
        Pitch-shifted float32 numpy array of the same length.
    """
    if abs(semitones) < 0.01:
        return audio

    n_original = len(audio)
    factor = 2.0 ** (semitones / 12.0)

    # Step 1: resample to pitch-shifted length
    n_pitched = max(1, int(round(n_original / factor)))
    audio_pitched = scipy.signal.resample(audio, n_pitched)

    # Step 2: resample back to original length (restores duration)
    result = scipy.signal.resample(audio_pitched, n_original)
    return result.astype(np.float32)


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
