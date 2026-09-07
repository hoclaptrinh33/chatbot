"""Runtime LLM settings: MongoDB document with .env fallback."""
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.tts_voices import normalize_tts_voice
from app.models.database import Collections
from app.models.settings_schemas import SystemLLMSettingsResponse, SystemLLMSettingsUpdate
from app.repositories.system_settings_repository import SystemSettingsRepository
from app.services.llm_resolve import mask_api_key, normalize_base_url

_MASK_SENTINELS = {"", "••••••••", "********", "****"}

_cache: Optional[Dict[str, Any]] = None


def invalidate_llm_settings_cache() -> None:
    global _cache
    _cache = None


def _from_env() -> Dict[str, Any]:
    return {
        "base_url": settings.llm_api_base_url,
        "api_key": settings.llm_api_key,
        "model_name": settings.llm_model_name,
        "tts_voice": normalize_tts_voice(settings.tts_voice),
        "source": "env",
        "updated_at": None,
        "updated_by": None,
        "key_in_db": False,
    }


def _from_doc(doc: dict) -> Dict[str, Any]:
    db_url = (doc.get("llm_api_base_url") or "").strip()
    db_key = doc.get("llm_api_key")
    db_model = (doc.get("llm_model_name") or "").strip()
    key_in_db = bool(isinstance(db_key, str) and db_key.strip())
    return {
        "base_url": db_url or settings.llm_api_base_url,
        "api_key": db_key.strip() if key_in_db else settings.llm_api_key,
        "model_name": db_model or settings.llm_model_name,
        "tts_voice": normalize_tts_voice(doc.get("tts_voice") or settings.tts_voice),
        "source": "database",
        "updated_at": doc.get("updated_at"),
        "updated_by": doc.get("updated_by"),
        "key_in_db": key_in_db,
    }


async def get_effective_llm_settings() -> Dict[str, Any]:
    """
    Effective LLM connection used by chat/processing.
    Cached after a successful DB read. Env-only results are not cached
    so a late Mongo connection still gets picked up.
    """
    global _cache
    if _cache is not None:
        return _cache

    from app.core.database import mongodb

    db = getattr(mongodb, "db", None)
    if db is None:
        return _from_env()
    try:
        doc = await db[Collections.SYSTEM_SETTINGS].find_one({"_id": "llm"})
    except Exception:
        return _from_env()

    if not doc:
        return _from_env()

    _cache = _from_doc(doc)
    return _cache


def to_public_response(effective: Dict[str, Any]) -> SystemLLMSettingsResponse:
    key = effective.get("api_key")
    return SystemLLMSettingsResponse(
        llm_api_base_url=normalize_base_url(effective["base_url"]),
        llm_api_key_set=bool(key),
        llm_api_key_masked=mask_api_key(key),
        llm_model_name=effective["model_name"],
        tts_voice=normalize_tts_voice(effective.get("tts_voice")),
        source=effective["source"],
        updated_at=effective.get("updated_at"),
        updated_by=effective.get("updated_by"),
    )


class SystemSettingsService:
    def __init__(self, repo: SystemSettingsRepository):
        self.repo = repo

    async def get_settings(self) -> SystemLLMSettingsResponse:
        invalidate_llm_settings_cache()
        effective = await get_effective_llm_settings()
        return to_public_response(effective)

    async def update_settings(
        self,
        payload: SystemLLMSettingsUpdate,
        updated_by: str,
    ) -> SystemLLMSettingsResponse:
        existing = await self.repo.get_llm() or {}
        env = _from_env()

        url = payload.llm_api_base_url
        if url is None:
            url = existing.get("llm_api_base_url") or env["base_url"]
        url = normalize_base_url(url)
        if not url.startswith(("http://", "https://")):
            raise ValueError("LLM endpoint phải bắt đầu bằng http:// hoặc https://")

        incoming_key = payload.llm_api_key
        if incoming_key is None or incoming_key in _MASK_SENTINELS or incoming_key == mask_api_key(existing.get("llm_api_key")):
            stored_key = existing.get("llm_api_key")
            if not stored_key:
                stored_key = env["api_key"]
        else:
            stored_key = incoming_key

        model_name = payload.llm_model_name
        if model_name is None or model_name == "":
            model_name = existing.get("llm_model_name") or env["model_name"]

        tts_voice = normalize_tts_voice(
            payload.tts_voice
            if payload.tts_voice
            else (existing.get("tts_voice") or env.get("tts_voice"))
        )

        await self.repo.upsert_llm({
            "llm_api_base_url": url,
            "llm_api_key": stored_key,
            "llm_model_name": model_name,
            "tts_voice": tts_voice,
            "updated_by": updated_by,
        })
        invalidate_llm_settings_cache()
        return await self.get_settings()
