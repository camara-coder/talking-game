# Voice Conversational Kids Game (5+) - Web Version Setup Guide

**React + PixiJS + Python Voice Service + Ollama (LLM) + faster-whisper (STT) + Kokoro (TTS)**

## Overview

This is a **Windows PC proof-of-concept** voice-interactive game for children 5+. The game uses a **web-based frontend** (React + PixiJS) instead of Unity, communicating with a local Python backend for voice processing.

### What's Changed from Unity Version

- **Frontend**: Web application (React + TypeScript + PixiJS) instead of Unity C#
- **Deployment**: Runs in any modern web browser
- **Same Backend**: Python Voice Service remains unchanged
- **Easier Development**: Hot-reload, web debugging tools, cross-platform

---

## Architecture

```
┌─────────────────────────┐
│   Web Browser           │
│   (React + PixiJS)      │  ← UI, 2D Character, Push-to-Talk, Audio
│   http://localhost:5173 │
└───────────┬─────────────┘
            │ HTTP + WebSocket (localhost)
            ↓
┌─────────────────────────┐
│  Voice Service          │
│  (Python/FastAPI)       │  ← Pipecat Pipeline, STT, TTS, Math Router
│  http://127.0.0.1:8008  │
└───────────┬─────────────┘
            │ HTTP (localhost)
            ↓
┌─────────────────────────┐
│  Ollama LLM             │
│  http://127.0.0.1:11434 │  ← Local Language Model
└─────────────────────────┘
```

---

## Tech Stack

### Web Frontend
- **React 18** with TypeScript
- **Vite** (build tool, dev server)
- **PixiJS** (2D WebGL rendering for character)
- **Web Audio API** (audio playback)
- **Native WebSocket API** (real-time events)

### Python Backend (Unchanged)
- **Python 3.11+**
- **FastAPI** + Uvicorn
- **Pipecat** (pipeline orchestration)
- **faster-whisper** (STT)
- **Kokoro** (TTS, requires eSpeak NG)
- **Ollama client** (LLM)

### System Dependencies
- **Node.js 18+** and npm
- **Ollama** (Windows installer)
- **eSpeak NG** (Windows installer)
- **Python 3.11+**

---

## Quick Start

### 1. Install System Dependencies

#### Install Ollama
1. Download from: https://ollama.com/download
2. Install and start service
3. Pull the model:
   ```bash
   ollama pull qwen2.5:0.5b-instruct
   ```

