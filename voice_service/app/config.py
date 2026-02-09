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
    # Public URL for production (set via environment variable)
    # Example: https://your-app.up.railway.app
    PUBLIC_URL: str = ""  # If empty, uses http://SERVICE_HOST:SERVICE_PORT

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

    # ElevenLabs TTS (legacy, replaced by Qwen3-TTS)
    ELEVENLABS_VOICE: str = "tapn1QwocNXk3viVSowa"  # Selected voice
    ELEVENLABS_MODEL: str = "eleven_monolingual_v1"  # or eleven_multilingual_v2

    # Qwen3-TTS Configuration (local)
    QWEN_TTS_MODEL_ID: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
    QWEN_TTS_DEVICE: str = "cpu"  # "cpu" or "cuda"
    QWEN_TTS_DTYPE: str = "float32"  # "float32", "float16", "bfloat16"
    QWEN_TTS_ATTN_IMPL: str = ""  # Optional: "flash_attention_2" on compatible GPUs
    QWEN_TTS_LANGUAGE: str = "Auto"
    QWEN_TTS_SPEAKER: str = "Auto"
    QWEN_TTS_INSTRUCTION: str = "Warm, friendly voice for a young child."

    # ElevenLabs STT (Scribe)
    ELEVENLABS_STT_MODEL: str = "scribe_v1"  # ElevenLabs Scribe model

    # Canary-Qwen STT Configuration (NeMo)
    CANARY_QWEN_MODEL_ID: str = "nvidia/canary-qwen-2.5b"
    CANARY_QWEN_DEVICE: str = "auto"  # "auto", "cpu", "cuda"
    CANARY_QWEN_MAX_TOKENS: int = 256
    CANARY_QWEN_TEMPERATURE: float = 0.1
    CANARY_QWEN_TOP_P: float = 0.95
    CANARY_QWEN_PROMPT: str = ""  # Optional override prompt, must include audio locator tag
    CANARY_QWEN_STARTUP_LOAD: bool = True  # Load Canary model at startup for validation

    # VAD Configuration
    VAD_AGGRESSIVENESS: int = 2  # 0-3, higher = more aggressive
    VAD_PADDING_MS: int = 300  # Padding before/after speech
    VAD_MAX_UTTERANCE_SEC: int = 12  # Maximum recording length
    VAD_FRAME_DURATION_MS: int = 30  # Must be 10, 20, or 30

    # Silero VAD Configuration (neural network VAD — replaces webrtcvad)
    SILERO_VAD_THRESHOLD: float = 0.35       # Speech probability threshold (0.0-1.0)
    SILERO_VAD_MIN_SPEECH_MS: int = 250      # Minimum speech duration to keep (ms)
    SILERO_VAD_MIN_SILENCE_MS: int = 150     # Silence duration to split segments (ms)
    SILERO_VAD_SPEECH_PAD_MS: int = 60       # Padding before/after speech (ms)

    # Streaming VAD endpointing
    STREAMING_VAD_ENABLED: bool = True  # Set to False to disable endpointing
    ENDPOINT_CONFIRM_MS: int = 450  # Silence confirmation before triggering (ms)
    ENDPOINT_POST_ROLL_MS: int = 200  # Audio kept after end (ms)

    # Noise Reduction Configuration
    NOISE_REDUCE_PROP_DECREASE: float = 0.6  # Reduction strength (0.0-1.0)

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

    # Database Configuration (PostgreSQL)
    DATABASE_URL: str = ""  # Set via environment variable (e.g., postgresql+asyncpg://user:pass@host:5432/dbname)
    ENABLE_DB_PERSISTENCE: bool = False  # Feature flag to enable/disable database persistence
    DB_POOL_SIZE: int = 10  # Number of connections to maintain in the pool
    DB_MAX_OVERFLOW: int = 20  # Maximum overflow connections beyond pool_size
    DB_ECHO: bool = False  # SQLAlchemy query logging for debugging

    # Data Retention Policy
    DATA_RETENTION_DAYS: int = 30  # Delete sessions and audio older than this
    CLEANUP_INTERVAL_HOURS: int = 24  # Run cleanup task every N hours

    @property
    def database_url_async(self) -> str:
        """Get DATABASE_URL with async driver for SQLAlchemy async operations

        Railway provides DATABASE_URL as postgresql:// which defaults to psycopg2 (sync).
        We need postgresql+asyncpg:// for async operations.
        """
        if not self.DATABASE_URL:
            return ""

        # Convert standard postgresql:// to async asyncpg driver
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
        else:
            # Already has driver specified or is empty
            return self.DATABASE_URL

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
