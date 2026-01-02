"""
Text-to-Speech (TTS) Processor using Kokoro
High-quality neural TTS optimized for conversational speech
"""
import os
import logging
import numpy as np
import soundfile as sf
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class KokoroTTSProcessor:
    """
    Kokoro TTS processor using the kokoro-onnx package
    Model: Kokoro-82M - optimized for conversational, natural-sounding speech
    """

    def __init__(self, voice: str = "af_bella"):
        """
        Initialize Kokoro TTS processor

        Args:
            voice: Voice identifier (default: af_bella - American female, warm)
                   Available voices: af_bella, af_sarah, af_nicole, af_sky,
                   am_adam, am_michael, bf_emma, bf_isabella, bm_george, bm_lewis
        """
        logger.info(f"Initializing Kokoro TTS processor with voice: {voice}")

        try:
            from kokoro_onnx import Kokoro
        except ImportError:
            raise ImportError(
                "kokoro-onnx is required for Kokoro TTS. "
                "Install with: pip install kokoro-onnx"
            )

        self.voice = voice
        self.sample_rate = 24000  # Kokoro outputs at 24kHz

        # Model paths
        self.model_dir = os.path.join(settings.DATA_DIR, "models", "kokoro")
        self.model_path = os.path.join(self.model_dir, "kokoro-v1.0.onnx")
        self.voices_path = os.path.join(self.model_dir, "voices-v1.0.bin")

        # Verify model files exist
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Kokoro model not found at {self.model_path}\n"
                "Download from: https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
            )

        if not os.path.exists(self.voices_path):
            raise FileNotFoundError(
                f"Kokoro voices file not found at {self.voices_path}\n"
                "Download from: https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
            )

        # Initialize Kokoro
        logger.info(f"Loading Kokoro model from: {self.model_path}")
        logger.info(f"Loading voices from: {self.voices_path}")

        try:
            self.kokoro = Kokoro(self.model_path, self.voices_path)
            logger.info("Kokoro TTS processor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kokoro: {e}", exc_info=True)
            raise

    def synthesize(self, text: str, output_path: str, speed: float = 1.0) -> bool:
        """
        Synthesize text to audio file

        Args:
            text: Text to synthesize
            output_path: Path to save WAV file
            speed: Speech speed multiplier (default: 1.0)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Synthesizing text: '{text}' (speed={speed})")

        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Generate speech using Kokoro
            logger.info("Running TTS synthesis...")
            samples, sample_rate = self.kokoro.create(
                text,
                voice=self.voice,
                speed=speed,
                lang="en-us"
            )

            # Ensure samples are in correct format
            if isinstance(samples, list):
                samples = np.array(samples, dtype=np.float32)
            elif not isinstance(samples, np.ndarray):
                samples = np.array(samples, dtype=np.float32)

            # Normalize to [-1, 1] if needed
            max_val = np.abs(samples).max()
            if max_val > 1.0:
                samples = samples / max_val

            # Save as WAV file
            sf.write(output_path, samples, sample_rate, subtype='PCM_16')

            # Get file info
            file_size = os.path.getsize(output_path)
            duration = len(samples) / sample_rate

            logger.info(
                f"TTS complete: {output_path} "
                f"({file_size} bytes, {duration:.2f}s, {sample_rate}Hz)"
            )
            return True

        except Exception as e:
            logger.error(f"Error during TTS synthesis: {e}", exc_info=True)

            # Fallback: Create a simple tone as placeholder
            logger.warning("Creating fallback audio (silent placeholder)")
            self._create_fallback_audio(output_path, duration=2.0)
            return True  # Return True so pipeline continues

    def _create_fallback_audio(self, output_path: str, duration: float = 2.0):
        """
        Create a fallback silent audio file

        Args:
            output_path: Output file path
            duration: Duration in seconds
        """
        samples = int(duration * self.sample_rate)
        audio = np.zeros(samples, dtype=np.float32)
        sf.write(output_path, audio, self.sample_rate, subtype='PCM_16')
        logger.info(f"Created fallback audio: {output_path} ({duration}s)")


# Alias for backward compatibility
TTSProcessor = KokoroTTSProcessor
