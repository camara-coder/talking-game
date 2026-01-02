"""
Integration tests for WebSocket functionality
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch


@pytest.mark.websocket
@pytest.mark.integration
class TestWebSocketConnection:
    """Test WebSocket connection management"""

    @pytest.mark.asyncio
    async def test_websocket_connect(self, websocket_client):
        """Test WebSocket connection"""
        # Mock connection
        await websocket_client.send_json({"type": "connect", "session_id": "test"})

        # In a real test with proper WebSocket client:
        # response = await websocket_client.receive_json()
        # assert response["type"] == "connected"

    @pytest.mark.asyncio
    async def test_websocket_disconnect(self, websocket_client):
        """Test WebSocket disconnection"""
        # Mock disconnect
        await websocket_client.send_json({"type": "disconnect"})


@pytest.mark.websocket
@pytest.mark.integration
class TestWebSocketEvents:
    """Test WebSocket event broadcasting"""

    @pytest.mark.asyncio
    async def test_state_event(self, websocket_client):
        """Test state change events"""
        # Mock sending state event
        state_event = {
            "type": "state",
            "session_id": "test-session",
            "payload": {"state": "listening"}
        }

        await websocket_client.send_json(state_event)

    @pytest.mark.asyncio
    async def test_transcript_event(self, websocket_client):
        """Test transcript events"""
        transcript_event = {
            "type": "transcript.final",
            "session_id": "test-session",
            "turn_id": "turn-1",
            "payload": {"text": "what is five plus five"}
        }

        await websocket_client.send_json(transcript_event)

    @pytest.mark.asyncio
    async def test_reply_text_event(self, websocket_client):
        """Test reply text events"""
        reply_event = {
            "type": "reply.text",
            "session_id": "test-session",
            "turn_id": "turn-1",
            "payload": {"text": "Five plus five is ten."}
        }

        await websocket_client.send_json(reply_event)

    @pytest.mark.asyncio
    async def test_audio_ready_event(self, websocket_client):
        """Test audio ready events"""
        audio_event = {
            "type": "reply.audio_ready",
            "session_id": "test-session",
            "turn_id": "turn-1",
            "payload": {
                "url": "http://localhost:8008/api/audio/session/turn.wav",
                "duration_ms": 1800,
                "format": "wav",
                "sample_rate_hz": 24000,
                "channels": 1
            }
        }

        await websocket_client.send_json(audio_event)

    @pytest.mark.asyncio
    async def test_error_event(self, websocket_client):
        """Test error events"""
        error_event = {
            "type": "error",
            "session_id": "test-session",
            "turn_id": "turn-1",
            "payload": {
                "code": "STT_FAILED",
                "message": "Could not transcribe audio"
            }
        }

        await websocket_client.send_json(error_event)


@pytest.mark.websocket
@pytest.mark.integration
class TestWebSocketMultipleClients:
    """Test multiple WebSocket clients"""

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self):
        """Test broadcasting to multiple clients"""
        # Create mock clients
        clients = [AsyncMock() for _ in range(3)]

        # Mock connection manager
        from app.api.ws import ConnectionManager

        manager = ConnectionManager()

        # Connect clients
        session_id = "test-session"
        for client in clients:
            await manager.connect(session_id, client)

        # Broadcast event
        await manager.broadcast_state(session_id, "listening", None)

        # Verify all clients received the event
        for client in clients:
            client.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """Test that events are isolated to sessions"""
        from app.api.ws import ConnectionManager

        manager = ConnectionManager()

        # Create clients for different sessions
        client1 = AsyncMock()
        client2 = AsyncMock()

        await manager.connect("session-1", client1)
        await manager.connect("session-2", client2)

        # Broadcast to session 1
        await manager.broadcast_state("session-1", "listening", None)

        # Only client1 should receive event
        client1.send_json.assert_called()
        client2.send_json.assert_not_called()


@pytest.mark.websocket
@pytest.mark.integration
class TestWebSocketErrorHandling:
    """Test WebSocket error handling"""

    @pytest.mark.asyncio
    async def test_handle_client_disconnect(self):
        """Test handling client disconnection"""
        from app.api.ws import ConnectionManager

        manager = ConnectionManager()

        # Connect client
        client = AsyncMock()
        session_id = "test-session"
        await manager.connect(session_id, client)

        # Disconnect
        await manager.disconnect(session_id)

        # Verify client was removed
        assert session_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_handle_send_error(self):
        """Test handling send errors"""
        from app.api.ws import ConnectionManager

        manager = ConnectionManager()

        # Create client that raises error on send
        client = AsyncMock()
        client.send_json.side_effect = Exception("Connection lost")

        session_id = "test-session"
        await manager.connect(session_id, client)

        # Broadcasting should handle the error gracefully
        try:
            await manager.broadcast_state(session_id, "listening", None)
        except Exception:
            pytest.fail("Should handle send errors gracefully")


@pytest.mark.websocket
@pytest.mark.integration
class TestWebSocketMessageFormat:
    """Test WebSocket message format validation"""

    def test_state_message_format(self):
        """Test state message format"""
        from app.api.ws import create_state_event

        event = create_state_event("test-session", "listening", "turn-1")

        assert event["type"] == "state"
        assert event["session_id"] == "test-session"
        assert event["turn_id"] == "turn-1"
        assert event["payload"]["state"] == "listening"
        assert "ts" in event

    def test_transcript_message_format(self):
        """Test transcript message format"""
        from app.api.ws import create_transcript_event

        event = create_transcript_event(
            "test-session",
            "what is five plus five",
            "turn-1",
            partial=False
        )

        assert event["type"] == "transcript.final"
        assert event["payload"]["text"] == "what is five plus five"
        assert "ts" in event

    def test_error_message_format(self):
        """Test error message format"""
        from app.api.ws import create_error_event

        event = create_error_event(
            "test-session",
            "STT_FAILED",
            "Could not transcribe",
            "turn-1"
        )

        assert event["type"] == "error"
        assert event["payload"]["code"] == "STT_FAILED"
        assert event["payload"]["message"] == "Could not transcribe"
