"""
WebSocket manager and endpoints for real-time event streaming and audio upload
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set, Optional
import logging
import json
import asyncio
from io import BytesIO

from app.api.models import WebSocketEvent, EventType, SessionStatus
from app.config import settings
from app.api.session_manager import session_manager
from app.pipeline.streaming_vad import (
    StreamingVADState,
    create_streaming_vad_state,
    process_chunk as vad_process_chunk,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class AudioBuffer:
    """Buffer for accumulating audio chunks from client"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.chunks: list[bytes] = []
        self.config: dict = {}
        self.total_bytes = 0

    def add_chunk(self, chunk: bytes):
        """Add an audio chunk to the buffer"""
        self.chunks.append(chunk)
        self.total_bytes += len(chunk)
        logger.debug(f"Added audio chunk: {len(chunk)} bytes (total: {self.total_bytes})")

    def get_audio_data(self) -> bytes:
        """Get all buffered audio as bytes"""
        return b''.join(self.chunks)

    def get_audio_data_up_to_samples(self, max_samples: int) -> bytes:
        """Get buffered audio up to max_samples (PCM16 => 2 bytes per sample)."""
        if max_samples <= 0:
            return b""
        max_bytes = max_samples * 2
        data = self.get_audio_data()
        if len(data) <= max_bytes:
            return data
        return data[:max_bytes]

    def clear(self):
        """Clear the buffer"""
        self.chunks.clear()
        self.total_bytes = 0
        logger.debug("Audio buffer cleared")


