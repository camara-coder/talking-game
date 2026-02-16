# Lightweight Model Evaluation for Talking Game

## Current Setup Summary

| Component | Current Model | Parameters | Latency (CPU) | RAM |
|-----------|--------------|------------|---------------|-----|
| **STT** | Canary-Qwen-2.5B (NVIDIA NeMo) | 2.5B | ~500-2000ms | ~2GB |
| **TTS** | Qwen3-TTS-0.6B (Alibaba) | 600M | ~1000-3000ms | ~400MB |
| **LLM** | Qwen2.5:0.5b-instruct (Ollama) | 500M | ~500-1500ms | ~300MB |
| **VAD** | Silero VAD | ~20M | ~100-300ms | ~100MB |

**Total estimated end-to-end latency: 3-8 seconds on CPU-only systems.**

For a children's game, this latency is too high. Kids lose attention with response times above ~2 seconds. The current pipeline is accurate and feature-rich, but the models are oversized for this use case where we only need English, short utterances, and simple responses.

---

## 1. Evaluation of Proposed Alternatives

### STT: "Handy"

**Finding: No model called "Handy" exists in the STT/ASR space.**

Extensive search across HuggingFace, GitHub, PyPI, and academic papers found no speech-to-text model with this name. Possible explanations:
- It may be a misremembered name for another model
- It could be a wrapper/tool name rather than a model name
- It might refer to Kyutai's STT models (since Pocket-TTS is from Kyutai, their STT line includes `kyutai/stt-1b-en_fr` and `kyutai/stt-2.6b-en`)

**If the intent was Kyutai's STT-1B:** This is a 1B-parameter streaming STT model. It would be smaller than Canary-Qwen (2.5B) but still large. Its streaming architecture is excellent, but at 1B parameters it won't dramatically improve CPU latency over the current setup.

**Verdict: Cannot evaluate. Need clarification on the actual model name.**

---

### TTS: Pocket-TTS (Kyutai)