#### Install eSpeak NG
1. Download from: https://github.com/espeak-ng/espeak-ng/releases
2. Install to default location (`C:\Program Files\eSpeak NG\`)
3. Verify installation:
   ```bash
   espeak-ng --version
   ```

#### Install Node.js
1. Download from: https://nodejs.org/ (LTS version)
2. Install with defaults
3. Verify:
   ```bash
   node --version
   npm --version
   ```

### 2. Setup Python Backend

```powershell
cd voice_service
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Setup Web Frontend

```powershell
cd web-client
npm install
```

### 4. Start Everything

Use the provided PowerShell script:

```powershell
.\scripts\start-web-game.ps1
```

This will:
- Check Ollama is running
- Start the Python Voice Service on port 8008
- Start the React frontend on port 5173
- Open your browser to http://localhost:5173

**Alternatively**, start services manually:

**Terminal 1 - Voice Service:**
```powershell
cd voice_service
.\.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8008
```

**Terminal 2 - Web Frontend:**
```powershell
cd web-client
npm run dev
```

Then open http://localhost:5173 in your browser.

---

## How to Use

1. **Wait for "Connected" status** in the top-right corner (green dot)
2. **Hold the talk button** (circular button in the center)
3. **Speak your question** or message
4. **Release the button** to send
5. **Watch the character** animate and **listen to the response**

### Try These Examples:
- "What is 5 plus 5?"
- "What is 12 minus 7?"
- "What is a cat?"
- "Tell me about dogs"

---

## Project Structure

```
voice-game/
├── web-client/                    # React frontend
│   ├── src/
│   │   ├── components/            # React UI components
│   │   │   ├── CharacterCanvas.tsx
│   │   │   ├── PushToTalkButton.tsx
│   │   │   └── CaptionDisplay.tsx
│   │   ├── services/              # API clients
│   │   │   ├── api.ts             # HTTP client
│   │   │   └── websocket.ts       # WebSocket client
│   │   ├── lib/                   # Core libraries
│   │   │   ├── character.ts       # PixiJS character
│   │   │   └── audio.ts           # Audio playback
│   │   ├── hooks/                 # React hooks
│   │   │   └── useVoiceService.ts
│   │   ├── types/                 # TypeScript types
│   │   │   └── index.ts
│   │   ├── App.tsx                # Main app
│   │   └── main.tsx               # Entry point
│   ├── package.json
│   └── vite.config.ts
│
├── voice_service/                 # Python backend (unchanged)
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   ├── pipeline/
│   │   └── utils/
│   └── requirements.txt
│
└── scripts/
    ├── start-web-game.ps1         # Start all services
    └── check-health.ps1           # Health check
```

---

## Features

### Frontend Features
- **Animated 2D Character** (PixiJS Canvas)
  - Idle: Gentle breathing animation
  - Listening: Attentive eyes, slight bounce
  - Thinking: Thoughtful expression
  - Speaking: Animated mouth movement

- **Push-to-Talk Interface**
  - Hold button to record
  - Visual feedback (color changes, scaling)
  - Disabled during processing

- **Live Captions**
  - Transcript of what you said
  - Character's reply text
  - Smooth fade-in animations

- **Connection Status**
  - Real-time indicator
  - Auto-reconnect on disconnect

### Backend Features (Unchanged)
- **Deterministic Math Router** - Math questions get correct answers every time
- **Kid-Mode LLM** - Short, simple, safe responses
- **Voice Activity Detection** - Automatically trims silence
- **Safety Filter** - Blocks inappropriate content

---

## API Endpoints

### HTTP REST API

**POST /session/start**
- Start a new voice session
- Returns: `{ session_id, status }`

**POST /session/stop**
- Stop session and process audio
- Request: `{ session_id, return_audio }`
- Returns: `{ session_id, status }`

**GET /audio/{session_id}/{turn_id}.wav**
- Download synthesized speech audio

**GET /health**
- Health check endpoint

### WebSocket

**WS /ws?session_id={id}**
- Real-time event stream
- Events:
  - `state` - Game state changes
  - `transcript.final` - Speech-to-text result
  - `reply.text` - Character's text response
  - `reply.audio_ready` - Audio file ready to play
  - `error` - Error messages

---

## Port Configuration

| Service | URL | Purpose |
|---------|-----|---------|
| Web Frontend | http://localhost:5173 | React app (Vite dev server) |
| Voice Service | http://127.0.0.1:8008 | Python FastAPI backend |
| Ollama | http://127.0.0.1:11434 | LLM inference |

---

## Development

### Frontend Development

**Run dev server with hot reload:**
```bash
cd web-client
npm run dev
```

**Build for production:**
```bash
npm run build
```

**Preview production build:**
```bash
npm run preview
```

### Backend Development

**Run with auto-reload:**
```bash
cd voice_service
uvicorn app.main:app --host 127.0.0.1 --port 8008 --reload
```

---

## Troubleshooting

### "Disconnected" Status

**Problem**: Red status indicator, can't connect to backend

**Solutions**:
1. Check Voice Service is running: http://127.0.0.1:8008/health
2. Check Ollama is running: http://127.0.0.1:11434
3. Check browser console for errors (F12)
4. Restart services using `start-web-game.ps1`

### No Audio Playback

**Problem**: Character responds but no sound

**Solutions**:
1. Check browser audio permissions
2. Check system volume/mute
3. Check browser console for audio errors
4. Try clicking page first (browser autoplay policy)

### Character Not Animating

**Problem**: Character appears but doesn't animate

**Solutions**:
1. Check browser console for PixiJS errors
2. Ensure WebGL is supported (try another browser)
3. Update graphics drivers
4. Try Ctrl+F5 to hard refresh

### Math Answers Wrong

**Problem**: "5 plus 5" doesn't return "10"

**Solutions**:
1. Check Python logs for math router activity
2. Verify backend is processing correctly
3. Check transcript text matches expected format

---

## Health Check

Run the health check script to verify all services:

```powershell
.\scripts\check-health.ps1
```

This checks:
- ✓ Ollama is running
- ✓ Voice Service is accessible
- ✓ Web Frontend is serving
- ✓ eSpeak NG is installed

---

## Performance

Expected performance on modern Windows PC:

- **Startup Time**: ~10 seconds
- **Response Latency**: 3-5 seconds per turn
  - STT: < 2 seconds
  - LLM: < 2 seconds
  - TTS: < 1 second
- **CPU Usage**: 30-50% during processing
- **Memory**: ~1 GB total

---

## Browser Compatibility

**Recommended**: Chrome 90+, Edge 90+, Firefox 88+

**Requirements**:
- WebGL support (for PixiJS)
- Web Audio API
- WebSocket
- ES2020+ JavaScript

---

## Next Steps

After the POC is working, consider:

1. **Improved Character Design**
   - Add character sprites/artwork
   - More animation states
   - Particle effects

2. **Enhanced UX**
   - Background music
   - Sound effects
   - Multiple characters to choose from

3. **Additional Features**
   - Conversation history
   - Save/load sessions
   - Mini-games (quiz mode, stories)

4. **Performance**
   - Stream TTS audio
   - Parallel processing
   - Model optimization

5. **Deployment**
   - Build standalone desktop app (Electron)
   - Docker containers
   - Mobile PWA version

---

## Differences from Unity Version

| Aspect | Unity | Web |
|--------|-------|-----|
| Language | C# | TypeScript |
| Rendering | Unity Engine | PixiJS (WebGL) |
| Build Size | ~100-200 MB | ~2-5 MB |
| Deployment | Windows .exe | Browser |
| Dev Reload | Slow | Instant (HMR) |
| Debugging | Visual Studio | Browser DevTools |
| Cross-platform | Windows only (POC) | Any OS with browser |
| Distribution | Executable | URL or PWA |

---

## Support

For issues or questions:
1. Check this guide
2. Run `check-health.ps1`
3. Check browser console (F12)
4. Check Python logs in terminal

---

**Enjoy building with voice AI!** 🎮🗣️
