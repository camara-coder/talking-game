"""
Integration tests for API endpoints
"""
import pytest
import json
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client: TestClient):
        """Test basic health check"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "healthy"
        assert "timestamp" in data
        assert "checks" in data

    def test_health_check_structure(self, client: TestClient):
        """Test health check response structure"""
        response = client.get("/health")
        data = response.json()

        # Check for required sections
        assert "checks" in data
        checks = data["checks"]

        assert "ollama" in checks
        assert "stt" in checks
        assert "storage" in checks

    @pytest.mark.requires_ollama
    def test_health_check_ollama(self, client: TestClient):
        """Test Ollama health status"""
        response = client.get("/health")
        data = response.json()

        ollama_status = data["checks"]["ollama"]["status"]
        assert ollama_status in ["healthy", "unhealthy"]


@pytest.mark.integration
class TestSessionEndpoints:
    """Test session management endpoints"""

    def test_start_session(self, client: TestClient):
        """Test starting a new session"""
        response = client.post(
            "/api/session/start",
            json={
                "language": "en",
                "mode": "ptt"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert "status" in data
        assert data["status"] == "listening"

    def test_start_session_with_custom_id(self, client: TestClient):
        """Test starting session with custom ID"""
        custom_id = "test-session-123"

        response = client.post(
            "/api/session/start",
            json={
                "session_id": custom_id,
                "language": "en",
                "mode": "ptt"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == custom_id

    def test_start_session_defaults(self, client: TestClient):
        """Test session start with default values"""
        response = client.post("/api/session/start", json={})

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_stop_session(self, client: TestClient):
        """Test stopping a session"""
        # Start session
        start_response = client.post("/api/session/start", json={})
        session_id = start_response.json()["session_id"]

        # Stop session
        stop_response = client.post(
            "/api/session/stop",
            json={
                "session_id": session_id,
                "return_audio": False
            }
        )

        assert stop_response.status_code == 200
        data = stop_response.json()
        assert data["session_id"] == session_id
        assert "status" in data

    def test_stop_nonexistent_session(self, client: TestClient):
        """Test stopping a session that doesn't exist"""
        response = client.post(
            "/api/session/stop",
            json={
                "session_id": "nonexistent-session",
                "return_audio": False
            }
        )

        assert response.status_code == 404

    def test_get_session(self, client: TestClient):
        """Test getting session information"""
        # Start session
        start_response = client.post("/api/session/start", json={})
        session_id = start_response.json()["session_id"]

        # Get session
        response = client.get(f"/api/session/{session_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == session_id
        assert "status" in data
        assert "turns" in data

    def test_get_nonexistent_session(self, client: TestClient):
        """Test getting a session that doesn't exist"""
        response = client.get("/api/session/nonexistent")

        assert response.status_code == 404


@pytest.mark.integration
class TestAudioEndpoints:
    """Test audio-related endpoints"""

    def test_upload_audio(self, client: TestClient, temp_wav_file):
        """Test uploading audio file"""
        # Start session
        start_response = client.post("/api/session/start", json={})
        session_id = start_response.json()["session_id"]

        # Upload audio
        with open(temp_wav_file, "rb") as f:
            response = client.post(
                f"/api/audio/upload/{session_id}",
                files={"file": ("test.wav", f, "audio/wav")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data

    def test_upload_audio_invalid_session(self, client: TestClient, temp_wav_file):
        """Test uploading audio to invalid session"""
        with open(temp_wav_file, "rb") as f:
            response = client.post(
                "/api/audio/upload/invalid-session",
                files={"file": ("test.wav", f, "audio/wav")}
            )

        assert response.status_code in [404, 400]

    def test_download_audio(self, client: TestClient):
        """Test downloading generated audio"""
        # This would require a full pipeline run
        # For now, test the endpoint structure
        response = client.get("/api/audio/session-id/turn-id.wav")

        # Should return 404 if audio doesn't exist
        assert response.status_code == 404


@pytest.mark.integration
class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Check CORS headers
        assert "access-control-allow-origin" in response.headers

    def test_cors_allowed_origins(self, client: TestClient):
        """Test allowed origins"""
        allowed_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

        for origin in allowed_origins:
            response = client.get(
                "/health",
                headers={"Origin": origin}
            )

            assert response.status_code == 200


@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling"""

    def test_invalid_json(self, client: TestClient):
        """Test handling of invalid JSON"""
        response = client.post(
            "/api/session/start",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_missing_required_fields(self, client: TestClient):
        """Test handling of missing required fields"""
        response = client.post(
            "/api/session/stop",
            json={}  # Missing session_id
        )

        assert response.status_code == 422

    def test_invalid_method(self, client: TestClient):
        """Test invalid HTTP method"""
        response = client.delete("/api/session/start")

        assert response.status_code == 405


@pytest.mark.integration
class TestConcurrentSessions:
    """Test handling of multiple concurrent sessions"""

    def test_multiple_sessions(self, client: TestClient):
        """Test creating multiple sessions"""
        sessions = []

        # Create 5 sessions
        for i in range(5):
            response = client.post("/api/session/start", json={})
            assert response.status_code == 200
            sessions.append(response.json()["session_id"])

        # Verify all sessions are unique
        assert len(sessions) == len(set(sessions))

        # Get info for each session
        for session_id in sessions:
            response = client.get(f"/api/session/{session_id}")
            assert response.status_code == 200

    def test_session_isolation(self, client: TestClient):
        """Test that sessions are isolated from each other"""
        # Create two sessions
        response1 = client.post("/api/session/start", json={})
        session1_id = response1.json()["session_id"]

        response2 = client.post("/api/session/start", json={})
        session2_id = response2.json()["session_id"]

        # Stop first session
        client.post(
            "/api/session/stop",
            json={"session_id": session1_id, "return_audio": False}
        )

        # Second session should still be accessible
        response = client.get(f"/api/session/{session2_id}")
        assert response.status_code == 200
