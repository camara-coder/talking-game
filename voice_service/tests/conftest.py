"""
Pytest configuration and shared fixtures for Voice Service tests
"""
import os
import sys
import asyncio
import pytest
import numpy as np
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app
from app.config import settings
from app.api.session_manager import SessionManager, Session
from app.pipeline.voice_pipeline import VoicePipeline


# ============================================================================
# Event Loop Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Test Client Fixtures
# ============================================================================

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Audio Data Fixtures
# ============================================================================

@pytest.fixture
def sample_audio_16khz() -> np.ndarray:
    """Generate sample audio data at 16kHz (1 second)"""
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    return audio


@pytest.fixture
def sample_audio_24khz() -> np.ndarray:
    """Generate sample audio data at 24kHz (1 second)"""
    sample_rate = 24000
    duration = 1.0
    frequency = 440.0  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    return audio


@pytest.fixture
def silence_audio() -> np.ndarray:
    """Generate silent audio (1 second at 16kHz)"""
    sample_rate = 16000
    duration = 1.0

    audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

    return audio


@pytest.fixture
def short_audio() -> np.ndarray:
    """Generate very short audio (100ms at 16kHz)"""
    sample_rate = 16000
    duration = 0.1
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    return audio


# ============================================================================
# Session Fixtures
# ============================================================================

@pytest.fixture
def session_manager() -> SessionManager:
    """Create a fresh session manager for testing"""
    return SessionManager()


@pytest.fixture
def test_session(session_manager: SessionManager) -> Session:
    """Create a test session"""
    session = session_manager.create_session()
    yield session
    session_manager.end_session(session.session_id)


# ============================================================================
# Mock Fixtures for External Services
# ============================================================================

@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for LLM testing"""
    with patch('app.pipeline.processors.llm_ollama.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "This is a test response from the mock LLM.",
            "done": True
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_stt_processor():
    """Mock STT processor for testing"""
    mock = MagicMock()
    mock.transcribe.return_value = "what is five plus five"
    return mock


@pytest.fixture
def mock_tts_processor():
    """Mock TTS processor for testing"""
    mock = MagicMock()
    mock.synthesize.return_value = True
    mock.sample_rate = 24000
    return mock


@pytest.fixture
def mock_vad_processor():
    """Mock VAD processor for testing"""
    mock = MagicMock()
    mock.is_speech.return_value = True
    mock.trim_silence.return_value = np.random.randn(16000).astype(np.float32)
    return mock


# ============================================================================
# Pipeline Fixtures
# ============================================================================

@pytest.fixture
def voice_pipeline():
    """Create a voice pipeline instance for testing"""
    return VoicePipeline()


@pytest.fixture
def mock_voice_pipeline():
    """Create a mock voice pipeline for testing"""
    mock = MagicMock()
    mock.process.return_value = {
        "transcript": "what is five plus five",
        "reply_text": "Five plus five is ten.",
        "route": "math",
        "processing_time_ms": 100
    }
    return mock


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_audio_dir(tmp_path):
    """Create a temporary directory for audio files"""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    return audio_dir


@pytest.fixture
def temp_wav_file(temp_audio_dir, sample_audio_16khz):
    """Create a temporary WAV file"""
    import soundfile as sf

    wav_path = temp_audio_dir / "test.wav"
    sf.write(str(wav_path), sample_audio_16khz, 16000, subtype='PCM_16')

    return wav_path


# ============================================================================
# WebSocket Fixtures
# ============================================================================

@pytest.fixture
async def websocket_client(async_client):
    """Create a WebSocket test client"""
    # This would need a WebSocket testing library
    # For now, return a mock
    mock_ws = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.receive_json = AsyncMock()
    return mock_ws


# ============================================================================
# Settings Fixtures
# ============================================================================

@pytest.fixture
def test_settings():
    """Provide test settings"""
    return settings


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_sessions(session_manager):
    """Cleanup all sessions after each test"""
    yield
    # Clean up all sessions
    for session_id in list(session_manager.sessions.keys()):
        session_manager.end_session(session_id)


# ============================================================================
# Math Router Test Data
# ============================================================================

@pytest.fixture
def math_test_cases():
    """Provide test cases for math router"""
    return [
        # (input_text, expected_result, expected_operator)
        ("what is five plus five", 10, "plus"),
        ("5 + 5", 10, "plus"),
        ("ten minus three", 7, "minus"),
        ("12 divided by 4", 3, "divided"),
        ("6 times 7", 42, "times"),
        ("what is 100 plus 200", 300, "plus"),
        ("fifteen minus eight", 7, "minus"),
    ]


@pytest.fixture
def invalid_math_cases():
    """Provide invalid math test cases"""
    return [
        "what is your name",
        "tell me a story",
        "hello there",
        "5 divided by 0",  # Division by zero
        "one million plus two million",  # Out of range
    ]
