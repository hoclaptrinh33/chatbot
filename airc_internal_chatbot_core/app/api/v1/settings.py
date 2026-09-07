"""
System settings API — admin-only runtime LLM provider configuration.
"""
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user, require_permission
from app.core.database import get_database
from app.models.auth import Permission, User
from app.models.settings_schemas import (
    LLMConnectionTestRequest,
    LLMConnectionTestResponse,
    SystemLLMSettingsResponse,
    SystemLLMSettingsUpdate,
)
from app.repositories.system_settings_repository import SystemSettingsRepository
from app.services.llm_resolve import empty_to_none, normalize_base_url, resolve_llm_connection
from app.services.system_settings_service import (
    SystemSettingsService,
    get_effective_llm_settings,
)

logger = logging.getLogger(__name__)

router = APIRouter()
admin_only = require_permission(Permission.SYSTEM_MANAGE)


def get_system_settings_service(db=Depends(get_database)) -> SystemSettingsService:
    return SystemSettingsService(SystemSettingsRepository(db))


async def fetch_provider_models(base_url: str, api_key: Optional[str]) -> list:
    url = f"{normalize_base_url(base_url)}/models"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:240]}")
        data = response.json()
        models_data = data.get("data") or []
        return [m.get("id") for m in models_data if isinstance(m, dict) and m.get("id")]


@router.get("", response_model=SystemLLMSettingsResponse)
async def get_system_settings(
    current_user: User = Depends(admin_only),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    return await service.get_settings()


@router.put("", response_model=SystemLLMSettingsResponse)
async def update_system_settings(
    payload: SystemLLMSettingsUpdate,
    current_user: User = Depends(admin_only),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    try:
        return await service.update_settings(payload, updated_by=current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test", response_model=LLMConnectionTestResponse)
async def test_llm_connection(
    payload: LLMConnectionTestRequest,
    current_user: User = Depends(admin_only),
):
    """Probe an OpenAI-compatible /models endpoint without saving."""
    try:
        base_url = normalize_base_url(payload.llm_api_base_url)
        api_key = empty_to_none(payload.llm_api_key)
        if api_key in {"••••••••", "********"}:
            api_key = None
        if not api_key:
            effective = await get_effective_llm_settings()
            # Reuse the stored key only when testing the same provider.
            if normalize_base_url(effective["base_url"]) == base_url:
                api_key = empty_to_none(effective.get("api_key"))
        models = await fetch_provider_models(base_url, api_key)
        return LLMConnectionTestResponse(ok=True, models=models)
    except Exception as e:
        logger.warning("[SETTINGS] LLM connection test failed: %s", e)
        return LLMConnectionTestResponse(ok=False, error=str(e)[:300])


@router.get("/llm-models")
async def list_llm_models_for_provider(
    current_user: User = Depends(get_current_user),
    api_base_url: Optional[str] = Query(None),
    api_key: Optional[str] = Query(None),
):
    """
    List models from the system provider, or from a per-bot override
    when api_base_url / api_key are supplied.
    """
    effective = await get_effective_llm_settings()
    base_url, token = resolve_llm_connection(
        bot_base_url=api_base_url,
        bot_api_key=api_key,
        system_base_url=effective["base_url"],
        system_api_key=effective.get("api_key"),
    )
    default_model = effective["model_name"]
    models = []
    try:
        models = await fetch_provider_models(base_url, token)
    except Exception as e:
        logger.warning("[SETTINGS] Error fetching models from %s: %s", base_url, e)

    if default_model and default_model not in models and not api_base_url:
        models.insert(0, default_model)
    return {"models": models, "default_model": default_model}