**Source:** [kyutai-labs/pocket-tts](https://github.com/kyutai-labs/pocket-tts) | [HuggingFace](https://huggingface.co/kyutai/pocket-tts)

| Metric | Pocket-TTS | Current (Qwen3-TTS-0.6B) |
|--------|-----------|--------------------------|
| Parameters | **100M** | 600M |
| First audio chunk | **~200ms** | ~1000-3000ms |
| RTF (Real-Time Factor) | **0.17** (6x faster than real-time) | >1.0 on CPU |
| CPU cores needed | **2** | Multiple |
| GPU required | **No** (no speedup observed) | No (but slow) |
| RAM | **~few hundred MB** | ~400MB |
| Python support | 3.10-3.14 | 3.11+ |
| PyTorch version | 2.5+ | 2.0+ |
| License | **MIT** | Apache 2.0 |
| Voice cloning | Yes (via WAV file) | Yes (CustomVoice variant) |
| Streaming | **Yes** | No |
| Languages | English | Multi-language |

#### Compatibility with Current Codebase

**High compatibility.** The integration would be straightforward:

```python
# Current Qwen3-TTS interface (tts_qwen3.py)
class Qwen3TTSProcessor:
    def synthesize(self, text: str, output_path: str) -> bool

# Pocket-TTS equivalent would match the same interface:
class PocketTTSProcessor:
    def __init__(self):
        from pocket_tts import TTSModel
        self.model = TTSModel.load_model()
        self.voice_state = self.model.get_state_for_audio_prompt("alba")

    def synthesize(self, text: str, output_path: str) -> bool:
        audio = self.model.generate_audio(self.voice_state, text)
        scipy.io.wavfile.write(output_path, self.model.sample_rate, audio.numpy())
        return True
```

Key observations:
- Drop-in replacement for `tts_qwen3.py` — same `synthesize(text, output_path)` interface
- Output is a WAV file (matches current pipeline)
- `pip install pocket-tts` — single dependency
- Removes heavy `qwen-tts` and potentially `nemo_toolkit` dependencies
- Model stays in memory between calls (already how the app works with `_qwen_model` global)

#### Performance Impact

**This is a massive improvement.** Pocket-TTS would reduce the TTS step from ~1000-3000ms to ~200ms first chunk. For the short responses this game produces (1-2 sentences, max 35 words), total TTS time would be well under 500ms. This alone would cut total pipeline latency by 1-2.5 seconds.

#### What We Lose

- Multi-language support (not needed — game is English-only)
- The specific "warm, friendly voice for a young child" instruction tuning (Pocket-TTS has built-in voices like "alba" that sound natural, and supports voice cloning from a WAV reference)

**Verdict: STRONGLY RECOMMENDED. 6x smaller, 5-15x faster, MIT licensed, easy integration.**

---

## 2. Alternative Lightweight Models — Ranked Recommendations

### STT Alternatives (replacing Canary-Qwen-2.5B)

#### Recommendation #1: Moonshine (Best Overall)

**Source:** [moonshine-ai/moonshine](https://github.com/moonshine-ai/moonshine) | [HuggingFace](https://huggingface.co/UsefulSensors/moonshine)

| Metric | Moonshine Tiny | Moonshine Medium | Current (Canary-Qwen) |
|--------|---------------|-----------------|----------------------|
| Parameters | **34M** | 245M | 2.5B |
| WER | 12.0% | **6.65%** | ~5.6% |
| Latency | **50ms** (MacBook Pro) | 258ms | 500-2000ms |
| Streaming | **Yes** (built-in) | **Yes** | No |
| Built-in VAD | **Yes** | **Yes** | No (separate Silero) |
| CPU-only | **Yes** (ONNX optimized) | **Yes** | Yes (slow) |
| Languages | English | English | Multi-language |
| License | MIT | MIT | NeMo license |

**Why Moonshine is ideal for this game:**
- **Tiny (34M)** — 73x smaller than Canary-Qwen, 50ms latency, good enough for children's speech
- **Medium (245M)** — 10x smaller, 258ms latency, 6.65% WER is excellent
- Built-in VAD means we could potentially remove Silero VAD as a separate step
- Variable-length input window (doesn't waste compute on padding like Whisper)
- Streaming support built-in — could enable real-time partial transcripts
- MIT licensed, pip installable (`pip install moonshine-voice`)
- Works on Raspberry Pi, IoT, phones — future-proofs for edge deployment

**Integration complexity:** Medium. Different API than Canary-Qwen but straightforward. The event-driven API maps well to the WebSocket architecture.

#### Recommendation #2: Whisper Tiny/Base (via faster-whisper)

| Metric | Whisper Tiny | Whisper Base | Current (Canary-Qwen) |
|--------|-------------|-------------|----------------------|
| Parameters | **39M** | 74M | 2.5B |
| WER | ~12.7% | ~9.8% | ~5.6% |
| Latency (CPU) | ~200ms | ~400ms | 500-2000ms |
| Streaming | No (30s chunks) | No | No |
| License | MIT | MIT | NeMo |

**Why consider Whisper:** Already commented out in `requirements.txt` (`faster-whisper>=1.1.0`), meaning the codebase previously supported it. Re-enabling it would be trivial. However, Moonshine is strictly better for this use case.

#### Recommendation #3: Vosk

| Metric | Vosk (small) | Current (Canary-Qwen) |
|--------|-------------|----------------------|
| Model size | **50MB disk** | ~2GB+ |
| WER | 10-15% | ~5.6% |
| Latency | ~100-200ms | 500-2000ms |
| Streaming | **Yes** | No |
| RAM | **<100MB** | ~2GB |
| Languages | 20+ | Multi |

**Why Vosk:** Absolute minimum footprint. Best for extremely constrained environments. But accuracy is notably worse, especially with children's voices and background noise. Not recommended as primary choice but viable as fallback.

---

### TTS Alternatives (replacing Qwen3-TTS-0.6B)

#### Recommendation #1: Pocket-TTS (Best Overall) — See detailed analysis above

#### Recommendation #2: Kokoro-82M

**Source:** [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)

| Metric | Kokoro-82M | Pocket-TTS | Current (Qwen3-TTS) |
|--------|-----------|-----------|---------------------|
| Parameters | 82M | **100M** | 600M |
| Latency | ~120ms (GPU), ~300ms (CPU) | **47ms first chunk** | 1000-3000ms |
| Quality (Elo) | #1 TTS Arena | Comparable | Good |
| Streaming | Limited | **Yes** | No |
| ONNX support | **Yes** | Yes (community) | No |
| Voice cloning | No | **Yes** | Yes |
| License | Apache 2.0 | **MIT** | Apache 2.0 |

**Note:** Kokoro was previously in this codebase (commented out in `requirements.txt` as `kokoro-onnx>=0.4.9`). It was replaced by Qwen3-TTS. Pocket-TTS is the better choice due to faster first-chunk latency, streaming support, and voice cloning.

#### Recommendation #3: Piper TTS

| Metric | Piper | Pocket-TTS |
|--------|-------|-----------|
| Parameters | ~15-60M (ONNX) | 100M |
| Latency | ~50-100ms | ~200ms |
| Quality | Good (not neural-quality) | **Excellent** |
| Streaming | No | **Yes** |

Piper is faster but lower quality. For a children's game where voice quality matters for engagement, Pocket-TTS is the better trade-off.

---

## 3. Recommended Optimal Stack

### Best Latency Configuration

| Component | Model | Params | Est. Latency | Est. RAM |
|-----------|-------|--------|-------------|----------|
| **STT** | Moonshine Tiny Streaming | 34M | ~50-80ms | ~50MB |
| **VAD** | Moonshine built-in | — | included | included |
| **LLM** | Qwen2.5:0.5b (keep current) | 500M | ~500-1500ms | ~300MB |
| **TTS** | Pocket-TTS | 100M | ~200ms | ~200MB |
| **Total** | — | **634M** | **~750-1800ms** | **~550MB** |

vs. current: **3.6B params, 3-8 seconds, ~2.8GB RAM**

**Improvement: ~5x fewer parameters, ~3-4x faster, ~5x less RAM.**

### Best Quality Configuration

| Component | Model | Params | Est. Latency | Est. RAM |
|-----------|-------|--------|-------------|----------|
| **STT** | Moonshine Medium Streaming | 245M | ~260ms | ~300MB |
| **VAD** | Moonshine built-in | — | included | included |
| **LLM** | Qwen2.5:0.5b (keep current) | 500M | ~500-1500ms | ~300MB |
| **TTS** | Pocket-TTS | 100M | ~200ms | ~200MB |
| **Total** | — | **845M** | **~960-1960ms** | **~800MB** |

**Improvement: ~4x fewer parameters, ~2-4x faster, ~3.5x less RAM. WER only ~1% worse.**

---

## 4. Migration Path

### Phase 1: Replace TTS (Lowest Risk, Highest Impact)
1. `pip install pocket-tts`
2. Create `tts_pocket.py` processor mirroring the `Qwen3TTSProcessor` interface
3. Update `voice_pipeline.py` import
4. Update `pipeline_runner.py` import
5. Update `config.py` with Pocket-TTS settings
6. Remove `qwen-tts` from `requirements.txt`

**Expected latency reduction: 1-2.5 seconds** (TTS goes from 1-3s to <0.5s)

### Phase 2: Replace STT (Medium Risk, High Impact)
1. `pip install moonshine-voice`
2. Create `stt_moonshine.py` processor
3. Evaluate if Moonshine's built-in VAD can replace Silero VAD
4. Update pipeline imports
5. Remove `nemo_toolkit[asr,tts]` from `requirements.txt` (this is a heavy dependency)

**Expected latency reduction: 0.5-1.5 seconds** (STT goes from 0.5-2s to 50-260ms)

### Phase 3: Cleanup
1. Remove unused ElevenLabs config from `config.py`
2. Remove unused OpenAI Whisper config
3. Slim down Docker image (removing NeMo/NVIDIA deps will significantly reduce image size)
4. Update `requirements.txt` to remove heavy dependencies

---

## 5. Dependencies Impact

### Current heavy dependencies that could be removed:
```
# These are the heaviest items in requirements.txt:
nemo_toolkit[asr,tts] @ git+https://github.com/NVIDIA/NeMo.git  # Several GB
qwen-tts>=0.1.0                                                   # ~500MB+
elevenlabs>=1.0.0                                                  # Legacy, unused
torch>=2.0.0                                                       # Still needed but lighter usage
```

### New minimal dependencies:
```
pocket-tts>=0.1.0       # ~100MB model, auto-downloads
moonshine-voice>=1.0.0  # ~30-250MB model depending on size
torch>=2.5.0            # Still needed by pocket-tts
```

**Docker image size reduction: potentially 3-5GB smaller.**

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pocket-TTS voice quality not kid-friendly enough | Low | Medium | Test built-in voices; use voice cloning with a child-friendly reference WAV |
| Moonshine WER too high for children's speech | Medium | Medium | Use Medium (6.65% WER) instead of Tiny; test with actual children |
| API incompatibility | Low | Low | Both models have simple Python APIs that match current interface patterns |
| Moonshine VAD less accurate than Silero | Low | Low | Keep Silero as fallback; test Moonshine VAD independently first |
| Model download/availability issues | Low | Low | Both are on HuggingFace + pip; can be bundled in Docker image |
