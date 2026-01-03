"""
Configuration module for Voice Agent Service
Centralizes all application settings and parameters
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Service Configuration
    SERVICE_HOST: str = "127.0.0.1"
    SERVICE_PORT: int = 8008
    SERVICE_NAME: str = "Voice Agent Service"

    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:0.5b-instruct"
    OLLAMA_TIMEOUT: int = 30  # seconds

    # Audio Configuration
    AUDIO_SAMPLE_RATE: int = 16000  # Hz for STT
    AUDIO_CHANNELS: int = 1  # Mono
    AUDIO_CHUNK_DURATION_MS: int = 30  # For VAD
    AUDIO_FORMAT: str = "float32"

    # TTS Audio Configuration
    TTS_SAMPLE_RATE: int = 24000  # Hz for output
    TTS_CHANNELS: int = 1  # Mono

    # ElevenLabs Configuration
    ELEVENLABS_API_KEY: str = ""  # Set via environment variable

    # ElevenLabs TTS
    ELEVENLABS_VOICE: str = "tapn1QwocNXk3viVSowa"  # Selected voice
    ELEVENLABS_MODEL: str = "eleven_monolingual_v1"  # or eleven_multilingual_v2

    # ElevenLabs STT (Scribe)
    ELEVENLABS_STT_MODEL: str = "scribe_v1"  # ElevenLabs Scribe model

    # VAD Configuration
    VAD_AGGRESSIVENESS: int = 2  # 0-3, higher = more aggressive
    VAD_PADDING_MS: int = 300  # Padding before/after speech
    VAD_MAX_UTTERANCE_SEC: int = 12  # Maximum recording length
    VAD_FRAME_DURATION_MS: int = 30  # Must be 10, 20, or 30

    # STT Configuration
    STT_MODEL_SIZE: str = "base.en"  # or "small.en" for better accuracy
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"  # CPU-friendly
    STT_BEAM_SIZE: int = 5
    STT_LANGUAGE: str = "en"

    # OpenAI Configuration (for Whisper STT)
    OPENAI_API_KEY: str = ""  # Set via environment variable
    OPENAI_WHISPER_MODEL: str = "whisper-1"  # OpenAI Whisper model

    # LLM Configuration
    LLM_TEMPERATURE: float = 0.7
    LLM_TOP_P: float = 0.9
    LLM_MAX_TOKENS: int = 100
    LLM_CONTEXT_TURNS: int = 4  # Number of previous turns to keep

    # Response Shaping Configuration
    MAX_RESPONSE_SENTENCES: int = 2
    MAX_RESPONSE_WORDS: int = 35

    # Kid-Mode System Prompt
    SYSTEM_PROMPT: str = (
        "You are a friendly game character talking to a child age 5+. "
        "Use simple words and short sentences. "
        "Answer in 1 or 2 sentences. "
        "If the child asks for something unsafe or grown-up, say you can't help and offer a safe topic. "
        "If you don't understand, ask one short question."
    )

    # Safety Filter Keywords (basic list - expand as needed)
    UNSAFE_KEYWORDS: list = [
        "kill", "hurt", "weapon", "gun", "knife",
        "suicide", "die", "death",
        "drug", "alcohol", "smoke",
        "sex", "naked"
    ]

    SAFE_FALLBACK_RESPONSE: str = (
        "I can't help with that. Let's talk about something safe, like animals or math."
    )

    # File Storage
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    AUDIO_DIR: str = os.path.join(DATA_DIR, "audio")
    LOGS_DIR: str = os.path.join(DATA_DIR, "logs")

    # Session Configuration
    SESSION_TIMEOUT_SECONDS: int = 300  # 5 minutes
    MAX_CONCURRENT_SESSIONS: int = 10

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # CORS Configuration (for Web Frontend)
    # Can be overridden via CORS_ORIGINS environment variable (comma-separated)
    CORS_ORIGINS: str = ""  # Will be parsed below

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from environment or use defaults"""
        if self.CORS_ORIGINS:
            # Parse from environment variable (comma-separated)
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        else:
            # Default origins for local development
            # Note: FastAPI CORSMiddleware doesn't support port wildcards
            # so we must list each port explicitly
            return [
                "http://localhost",
                "http://127.0.0.1",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
                "http://localhost:5175",
                "http://127.0.0.1:5175",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ]

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


# Ensure data directories exist
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
os.makedirs(settings.LOGS_DIR, exist_ok=True)