class ConnectionManager:
    """Manages WebSocket connections, event broadcasting, and audio streaming"""

    def __init__(self):
        # Map of session_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of session_id -> AudioBuffer for accumulating audio chunks
        self.audio_buffers: Dict[str, AudioBuffer] = {}
        # Map of session_id -> StreamingVADState for endpointing
        self.streaming_vad_states: Dict[str, StreamingVADState] = {}
        # Guard to ensure pipeline runs once per turn
        self.processing_started: Dict[str, bool] = {}
        # Pending endpoint confirmation tasks
        self.endpoint_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()

        async with self._lock:
            if session_id not in self.active_connections:
                self.active_connections[session_id] = set()
            self.active_connections[session_id].add(websocket)

        logger.info(
            f"WebSocket connected for session {session_id}. "
            f"Total connections for session: {len(self.active_connections[session_id])}"
        )

    async def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection"""
        async with self._lock:
            if session_id in self.active_connections:
                self.active_connections[session_id].discard(websocket)
                if not self.active_connections[session_id]:
                    # No more connections for this session
                    del self.active_connections[session_id]

            # Clean up audio buffer
            if session_id in self.audio_buffers:
                del self.audio_buffers[session_id]
            # Clean up streaming VAD state
            if session_id in self.streaming_vad_states:
                del self.streaming_vad_states[session_id]
            if session_id in self.processing_started:
                del self.processing_started[session_id]
            if session_id in self.endpoint_tasks:
                self.endpoint_tasks[session_id].cancel()
                del self.endpoint_tasks[session_id]

        logger.info(f"WebSocket disconnected for session {session_id}")

    async def handle_audio_start(self, session_id: str, config: dict):
        """Handle audio.start message - creates a new turn and starts buffering audio"""
        logger.info(f"Audio streaming started for session {session_id}: {config}")

        # Look up session and start a new turn
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session not found for audio.start: {session_id}")
            await self.broadcast_error(
                session_id,
                "SESSION_NOT_FOUND",
                f"Session {session_id} not found. Please start a new session."
            )
            return

        # Start a new turn if one isn't already in progress
        if session.current_turn is None:
            session.start_turn()
            logger.info(f"New turn started for session {session_id}: {session.current_turn.turn_id}")

        async with self._lock:
            # Create new audio buffer
            self.audio_buffers[session_id] = AudioBuffer(session_id)
            self.audio_buffers[session_id].config = config
            self.processing_started[session_id] = False
            if settings.STREAMING_VAD_ENABLED:
                try:
                    self.streaming_vad_states[session_id] = create_streaming_vad_state(session_id)
                    logger.info(f"Streaming VAD initialized for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to init streaming VAD (will use batch): {e}")

        # Broadcast listening state
        await self.broadcast_state(session_id, SessionStatus.LISTENING)

    async def handle_audio_chunk(self, session_id: str, chunk: bytes):
        """Handle binary audio chunk"""
        async with self._lock:
            if self.processing_started.get(session_id):
                # Ignore late chunks after processing has started
                return
            if session_id not in self.audio_buffers:
                logger.warning(f"Received audio chunk for session {session_id} without audio.start")
                # Create buffer if not exists
                self.audio_buffers[session_id] = AudioBuffer(session_id)

            self.audio_buffers[session_id].add_chunk(chunk)
        # Run streaming endpointing outside the lock
        if settings.STREAMING_VAD_ENABLED:
            vad_state = self.streaming_vad_states.get(session_id)
            if vad_state:
                result = vad_process_chunk(vad_state, chunk)
                if result.get("speech_resumed"):
                    await self._cancel_endpoint_task(session_id)
                if result.get("end_detected"):
                    await self._schedule_endpoint_trigger(session_id)

    async def handle_audio_end(self, session_id: str):
        """Handle audio.end message and trigger processing"""
        logger.info(f"Audio streaming ended for session {session_id}")
        await self._trigger_processing_once(session_id, source="audio_end")

    async def _process_audio(self, session_id: str, audio_data: bytes, audio_config: dict = None):
        """Process received audio through the pipeline"""
        try:
            # Import here to avoid circular dependency
            from app.pipeline.pipeline_runner import process_audio_stream

            # Pass client-reported sample rate so the backend can resample if
            # the browser's AudioContext used a different rate than 16kHz
            # (common on Android Chrome which may use 44100 or 48000).
            client_sample_rate = None
            if audio_config:
                client_sample_rate = audio_config.get("sample_rate")

            # Process the audio
            await process_audio_stream(session_id, audio_data, sample_rate=client_sample_rate)

        except Exception as e:
            logger.error(f"Error processing audio for session {session_id}: {e}", exc_info=True)
            await self.broadcast_error(
                session_id,
                "PROCESSING_ERROR",
                f"Failed to process audio: {str(e)}"
            )
            await self.broadcast_state(session_id, SessionStatus.IDLE)

        finally:
            # Clean up audio buffer
            async with self._lock:
                if session_id in self.audio_buffers:
                    del self.audio_buffers[session_id]
                if session_id in self.processing_started:
                    del self.processing_started[session_id]

    async def _trigger_processing_once(
        self,
        session_id: str,
        source: str,
        audio_override: Optional[bytes] = None,
        audio_config_override: Optional[dict] = None,
    ):
        async with self._lock:
            if self.processing_started.get(session_id):
                logger.info(f"Processing already started for {session_id} (source={source})")
                return
            self.processing_started[session_id] = True

            audio_data = audio_override
            audio_config = audio_config_override
            if audio_data is None or audio_config is None:
                if session_id in self.audio_buffers:
                    if audio_data is None:
                        audio_data = self.audio_buffers[session_id].get_audio_data()
                    if audio_config is None:
                        audio_config = self.audio_buffers[session_id].config
                    logger.info(
                        f"Triggering processing from {source}, bytes={len(audio_data)}, config={audio_config}"
                    )
                else:
                    logger.warning(f"No audio buffer for session {session_id}")

            if session_id in self.streaming_vad_states:
                del self.streaming_vad_states[session_id]
            if session_id in self.endpoint_tasks:
                self.endpoint_tasks[session_id].cancel()
                del self.endpoint_tasks[session_id]

        await self.broadcast_state(session_id, SessionStatus.PROCESSING)

        if audio_data:
            asyncio.create_task(self._process_audio(session_id, audio_data, audio_config))
        else:
            await self.broadcast_error(
                session_id,
                "NO_AUDIO",
                "No audio data received"
            )
            await self.broadcast_state(session_id, SessionStatus.IDLE)

    async def _cancel_endpoint_task(self, session_id: str):
        task = self.endpoint_tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"Cancelled pending endpoint trigger for session {session_id}")
        if session_id in self.endpoint_tasks:
            del self.endpoint_tasks[session_id]

    async def _schedule_endpoint_trigger(self, session_id: str):
        if session_id in self.endpoint_tasks and not self.endpoint_tasks[session_id].done():
            return

        async def _endpoint_wait_and_trigger():
            try:
                await asyncio.sleep(settings.ENDPOINT_CONFIRM_MS / 1000.0)
                async with self._lock:
                    if self.processing_started.get(session_id):
                        return
                    vad_state = self.streaming_vad_states.get(session_id)
                    if not vad_state or not vad_state.pending_endpoint:
                        return
                    end_sample = vad_state.last_end_sample or 0
                    post_roll_samples = int(
                        settings.AUDIO_SAMPLE_RATE * (settings.ENDPOINT_POST_ROLL_MS / 1000.0)
                    )
                    max_samples = end_sample + post_roll_samples
                    audio_override = None
                    audio_config = None
                    if session_id in self.audio_buffers:
                        audio_override = self.audio_buffers[session_id].get_audio_data_up_to_samples(
                            max_samples
                        )
                        audio_config = self.audio_buffers[session_id].config
                await self._trigger_processing_once(
                    session_id,
                    source="vad_end_confirmed",
                    audio_override=audio_override,
                    audio_config_override=audio_config,
                )
            except asyncio.CancelledError:
                return

        self.endpoint_tasks[session_id] = asyncio.create_task(_endpoint_wait_and_trigger())

    async def send_event(self, session_id: str, event: WebSocketEvent):
        """Send event to all connections for a session"""
        if session_id not in self.active_connections:
            logger.warning(f"No active connections for session {session_id}")
            return

        # Convert event to JSON
        event_json = event.model_dump_json()

        # Send to all connections
        disconnected = []
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_text(event_json)
            except Exception as e:
                logger.error(f"Error sending event: {e}")
                disconnected.append(connection)

        # Cleanup disconnected connections
        if disconnected:
            async with self._lock:
                for connection in disconnected:
                    self.active_connections[session_id].discard(connection)

    async def broadcast_state(self, session_id: str, state: SessionStatus, turn_id: str = None):
        """Helper to broadcast state change event"""
        event = WebSocketEvent(
            type=EventType.STATE,
            session_id=session_id,
            turn_id=turn_id,
            payload={"state": state}
        )
        await self.send_event(session_id, event)

    async def broadcast_transcript(self, session_id: str, text: str, turn_id: str, partial: bool = False):
        """Helper to broadcast transcript event"""
        event = WebSocketEvent(
            type=EventType.TRANSCRIPT_PARTIAL if partial else EventType.TRANSCRIPT_FINAL,
            session_id=session_id,
            turn_id=turn_id,
            payload={"text": text}
        )
        await self.send_event(session_id, event)

    async def broadcast_reply_text(self, session_id: str, text: str, turn_id: str):
        """Helper to broadcast reply text event"""
        event = WebSocketEvent(
            type=EventType.REPLY_TEXT,
            session_id=session_id,
            turn_id=turn_id,
            payload={"text": text}
        )
        await self.send_event(session_id, event)

    async def broadcast_audio_ready(
        self,
        session_id: str,
        turn_id: str,
        url: str,
        duration_ms: int = 0
    ):
        """Helper to broadcast audio ready event"""
        event = WebSocketEvent(
            type=EventType.REPLY_AUDIO_READY,
            session_id=session_id,
            turn_id=turn_id,
            payload={
                "url": url,
                "duration_ms": duration_ms,
                "format": "wav",
                "sample_rate_hz": settings.TTS_SAMPLE_RATE,
                "channels": settings.TTS_CHANNELS
            }
        )
        await self.send_event(session_id, event)

    async def broadcast_error(self, session_id: str, code: str, message: str, turn_id: str = None):
        """Helper to broadcast error event"""
        event = WebSocketEvent(
            type=EventType.ERROR,
            session_id=session_id,
            turn_id=turn_id,
            payload={"code": code, "message": message}
        )
        await self.send_event(session_id, event)


# Global connection manager instance
connection_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Query(...)
):
    """
    WebSocket endpoint for real-time event streaming and audio upload
    Client should connect with: ws://127.0.0.1:8008/ws?session_id=<session_id>

    Message types:
    - Text: JSON messages (audio.start, audio.end, ping)
    - Binary: Audio chunks
    """
    await connection_manager.connect(websocket, session_id)

    try:
        # Ensure session is loaded (from memory or DB) before processing messages
        await session_manager.resume_or_create_session(session_id)

        # Send initial connection confirmation
        await connection_manager.broadcast_state(session_id, SessionStatus.IDLE)

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message (can be text or binary)
                message = await websocket.receive()

                if "text" in message:
                    # Handle JSON text messages
                    data = message["text"]
                    logger.debug(f"Received text message: {data[:100]}...")

                    try:
                        msg = json.loads(data)
                        msg_type = msg.get("type")

                        if msg_type == "audio.start":
                            await connection_manager.handle_audio_start(
                                session_id,
                                msg.get("config", {})
                            )

                        elif msg_type == "audio.end":
                            await connection_manager.handle_audio_end(session_id)

                        elif msg_type == "ping":
                            await websocket.send_json({"type": "pong"})

                        else:
                            logger.warning(f"Unknown message type: {msg_type}")

                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from client: {data}")

                elif "bytes" in message:
                    # Handle binary audio chunks
                    audio_chunk = message["bytes"]
                    logger.debug(f"Received audio chunk: {len(audio_chunk)} bytes")
                    await connection_manager.handle_audio_chunk(session_id, audio_chunk)

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally for session {session_id}")
                break

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)

    finally:
        await connection_manager.disconnect(websocket, session_id)
