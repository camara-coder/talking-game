"""
Streaming VAD endpointing -- detects end of speech in real time.
This does NOT trim audio or run the pipeline. It only signals endpoint.
"""
import torch
import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from silero_vad import load_silero_vad, VADIterator
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class StreamingVADState:
    session_id: str
    vad_iterator: VADIterator
    total_samples: int = 0
    pending_endpoint: bool = False
    last_end_sample: Optional[int] = None

    def reset(self):
        self.total_samples = 0
        self.pending_endpoint = False
        self.last_end_sample = None
        self.vad_iterator.reset_states()


_vad_model = None


def _get_vad_model():
    global _vad_model
    if _vad_model is None:
        _vad_model = load_silero_vad()
    return _vad_model


def create_streaming_vad_state(session_id: str) -> StreamingVADState:
    model = _get_vad_model()
    vad_iterator = VADIterator(
        model,
        sampling_rate=settings.AUDIO_SAMPLE_RATE,
        threshold=getattr(settings, "SILERO_VAD_THRESHOLD", 0.35),
        min_silence_duration_ms=getattr(settings, "SILERO_VAD_MIN_SILENCE_MS", 150),
    )
    return StreamingVADState(session_id=session_id, vad_iterator=vad_iterator)


def process_chunk(state: StreamingVADState, chunk_bytes: bytes) -> Dict[str, Any]:
    """
    Process one chunk. Returns a dict with keys:
    - end_detected: bool
    - speech_resumed: bool
    - end_sample: Optional[int]
    """
    pcm16 = np.frombuffer(chunk_bytes, dtype=np.int16)
    audio_float = pcm16.astype(np.float32) / 32768.0
    state.total_samples += len(audio_float)
    chunk_tensor = torch.from_numpy(audio_float).float()

    try:
        speech_dict = state.vad_iterator(chunk_tensor, return_seconds=False)
    except Exception as e:
        logger.debug(f"Streaming VAD chunk error (non-fatal): {e}")
        return {"end_detected": False, "speech_resumed": False, "end_sample": None}

    if speech_dict and "start" in speech_dict:
        resumed = False
        if state.pending_endpoint:
            resumed = True
            state.pending_endpoint = False
            state.last_end_sample = None
        return {"end_detected": False, "speech_resumed": resumed, "end_sample": None}

    if speech_dict and "end" in speech_dict:
        state.pending_endpoint = True
        state.last_end_sample = state.total_samples
        return {"end_detected": True, "speech_resumed": False, "end_sample": state.last_end_sample}

    return {"end_detected": False, "speech_resumed": False, "end_sample": None}
