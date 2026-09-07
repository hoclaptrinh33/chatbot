"""Schemas for runtime system LLM settings (admin)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class SystemLLMSettingsUpdate(BaseModel):
    llm_api_base_url: Optional[str] = Field(
        None,
        max_length=500,
        description="OpenAI-compatible base URL, e.g. https://api.openai.com/v1",
    )
    llm_api_key: Optional[str] = Field(
        None,
        max_length=500,
        description="Leave empty/masked to keep the stored key",
    )
    llm_model_name: Optional[str] = Field(None, max_length=200)
    tts_voice: Optional[str] = Field(
        None,
        max_length=80,
        description="Edge-TTS voice for live mode, e.g. vi-VN-HoaiMyNeural",
    )

    @field_validator("llm_api_base_url", "llm_api_key", "llm_model_name", "tts_voice", mode="before")
    @classmethod
    def strip_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("tts_voice")
    @classmethod
    def validate_tts_voice(cls, value):
        if value is None or value == "":
            return None
        from app.core.tts_voices import ALLOWED_TTS_VOICES
        if value not in ALLOWED_TTS_VOICES:
            raise ValueError(
                "Giọng đọc không hợp lệ. Chỉ hỗ trợ Hoài My hoặc Nam Minh."
            )
        return value


class SystemLLMSettingsResponse(BaseModel):
    llm_api_base_url: str
    llm_api_key_set: bool
    llm_api_key_masked: Optional[str] = None
    llm_model_name: str
    tts_voice: str = "vi-VN-HoaiMyNeural"
    source: str = Field(description="database or env")
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class LLMConnectionTestRequest(BaseModel):
    llm_api_base_url: str = Field(..., min_length=8, max_length=500)
    llm_api_key: Optional[str] = Field(None, max_length=500)

    @field_validator("llm_api_base_url", "llm_api_key", mode="before")
    @classmethod
    def strip_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class LLMConnectionTestResponse(BaseModel):
    ok: bool
    models: List[str] = Field(default_factory=list)
    error: Optional[str] = None
