"""
Voice Activity Detection (VAD) Processor
Uses webrtcvad to detect and trim silence from audio
"""
import webrtcvad
import numpy as np
import logging
from typing import Optional

from app.config import settings
from app.utils.audio_io import audio_to_int16, int16_to_audio

logger = logging.getLogger(__name__)


class VADProcessor:
    """Voice Activity Detection processor using WebRTC VAD"""

    def __init__(
        self,
        aggressiveness: int = None,
        frame_duration_ms: int = None,
        padding_ms: int = None,
        sample_rate: int = None
    ):
        """
        Initialize VAD processor

        Args:
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
            frame_duration_ms: Frame duration in ms (10, 20, or 30)
            padding_ms: Padding before/after speech in ms
            sample_rate: Sample rate in Hz
        """
        self.aggressiveness = aggressiveness or settings.VAD_AGGRESSIVENESS
        self.frame_duration_ms = frame_duration_ms or settings.VAD_FRAME_DURATION_MS
        self.padding_ms = padding_ms or settings.VAD_PADDING_MS
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE

        # Validate frame duration
        if self.frame_duration_ms not in [10, 20, 30]:
            raise ValueError("frame_duration_ms must be 10, 20, or 30")

        # Validate sample rate
        if self.sample_rate not in [8000, 16000, 32000, 48000]:
            logger.warning(
                f"Sample rate {self.sample_rate} not officially supported by webrtcvad. "
                "Supported rates: 8000, 16000, 32000, 48000. "
                "Results may be inaccurate."
            )

        # Initialize VAD
        self.vad = webrtcvad.Vad(self.aggressiveness)

        # Calculate frame size
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        self.padding_frames = int(self.padding_ms / self.frame_duration_ms)

        logger.info(
            f"VAD initialized: aggressiveness={self.aggressiveness}, "
            f"frame_duration={self.frame_duration_ms}ms, "
            f"padding={self.padding_ms}ms, "
            f"sample_rate={self.sample_rate}Hz"
        )

    def process(self, audio: np.ndarray) -> Optional[np.ndarray]:
        """
        Process audio and trim silence

        Args:
            audio: Audio data as float32 numpy array

        Returns:
            Trimmed audio or None if no speech detected
        """
        logger.info(f"Processing audio with VAD: {len(audio)} samples")

        # Convert to int16 for webrtcvad
        audio_int16 = audio_to_int16(audio)

        # Split into frames
        frames = self._frame_generator(audio_int16)

        # Detect speech frames
        speech_frames = []
        triggered = False
        num_padding_frames = 0

        for frame in frames:
            is_speech = self.vad.is_speech(frame.tobytes(), self.sample_rate)

            if not triggered:
                if is_speech:
                    # Start of speech
                    triggered = True
                    # Add padding frames before speech
                    speech_frames.extend([frame] * (self.padding_frames + 1))
                    logger.debug("Speech started")
            else:
                if is_speech:
                    # Continue speech
                    speech_frames.append(frame)
                    num_padding_frames = 0
                else:
                    # Possible end of speech
                    num_padding_frames += 1
                    speech_frames.append(frame)

                    if num_padding_frames > self.padding_frames:
                        # End of speech
                        logger.debug("Speech ended")
                        break

        if not speech_frames:
            logger.warning("No speech detected")
            return None

        # Concatenate speech frames
        speech_audio = np.concatenate(speech_frames)

        # Convert back to float32
        speech_audio = int16_to_audio(speech_audio)

        logger.info(
            f"VAD complete: {len(audio)} -> {len(speech_audio)} samples "
            f"({len(speech_audio) / self.sample_rate:.2f}s)"
        )

        return speech_audio

    def _frame_generator(self, audio: np.ndarray):
        """
        Generate frames from audio

        Args:
            audio: Audio data as int16

        Yields:
            Audio frames
        """
        n = len(audio)
        offset = 0

        while offset + self.frame_size <= n:
            yield audio[offset:offset + self.frame_size]
            offset += self.frame_size
