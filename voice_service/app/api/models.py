"""
Data models for API requests, responses, and session management
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# Enums
class SessionStatus(str, Enum):
    """Session status states"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class EventType(str, Enum):
    """WebSocket event types"""
    STATE = "state"
    TRANSCRIPT_PARTIAL = "transcript.partial"
    TRANSCRIPT_FINAL = "transcript.final"
    REPLY_TEXT = "reply.text"
    REPLY_AUDIO_READY = "reply.audio_ready"
    ERROR = "error"


# Request Models
class SessionStartRequest(BaseModel):
    """Request to start a new session"""
    session_id: Optional[str] = None
    language: str = "en"
    mode: str = "ptt"  # push-to-talk


class SessionStopRequest(BaseModel):
    """Request to stop current session"""
    session_id: str
    return_audio: bool = True


# Response Models
class SessionStartResponse(BaseModel):
    """Response from session start"""
    session_id: str
    status: SessionStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionStopResponse(BaseModel):
    """Response from session stop"""
    session_id: str
    status: SessionStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# WebSocket Event Models
class EventPayload(BaseModel):
    """Base payload for events"""
    pass


class StatePayload(EventPayload):
    """State change event payload"""
    state: SessionStatus


class TranscriptPayload(EventPayload):
    """Transcript event payload"""
    text: str


class ReplyTextPayload(EventPayload):
    """Reply text event payload"""
    text: str


class AudioReadyPayload(EventPayload):
    """Audio ready event payload"""
    url: str
    duration_ms: int
    format: str = "wav"
    sample_rate_hz: int = 24000
    channels: int = 1


class ErrorPayload(EventPayload):
    """Error event payload"""
    code: str
    message: str


class WebSocketEvent(BaseModel):
    """WebSocket event envelope"""
    type: EventType
    session_id: str
    turn_id: Optional[str] = None
    ts: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any]


# Session State Models
class Turn(BaseModel):
    """Represents a single conversation turn"""
    turn_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    transcript: Optional[str] = None
    reply_text: Optional[str] = None
    audio_path: Optional[str] = None
    processing_time_ms: Optional[int] = None

    @classmethod
    def from_db(cls, db_turn: "DBTurn") -> "Turn":
        """Convert database model to Pydantic model

        Args:
            db_turn: DBTurn ORM model from database

        Returns:
            Turn Pydantic model
        """
        return cls(
            turn_id=db_turn.turn_id,
            timestamp=db_turn.timestamp,
            transcript=db_turn.transcript,
            reply_text=db_turn.reply_text,
            audio_path=db_turn.audio_path,
            processing_time_ms=db_turn.processing_time_ms
        )

    def to_db(self) -> "DBTurn":
        """Convert to database model

        Returns:
            DBTurn ORM model for database persistence
        """
        from app.db.models import DBTurn
        return DBTurn(
            turn_id=self.turn_id,
            timestamp=self.timestamp,
            transcript=self.transcript,
            reply_text=self.reply_text,
            audio_path=self.audio_path,
            processing_time_ms=self.processing_time_ms
        )


class Session(BaseModel):
    """Represents a conversation session"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: SessionStatus = SessionStatus.IDLE
    language: str = "en"
    mode: str = "ptt"

    # Audio buffer for current turn
    audio_buffer: bytes = b""

    # Conversation history
    turns: List[Turn] = []

    # Current turn being processed
    current_turn: Optional[Turn] = None

    def start_turn(self) -> Turn:
        """Start a new turn"""
        turn = Turn()
        self.current_turn = turn
        self.status = SessionStatus.LISTENING
        self.updated_at = datetime.utcnow()
        return turn

    def complete_turn(self) -> None:
        """Complete current turn and add to history"""
        if self.current_turn:
            self.turns.append(self.current_turn)
            self.current_turn = None
        self.status = SessionStatus.IDLE
        self.updated_at = datetime.utcnow()

    def get_context(self, num_turns: int = 4) -> List[Dict[str, str]]:
        """Get conversation context for LLM"""
        context = []
        for turn in self.turns[-num_turns:]:
            if turn.transcript and turn.reply_text:
                context.append({
                    "user": turn.transcript,
                    "assistant": turn.reply_text
                })
        return context

    @classmethod
    def from_db(cls, db_session: "DBSession", turns: Optional[List["DBTurn"]] = None) -> "Session":
        """Convert database model to Pydantic model

        Args:
            db_session: DBSession ORM model from database
            turns: Optional list of DBTurn models to include

        Returns:
            Session Pydantic model with turns loaded
        """
        session = cls(
            session_id=db_session.session_id,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            status=db_session.status,
            language=db_session.language,
            mode=db_session.mode
        )
        if turns:
            session.turns = [Turn.from_db(t) for t in turns]
        return session

    def to_db(self) -> "DBSession":
        """Convert to database model

        Returns:
            DBSession ORM model for database persistence
        """
        from app.db.models import DBSession
        return DBSession(
            session_id=self.session_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            status=self.status,
            language=self.language,
            mode=self.mode,
            total_turns=len(self.turns),
            last_activity_at=self.updated_at
        )
