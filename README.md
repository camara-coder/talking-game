# 🎮 Voice Conversational Kids Game (5+)

A local, privacy-first voice AI game for children that runs entirely on your Windows PC with **no cloud dependencies**.

## 🌟 Quick Start

### Prerequisites
- Windows 10/11
- Node.js 18+ ([download](https://nodejs.org/))
- Python 3.11+ ([download](https://www.python.org/))
- Ollama ([download](https://ollama.com/download))
- eSpeak NG ([download](https://github.com/espeak-ng/espeak-ng/releases))

### Installation

1. **Clone/Download this repository**

2. **Install Ollama and pull the model:**
   ```bash
   ollama pull qwen2.5:0.5b-instruct
   ```

3. **Install eSpeak NG** (use default installation path)

4. **Setup Python backend:**
   ```powershell
   cd voice_service
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

5. **Setup Web frontend:**
   ```powershell
   cd web-client
   npm install
   ```

### Run the Game

**Easy way** - Use the startup script:
```powershell
.\scripts\start-web-game.ps1
```

The game will open automatically in your browser at http://localhost:5173

**Manual way** - Start services in separate terminals:
```powershell
# Terminal 1 - Backend
cd voice_service
.\.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8008

# Terminal 2 - Frontend
cd web-client
npm run dev
```

## 🎯 How to Play

1. Wait for the **green "Connected"** indicator
2. **Hold** the circular button
3. **Speak** your question (e.g., "What is 5 plus 5?")
4. **Release** the button
5. Watch the character respond!

### Try These:
- Math: "What is 7 times 8?"
- Questions: "What is a dog?"
- Conversation: "Tell me about space"

## 🏗️ Architecture

This project uses a **web-based frontend** communicating with a **local Python backend**:

```
Browser (React + PixiJS)
    ↓ HTTP + WebSocket
Python Voice Service (FastAPI)
    ↓ HTTP
Ollama LLM (Local AI)
```

### Key Features

✅ **100% Local** - No cloud, no internet needed (after setup)
✅ **Kid-Safe** - Built-in content filtering and simple language
✅ **Math Accuracy** - Deterministic math router for correct answers
✅ **Animated Character** - PixiJS 2D character with state animations
✅ **Real-time** - WebSocket for instant feedback
✅ **Privacy-First** - All data stays on your machine

## 📁 Project Structure

```
voice-game/
├── web-client/          # React + TypeScript frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── services/    # API clients
│   │   ├── lib/         # PixiJS character, audio
│   │   └── hooks/       # React hooks
│   └── package.json
│
├── voice_service/       # Python FastAPI backend
│   ├── app/
│   │   ├── api/         # REST & WebSocket
│   │   ├── pipeline/    # Pipecat processors
│   │   └── utils/       # Helper functions
│   └── requirements.txt
│
├── scripts/
│   ├── start-web-game.ps1    # Start everything
│   └── check-health.ps1      # Health check
│
├── WEB_SETUP_GUIDE.md        # Detailed setup guide
└── README.md                 # This file
```

## 🛠️ Technology Stack

### Frontend
- **React 18** + TypeScript
- **Vite** - Fast build tool
- **PixiJS** - 2D WebGL rendering
- **Web Audio API** - Audio playback

### Backend
- **Python 3.11+**
- **FastAPI** - Modern async web framework
- **Pipecat** - Voice AI pipeline orchestration
- **faster-whisper** - Speech-to-text (STT)
- **Kokoro-82M** - Text-to-speech (TTS)
- **Ollama** - Local LLM inference

## 📚 Documentation

- **[WEB_SETUP_GUIDE.md](WEB_SETUP_GUIDE.md)** - Complete setup instructions
- **[CLAUDE.md](CLAUDE.md)** - Original technical spec (Unity version)
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Implementation details

## 🔧 Troubleshooting

### Health Check
Run the health check script:
```powershell
.\scripts\check-health.ps1
```

### Common Issues

**"Disconnected" status:**
- Ensure Voice Service is running on port 8008
- Check Ollama is running: http://127.0.0.1:11434

**No audio:**
- Check browser audio permissions
- Verify eSpeak NG is installed
- Click the page first (browser autoplay policy)

**Slow responses:**
- Normal on CPU-only systems (3-5 seconds)
- Consider smaller models if too slow

See [WEB_SETUP_GUIDE.md](WEB_SETUP_GUIDE.md) for more troubleshooting.

## 🚀 Development

### Frontend Development
```bash
cd web-client
npm run dev          # Start dev server with hot reload
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend Development
```bash
cd voice_service
.\.venv\Scripts\activate
uvicorn app.main:app --reload    # Auto-reload on changes
```

## 📊 Performance

Expected on modern Windows PC:
- **Startup**: ~10 seconds
- **Response latency**: 3-5 seconds
- **CPU usage**: 30-50% during processing
- **Memory**: ~1 GB total

## 🔐 Privacy & Safety

- **100% Local** - All processing on your machine
- **No telemetry** - No data sent anywhere
- **Kid-safe prompts** - Built-in content filtering
- **Open source** - Review all code

## 🎨 Customization

The character, colors, and behavior can be customized:
- **Character animations**: `web-client/src/lib/character.ts`
- **UI colors**: `web-client/src/App.css`
- **LLM prompts**: `voice_service/app/pipeline/processors/`

## 📝 License

[Specify your license here]

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.com/) - Local LLM inference
- [Pipecat](https://github.com/pipecat-ai/pipecat) - Voice AI pipeline
- [PixiJS](https://pixijs.com/) - WebGL rendering
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Vite](https://vitejs.dev/) - Next generation frontend tooling

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📬 Support

For issues or questions:
1. Check [WEB_SETUP_GUIDE.md](WEB_SETUP_GUIDE.md)
2. Run the health check script
3. Open an issue on GitHub

---

**Made with ❤️ for curious kids and their families**
