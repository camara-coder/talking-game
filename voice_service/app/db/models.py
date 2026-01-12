"""SQLAlchemy ORM models for database tables"""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base


class DBSession(Base):
    """Database model for conversation sessions"""
    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False)
    language = Column(String(10), nullable=False)
    mode = Column(String(20), nullable=False)
    total_turns = Column(Integer, default=0)
    last_activity_at = Column(DateTime, nullable=False)

    # Relationship to turns
    turns = relationship("DBTurn", back_populates="session", cascade="all, delete-orphan")

    # Index for cleanup queries
    __table_args__ = (
        Index('idx_sessions_last_activity', 'last_activity_at'),
    )


class DBTurn(Base):
    """Database model for conversation turns"""
    __tablename__ = "turns"

    turn_id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    transcript = Column(Text, nullable=True)
    reply_text = Column(Text, nullable=True)
    audio_path = Column(String(500), nullable=True)
    audio_duration_ms = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    route = Column(String(50), nullable=True)

    # Relationship to session
    session = relationship("DBSession", back_populates="turns")

    # Indexes for queries
    __table_args__ = (
        Index('idx_turns_session_id', 'session_id'),
        Index('idx_turns_timestamp', 'timestamp'),
    )
