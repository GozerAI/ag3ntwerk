"""
Unit tests for voice recording API routes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
from fastapi.testclient import TestClient

from ag3ntwerk.api.app import app


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestVoiceStatus:
    """Tests for voice status endpoint."""

    def test_get_voice_status(self, test_client):
        """Test getting voice service status."""
        response = test_client.get("/api/v1/voice/status")
        assert response.status_code == 200

        data = response.json()
        assert "whisper" in data
        assert "supported_formats" in data
        assert "max_file_size_mb" in data

        # Check whisper status structure
        whisper = data["whisper"]
        assert "available" in whisper
        assert "default_model" in whisper

        # Check supported formats
        formats = data["supported_formats"]
        assert "wav" in formats
        assert "mp3" in formats
        assert "webm" in formats

    def test_voice_status_max_file_size(self, test_client):
        """Test that max file size is reasonable."""
        response = test_client.get("/api/v1/voice/status")
        data = response.json()

        assert data["max_file_size_mb"] == 25


class TestTranscribeAudio:
    """Tests for audio transcription endpoint."""

    def test_transcribe_requires_audio_file(self, test_client):
        """Test that transcription requires an audio file."""
        response = test_client.post("/api/v1/voice/transcribe")
        assert response.status_code == 422  # Validation error

    def test_transcribe_rejects_unsupported_format(self, test_client):
        """Test that unsupported formats are rejected."""
        # Create a fake file with unsupported extension
        files = {"audio": ("test.txt", BytesIO(b"not audio"), "text/plain")}
        response = test_client.post("/api/v1/voice/transcribe", files=files)

        assert response.status_code == 400
        data = response.json()
        # API uses custom error format with 'message' field
        error_message = data.get("message") or data.get("detail", "")
        assert "Unsupported audio format" in error_message

    @patch("ag3ntwerk.api.voice_routes._get_whisper_async", new_callable=AsyncMock)
    def test_transcribe_checks_whisper_availability(self, mock_get_whisper, test_client):
        """Test that transcription checks Whisper availability."""
        # Mock Whisper as unavailable
        mock_whisper = MagicMock()
        mock_whisper.is_available.return_value = False
        mock_get_whisper.return_value = mock_whisper

        # Create a valid audio file
        files = {"audio": ("test.wav", BytesIO(b"RIFF" + b"\x00" * 100), "audio/wav")}
        response = test_client.post("/api/v1/voice/transcribe", files=files)

        assert response.status_code == 503
        data = response.json()
        error_message = data.get("message") or data.get("detail", "")
        assert "not available" in error_message

    @patch("ag3ntwerk.api.voice_routes._get_whisper_async", new_callable=AsyncMock)
    def test_transcribe_success(self, mock_get_whisper, test_client):
        """Test successful transcription."""
        # Mock Whisper
        mock_whisper = MagicMock()
        mock_whisper.is_available.return_value = True

        # Mock transcription result
        mock_result = MagicMock()
        mock_result.text = "Hello world"
        mock_result.language = "en"
        mock_result.duration = 2.5
        mock_result.segments = []

        # Make transcribe an async function
        async def mock_transcribe(*args, **kwargs):
            return mock_result

        mock_whisper.transcribe = mock_transcribe
        mock_get_whisper.return_value = mock_whisper

        # Create a valid audio file
        files = {"audio": ("test.wav", BytesIO(b"RIFF" + b"\x00" * 100), "audio/wav")}
        response = test_client.post("/api/v1/voice/transcribe", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello world"
        assert data["language"] == "en"
        assert data["duration"] == 2.5
        assert data["status"] == "completed"

    def test_transcribe_accepts_model_parameter(self, test_client):
        """Test that model parameter is accepted."""
        files = {"audio": ("test.wav", BytesIO(b"RIFF" + b"\x00" * 100), "audio/wav")}
        data = {"model": "small"}

        # Will fail on Whisper availability, but validates params
        with patch(
            "ag3ntwerk.api.voice_routes._get_whisper_async", new_callable=AsyncMock
        ) as mock_get_whisper:
            mock_whisper = MagicMock()
            mock_whisper.is_available.return_value = False
            mock_get_whisper.return_value = mock_whisper

            response = test_client.post(
                "/api/v1/voice/transcribe",
                files=files,
                data=data,
            )
            # Should reach Whisper check, not validation error
            assert response.status_code == 503

    def test_transcribe_accepts_language_parameter(self, test_client):
        """Test that language parameter is accepted."""
        files = {"audio": ("test.wav", BytesIO(b"RIFF" + b"\x00" * 100), "audio/wav")}
        data = {"language": "es"}

        with patch(
            "ag3ntwerk.api.voice_routes._get_whisper_async", new_callable=AsyncMock
        ) as mock_get_whisper:
            mock_whisper = MagicMock()
            mock_whisper.is_available.return_value = False
            mock_get_whisper.return_value = mock_whisper

            response = test_client.post(
                "/api/v1/voice/transcribe",
                files=files,
                data=data,
            )
            # Should reach Whisper check, not validation error
            assert response.status_code == 503


class TestTranscriptionsList:
    """Tests for transcriptions list endpoint."""

    def test_list_transcriptions_empty(self, test_client):
        """Test listing transcriptions when empty."""
        # Clear any existing transcriptions
        from ag3ntwerk.api.voice_routes import _transcriptions

        _transcriptions.clear()

        response = test_client.get("/api/v1/voice/transcriptions")
        assert response.status_code == 200

        data = response.json()
        assert "transcriptions" in data
        assert "count" in data
        assert data["count"] == 0

    @patch("ag3ntwerk.api.voice_routes._get_whisper_async", new_callable=AsyncMock)
    def test_list_transcriptions_after_transcribe(self, mock_get_whisper, test_client):
        """Test that transcriptions appear in list after transcribing."""
        from ag3ntwerk.api.voice_routes import _transcriptions

        _transcriptions.clear()

        # Mock successful transcription
        mock_whisper = MagicMock()
        mock_whisper.is_available.return_value = True

        mock_result = MagicMock()
        mock_result.text = "Test transcription"
        mock_result.language = "en"
        mock_result.duration = 1.0
        mock_result.segments = []

        async def mock_transcribe(*args, **kwargs):
            return mock_result

        mock_whisper.transcribe = mock_transcribe
        mock_get_whisper.return_value = mock_whisper

        # Perform transcription
        files = {"audio": ("test.wav", BytesIO(b"RIFF" + b"\x00" * 100), "audio/wav")}
        test_client.post("/api/v1/voice/transcribe", files=files)

        # Check list
        response = test_client.get("/api/v1/voice/transcriptions")
        data = response.json()

        assert data["count"] >= 1


class TestTranscriptionDetail:
    """Tests for transcription detail endpoint."""

    def test_get_transcription_not_found(self, test_client):
        """Test getting non-existent transcription."""
        response = test_client.get("/api/v1/voice/transcriptions/nonexistent")
        assert response.status_code == 404

    @patch("ag3ntwerk.api.voice_routes._get_whisper_async", new_callable=AsyncMock)
    def test_get_transcription_success(self, mock_get_whisper, test_client):
        """Test getting a specific transcription."""
        from ag3ntwerk.api.voice_routes import _transcriptions

        _transcriptions.clear()

        # Mock successful transcription
        mock_whisper = MagicMock()
        mock_whisper.is_available.return_value = True

        mock_result = MagicMock()
        mock_result.text = "Specific transcription"
        mock_result.language = "en"
        mock_result.duration = 3.0
        mock_result.segments = []

        async def mock_transcribe(*args, **kwargs):
            return mock_result

        mock_whisper.transcribe = mock_transcribe
        mock_get_whisper.return_value = mock_whisper

        # Perform transcription
        files = {"audio": ("test.wav", BytesIO(b"RIFF" + b"\x00" * 100), "audio/wav")}
        trans_response = test_client.post("/api/v1/voice/transcribe", files=files)
        trans_id = trans_response.json()["id"]

        # Get specific transcription
        response = test_client.get(f"/api/v1/voice/transcriptions/{trans_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == trans_id
        assert data["text"] == "Specific transcription"


class TestTranscribeForInterview:
    """Tests for interview-specific transcription endpoint."""

    def test_transcribe_for_interview_requires_session_id(self, test_client):
        """Test that session_id is required."""
        files = {"audio": ("test.wav", BytesIO(b"RIFF" + b"\x00" * 100), "audio/wav")}
        response = test_client.post("/api/v1/voice/transcribe-for-interview", files=files)

        assert response.status_code == 422  # Validation error

    @patch("ag3ntwerk.api.voice_routes._get_whisper_async", new_callable=AsyncMock)
    def test_transcribe_for_interview_success(self, mock_get_whisper, test_client):
        """Test successful interview transcription."""
        # Mock Whisper
        mock_whisper = MagicMock()
        mock_whisper.is_available.return_value = True

        mock_result = MagicMock()
        mock_result.text = "Interview answer"
        mock_result.language = "en"
        mock_result.duration = 5.0
        mock_result.segments = []

        async def mock_transcribe(*args, **kwargs):
            return mock_result

        mock_whisper.transcribe = mock_transcribe
        mock_get_whisper.return_value = mock_whisper

        # Create request
        files = {"audio": ("test.wav", BytesIO(b"RIFF" + b"\x00" * 100), "audio/wav")}
        data = {"session_id": "session_123"}
        response = test_client.post(
            "/api/v1/voice/transcribe-for-interview",
            files=files,
            data=data,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["session_id"] == "session_123"
        assert result["text"] == "Interview answer"
        assert result["ready_for_submission"] is True


class TestFileSizeLimit:
    """Tests for file size limits."""

    @patch("ag3ntwerk.api.voice_routes._get_whisper_async", new_callable=AsyncMock)
    def test_file_too_large(self, mock_get_whisper, test_client):
        """Test that large files are rejected."""
        mock_whisper = MagicMock()
        mock_whisper.is_available.return_value = True
        mock_get_whisper.return_value = mock_whisper

        # Create a "large" file (we'll check the size limit logic)
        # In practice, this would be checked by size
        large_content = b"RIFF" + (b"\x00" * (26 * 1024 * 1024))  # 26MB
        files = {"audio": ("large.wav", BytesIO(large_content), "audio/wav")}

        response = test_client.post("/api/v1/voice/transcribe", files=files)
        assert response.status_code == 400
        data = response.json()
        error_message = data.get("message") or data.get("detail", "")
        assert "too large" in error_message


class TestAudioFormats:
    """Tests for supported audio formats."""

    @pytest.mark.parametrize(
        "ext,mime_type",
        [
            (".wav", "audio/wav"),
            (".mp3", "audio/mpeg"),
            (".ogg", "audio/ogg"),
            (".webm", "audio/webm"),
            (".m4a", "audio/x-m4a"),
            (".flac", "audio/flac"),
        ],
    )
    @patch("ag3ntwerk.api.voice_routes._get_whisper_async", new_callable=AsyncMock)
    def test_supported_formats(self, mock_get_whisper, ext, mime_type, test_client):
        """Test that all supported formats are accepted."""
        mock_whisper = MagicMock()
        mock_whisper.is_available.return_value = False
        mock_get_whisper.return_value = mock_whisper

        files = {"audio": (f"test{ext}", BytesIO(b"audio data"), mime_type)}
        response = test_client.post("/api/v1/voice/transcribe", files=files)

        # Should reach Whisper check, not format error
        assert response.status_code == 503

    @pytest.mark.parametrize("ext", [".txt", ".pdf", ".jpg", ".exe"])
    def test_unsupported_formats(self, ext, test_client):
        """Test that unsupported formats are rejected."""
        files = {"audio": (f"test{ext}", BytesIO(b"not audio"), "application/octet-stream")}
        response = test_client.post("/api/v1/voice/transcribe", files=files)

        assert response.status_code == 400
        data = response.json()
        error_message = data.get("message") or data.get("detail", "")
        assert "Unsupported audio format" in error_message
