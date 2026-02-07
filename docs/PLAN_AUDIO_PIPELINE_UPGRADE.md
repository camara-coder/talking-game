# Audio Pipeline Upgrade — Implementation Plan

## Goal

Apply 4 surgical improvements to the voice capture and processing pipeline.
Each improvement is independently testable and has a rollback path.
The application MUST work at every step boundary — no partial states.

**Improvements in execution order:**

| # | Improvement | Risk | Files changed |
|---|---|---|---|
| 1 | Reduce frontend audio chunk size 4096→1024 | Low | 1 file |
| 2 | Replace webrtcvad with Silero VAD | Medium | 4 files |
| 3 | Add server-side noise reduction before VAD | Low | 4 files |
| 4 | Streaming VAD endpointing with single-trigger guard | High | 3 files |

---

## Prerequisites

Before starting ANY step, run this verification to confirm the application works:

```bash
# Terminal 1 — start voice service
cd voice_service
.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8008

# Terminal 2 — start web client
cd web-client
npm run dev

# Manual test: open browser, press talk, say "what is five plus five", release
# Expected: transcript appears, reply audio plays, answer is "ten"
```

Record the baseline latency (time from button release to audio playback start).
This number is the benchmark every step must beat or match.

---

## STEP 1: Reduce Frontend Audio Chunk Size (4096 → 1024 samples)

### Why

Current chunk size is 4096 samples = **256ms** at 16kHz.
This means the backend can't react to audio faster than every 256ms.
Reducing to 1024 samples = **64ms** gives 4x faster responsiveness.
This is critical for Step 4 (streaming VAD) and is safe on its own.

1024 samples at 16kHz = 2048 bytes per WebSocket message.
At continuous speech: ~15.6 messages/sec. WebSocket handles this trivially.

### Files to modify

**File 1 of 1: `web-client/public/pcm-processor.js`**

Change line 11 from:
```javascript
this.bufferSize = 4096; // Send chunks of 4096 samples (~256ms at 16kHz)
```
To:
```javascript
this.bufferSize = 1024; // Send chunks of 1024 samples (~64ms at 16kHz)
```

That is the ONLY change for Step 1. No backend changes needed.
The backend `AudioBuffer` in `ws.py` already accumulates arbitrary-size chunks.
The `pipeline_runner.py` `np.frombuffer()` call works with any byte length.

### Verification

1. Start voice service and web client.
2. Open browser console. Press Talk and speak for ~2 seconds.
3. Verify console logs show `PCM chunk received: 2048 bytes` (was 8192).
4. Verify chunks arrive ~4x more frequently.
5. Complete the full talk flow — transcript and audio response must work identically.
6. Verify: no WebSocket errors, no audio glitches, same transcription quality.

### Rollback

Change line 11 back to `this.bufferSize = 4096;`.

---

## STEP 2: Replace webrtcvad with Silero VAD

### Why

webrtcvad is a 2012-era energy-based VAD. It makes binary speech/non-speech
decisions per frame using signal energy — no learned representations.

Silero VAD is a neural network VAD (small DNN, ~2MB model) that:
- Has dramatically better accuracy on children's voices (higher pitch, variable volume)
- Handles background noise (TV, other children, toys) without misclassifying
- Returns speech probability per chunk, enabling smooth confidence thresholds
- Provides `get_speech_timestamps()` for precise speech boundary detection
- Provides `VADIterator` for real-time streaming (needed in Step 4)

### Dependencies to install

```bash
cd voice_service
.venv\Scripts\activate

# Install CPU-only PyTorch (small ~150MB, not the full 2GB GPU version)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install Silero VAD
pip install silero-vad
```

**Verify installation:**
```python
python -c "import torch; from silero_vad import load_silero_vad; model = load_silero_vad(); print('Silero VAD loaded OK')"
```
This must print `Silero VAD loaded OK` before proceeding.

### Files to modify

**File 1 of 4: `voice_service/requirements.txt`**

Add after line 14 (`webrtcvad>=2.0.10`):
```
# webrtcvad>=2.0.10  # Legacy energy-based VAD (replaced by Silero VAD)
torch>=2.0.0  # CPU-only; install with: pip install torch --index-url https://download.pytorch.org/whl/cpu
silero-vad>=5.1
```

