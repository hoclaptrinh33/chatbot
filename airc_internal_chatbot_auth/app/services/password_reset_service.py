"""
Password reset tokens stored as SHA-256 hashes.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId

from app.core.settings import settings
from app.services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)

COLLECTION = "password_reset_tokens"


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class PasswordResetService:
    def __init__(self, db, user_repo, hash_password):
        self.db = db
        self.user_repo = user_repo
        self.hash_password = hash_password
        self.collection = db[COLLECTION]

    async def request_reset(self, email: str) -> None:
        """Always succeeds from the caller's perspective (no email enumeration)."""
        user = await self.user_repo.get_by_email(email.strip().lower())
        if not user:
            logger.info("[RESET] Request for unknown email ignored")
            return

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=settings.password_reset_expire_minutes)

        await self.collection.update_many(
            {"user_id": user["id"], "used_at": None},
            {"$set": {"used_at": now}},
        )
        await self.collection.insert_one({
            "user_id": user["id"],
            "email": user["email"],
            "token_hash": token_hash,
            "created_at": now,
            "expires_at": expires_at,
            "used_at": None,
        })

        reset_url = f"{settings.frontend_url.rstrip('/')}/auth/reset-password?token={raw_token}"
        try:
            send_password_reset_email(user["email"], reset_url)
        except Exception:
            logger.exception("[RESET] Email send failed; token still issued")
        logger.info("[RESET] Token issued for user_id=%s expires=%s", user["id"], expires_at)

    async def reset_password(self, raw_token: str, new_password: str) -> bool:
        token_hash = _hash_token(raw_token)
        now = datetime.utcnow()
        doc = await self.collection.find_one({
            "token_hash": token_hash,
            "used_at": None,
            "expires_at": {"$gt": now},
        })
        if not doc:
            return False

        hashed = self.hash_password(new_password)
        updated = await self.user_repo.update_user(doc["user_id"], {"hashed_password": hashed})
        if not updated:
            return False

        await self.collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"used_at": now}},
        )
        return True
