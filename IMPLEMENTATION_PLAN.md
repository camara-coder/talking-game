# Voice Conversational Kids Game - Implementation Plan

**Version:** 1.0
**Date:** December 23, 2025
**Target Platform:** Windows PC (CPU-only)
**Architecture:** Unity Frontend + Python Voice Service + Ollama LLM

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites & Environment Setup](#prerequisites--environment-setup)
3. [Project Structure Setup](#project-structure-setup)
4. [Implementation Phases](#implementation-phases)
5. [Testing Strategy](#testing-strategy)
6. [Integration & Validation](#integration--validation)
7. [Acceptance Criteria](#acceptance-criteria)
8. [Troubleshooting Guide](#troubleshooting-guide)

---

## Overview

### Project Goal
Build a proof-of-concept voice-interactive game for children 5+ that:
- Uses push-to-talk interaction
- Responds with short, kid-friendly answers
- Handles basic math deterministically (correct answers every time)
- Runs entirely locally on Windows (no cloud dependencies)

### Architecture Summary
```
┌─────────────────┐
│  Unity Game     │  ← User Interface, Audio Playback, Push-to-Talk
│  (C#)           │
└────────┬────────┘
         │ HTTP/WebSocket (localhost)
         ↓
┌─────────────────┐
│ Voice Service   │  ← Pipecat Pipeline, STT, TTS, Math Router
│ (Python/FastAPI)│
└────────┬────────┘
         │ HTTP (localhost)
         ↓
┌─────────────────┐
│ Ollama LLM      │  ← Local Language Model
│ (Service)       │
└─────────────────┘
```

### Technology Stack
- **Frontend:** Unity 2022/2023 LTS, C#, Canvas UI
- **Backend:** Python 3.11+, FastAPI, Pipecat
- **STT:** faster-whisper (base.en)
- **TTS:** Kokoro-82M (requires eSpeak NG)
- **LLM:** Ollama (qwen2.5:0.5b-instruct)
- **VAD:** webrtcvad

---

## Prerequisites & Environment Setup

### Phase 0: Install System Dependencies

#### 0.1 Install Unity Hub & Unity Editor
**Actions:**
1. Download Unity Hub from https://unity.com/download
2. Install Unity Hub
3. Open Unity Hub → Installs → Add
4. Select Unity 2022 LTS (latest) or 2023 LTS
5. Include these modules in installation:
   - Windows Build Support (IL2CPP)
   - Visual Studio Community (or use existing VS)

**Verification:**
- Open Unity Hub
- Verify Unity version is listed under "Installs"

#### 0.2 Install Ollama
**Actions:**
1. Download Ollama for Windows from https://ollama.com/download
2. Run installer
3. Verify installation: open terminal and run `ollama --version`
4. Pull the model: `ollama pull qwen2.5:0.5b-instruct`
5. Test model: `ollama run qwen2.5:0.5b-instruct "Hello"`

**Verification:**
- Ollama service should start automatically on Windows
- Check service is running: `curl http://127.0.0.1:11434`
- Should return "Ollama is running"

#### 0.3 Install eSpeak NG
**Actions:**
1. Download eSpeak NG for Windows from https://github.com/espeak-ng/espeak-ng/releases
2. Run installer
3. Add to PATH: `C:\Program Files\eSpeak NG\` (installer may do this automatically)
4. Verify: `espeak-ng --version`

**Verification:**
- Run `espeak-ng "Hello world"` in terminal
- Should hear synthesized speech

#### 0.4 Verify Python Environment
**Actions:**
1. Verify Python version: `python --version` (should be 3.11+)
2. Ensure pip is updated: `python -m pip install --upgrade pip`

**Verification:**
- `python --version` shows 3.11.x or higher

---

## Project Structure Setup

### Phase 1: Create Project Scaffolding

#### 1.1 Create Folder Structure
**Actions:**
Create the following directory structure in `C:\Users\rober\OneDrive\dev\ai\voice-game\`:

```
voice-game/
├── unity/
│   └── KidsVoiceGame/          # Unity project (will be created by Unity)
├── voice_service/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   └── ws.py
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── build_pipeline.py
│   │   │   └── processors/
│   │   │       ├── __init__.py
│   │   │       ├── vad_processor.py
│   │   │       ├── stt_processor.py
│   │   │       ├── skills_router.py
│   │   │       ├── llm_ollama.py
│   │   │       ├── response_shaper.py
│   │   │       ├── tts_kokoro.py
│   │   │       └── output_events.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── audio_io.py
│   │       ├── wav_utils.py
│   │       ├── text_math.py
│   │       └── safety_filter.py
│   ├── data/
│   │   ├── audio/              # Generated WAV files
│   │   └── logs/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_math_router.py
│   │   ├── test_safety_filter.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── README.md
└── scripts/
    ├── run_all.ps1
    └── health_check.ps1
```

**Commands:**
```powershell
# Run from voice-game directory
mkdir -p voice_service/app/api
mkdir -p voice_service/app/pipeline/processors
mkdir -p voice_service/app/utils
mkdir -p voice_service/data/audio
mkdir -p voice_service/data/logs
mkdir -p voice_service/tests
mkdir -p scripts
mkdir -p unity
```

#### 1.2 Create Python Virtual Environment
**Actions:**
```powershell
cd voice_service
python -m venv .venv
.\.venv\Scripts\activate
```

**Verification:**
- Command prompt should show `(.venv)` prefix

#### 1.3 Create requirements.txt
**Actions:**
Create `voice_service/requirements.txt` with:

```txt
# Core Framework
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.10.0
python-multipart==0.0.9
websockets==14.1

# Audio Processing
sounddevice==0.5.1
soundfile==0.12.1
numpy>=1.24.0,<2.0.0
scipy==1.14.1
webrtcvad==2.0.10

# Speech-to-Text
faster-whisper==1.1.0
ctranslate2>=4.0.0

# LLM Client
requests==2.32.3
httpx==0.28.1

# TTS (Kokoro) - adjust based on actual package
torch>=2.0.0,<2.5.0
transformers>=4.36.0
phonemizer==3.3.0

# Pipecat
pipecat-ai>=0.0.1  # Check for latest version

# Utilities
python-dotenv==1.0.1
aiofiles==24.1.0

# Testing
pytest==8.3.4
pytest-asyncio==0.24.0
httpx==0.28.1  # For testing FastAPI
```

**Note:** Kokoro TTS package name may vary. Check the official Kokoro repository for exact installation instructions.

#### 1.4 Install Python Dependencies
**Actions:**
```powershell
pip install -r requirements.txt
```

**Note:** This may take 10-15 minutes depending on your internet connection and CPU.

**Verification:**
```powershell
python -c "import fastapi; import faster_whisper; import webrtcvad; print('All imports successful')"
```

---

## Implementation Phases

### Phase 2: Voice Service - Core Infrastructure

#### 2.1 Configuration Module (`app/config.py`)
**Purpose:** Centralize all configuration settings

**Key Components:**
- Service host/port (127.0.0.1:8008)
- Ollama endpoint (127.0.0.1:11434)
- Audio settings (sample rates, channels)
- Model paths and parameters
- Logging configuration

**Testing:**
- Verify all settings load correctly
- Test environment variable overrides

---

#### 2.2 FastAPI Bootstrap (`app/main.py`)
**Purpose:** Initialize FastAPI app, setup routes, WebSocket, CORS

**Key Components:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes, ws

app = FastAPI(title="Voice Agent Service")

# CORS for localhost Unity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router)
app.include_router(ws.router)
```

**Endpoints to implement:**
- `GET /` - Health check
- `GET /health` - Detailed health status (Ollama connection, models loaded)
- API routes (Phase 3)
- WebSocket (Phase 3)

**Testing:**
- Start server: `uvicorn app.main:app --host 127.0.0.1 --port 8008`
- Verify: `curl http://127.0.0.1:8008/health`

---

### Phase 3: Voice Service - API Layer

#### 3.1 Session Management & REST API (`app/api/routes.py`)
**Purpose:** Handle HTTP endpoints for session control and audio delivery

**Endpoints:**

**POST /session/start**
- Accept: `{session_id?, language, mode}`
- Generate session_id if not provided
- Initialize session state (in-memory dict for POC)
- Start audio capture
- Return: `{session_id, status: "listening"}`

**POST /session/stop**
- Accept: `{session_id, return_audio}`
- Stop audio capture
- Trigger pipeline processing
- Return: `{session_id, status: "processing"}`

**GET /audio/{session_id}/{turn_id}.wav**
- Serve WAV file from `data/audio/{session_id}/{turn_id}.wav`
- Return WAV with proper content-type

**Session State Schema:**
```python
{
    "session_id": str,
    "created_at": datetime,
    "status": "listening | processing | idle",
    "audio_buffer": bytes,
    "turns": [
        {
            "turn_id": str,
            "transcript": str,
            "reply_text": str,
            "audio_path": str
        }
    ]
}
```

**Testing:**
- Unit tests for session creation
- Test concurrent sessions
- Test audio file serving

---

#### 3.2 WebSocket Event Stream (`app/api/ws.py`)
**Purpose:** Real-time event delivery to Unity

**WebSocket Endpoint:** `WS /ws?session_id={session_id}`

**Event Types:**
```python
class EventType(Enum):
    STATE = "state"
    TRANSCRIPT_PARTIAL = "transcript.partial"
    TRANSCRIPT_FINAL = "transcript.final"
    REPLY_TEXT = "reply.text"
    REPLY_AUDIO_READY = "reply.audio_ready"
    ERROR = "error"

class Event:
    type: EventType
    session_id: str
    turn_id: str
    ts: datetime
    payload: dict
```

**Implementation:**
- Maintain WebSocket connection per session
- Broadcast events from pipeline processors
- Handle disconnections gracefully
- Queue events if client temporarily unavailable

**Testing:**
- WebSocket connection test
- Event delivery test
- Reconnection handling

---

### Phase 4: Voice Service - Audio Processing Pipeline

#### 4.1 Audio I/O Utilities (`app/utils/audio_io.py`, `wav_utils.py`)
**Purpose:** Handle microphone capture and WAV file operations

**Key Functions:**
- `capture_audio()` - Capture from default mic using sounddevice
- `save_wav()` - Write audio to WAV file
- `load_wav()` - Load WAV file for processing
- `resample_audio()` - Convert between sample rates (48kHz → 16kHz)
- `normalize_audio()` - Basic audio normalization

**Audio Specs:**
- Input: Mono, 16kHz or 48kHz
- Processing: Float32, normalized [-1.0, 1.0]
- Output: Mono, 24kHz WAV

**Testing:**
- Test mic capture (record 3 seconds, verify)
- Test WAV read/write
- Test resampling accuracy

---

#### 4.2 VAD Processor (`app/pipeline/processors/vad_processor.py`)
**Purpose:** Voice Activity Detection - trim silence, detect speech endpoints

**Configuration:**
```python
VAD_CONFIG = {
    "aggressiveness": 2,  # 0-3, higher = more aggressive
    "frame_duration_ms": 30,  # 10, 20, or 30
    "padding_ms": 300,  # Padding before/after speech
    "max_utterance_sec": 12,  # Maximum recording length
}
```

**Processing Flow:**
1. Receive audio chunks (30ms frames)
2. Run webrtcvad on each frame
3. Detect speech start/end
4. Trim leading/trailing silence
5. Output clean speech segment

**Testing:**
- Test with silent audio (should return empty)
- Test with speech (should trim silence)
- Test with long utterance (should cap at 12s)

---

#### 4.3 STT Processor (`app/pipeline/processors/stt_processor.py`)
**Purpose:** Speech-to-Text using faster-whisper

**Configuration:**
```python
STT_CONFIG = {
    "model_size": "base.en",  # or "small.en" for better accuracy
    "device": "cpu",
    "compute_type": "int8",  # CPU-friendly
    "beam_size": 5,
    "language": "en",
}
```

**Implementation:**
```python
from faster_whisper import WhisperModel

class STTProcessor:
    def __init__(self):
        self.model = WhisperModel(
            STT_CONFIG["model_size"],
            device=STT_CONFIG["device"],
            compute_type=STT_CONFIG["compute_type"]
        )

    def transcribe(self, audio_array: np.ndarray) -> str:
        segments, info = self.model.transcribe(
            audio_array,
            beam_size=STT_CONFIG["beam_size"],
            language=STT_CONFIG["language"]
        )
        transcript = " ".join([seg.text for seg in segments])
        return transcript.strip()
```

**Testing:**
- Test with known audio samples
- Measure transcription accuracy
- Test latency (should be < 2 seconds for 5-second audio)

---

#### 4.4 Math Skills Router (`app/pipeline/processors/skills_router.py`, `app/utils/text_math.py`)
**Purpose:** Detect math questions and compute answers deterministically

**Math Detection Patterns:**
```python
OPERATORS = {
    "plus", "add", "added to",
    "minus", "subtract", "take away",
    "times", "multiplied by", "multiply",
    "divided by", "divide"
}

NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, ..., "hundred": 100
}
```

**Routing Logic:**
1. Normalize transcript (lowercase, strip)
2. Check for operator keywords
3. Extract numbers (digits or words)
4. Parse expression (2 operands for POC)
5. If math detected → compute answer
6. If not math → pass to LLM

**Math Response Templates:**
```python
MATH_RESPONSES = {
    "add": "{a} plus {b} is {result}.",
    "subtract": "{a} minus {b} is {result}.",
    "multiply": "{a} times {b} is {result}.",
    "divide": "{a} divided by {b} is {result}.",
    "divide_by_zero": "I can't divide by zero. Try another number."
}
```

**Examples:**
- "what is five plus five" → "Five plus five is ten."
- "12 divided by 0" → "I can't divide by zero. Try another number."
- "what's 7 times 8" → "Seven times eight is fifty-six."

**Testing:**
- **Critical:** Test all operators with various inputs
- Test spoken numbers ("five") vs digits ("5")
- Test edge cases (divide by zero, negative results)
- Test non-math queries (should route to LLM)

---

#### 4.5 LLM Processor (`app/pipeline/processors/llm_ollama.py`)
**Purpose:** Handle non-math queries via Ollama

**Ollama API Client:**
```python
import requests

class OllamaClient:
    def __init__(self, base_url="http://127.0.0.1:11434"):
        self.base_url = base_url
        self.model = "qwen2.5:0.5b-instruct"

    def generate(self, prompt: str, system: str, context: list) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "context": context,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 100  # Keep responses short
            }
        }
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload
        )
        return response.json()["response"]
```

**System Prompt:**
```
You are a friendly game character talking to a child age 5+.
Use simple words and short sentences.
Answer in 1 or 2 sentences.
If the child asks for something unsafe or grown-up, say you can't help and offer a safe topic.
If you don't understand, ask one short question.
```

**Context Window:**
- Keep last 4 turns (user + assistant pairs)
- Format: `[{user: "...", assistant: "..."}, ...]`

**Testing:**
- Test basic questions ("What is a dog?")
- Test conversation continuity (context)
- Measure response time

---

#### 4.6 Response Shaper (`app/pipeline/processors/response_shaper.py`, `app/utils/safety_filter.py`)
**Purpose:** Enforce kid-mode constraints and safety

**Constraints:**
```python
MAX_SENTENCES = 2
MAX_WORDS = 35
```

**Safety Filter:**
```python
UNSAFE_KEYWORDS = [
    # Profanity
    "badword1", "badword2", ...

    # Adult content
    "sex", "drug", ...

    # Violence
    "kill", "hurt", "weapon", ...

    # Self-harm
    "suicide", "harm yourself", ...
]

SAFE_FALLBACK = "I can't help with that. Let's talk about something safe, like animals or math."
```

**Shaping Logic:**
1. Check for unsafe keywords → return safe fallback if found
2. Count sentences → truncate if > 2
3. Count words → truncate if > 35 (try to end at sentence boundary)
4. Simplify vocabulary (optional, soft goal)

**Testing:**
- Test unsafe content detection
- Test sentence/word truncation
- Test edge cases (exactly 2 sentences, exactly 35 words)

---

#### 4.7 TTS Processor (`app/pipeline/processors/tts_kokoro.py`)
**Purpose:** Text-to-Speech using Kokoro

**Note:** Exact implementation depends on Kokoro package. General approach:

```python
from kokoro import KokoroTTS  # Example, verify actual import

class TTSProcessor:
    def __init__(self):
        self.tts = KokoroTTS(
            model="Kokoro-82M",
            device="cpu",
            espeak_path="C:\\Program Files\\eSpeak NG\\espeak-ng.exe"
        )

    def synthesize(self, text: str, output_path: str):
        audio = self.tts.generate(text, voice="child_friendly")
        self.tts.save_wav(audio, output_path, sample_rate=24000)
```

**Output:**
- Format: Mono WAV
- Sample Rate: 24kHz
- Bit Depth: 16-bit PCM

**Testing:**
- Synthesize test phrases
- Verify audio quality (listen)
- Measure synthesis time (should be < 1 second per sentence)

---

#### 4.8 Output Events Processor (`app/pipeline/processors/output_events.py`)
**Purpose:** Emit WebSocket events at each pipeline stage

**Events to Emit:**
1. **State: listening** (when mic capture starts)
2. **State: thinking** (when processing pipeline)
3. **Transcript final** (after STT)
4. **Reply text** (after response shaping)
5. **State: speaking** (when TTS starts)
6. **Reply audio ready** (after TTS completes)
7. **State: idle** (when turn completes)
8. **Error** (on any failure)

**Implementation:**
- Inject WebSocket manager into processors
- Call `emit_event(session_id, event)` at each stage

**Testing:**
- Mock WebSocket and verify events
- Test event ordering
- Test error event on failure

---

#### 4.9 Pipeline Orchestration (`app/pipeline/build_pipeline.py`)
**Purpose:** Wire all processors together using Pipecat

**Pipeline Structure:**
```python
from pipecat import Pipeline

def build_pipeline(session_id: str, ws_manager):
    pipeline = Pipeline([
        AudioInputProcessor(session_id),
        VADProcessor(),
        STTProcessor(),
        SkillsRouterProcessor(),  # Math or LLM
        LLMProcessor(),           # Only if not math
        ResponseShaperProcessor(),
        TTSProcessor(session_id),
        OutputEventsProcessor(session_id, ws_manager)
    ])
    return pipeline

async def run_turn(session_id: str, audio_data: bytes):
    pipeline = build_pipeline(session_id, ws_manager)
    result = await pipeline.process(audio_data)
    return result
```

**Testing:**
- End-to-end test with sample audio
- Test math path (should skip LLM)
- Test LLM path
- Measure total latency (target < 5 seconds)

---

### Phase 5: Unity Game - Project Setup

#### 5.1 Create Unity Project
**Actions:**
1. Open Unity Hub
2. New Project → 3D Core (or 2D if you prefer)
3. Name: `KidsVoiceGame`
4. Location: `C:\Users\rober\OneDrive\dev\ai\voice-game\unity\`
5. Create

**Verification:**
- Project opens successfully in Unity Editor

---

#### 5.2 Project Settings
**Actions:**
1. Edit → Project Settings → Player
2. Company Name: [Your Name]
3. Product Name: Kids Voice Game POC
4. Target Platform: Windows (standalone)
5. API Compatibility Level: .NET Standard 2.1

**Verification:**
- Settings saved

---

#### 5.3 Install NuGet Package (Newtonsoft.Json)
**Actions:**
1. Download `Newtonsoft.Json.dll` for Unity
   - Or use NuGetForUnity package
2. Place in `Assets/Plugins/`
3. Verify import in Unity

**Alternative:** Use Unity's built-in JsonUtility (more limited but no dependencies)

---

#### 5.4 Install WebSocket Client
**Actions:**
1. Install `NativeWebSocket` package:
   - Window → Package Manager
   - Add package from git URL: `https://github.com/endel/NativeWebSocket.git#upm`

**Alternative:** Use `websocket-sharp` or write custom WebSocket client

**Verification:**
- Package appears in Package Manager

---

### Phase 6: Unity Game - API Client Layer

#### 6.1 HTTP Client (`Assets/Scripts/Api/VoiceServiceClient.cs`)
**Purpose:** Handle HTTP requests to Voice Service

**Key Methods:**
```csharp
public class VoiceServiceClient : MonoBehaviour
{
    private string baseUrl = "http://127.0.0.1:8008";

    public async Task<SessionStartResponse> StartSession();
    public async Task<SessionStopResponse> StopSession(string sessionId);
    public async Task<AudioClip> DownloadAudio(string url);
}
```

**Implementation Details:**
- Use `UnityWebRequest` for HTTP calls
- Handle JSON serialization/deserialization
- Error handling and timeouts

**Testing:**
- Test with Voice Service running
- Test error handling (service down)

---

#### 6.2 WebSocket Client (`Assets/Scripts/Api/VoiceWsClient.cs`)
**Purpose:** Receive real-time events from Voice Service

**Key Methods:**
```csharp
public class VoiceWsClient : MonoBehaviour
{
    private WebSocket ws;

    public async Task Connect(string sessionId);
    public void Disconnect();

    // Events
    public event Action<string> OnTranscriptFinal;
    public event Action<string> OnReplyText;
    public event Action<AudioReadyPayload> OnReplyAudioReady;
    public event Action<string> OnStateChange;
    public event Action<string> OnError;
}
```

**Event Handling:**
- Parse incoming JSON events
- Trigger C# events for subscribers
- Handle reconnection logic

**Testing:**
- Test event reception
- Test reconnection on disconnect

---

### Phase 7: Unity Game - Audio System

#### 7.1 WAV Loader (`Assets/Scripts/Audio/WavLoader.cs`)
**Purpose:** Load WAV files into AudioClip

**Implementation:**
```csharp
public static class WavLoader
{
    public static AudioClip LoadFromBytes(byte[] wavData, string name = "clip")
    {
        // Parse WAV header
        // Extract PCM data
        // Create AudioClip
        // Return clip
    }
}
```

**Testing:**
- Test with known WAV files
- Verify audio plays correctly

---

#### 7.2 Audio Player (`Assets/Scripts/Audio/AudioPlayer.cs`)
**Purpose:** Play TTS audio and manage playback state

**Key Methods:**
```csharp
public class AudioPlayer : MonoBehaviour
{
    private AudioSource audioSource;

    public void PlayClip(AudioClip clip);
    public void Stop();
    public bool IsPlaying { get; }

    public event Action OnPlaybackComplete;
}
```

**Testing:**
- Test audio playback
- Test stop functionality
- Verify event firing on completion

---

### Phase 8: Unity Game - UI System

#### 8.1 Game States
**States:**
- **Idle**: Waiting for user input
- **Listening**: Recording user speech
- **Thinking**: Processing in backend
- **Speaking**: Playing TTS response

**State Machine:**
```csharp
public enum GameState { Idle, Listening, Thinking, Speaking }

public class GameStateManager : MonoBehaviour
{
    public GameState CurrentState { get; private set; }

    public void SetState(GameState newState);

    public event Action<GameState> OnStateChanged;
}
```

---

#### 8.2 Push-to-Talk Controller (`Assets/Scripts/UI/PushToTalkController.cs`)
**Purpose:** Handle talk button interaction

**Behavior:**
- User presses/holds button → start listening
- User releases button → stop listening
- Visual feedback (button color, scale animation)

**Implementation:**
```csharp
public class PushToTalkController : MonoBehaviour
{
    private Button talkButton;
    private VoiceServiceClient client;
    private GameStateManager stateManager;

    void Start()
    {
        talkButton.onClick.AddListener(OnTalkButtonPressed);
    }

    async void OnTalkButtonPressed()
    {
        if (stateManager.CurrentState == GameState.Idle)
        {
            await StartListening();
        }
        else if (stateManager.CurrentState == GameState.Listening)
        {
            await StopListening();
        }
    }
}
```

**Alternative:** Use EventTrigger for press/release events (hold-to-talk)

**Testing:**
- Test button states
- Test rapid clicking
- Test while already processing

---

#### 8.3 Caption Controller (`Assets/Scripts/UI/CaptionController.cs`)
**Purpose:** Display transcript and reply text

**UI Elements:**
- Transcript text box (user speech)
- Reply text box (character response)

**Implementation:**
```csharp
public class CaptionController : MonoBehaviour
{
    public TextMeshProUGUI transcriptText;
    public TextMeshProUGUI replyText;

    public void ShowTranscript(string text);
    public void ShowReply(string text);
    public void Clear();
}
```

**Styling:**
- Large, readable font (kid-friendly)
- High contrast colors
- Optional text animations (fade in)

**Testing:**
- Test text display
- Test long text (overflow handling)

---

#### 8.4 Character State Controller (`Assets/Scripts/UI/CharacterStateController.cs`)
**Purpose:** Animate character based on game state

**States:**
- Idle: Neutral/breathing animation
- Listening: Attentive, ears perk up
- Thinking: Thoughtful expression
- Speaking: Mouth moves, animated

**Implementation:**
```csharp
public class CharacterStateController : MonoBehaviour
{
    public Animator characterAnimator;

    public void SetIdleState();
    public void SetListeningState();
    public void SetThinkingState();
    public void SetSpeakingState();
}
```

**POC Simplification:**
- Use simple sprite swaps or color changes
- Full animation can be added post-POC

**Testing:**
- Test all state transitions
- Verify visuals match state

---

### Phase 9: Unity Game - Main Game Controller

#### 9.1 Main Controller (`Assets/Scripts/GameController.cs`)
**Purpose:** Orchestrate all components

**Responsibilities:**
- Initialize all systems
- Connect WebSocket events to UI updates
- Manage conversation flow
- Handle errors

**Conversation Flow:**
```csharp
public class GameController : MonoBehaviour
{
    // References
    private VoiceServiceClient httpClient;
    private VoiceWsClient wsClient;
    private GameStateManager stateManager;
    private PushToTalkController talkController;
    private CaptionController captionController;
    private CharacterStateController characterController;
    private AudioPlayer audioPlayer;

    private string currentSessionId;

    async void Start()
    {
        // Initialize components
        await ConnectWebSocket();
        SetupEventHandlers();
    }

    void SetupEventHandlers()
    {
        wsClient.OnStateChange += HandleStateChange;
        wsClient.OnTranscriptFinal += captionController.ShowTranscript;
        wsClient.OnReplyText += captionController.ShowReply;
        wsClient.OnReplyAudioReady += HandleAudioReady;
        wsClient.OnError += HandleError;

        audioPlayer.OnPlaybackComplete += () => stateManager.SetState(GameState.Idle);
    }

    async void HandleAudioReady(AudioReadyPayload payload)
    {
        AudioClip clip = await httpClient.DownloadAudio(payload.url);
        audioPlayer.PlayClip(clip);
    }

    void HandleStateChange(string state)
    {
        switch (state)
        {
            case "listening":
                stateManager.SetState(GameState.Listening);
                characterController.SetListeningState();
                break;
            case "thinking":
                stateManager.SetState(GameState.Thinking);
                characterController.SetThinkingState();
                break;
            case "speaking":
                stateManager.SetState(GameState.Speaking);
                characterController.SetSpeakingState();
                break;
            case "idle":
                stateManager.SetState(GameState.Idle);
                characterController.SetIdleState();
                break;
        }
    }
}
```

**Testing:**
- Full end-to-end test
- Test error recovery
- Test multiple turns

---

### Phase 10: Launcher Scripts

#### 10.1 Health Check Script (`scripts/health_check.ps1`)
**Purpose:** Verify all services are running

```powershell
# Check Ollama
$ollamaStatus = Invoke-RestMethod -Uri "http://127.0.0.1:11434" -Method Get
if ($ollamaStatus -match "Ollama is running") {
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} else {
    Write-Host "✗ Ollama is not running" -ForegroundColor Red
}

# Check Voice Service
try {
    $voiceStatus = Invoke-RestMethod -Uri "http://127.0.0.1:8008/health" -Method Get
    Write-Host "✓ Voice Service is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Voice Service is not running" -ForegroundColor Red
}

# Check eSpeak NG
$espeakPath = "C:\Program Files\eSpeak NG\espeak-ng.exe"
if (Test-Path $espeakPath) {
    Write-Host "✓ eSpeak NG is installed" -ForegroundColor Green
} else {
    Write-Host "✗ eSpeak NG is not installed" -ForegroundColor Red
}
```

---

#### 10.2 Run All Script (`scripts/run_all.ps1`)
**Purpose:** Start all services in correct order

```powershell
Write-Host "Starting Voice Conversational Kids Game..." -ForegroundColor Cyan

# Check Ollama
Write-Host "Checking Ollama..." -ForegroundColor Yellow
try {
    $ollamaStatus = Invoke-RestMethod -Uri "http://127.0.0.1:11434" -Method Get
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "Starting Ollama..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

# Start Voice Service
Write-Host "Starting Voice Service..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\..\voice_service"
Start-Process "powershell" -ArgumentList "-NoExit", "-Command", ".\.venv\Scripts\activate; uvicorn app.main:app --host 127.0.0.1 --port 8008"

Write-Host "`nAll services started!" -ForegroundColor Green
Write-Host "Voice Service: http://127.0.0.1:8008" -ForegroundColor Cyan
Write-Host "Now open Unity and press Play." -ForegroundColor Cyan
```

---

## Testing Strategy

### Unit Tests

#### Python Voice Service Tests

**Test Math Router (`tests/test_math_router.py`):**
```python
def test_addition():
    assert parse_math("what is 5 plus 5") == ("add", 5, 5)
    assert compute_math("add", 5, 5) == 10
    assert format_math_response("add", 5, 5, 10) == "Five plus five is ten."

def test_division_by_zero():
    result = compute_math("divide", 10, 0)
    assert result == "error:divide_by_zero"

def test_non_math():
    assert is_math_query("what is a dog") == False
```

**Test Safety Filter (`tests/test_safety_filter.py`):**
```python
def test_unsafe_keywords():
    assert is_safe("Hello, how are you?") == True
    assert is_safe("Tell me about violence") == False

def test_response_shaping():
    long_text = "This is sentence one. This is sentence two. This is sentence three."
    shaped = shape_response(long_text)
    assert count_sentences(shaped) <= 2
    assert count_words(shaped) <= 35
```

**Test API Endpoints (`tests/test_api.py`):**
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_session_start():
    response = client.post("/session/start", json={"language": "en", "mode": "ptt"})
    assert response.status_code == 200
    assert "session_id" in response.json()
```

---

#### Unity Tests

**Test State Transitions:**
- Create play mode tests
- Verify state changes on events
- Test button enable/disable logic

**Test Audio Loading:**
- Test WAV parser with sample files
- Verify AudioClip creation

---

### Integration Tests

#### Voice Service Integration

**Test End-to-End Pipeline:**
1. Load sample audio file (known phrase)
2. Process through entire pipeline
3. Verify:
   - Transcript matches expected text
   - Math is computed correctly (if math)
   - Reply text is kid-friendly
   - TTS audio is generated
   - All events are emitted

**Example:**
```python
async def test_pipeline_math():
    audio = load_test_audio("five_plus_five.wav")
    result = await run_turn("test-session", audio)
    assert result["transcript"] == "five plus five"
    assert result["reply_text"] == "Five plus five is ten."
    assert os.path.exists(result["audio_path"])
```

---

#### Unity-Service Integration

**Test Full Interaction:**
1. Start Voice Service
2. Start Unity in test mode
3. Simulate button press
4. Record test audio (or use pre-recorded)
5. Verify:
   - HTTP requests succeed
   - WebSocket events received
   - Transcript displayed
   - Reply displayed
   - Audio plays

**Manual Test Protocol:**
- Start services
- Press Talk button in Unity
- Speak: "What is three plus seven?"
- Verify: Hears "Three plus seven is ten."
- Speak: "What is a cat?"
- Verify: Hears appropriate response about cats

---

### Performance Tests

**Measure Latency:**
- STT latency: < 2 seconds for 5-second audio
- LLM latency: < 3 seconds for response
- TTS latency: < 1 second per sentence
- Total turn latency: < 5 seconds (goal)

**Measure CPU Usage:**
- Voice Service: < 50% CPU during processing
- Unity: < 30% CPU during playback

**Measure Memory:**
- Voice Service: < 500 MB RAM
- Unity: < 1 GB RAM

---

## Integration & Validation

### Integration Checklist

#### Phase 11: First Integration Test

1. **Start Services:**
   - Run `scripts\run_all.ps1`
   - Verify Ollama running: `curl http://127.0.0.1:11434`
   - Verify Voice Service: `curl http://127.0.0.1:8008/health`

2. **Open Unity:**
   - Open Unity project
   - Press Play

3. **Test Basic Flow:**
   - Press Talk button
   - Speak: "Hello"
   - Verify: Response heard

4. **Test Math:**
   - Press Talk button
   - Speak: "What is two plus two?"
   - Verify: "Two plus two is four." (heard)

5. **Test Error Handling:**
   - Stop Voice Service
   - Press Talk button
   - Verify: Error message displayed

---

### Debugging Guide

**Common Issues:**

1. **WebSocket Connection Fails**
   - Check Voice Service is running
   - Check firewall settings
   - Verify URL: `ws://127.0.0.1:8008/ws`

2. **No Audio Captured**
   - Check microphone permissions
   - Verify default mic in Windows settings
   - Test with: `python -m sounddevice`

3. **STT Returns Empty**
   - Audio too short (< 1 second)
   - Audio too quiet (increase mic gain)
   - VAD too aggressive (reduce aggressiveness)

4. **Math Not Detected**
   - Check transcript for exact phrasing
   - Add more operator keywords
   - Log routing decision for debugging

5. **TTS Fails**
   - Verify eSpeak NG installed and on PATH
   - Check Kokoro model loaded
   - Test eSpeak directly: `espeak-ng "test"`

6. **Ollama Connection Fails**
   - Restart Ollama: `ollama serve`
   - Check model pulled: `ollama list`
   - Test: `curl http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5:0.5b-instruct","prompt":"Hi"}'`

---

## Acceptance Criteria

### POC Definition of Done

| Criterion | Test Method | Expected Result |
|-----------|-------------|-----------------|
| 1. Push-to-talk works | Press button, speak, release | Audio captured |
| 2. Transcript displayed | Speak "hello world" | "hello world" appears on screen |
| 3. Reply heard | Complete turn | Audio response plays |
| 4. Math correct | Ask "what is 5 plus 5" | Hear "Five plus five is ten." |
| 5. Short responses | Ask any question | Response is 1-2 sentences |
| 6. Local execution | Disconnect internet | Still works (after models downloaded) |
| 7. Multiple turns | Ask 3 questions | All 3 answered correctly |
| 8. Error handling | Stop service mid-turn | Error message shown, recovers gracefully |

---

### Final Validation Checklist

- [ ] All system dependencies installed
- [ ] Python virtual environment setup
- [ ] All Python packages installed
- [ ] Ollama model downloaded
- [ ] Voice Service starts without errors
- [ ] Unity project opens without errors
- [ ] WebSocket connects successfully
- [ ] Math router handles all operators
- [ ] Safety filter blocks unsafe content
- [ ] Response shaper enforces limits
- [ ] Audio quality is acceptable
- [ ] Latency is under 5 seconds per turn
- [ ] UI is kid-friendly
- [ ] Character animations work
- [ ] Launcher scripts work
- [ ] Health check passes
- [ ] All acceptance criteria met

---

## Troubleshooting Guide

### Service Won't Start

**Symptom:** Voice Service fails to start

**Possible Causes:**
1. Port 8008 already in use
   - Solution: Check `netstat -ano | findstr :8008`, kill process or change port
2. Missing dependencies
   - Solution: Re-run `pip install -r requirements.txt`
3. Python version mismatch
   - Solution: Verify Python 3.11+ with `python --version`

---

### Audio Issues

**Symptom:** No audio captured or played

**Microphone Capture Issues:**
1. Check Windows microphone permissions
2. Set default microphone in Windows Sound settings
3. Test with: `python -c "import sounddevice; sounddevice.rec(44100)"`

**Audio Playback Issues:**
1. Check default speakers in Windows Sound settings
2. Verify WAV file is valid (open in media player)
3. Check Unity AudioSource settings

---

### Model Performance Issues

**Symptom:** Very slow responses (> 10 seconds)

**Solutions:**
1. Use smaller models:
   - STT: `base.en` instead of `small.en`
   - LLM: `qwen2.5:0.5b-instruct` (already smallest)
2. Reduce beam size in STT (trade accuracy for speed)
3. Close other applications to free CPU

---

## Next Steps After POC

1. **Improve Accuracy:**
   - Upgrade to `small.en` STT model
   - Test larger LLM models (1.5b)

2. **Add Features:**
   - Conversation history display
   - Multiple character voices
   - Mini-games (quiz mode, animal facts)

3. **Polish UI:**
   - Better animations
   - Sound effects
   - Colorful character design

4. **Optimize Performance:**
   - Stream TTS audio (reduce latency)
   - Cache common responses
   - Parallel processing where possible

5. **Safety Enhancements:**
   - Parental controls
   - Content logging for review
   - Age-appropriate topic filters

---

## Appendix

### Estimated Time to Completion

| Phase | Estimated Time | Complexity |
|-------|----------------|------------|
| Phase 0: Prerequisites | 1-2 hours | Easy |
| Phase 1: Project Setup | 30 min | Easy |
| Phase 2: Core Infrastructure | 2 hours | Medium |
| Phase 3: API Layer | 3 hours | Medium |
| Phase 4: Audio Pipeline | 8-12 hours | Hard |
| Phase 5: Unity Setup | 1 hour | Easy |
| Phase 6: API Client | 2 hours | Medium |
| Phase 7: Audio System | 2 hours | Medium |
| Phase 8: UI System | 3 hours | Medium |
| Phase 9: Main Controller | 2 hours | Medium |
| Phase 10: Scripts | 1 hour | Easy |
| Testing & Integration | 4-6 hours | Medium |
| **Total** | **29-42 hours** | |

---

### Resources

**Documentation:**
- FastAPI: https://fastapi.tiangolo.com/
- Pipecat: https://github.com/pipecat-ai/pipecat
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- Unity WebGL: https://docs.unity3d.com/Manual/webgl-networking.html

**Community:**
- Discord/forums for Pipecat
- Unity forums
- Ollama Discord

---

## Questions & Clarifications

Before starting implementation, consider clarifying:

1. **Character Design:** What should the character look like? (2D sprite, 3D model, simple shape?)
2. **Voice Preference:** Should TTS voice sound child-like or adult-friendly?
3. **Conversation Topics:** Any specific topics to prioritize? (animals, colors, counting, etc.)
4. **Deployment:** Will this be distributed? (If yes, consider packaging/installers)

---

**Document End**

Review this plan carefully and let me know if you'd like to:
- Adjust priorities
- Add more detail to any section
- Clarify any technical decisions
- Begin implementation of a specific phase