And comment out the old webrtcvad line:
```
# webrtcvad>=2.0.10  # Legacy energy-based VAD (replaced by Silero VAD)
```

The full changed block (lines 9-16 region) becomes:
```
# Audio Processing
sounddevice>=0.5.1
soundfile>=0.12.1
numpy>=1.26.0
scipy>=1.14.0
# webrtcvad>=2.0.10  # Legacy energy-based VAD (replaced by Silero VAD)
torch>=2.0.0  # CPU-only; install with: pip install torch --index-url https://download.pytorch.org/whl/cpu
silero-vad>=5.1
# Note: Audio conversion uses ffmpeg directly (no Python package needed)
```

---

**File 2 of 4: `voice_service/app/pipeline/processors/vad_silero.py`** (NEW FILE)

Create this file with the following complete contents:

```python
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
```

---

**File 3 of 4: `voice_service/app/config.py`**

Add Silero VAD settings after the existing VAD block (after line 50).
Insert these lines after `VAD_FRAME_DURATION_MS: int = 30`:

```python
    # Silero VAD Configuration (neural network VAD — replaces webrtcvad)
    SILERO_VAD_THRESHOLD: float = 0.35       # Speech probability threshold (0.0-1.0)
    SILERO_VAD_MIN_SPEECH_MS: int = 250      # Minimum speech duration to keep (ms)
    SILERO_VAD_MIN_SILENCE_MS: int = 150     # Silence duration to split segments (ms)
    SILERO_VAD_SPEECH_PAD_MS: int = 60       # Padding before/after speech (ms)
```

Keep the old webrtcvad settings — they don't hurt anything and serve as documentation.

---

**File 4 of 4: `voice_service/app/pipeline/voice_pipeline.py`**

Change line 10 from:
```python
from app.pipeline.processors.vad_processor import VADProcessor
```
To:
```python
from app.pipeline.processors.vad_silero import SileroVADProcessor as VADProcessor
```

That is the ONLY change in this file. The class is used on line 28 as
`self.vad = VADProcessor()` and called on line 78 as `self.vad.process(audio)`.
Both work identically because `SileroVADProcessor.process()` has the exact same
signature: `process(audio: np.ndarray) -> Optional[np.ndarray]`.

### Verification

1. Restart the voice service (it will print `Silero VAD model loaded successfully` on first request).
2. Press Talk, say "hello", release. Transcript and reply must work.
3. Press Talk, say nothing, release. Must get "No speech detected" error (not a crash).
4. Press Talk, make a short noise (clap), release. Should be filtered out (no transcript).
5. Press Talk, whisper quietly, release. Silero should detect it (webrtcvad often missed whispers).
6. Check logs: should see `Silero VAD complete: X -> Y samples, N segment(s)`.

### Rollback

Change `voice_pipeline.py` line 10 back to:
```python
from app.pipeline.processors.vad_processor import VADProcessor
```
The old `vad_processor.py` is untouched and still works with webrtcvad.

---

## STEP 3: Add Server-Side Noise Reduction

### Why

The browser applies basic `noiseSuppression` via `getUserMedia` constraints, but
this is inconsistent across browsers and devices. Children use the app in noisy
environments (TV, siblings, toys). Adding server-side noise reduction:

- Removes stationary noise (fan, AC, hum) and non-stationary noise (TV, background speech)
- Runs BEFORE VAD, so VAD makes decisions on cleaner audio
- Runs BEFORE STT, so the transcription model gets cleaner input
- Uses `noisereduce` library: pure Python/numpy, works on all platforms, no C dependencies

### Dependencies to install

```bash
cd voice_service
.venv\Scripts\activate
pip install noisereduce>=3.0.0
```

**Verify installation:**
```python
python -c "import noisereduce; print(f'noisereduce {noisereduce.__version__} OK')"
```

### Files to modify

**File 1 of 4: `voice_service/requirements.txt`**

Add after the `silero-vad>=5.1` line:
```
noisereduce>=3.0.0  # Server-side noise reduction (runs before VAD and STT)
```

---

**File 2 of 4: `voice_service/app/pipeline/processors/noise_reducer.py`** (NEW FILE)

Create this file with the following complete contents:

```python
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
```

---

**File 3 of 4: `voice_service/app/config.py`**

Add noise reduction settings after the Silero VAD block added in Step 2:

