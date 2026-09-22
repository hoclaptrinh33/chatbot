"""Password reset hashing/expiry unit tests (no SMTP)."""
import hashlib
from datetime import datetime, timedelta

import pytest

from app.services.password_reset_service import _hash_token, PasswordResetService


def test_hash_token_is_sha256():
    token = "abc123"
    assert _hash_token(token) == hashlib.sha256(token.encode()).hexdigest()


class FakeUsers:
    def __init__(self):
        self.users = {
            "u1": {
                "id": "u1",
                "email": "sv@airc.vnu.edu.vn",
                "hashed_password": "old",
            }
        }

    async def get_by_email(self, email):
        for user in self.users.values():
            if user["email"] == email:
                return user
        return None

    async def update_user(self, user_id, update_data):
        if user_id not in self.users:
            return False
        self.users[user_id].update(update_data)
        return True


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def update_many(self, filt, update):
        return None

    async def insert_one(self, doc):
        self.docs.append(doc)
        return None

    async def find_one(self, filt):
        for doc in self.docs:
            if doc.get("token_hash") != filt.get("token_hash"):
                continue
            if doc.get("used_at") is not None:
                continue
            if doc.get("expires_at") <= datetime.utcnow():
                continue
            return doc
        return None

    async def update_one(self, filt, update):
        return None


class FakeDb(dict):
    def __getitem__(self, item):
        return super().setdefault(item, FakeCollection())


@pytest.mark.asyncio
async def test_reset_unknown_email_is_silent():
    service = PasswordResetService(FakeDb(), FakeUsers(), hash_password=lambda p: f"h:{p}")
    await service.request_reset("nobody@airc.vnu.edu.vn")


@pytest.mark.asyncio
async def test_reset_password_rejects_bad_token():
    service = PasswordResetService(FakeDb(), FakeUsers(), hash_password=lambda p: f"h:{p}")
    ok = await service.reset_password("not-a-real-token", "Newpass1!")
    assert ok is False


@pytest.mark.asyncio
async def test_reset_password_accepts_valid_token():
    db = FakeDb()
    users = FakeUsers()
    service = PasswordResetService(db, users, hash_password=lambda p: f"h:{p}")
    raw = "valid-token-value-123456"
    db["password_reset_tokens"].docs.append({
        "_id": "t1",
        "user_id": "u1",
        "token_hash": _hash_token(raw),
        "used_at": None,
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
    })
    ok = await service.reset_password(raw, "Newpass1!")
    assert ok is True
    assert users.users["u1"]["hashed_password"] == "h:Newpass1!"
