"""Data access for the singleton system LLM settings document."""
from datetime import datetime
from typing import Any, Dict, Optional

from app.models.database import Collections


LLM_SETTINGS_ID = "llm"


class SystemSettingsRepository:
    def __init__(self, db):
        self.collection = db[Collections.SYSTEM_SETTINGS]

    async def get_llm(self) -> Optional[dict]:
        return await self.collection.find_one({"_id": LLM_SETTINGS_ID})

    async def upsert_llm(self, data: Dict[str, Any]) -> dict:
        payload = dict(data)
        payload["updated_at"] = datetime.utcnow()
        await self.collection.update_one(
            {"_id": LLM_SETTINGS_ID},
            {"$set": payload},
            upsert=True,
        )
        doc = await self.get_llm()
        return doc or {"_id": LLM_SETTINGS_ID, **payload}