```python
    # Noise Reduction Configuration
    NOISE_REDUCE_PROP_DECREASE: float = 0.6  # Reduction strength (0.0-1.0)
```

---

**File 4 of 4: `voice_service/app/pipeline/voice_pipeline.py`**

Three changes to this file:

**Change A** — Add import (after line 10, the VAD import):
```python
from app.pipeline.processors.noise_reducer import NoiseReducer
```

**Change B** — Add processor initialization (after `self.vad = VADProcessor()` on line 28):
```python
        self.noise_reducer = NoiseReducer()
```

**Change C** — Add noise reduction step BEFORE VAD.

The current pipeline Step 1 (lines 76-83) is:
```python
            # Step 1: VAD - Trim silence
            logger.info("Step 1: VAD processing...")
            vad_audio = self.vad.process(audio)

            if vad_audio is None:
                result["error"] = "No speech detected"
                logger.warning(result["error"])
                return result
```

Replace with:
```python
            # Step 1: Noise Reduction
            logger.info("Step 1: Noise reduction...")
            clean_audio = self.noise_reducer.process(audio)

            # Step 2: VAD - Trim silence
            logger.info("Step 2: VAD processing...")
            vad_audio = self.vad.process(clean_audio)

            if vad_audio is None:
                result["error"] = "No speech detected"
                logger.warning(result["error"])
                return result
```

And renumber the remaining comments:
- Old "Step 2: STT" → "Step 3: STT"
- Old "Step 3: Skills routing" → "Step 4: Skills routing"
- Old "Step 4: LLM processing" → "Step 5: LLM processing"
- Old "Step 5: Response shaping" → "Step 6: Response shaping"

### Verification

1. Restart the voice service.
2. Press Talk, say "hello" in a quiet room. Must work exactly as before.
3. Press Talk, say "hello" with background noise (turn on TV or fan). Check logs for
   `Noise reduction complete: RMS X -> Y (-Z dB)`. Negative dB means noise was reduced.
4. Full flow must still produce correct transcripts and audio replies.
5. Verify noise reduction adds <100ms to total processing time (check pipeline timing logs).

### Rollback

Remove the noise reduction step from `voice_pipeline.py`:
- Delete the `NoiseReducer` import
- Delete `self.noise_reducer = NoiseReducer()`
- Revert the pipeline Step 1 back to VAD directly (remove the noise reduction call)
- Renumber steps back to original

---

## STEP 4: Streaming Endpointing with Single-Trigger Guard (Robust)

### Why

We still want early pipeline start, but we must avoid:
- Double-processing (early trigger plus audio.end fallback)
- Double VAD/noise reduction (streaming VAD then batch VAD again)
- Race conditions between streaming and end-of-stream

This revision uses streaming VAD only to detect endpoint. The pipeline runs once
per turn, and always runs the same batch path.

### Architecture

```
CURRENT FLOW:
User speaks -> [chunks buffered] -> audio.end -> pipeline starts

NEW FLOW (robust):
User speaks -> [chunks buffered + streaming VAD endpointing]
   -> endpoint detected OR audio.end
   -> single guarded trigger -> pipeline starts exactly once
```

### Design Rules

- Always accumulate full raw audio (batch pipeline uses it).
- Streaming VAD only decides "endpoint reached".
- A single "processing_started" gate prevents double trigger.
- If streaming never fires, audio.end behaves exactly as before.

### Files to modify

**File 1 of 3: `voice_service/app/pipeline/streaming_vad.py`** (NEW FILE)

Create this file with the following complete contents:

```python
"""
Streaming VAD endpointing -- detects end of speech in real time.
This does NOT trim audio or run the pipeline. It only signals endpoint.
"""
import torch
import numpy as np
import logging
from dataclasses import dataclass

from silero_vad import load_silero_vad, VADIterator
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class StreamingVADState:
    session_id: str
    vad_iterator: VADIterator
    endpoint_detected: bool = False

    def reset(self):
        self.endpoint_detected = False
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


def process_chunk(state: StreamingVADState, chunk_bytes: bytes) -> bool:
    """
    Process one chunk. Returns True if endpoint detected in this chunk.
    """
    pcm16 = np.frombuffer(chunk_bytes, dtype=np.int16)
    audio_float = pcm16.astype(np.float32) / 32768.0
    chunk_tensor = torch.from_numpy(audio_float).float()

    try:
        speech_dict = state.vad_iterator(chunk_tensor, return_seconds=False)
    except Exception as e:
        logger.debug(f"Streaming VAD chunk error (non-fatal): {e}")
        return False

    if speech_dict and "end" in speech_dict:
        state.endpoint_detected = True
        return True

    return False
```

