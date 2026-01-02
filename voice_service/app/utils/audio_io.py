"""
Audio I/O utilities for capturing, saving, and loading audio
"""
import sounddevice as sd
import soundfile as sf
import numpy as np
import logging
from typing import Optional, Tuple
import os

from app.config import settings

logger = logging.getLogger(__name__)


def capture_audio(duration: float, sample_rate: int = None) -> np.ndarray:
    """
    Capture audio from default microphone

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz (default from settings)

    Returns:
        Audio data as numpy array (float32, mono)
    """
    if sample_rate is None:
        sample_rate = settings.AUDIO_SAMPLE_RATE

    logger.info(f"Capturing audio: {duration}s at {sample_rate}Hz")

    try:
        # Record audio (blocking)
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=settings.AUDIO_CHANNELS,
            dtype='float32'
        )
        sd.wait()  # Wait until recording is finished

        # Convert to 1D array if mono
        if audio.shape[1] == 1:
            audio = audio.flatten()

        logger.info(f"Captured {len(audio)} samples")
        return audio

    except Exception as e:
        logger.error(f"Error capturing audio: {e}", exc_info=True)
        raise


def save_wav(audio: np.ndarray, file_path: str, sample_rate: int = None) -> None:
    """
    Save audio data to WAV file

    Args:
        audio: Audio data as numpy array
        file_path: Path to save WAV file
        sample_rate: Sample rate in Hz (default from settings)
    """
    if sample_rate is None:
        sample_rate = settings.TTS_SAMPLE_RATE

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    logger.info(f"Saving WAV to: {file_path}")

    try:
        # Ensure audio is in correct format
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Clip to valid range
        audio = np.clip(audio, -1.0, 1.0)

        # Save as WAV
        sf.write(file_path, audio, sample_rate)

        file_size = os.path.getsize(file_path)
        logger.info(f"WAV saved: {file_size} bytes")

    except Exception as e:
        logger.error(f"Error saving WAV: {e}", exc_info=True)
        raise


def load_wav(file_path: str) -> Tuple[np.ndarray, int]:
    """
    Load audio data from WAV file

    Args:
        file_path: Path to WAV file

    Returns:
        Tuple of (audio_data, sample_rate)
    """
    logger.info(f"Loading WAV from: {file_path}")

    try:
        audio, sample_rate = sf.read(file_path, dtype='float32')

        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        logger.info(f"Loaded {len(audio)} samples at {sample_rate}Hz")
        return audio, sample_rate

    except Exception as e:
        logger.error(f"Error loading WAV: {e}", exc_info=True)
        raise


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample audio to different sample rate

    Args:
        audio: Audio data
        orig_sr: Original sample rate
        target_sr: Target sample rate

    Returns:
        Resampled audio
    """
    if orig_sr == target_sr:
        return audio

    logger.info(f"Resampling: {orig_sr}Hz -> {target_sr}Hz")

    try:
        from scipy import signal

        # Calculate resampling ratio
        num_samples = int(len(audio) * target_sr / orig_sr)

        # Resample
        resampled = signal.resample(audio, num_samples)

        return resampled.astype(np.float32)

    except Exception as e:
        logger.error(f"Error resampling: {e}", exc_info=True)
        raise


def normalize_audio(audio: np.ndarray, target_level: float = 0.5) -> np.ndarray:
    """
    Normalize audio to target RMS level

    Args:
        audio: Audio data
        target_level: Target RMS level (0.0 to 1.0)

    Returns:
        Normalized audio
    """
    try:
        # Calculate RMS
        rms = np.sqrt(np.mean(audio ** 2))

        if rms > 0:
            # Scale to target level
            scaling_factor = target_level / rms
            audio = audio * scaling_factor

        # Clip to prevent clipping
        audio = np.clip(audio, -1.0, 1.0)

        return audio

    except Exception as e:
        logger.error(f"Error normalizing audio: {e}", exc_info=True)
        return audio


def audio_to_int16(audio: np.ndarray) -> np.ndarray:
    """
    Convert float32 audio to int16 (for compatibility)

    Args:
        audio: Audio data as float32 (-1.0 to 1.0)

    Returns:
        Audio as int16
    """
    # Scale to int16 range
    audio = np.clip(audio, -1.0, 1.0)
    audio = (audio * 32767).astype(np.int16)
    return audio


def int16_to_audio(audio: np.ndarray) -> np.ndarray:
    """
    Convert int16 audio to float32

    Args:
        audio: Audio data as int16

    Returns:
        Audio as float32 (-1.0 to 1.0)
    """
    audio = audio.astype(np.float32) / 32767.0
    return audio
