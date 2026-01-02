\# Voice Conversational Kids Game (5+) — Windows CPU POC

\*\*Unity UI + Local Pipecat Voice Service + Ollama (LLM) + faster-whisper (STT) + Kokoro (TTS)\*\*



This document is a build-ready technical outline for a \*\*Windows PC proof-of-concept\*\*.  

Goal: a child presses a button, speaks into the mic, the game understands and responds out loud with \*\*short, simple\*\*, kid-friendly answers (and gets \*\*basic math\*\* correct).



---



\## 0) Summary of what you’re building



\### Runtime (local, on one Windows PC)

\- \*\*Unity Game (C#)\*\*: UI, character, captions, button, audio playback.

\- \*\*Voice Agent Service (Python)\*\*: Pipecat-driven pipeline (VAD → STT → Skills → LLM → TTS).

\- \*\*Ollama (local service)\*\*: hosts a small instruct LLM (CPU-friendly).

\- \*\*eSpeak NG\*\*: required dependency for Kokoro voice synthesis.



\### Key POC behaviors

\- \*\*Push-to-talk\*\* in Unity (simple turn-taking).

\- \*\*Deterministic math router\*\* (so “5 plus 5” always answers “10”).

\- \*\*Kid-mode prompt\*\* (1–2 short sentences; safe topics only).

\- \*\*Local-only\*\* execution after model downloads.



---



\## 1) Process layout (how programs run)



\### Processes

1\. \*\*Ollama\*\* (background service)

&nbsp;  - Listens on `http://127.0.0.1:11434`

&nbsp;  - Provides LLM inference locally via HTTP.



2\. \*\*Voice Agent Service\*\* (Python)

&nbsp;  - Runs a FastAPI server:

&nbsp;    - HTTP on `http://127.0.0.1:8008`

&nbsp;    - WebSocket on `ws://127.0.0.1:8008/ws`

&nbsp;  - Owns mic capture + VAD + STT + Pipecat orchestration + TTS.



3\. \*\*Unity Game\*\* (Windows app)

&nbsp;  - Calls Voice Agent Service endpoints.

&nbsp;  - Plays returned WAV audio via `AudioSource`.

&nbsp;  - Updates UI states and captions.



\### Recommended port map (localhost only)

| Component | Protocol | Host | Port | Notes |

|---|---|---:|---:|---|

| Ollama | HTTP | 127.0.0.1 | 11434 | LLM inference |

| Voice Agent Service | HTTP | 127.0.0.1 | 8008 | REST API |

| Voice Agent Service | WebSocket | 127.0.0.1 | 8008 | Real-time events |



\*\*Security note (POC):\*\* bind to localhost only.



---



\## 2) Architecture diagram (logical)



Unity (UI)

\- Push-to-talk button + captions + character states

\- Audio playback



↕ (HTTP + WebSocket, localhost)



Python Voice Agent Service (Pipecat)

\- Mic capture

\- VAD/endpointing

\- STT (faster-whisper)

\- Skills router (math)

\- LLM client (Ollama)

\- Response shaping (kid-mode)

\- TTS (Kokoro)

\- Emits events + audio for Unity



↕ (HTTP, localhost)



Ollama LLM

\- small instruct model (CPU)



---



\## 3) Tech stack



\### Unity (C#)

\- Unity 2022 LTS or 2023 LTS

\- UI: Canvas UI (simple), later optionally UI Toolkit

\- Networking:

&nbsp; - `UnityWebRequest` (HTTP)

&nbsp; - WebSocket client (e.g., `NativeWebSocket` or similar)

\- Audio: `AudioClip.Create` + `AudioSource`

\- JSON: `Newtonsoft.Json` (recommended)



\### Python Voice Agent Service

\- Python 3.11+ recommended (3.12 ok)

\- FastAPI + Uvicorn

\- Pipecat (pipeline orchestration)

\- Audio I/O:

&nbsp; - `sounddevice` (mic capture)

&nbsp; - `soundfile` or `wave` (WAV writing)

\- VAD:

&nbsp; - `webrtcvad` (fast CPU endpointing)

\- STT:

&nbsp; - `faster-whisper` (CTranslate2) with `base.en` or `small.en`

\- LLM:

&nbsp; - Ollama HTTP client (simple requests)

\- TTS:

&nbsp; - Kokoro (Kokoro-82M)

&nbsp; - Requires \*\*eSpeak NG\*\* installed on Windows



\### Third-party apps

\- Ollama (Windows installer)

\- eSpeak NG (Windows installer)

\- Git + Git LFS (for model assets if needed)

\- (Optional) FFmpeg (audio debugging)



---



\## 4) POC interaction flow



\### Turn-taking (Push-to-talk)

1\. User holds/taps “Talk” in Unity.

2\. Unity calls `/session/start` to begin listening.

3\. Python service captures mic audio until Unity calls `/session/stop`.

4\. Python runs pipeline:

&nbsp;  - VAD trim → STT → route (math vs LLM) → response shaping → TTS.

5\. Python emits events to Unity over WebSocket:

&nbsp;  - partial transcript (optional)

&nbsp;  - final transcript

&nbsp;  - reply text

&nbsp;  - reply audio ready

6\. Unity plays reply audio, shows captions, sets character state “Speaking”.



---



\## 5) API contract (Unity ↔ Voice Service)



\### 5.1 REST endpoints (minimum)



\#### `POST /session/start`

Start mic capture for a new turn.

\- Request JSON:

```json

{

&nbsp; "session\_id": "optional-guid",

&nbsp; "language": "en",

&nbsp; "mode": "ptt"

}

```

\- Response JSON:

```json

{

&nbsp; "session\_id": "generated-guid",

&nbsp; "status": "listening"

}

```



\#### `POST /session/stop`

Stop mic capture and process the turn.

\- Request JSON:

```json

{

&nbsp; "session\_id": "guid",

&nbsp; "return\_audio": true

}

```

\- Response JSON:

```json

{

&nbsp; "session\_id": "guid",

&nbsp; "status": "processing"

}

```



Processing results are delivered via WebSocket events, plus optional direct download URL for the WAV.



\#### `GET /audio/{session\_id}/{turn\_id}.wav`

Download synthesized TTS audio for the reply.



---



\### 5.2 WebSocket events (recommended)



\#### `WS /ws?session\_id=...`

Server sends events as JSON lines.



\*\*Event envelope\*\*

```json

{

&nbsp; "type": "transcript.partial | transcript.final | reply.text | reply.audio\_ready | error | state",

&nbsp; "session\_id": "guid",

&nbsp; "turn\_id": "guid",

&nbsp; "ts": "2025-12-23T00:00:00Z",

&nbsp; "payload": {}

}

```



\*\*State events\*\*

```json

{

&nbsp; "type": "state",

&nbsp; "payload": { "state": "listening | thinking | speaking | idle" }

}

```



\*\*Transcript final\*\*

```json

{

&nbsp; "type": "transcript.final",

&nbsp; "payload": { "text": "what is five plus five" }

}

```



\*\*Reply text\*\*

```json

{

&nbsp; "type": "reply.text",

&nbsp; "payload": { "text": "Five plus five is ten. Want another one?" }

}

```



\*\*Reply audio ready\*\*

```json

{

&nbsp; "type": "reply.audio\_ready",

&nbsp; "payload": {

&nbsp;   "url": "http://127.0.0.1:8008/audio/<session>/<turn>.wav",

&nbsp;   "duration\_ms": 1800,

&nbsp;   "format": "wav",

&nbsp;   "sample\_rate\_hz": 24000,

&nbsp;   "channels": 1

&nbsp; }

}

```



\*\*Error\*\*

```json

{

&nbsp; "type": "error",

&nbsp; "payload": { "code": "STT\_FAILED", "message": "..." }

}

```



---



\## 6) Audio formats and constraints



\### Mic input (service side)

\- Capture mono audio at \*\*16 kHz\*\* or \*\*48 kHz\*\*

\- Convert to mono float32 for processing

\- Normalize/clamp lightly (avoid heavy DSP in POC)



\### STT input

\- faster-whisper works well with 16 kHz PCM

\- Keep segments < 15s for snappy UX



\### TTS output

\- Output \*\*mono WAV\*\* at \*\*24 kHz\*\* (common for Kokoro)

\- Unity reads WAV into `AudioClip` and plays



---



\## 7) Pipecat pipeline design (processors)



\*\*Pipeline (high level)\*\*

1\. AudioInputProcessor

2\. VADProcessor (webrtcvad)

3\. STTProcessor (faster-whisper)

4\. SkillsRouterProcessor

5\. LLMProcessor (Ollama client)

6\. ResponseShaperProcessor (kid-mode)

7\. TTSProcessor (Kokoro)

8\. OutputProcessor (WAV write + WebSocket events)



\### Processor responsibilities



\#### 7.1 VADProcessor

\- Detect speech frames

\- Trim leading/trailing silence

\- Provide final speech chunk to STT



Config:

\- aggressiveness: 2 (start)

\- padding: 200–400ms

\- max utterance: 12s (POC)



\#### 7.2 STTProcessor

\- Model: `base.en` (start) or `small.en` if accuracy needs improvement

\- Return:

&nbsp; - final text

&nbsp; - optional word timestamps (not required in POC)



\#### 7.3 SkillsRouterProcessor (must-have)

Route before LLM.

Rules:

\- Math intent → deterministic compute

\- Otherwise → LLM



Math parsing approach (safe):

\- Convert spoken numbers to digits (basic map: one..twenty, thirty, forty... one hundred)

\- Operators: plus/add, minus/subtract, times/multiplied, divided by

\- Allow simple two-operand expressions for POC

\- If ambiguous, ask a clarifying question.



Example outputs:

\- “5 plus 5” → “Five plus five is ten.”

\- “12 divided by 0” → “I can’t divide by zero. Try another number.”



\#### 7.4 LLMProcessor (Ollama)

\- Call Ollama `POST /api/generate` or chat endpoint (depending on model)

\- Provide:

&nbsp; - system prompt (kid mode)

&nbsp; - short conversation context window (last 4 turns)



LLM model suggestion:

\- Start: `qwen2.5:0.5b-instruct` (fast)

\- If too weak: `qwen2.5:1.5b-instruct` (better reasoning)



\#### 7.5 ResponseShaperProcessor (kid-mode guardrails)

Enforce:

\- Max 2 sentences

\- Max 25–35 words (hard cap)

\- Simple vocabulary (soft goal)

\- Refuse unsafe topics (basic filter)

\- If unsure: ask one short question



Also apply a basic content filter:

\- profanity blacklist

\- adult content keywords

\- self-harm instructions

\- violence/weapon instructions



POC behavior on unsafe:

\- “I can’t help with that. Let’s talk about something safe, like animals or math.”



\#### 7.6 TTSProcessor (Kokoro)

\- Convert reply text → WAV

\- Write to `./data/audio/<session>/<turn>.wav`

\- Emit `reply.audio\_ready` event with URL



---



\## 8) Kid-mode prompts (templates)



\### System prompt (recommended baseline)

> You are a friendly game character talking to a child age 5+.  

> Use simple words and short sentences.  

> Answer in 1 or 2 sentences.  

> If the child asks for something unsafe or grown-up, say you can’t help and offer a safe topic.  

> If you don’t understand, ask one short question.



\### LLM user prompt wrapper

\- Include transcript

\- Include a short instruction: “Reply briefly. One or two sentences.”



---



\## 9) Folder structure (repo layout)



```

kids-voice-game-poc/

&nbsp; unity/

&nbsp;   KidsVoiceGame/                 # Unity project

&nbsp;     Assets/

&nbsp;       Scripts/

&nbsp;         Api/

&nbsp;           VoiceServiceClient.cs

&nbsp;           VoiceWsClient.cs

&nbsp;         UI/

&nbsp;           PushToTalkController.cs

&nbsp;           CaptionController.cs

&nbsp;           CharacterStateController.cs

&nbsp;         Audio/

&nbsp;           WavLoader.cs

&nbsp;           AudioPlayer.cs

&nbsp;     ProjectSettings/

&nbsp; voice\_service/

&nbsp;   app/

&nbsp;     main.py                      # FastAPI bootstrap

&nbsp;     config.py

&nbsp;     api/

&nbsp;       routes.py                  # /session, /audio

&nbsp;       ws.py                      # websocket manager

&nbsp;     pipeline/

&nbsp;       build\_pipeline.py          # Pipecat pipeline wiring

&nbsp;       processors/

&nbsp;         vad\_processor.py

&nbsp;         stt\_processor.py

&nbsp;         skills\_router.py

&nbsp;         llm\_ollama.py

&nbsp;         response\_shaper.py

&nbsp;         tts\_kokoro.py

&nbsp;         output\_events.py

&nbsp;     utils/

&nbsp;       audio\_io.py

&nbsp;       wav\_utils.py

&nbsp;       text\_math.py

&nbsp;       safety\_filter.py

&nbsp;     data/

&nbsp;       audio/                     # generated wav

&nbsp;       logs/

&nbsp;   requirements.txt

&nbsp;   README.md

&nbsp; scripts/

&nbsp;   run\_all.ps1                    # start Ollama check + start voice service

&nbsp;   health\_check.ps1

```



---



\## 10) Setup steps (Windows)



\### 10.1 Install system dependencies

1\. Install \*\*Ollama\*\* (Windows)

2\. Install \*\*eSpeak NG\*\* (Windows) and ensure it’s on PATH

3\. Install \*\*Python 3.11+\*\*

4\. (Optional) Install Git + Git LFS



\### 10.2 Pull a local LLM in Ollama

Example:

\- `ollama pull qwen2.5:0.5b-instruct`



\### 10.3 Python env

From `voice\_service/`:

\- `python -m venv .venv`

\- `.venv\\Scripts\\activate`

\- `pip install -r requirements.txt`



\### 10.4 Run voice service

\- `uvicorn app.main:app --host 127.0.0.1 --port 8008`



\### 10.5 Run Unity

\- Open `unity/KidsVoiceGame` in Unity

\- Press Play (or build Windows exe)



---



\## 11) requirements.txt (guidance)



At minimum you will likely need:

\- fastapi

\- uvicorn

\- pydantic

\- sounddevice

\- numpy

\- faster-whisper

\- webrtcvad

\- requests (for Ollama)

\- (Kokoro deps) torch/transformers/etc depending on the Kokoro package approach

\- pipecat (core)



Note: exact Kokoro package/deps depend on how you integrate Kokoro (direct HF model load vs a wrapper package).



---



\## 12) Unity implementation notes



\### 12.1 States

\- Idle

\- Listening (button down)

\- Thinking (after stop)

\- Speaking (while audio playing)



\### 12.2 Audio loading (WAV)

Simplest POC:

\- Unity downloads WAV from `/audio/...`

\- Parse WAV header into float samples

\- Create AudioClip, play



\### 12.3 WebSocket handling

Unity listens for events:

\- transcript.final → show caption

\- reply.text → show caption bubble

\- reply.audio\_ready → download audio \& play

\- state → animate character



---



\## 13) POC acceptance criteria (Definition of Done)

\- Press and hold “Talk” → kid speaks → release.

\- Game displays transcript.

\- Game answers with a spoken reply.

\- Math questions return correct numeric answers deterministically.

\- Replies are short (1–2 sentences).

\- Everything runs locally on a Windows CPU machine.



---



\## 14) Next-step upgrades (after POC)

\- Enable barge-in (interrupt TTS when kid speaks)

\- Stream partial STT and partial TTS to reduce latency

\- Improve kid speech accuracy (bigger STT model, noise suppression)

\- Add parental settings (voice, strictness)

\- Add “mini-games” (quiz mode, story mode, animal facts)