---

**File 2 of 3: `voice_service/app/api/ws.py`**

This file requires several changes. Apply them in order:

**Change A** -- Add imports at the top:

```python
from app.pipeline.streaming_vad import (
    StreamingVADState,
    create_streaming_vad_state,
    process_chunk as vad_process_chunk,
)
```

**Change B** -- Add streaming VAD state and a processing guard to ConnectionManager.

In `ConnectionManager.__init__`, add after `self._lock = asyncio.Lock()`:

```python
        # Map of session_id -> StreamingVADState for endpointing
        self.streaming_vad_states: Dict[str, StreamingVADState] = {}
        # Guard to ensure pipeline runs once per turn
        self.processing_started: Dict[str, bool] = {}
```

**Change C** -- Initialize streaming VAD in `handle_audio_start`.

Inside `handle_audio_start` (under the lock), add:

```python
            self.processing_started[session_id] = False
            if settings.STREAMING_VAD_ENABLED:
                try:
                    self.streaming_vad_states[session_id] = create_streaming_vad_state(session_id)
                    logger.info(f"Streaming VAD initialized for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to init streaming VAD (will use batch): {e}")
```

**Change D** -- Process chunks through streaming VAD in `handle_audio_chunk`.

Append after buffer accumulation:

```python
        # Run streaming endpointing outside the lock
        if settings.STREAMING_VAD_ENABLED:
            vad_state = self.streaming_vad_states.get(session_id)
            if vad_state and not vad_state.endpoint_detected:
                if vad_process_chunk(vad_state, chunk):
                    await self._trigger_processing_once(session_id, source="vad_end")
```

**Change E** -- Add a single guarded trigger method.

Add this method to ConnectionManager:

```python
    async def _trigger_processing_once(self, session_id: str, source: str):
        async with self._lock:
            if self.processing_started.get(session_id):
                logger.info(f"Processing already started for {session_id} (source={source})")
                return
            self.processing_started[session_id] = True

            audio_data = None
            if session_id in self.audio_buffers:
                audio_data = self.audio_buffers[session_id].get_audio_data()
                logger.info(f"Triggering processing from {source}, bytes={len(audio_data)}")

            # Cleanup streaming VAD state
            if session_id in self.streaming_vad_states:
                del self.streaming_vad_states[session_id]

        await self.broadcast_state(session_id, SessionStatus.PROCESSING)

        if audio_data:
            asyncio.create_task(self._process_audio(session_id, audio_data))
        else:
            await self.broadcast_error(
                session_id,
                "NO_AUDIO",
                "No audio data received"
            )
            await self.broadcast_state(session_id, SessionStatus.IDLE)
```

**Change F** -- Simplify `handle_audio_end` to use the guard.

Replace `handle_audio_end` with:

```python
    async def handle_audio_end(self, session_id: str):
        logger.info(f"Audio streaming ended for session {session_id}")
        await self._trigger_processing_once(session_id, source="audio_end")
```

**Change G** -- Cleanup on disconnect.

In `disconnect`, add:

```python
            if session_id in self.streaming_vad_states:
                del self.streaming_vad_states[session_id]
            if session_id in self.processing_started:
                del self.processing_started[session_id]
```

---

**File 3 of 3: `voice_service/app/config.py`**

Add streaming VAD setting after the Silero VAD block:

```python
    # Streaming VAD endpointing
    STREAMING_VAD_ENABLED: bool = True  # Set to False to disable endpointing
```

### Verification

Run ALL of these:

**Test 1: Early endpointing**
1. Press Talk, speak, then hold the button 2 seconds.
2. Check logs: `Triggering processing from vad_end`.
3. Transcript and reply are correct.

**Test 2: Fast release (fallback)**
1. Press Talk, speak, release immediately.
2. Check logs: `Triggering processing from audio_end`.
3. Transcript and reply are correct.

