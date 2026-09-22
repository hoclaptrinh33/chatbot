"""
Voice Controller - FastAPI endpoints for Text-to-Speech (Edge-TTS)
"""
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
import edge_tts

from app.models.auth import User, Permission
from app.api.dependencies import require_permission
from app.core.tts_voices import (
    ALLOWED_TTS_VOICES,
    DEFAULT_TTS_VOICE,
    TTS_VOICE_CATALOG,
    normalize_tts_voice,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Export single module-level permission dependency closure for route protection and test overrides
chat_permission_dependency = require_permission(Permission.CHAT_USE)

ALLOWED_VIETNAMESE_VOICES = ALLOWED_TTS_VOICES


class VoiceTTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Text must not be empty")
        if len(v) > 2000:
            raise ValueError("Text exceeds maximum length of 2000 characters")
        return v

    @field_validator("voice")
    @classmethod
    def validate_voice(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if v not in ALLOWED_VIETNAMESE_VOICES:
            raise ValueError(
                f"Voice '{v}' is not allowed. Only Vietnamese Edge voices ({', '.join(sorted(ALLOWED_VIETNAMESE_VOICES))}) are permitted."
            )
        return v


@router.get("/config")
async def get_voice_config(
    current_user: User = Depends(chat_permission_dependency),
):
    """Default live-mode voice plus the allowed catalog."""
    from app.services.system_settings_service import get_effective_llm_settings

    try:
        effective = await get_effective_llm_settings()
        tts_voice = normalize_tts_voice(effective.get("tts_voice"))
    except Exception:
        tts_voice = DEFAULT_TTS_VOICE
    return {"tts_voice": tts_voice, "voices": TTS_VOICE_CATALOG}


@router.post("/tts")
async def generate_tts(
    request: VoiceTTSRequest,
    current_user: User = Depends(chat_permission_dependency)
) -> StreamingResponse:
    """
    Convert Vietnamese text into streaming audio/mpeg using Edge-TTS.
    
    - Requires CHAT_USE permission.
    - Text must be non-empty and <= 2000 chars.
    - Prefetches first audio chunk to guarantee HTTP 502 on upstream failures before returning StreamingResponse.
    - Never logs user text.
    - Client should send packed paragraphs (not tiny fragments) so Edge-TTS
      opens fewer Microsoft WebSocket sessions.
    """
    from app.services.system_settings_service import get_effective_llm_settings

    voice = request.voice
    if not voice:
        try:
            effective = await get_effective_llm_settings()
            voice = normalize_tts_voice(effective.get("tts_voice"))
        except Exception:
            voice = DEFAULT_TTS_VOICE

    # Log metadata only - NEVER log the text itself
    logger.info(
        f"[VOICE TTS] Request received - user: {current_user.user_id}, "
        f"voice: {voice}, text_len: {len(request.text)}"
    )

    try:
        communicate = edge_tts.Communicate(request.text, voice)
        stream_gen = communicate.stream()

        # Prefetch first audio chunk to catch upstream errors before response headers are sent
        first_chunk = None
        async for chunk in stream_gen:
            if chunk.get("type") == "audio":
                first_chunk = chunk["data"]
                break

        if first_chunk is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to generate voice audio from Edge-TTS"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VOICE TTS] Upstream Edge-TTS failure: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate voice audio from Edge-TTS"
        )

    async def tts_audio_wrapper() -> AsyncGenerator[bytes, None]:
        yield first_chunk
        async for chunk in stream_gen:
            if chunk.get("type") == "audio":
                yield chunk["data"]

    return StreamingResponse(
        tts_audio_wrapper(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store",
            "Connection": "keep-alive",
        }
    )
