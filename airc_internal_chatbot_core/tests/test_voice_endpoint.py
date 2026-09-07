"""
Unit tests for Voice TTS Endpoint (/api/v1/voice/tts)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.voice import router as voice_router, chat_permission_dependency
from app.models.auth import User, UserRole

# Isolated FastAPI test app mounting voice router
test_app = FastAPI()
test_app.include_router(voice_router, prefix="/api/v1/voice")

client = TestClient(test_app)


def mock_user_with_chat_permission():
    return User(
        id="user-123",
        user_id="user-123",
        email="student@airc.edu.vn",
        full_name="Student Test",
        role=UserRole.STUDENT,
        is_active=True
    )


@pytest.fixture(autouse=True)
def override_auth():
    test_app.dependency_overrides[chat_permission_dependency] = mock_user_with_chat_permission
    yield
    test_app.dependency_overrides.clear()


@patch("edge_tts.Communicate")
def test_voice_tts_success(mock_communicate):
    """Test successful TTS audio streaming with mocked Edge-TTS"""
    async def mock_stream():
        yield {"type": "audio", "data": b"HEADER_MP3"}
        yield {"type": "audio", "data": b"BODY_MP3"}

    instance = MagicMock()
    instance.stream = mock_stream
    mock_communicate.return_value = instance

    response = client.post(
        "/api/v1/voice/tts",
        json={"text": "Xin chào sinh viên AIRC", "voice": "vi-VN-HoaiMyNeural"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.headers["cache-control"] == "no-store"
    assert response.content == b"HEADER_MP3BODY_MP3"
    mock_communicate.assert_called_once_with("Xin chào sinh viên AIRC", "vi-VN-HoaiMyNeural")


@patch("edge_tts.Communicate")
def test_voice_tts_upstream_failure_returns_502(mock_communicate):
    """Test 502 Bad Gateway is returned when Edge-TTS fails upstream"""
    instance = MagicMock()
    instance.stream.side_effect = RuntimeError("Upstream connection error")
    mock_communicate.return_value = instance

    response = client.post(
        "/api/v1/voice/tts",
        json={"text": "Xin chào sinh viên AIRC", "voice": "vi-VN-HoaiMyNeural"}
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to generate voice audio from Edge-TTS"


def test_voice_tts_validation_empty_text():
    """Test validation fails for empty or whitespace-only text"""
    response = client.post(
        "/api/v1/voice/tts",
        json={"text": "   ", "voice": "vi-VN-HoaiMyNeural"}
    )
    assert response.status_code == 422


def test_voice_tts_validation_too_long_text():
    """Test validation fails for text exceeding 2000 chars"""
    long_text = "a" * 2001
    response = client.post(
        "/api/v1/voice/tts",
        json={"text": long_text, "voice": "vi-VN-HoaiMyNeural"}
    )
    assert response.status_code == 422


def test_voice_tts_validation_invalid_voice():
    """Test validation fails for non-Vietnamese voice"""
    response = client.post(
        "/api/v1/voice/tts",
        json={"text": "Hello", "voice": "en-US-AnaNeural"}
    )
    assert response.status_code == 422


@patch(
    "app.services.system_settings_service.get_effective_llm_settings",
    new_callable=AsyncMock,
    return_value={"tts_voice": "vi-VN-NamMinhNeural"},
)
def test_voice_config_returns_catalog(mock_settings):
    """Authenticated users can read the live-mode voice catalog."""
    response = client.get("/api/v1/voice/config")
    assert response.status_code == 200
    body = response.json()
    assert body["tts_voice"] == "vi-VN-NamMinhNeural"
    ids = [item["id"] for item in body["voices"]]
    assert "vi-VN-HoaiMyNeural" in ids
    assert "vi-VN-NamMinhNeural" in ids