**Test 3: No speech**
1. Press Talk, remain silent, release.
2. Must get "No speech detected" without crash.

**Test 4: No double processing**
1. Do 5 rapid turns.
2. Verify only one "Triggering processing" log per turn.

### Rollback

Set `STREAMING_VAD_ENABLED = False` to disable endpointing. This reverts behavior
to the original batch flow without code rollback.


## Post-Implementation Verification Checklist

Run ALL of these after all 4 steps are complete:

- [ ] `pip list | grep -i "torch\|silero\|noisereduce"` shows all 3 packages installed
- [ ] Voice service starts without errors
- [ ] Web client connects and shows "idle" state
- [ ] Say "what is five plus five" → get correct answer "ten" with audio
- [ ] Say "tell me about dogs" → get a 1-2 sentence kid-friendly reply with audio
- [ ] Say nothing → get "No speech detected" error (no crash)
- [ ] Server logs show: `Noise reduction complete`, `Silero VAD complete`, transcript
- [ ] Hold button 2 seconds after speaking → logs show `Triggering processing from vad_end`
- [ ] Latency from button release (with hold) is noticeably faster than baseline
- [ ] 5 consecutive talk-reply cycles work without errors
- [ ] No memory leaks: check process memory stays stable across 10+ cycles

---

## Configuration Reference (all new settings)

Add all of these to `voice_service/app/config.py` in the Settings class:

```python
    # Silero VAD Configuration
    SILERO_VAD_THRESHOLD: float = 0.35
    SILERO_VAD_MIN_SPEECH_MS: int = 250
    SILERO_VAD_MIN_SILENCE_MS: int = 150
    SILERO_VAD_SPEECH_PAD_MS: int = 60

    # Noise Reduction Configuration
    NOISE_REDUCE_PROP_DECREASE: float = 0.6

    # Streaming VAD endpointing
    STREAMING_VAD_ENABLED: bool = True
```

All settings can be overridden via environment variables or `.env` file.

---

## File Change Summary

| File | Action | Step |
|---|---|---|
| `web-client/public/pcm-processor.js` | Edit line 11: 4096→1024 | 1 |
| `voice_service/requirements.txt` | Comment webrtcvad, add torch+silero+noisereduce | 2,3 |
| `voice_service/app/pipeline/processors/vad_silero.py` | **CREATE** | 2 |
| `voice_service/app/pipeline/processors/noise_reducer.py` | **CREATE** | 3 |
| `voice_service/app/pipeline/streaming_vad.py` | **CREATE** | 4 |
| `voice_service/app/config.py` | Add 6 new settings | 2,3,4 |
| `voice_service/app/pipeline/voice_pipeline.py` | Change VAD import, add NR step | 2,3 |
| `voice_service/app/api/ws.py` | Add streaming endpointing guard | 4 |

**Files NOT modified** (preserved as rollback targets):
- `voice_service/app/pipeline/processors/vad_processor.py` — original webrtcvad, untouched
- `voice_service/app/pipeline/pipeline_runner.py` — untouched
- `web-client/src/lib/microphone.ts` — untouched
- `web-client/src/hooks/useVoiceService.ts` — untouched

---

## Failure Modes and Mitigations

| Failure | Impact | Mitigation |
|---|---|---|
| torch fails to install | Step 2 blocked | Use `pip install torch --index-url https://download.pytorch.org/whl/cpu` for minimal install |
| Silero model download fails | Step 2 blocked | Model downloads on first use; ensure internet. After first load it's cached in `~/.cache/silero-vad/` |
| noisereduce distorts audio | STT quality degrades | `NoiseReducer.process()` catches exceptions and returns original audio unchanged |
| Silero VAD misses speech | "No speech detected" errors | Lower `SILERO_VAD_THRESHOLD` from 0.35 to 0.2 in config |
| Endpointing triggers too early | Truncated transcript | Increase `SILERO_VAD_MIN_SILENCE_MS` from 150 to 300 |
| Endpointing never triggers | No latency improvement | Audio end fallback handles it — identical to pre-upgrade behavior |
| WebSocket message rate too high (1024 chunks) | Network issues | Revert `pcm-processor.js` buffer to 2048 or 4096 |
| Memory leak from streaming VAD state | Service degrades | State is cleaned up in `_trigger_processing_once` and `disconnect` |
