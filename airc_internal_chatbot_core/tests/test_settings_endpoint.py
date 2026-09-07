"""Unit tests for /api/v1/settings (admin LLM provider config)."""
import pytest

pytest.importorskip("qdrant_client")

from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.settings import get_system_settings_service, router
from app.models.auth import User, UserRole
from app.models.settings_schemas import SystemLLMSettingsResponse
from app.services.system_settings_service import SystemSettingsService

test_app = FastAPI()
test_app.include_router(router, prefix="/api/v1/settings")
client = TestClient(test_app)


def mock_admin():
    return User(
        id="admin-1",
        user_id="admin-1",
        email="admin@airc.edu.vn",
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )


def mock_student():
    return User(
        id="stu-1",
        user_id="stu-1",
        email="student@airc.edu.vn",
        full_name="Student",
        role=UserRole.STUDENT,
        is_active=True,
    )


class FakeService(SystemSettingsService):
    def __init__(self):
        self.repo = None
        self._doc = SystemLLMSettingsResponse(
            llm_api_base_url="http://localhost:11434/v1",
            llm_api_key_set=True,
            llm_api_key_masked="oll••••ama",
            llm_model_name="gemma-4-26b-qat",
            source="env",
            updated_at=None,
            updated_by=None,
        )

    async def get_settings(self):
        return self._doc

    async def update_settings(self, payload, updated_by: str):
        url = payload.llm_api_base_url or self._doc.llm_api_base_url
        model = payload.llm_model_name or self._doc.llm_model_name
        self._doc = SystemLLMSettingsResponse(
            llm_api_base_url=url,
            llm_api_key_set=True,
            llm_api_key_masked="sk-••••test",
            llm_model_name=model,
            source="database",
            updated_at=datetime.utcnow(),
            updated_by=updated_by,
        )
        return self._doc


fake_service = FakeService()


def test_student_cannot_read_settings():
    test_app.dependency_overrides[get_current_user] = mock_student
    try:
        response = client.get("/api/v1/settings")
        assert response.status_code == 403
    finally:
        test_app.dependency_overrides.clear()


def test_admin_get_settings_masks_key():
    test_app.dependency_overrides[get_current_user] = mock_admin
    test_app.dependency_overrides[get_system_settings_service] = lambda: fake_service
    try:
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        body = response.json()
        assert body["llm_api_base_url"] == "http://localhost:11434/v1"
        assert body["llm_api_key_set"] is True
        assert "llm_api_key" not in body
        assert body["llm_api_key_masked"]
    finally:
        test_app.dependency_overrides.clear()


def test_admin_put_settings():
    test_app.dependency_overrides[get_current_user] = mock_admin
    test_app.dependency_overrides[get_system_settings_service] = lambda: fake_service
    try:
        response = client.put(
            "/api/v1/settings",
            json={
                "llm_api_base_url": "https://api.openai.com/v1",
                "llm_model_name": "gpt-4o-mini",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["llm_api_base_url"] == "https://api.openai.com/v1"
        assert body["llm_model_name"] == "gpt-4o-mini"
        assert body["source"] == "database"
        assert body["updated_by"] == "admin-1"
    finally:
        test_app.dependency_overrides.clear()


@patch("app.api.v1.settings.fetch_provider_models", new_callable=AsyncMock)
def test_connection_test_ok(mock_fetch):
    mock_fetch.return_value = ["gpt-4o-mini", "gpt-4o"]
    test_app.dependency_overrides[get_current_user] = mock_admin
    try:
        response = client.post(
            "/api/v1/settings/test",
            json={
                "llm_api_base_url": "https://api.openai.com/v1",
                "llm_api_key": "sk-test",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert "gpt-4o-mini" in body["models"]
        mock_fetch.assert_awaited()
    finally:
        test_app.dependency_overrides.clear()
