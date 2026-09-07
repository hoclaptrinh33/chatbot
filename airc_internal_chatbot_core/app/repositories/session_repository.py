"""
Session Repository - Data Access Layer cho Chat Sessions & History
Xử lý các thao tác database liên quan đến phiên chat và lịch sử tin nhắn.
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from bson import ObjectId
from app.repositories.base_repository import BaseRepository
from app.models.database import Collections
import logging

logger = logging.getLogger(__name__)

class SessionRepository(BaseRepository):
    """
    Repository quản lý Sessions và Messages.
    Inherits BaseRepository for Session operations.
    Manages Message collection separately.
    """
    
    def __init__(self, db):
        super().__init__(db, Collections.SESSIONS)
        self.message_collection = db[Collections.MESSAGES]
        
    # ==================== Session Operations ====================
    # (Inherits basic CRUD from BaseRepository: find_one, insert_one, delete_one, etc.)
        
    async def create_session(self, user_id: str, name: str, parent_id: Optional[str] = None, branch_message_index: Optional[int] = None) -> dict:
        """Tạo phiên chat mới"""
        doc = {
            "user_id": user_id,
            "name": name,
            "parent_id": parent_id,
            "branch_message_index": branch_message_index,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        # Use BaseRepository's insert_one
        session_id = await self.insert_one(doc)
        doc["id"] = session_id
        return doc

    async def get_user_sessions(self, user_id: str, limit: int = 50, skip: int = 0) -> List[dict]:
        """Lấy danh sách sessions của user"""
        docs = await self.find_many(
            filter_dict={"user_id": user_id},
            limit=limit,
            skip=skip,
            sort=[("updated_at", -1)]
        )
        return self.serialize_docs(docs)

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Lấy detail session"""
        oid = self.to_object_id(session_id)
        if not oid:
            return None
        doc = await self.find_one({"_id": oid})
        return self.serialize_doc(doc)

    async def update_session(self, session_id: str, update_data: dict) -> Optional[dict]:
        """Update session info"""
        oid = self.to_object_id(session_id)
        if not oid:
            return None
        
        # Ensure updated_at is set
        update_data["updated_at"] = datetime.utcnow()
        
        success = await self.update_one(
            {"_id": oid},
            update_data
        )
        if success:
            return await self.get_session(session_id)
        return None

    async def delete_session(self, session_id: str) -> bool:
        """Xóa session và messages liên quan"""
        oid = self.to_object_id(session_id)
        if not oid:
            return False
            
        # 1. Delete session
        deleted = await self.delete_one({"_id": oid})
        
        # 2. Delete messages if session deleted
        if deleted:
            await self.message_collection.delete_many({"session_id": session_id})
            return True
        return False

    # ==================== Message Operations ====================

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Lưu tin nhắn mới. extra có thể chứa sources, latency_ms, feedback."""
        doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow()
        }
        if extra:
            doc.update({k: v for k, v in extra.items() if v is not None})
        result = await self.message_collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        
        # Update session timestamp
        oid = self.to_object_id(session_id)
        if oid:
            await self.collection.update_one(
                {"_id": oid},
                {"$set": {"updated_at": datetime.utcnow()}}
            )
            
        return doc

    async def get_messages(self, session_id: str, limit: int = 100) -> List[dict]:
        """Lấy lịch sử tin nhắn"""
        cursor = self.message_collection.find({"session_id": session_id}).sort("created_at", 1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return self.serialize_docs(docs)

    async def get_message(self, message_id: str) -> Optional[dict]:
        oid = self.to_object_id(message_id)
        if not oid:
            return None
        doc = await self.message_collection.find_one({"_id": oid})
        return self.serialize_doc(doc) if doc else None

    async def set_message_feedback(
        self,
        message_id: str,
        rating: str,
        comment: Optional[str] = None,
    ) -> bool:
        oid = self.to_object_id(message_id)
        if not oid:
            return False
        update = {"feedback": rating, "feedback_at": datetime.utcnow()}
        if comment is not None:
            update["feedback_comment"] = comment
        result = await self.message_collection.update_one(
            {"_id": oid, "role": "assistant"},
            {"$set": update},
        )
        return result.matched_count > 0

    async def get_recent_user_questions(self, user_id: str, limit: int = 8) -> List[str]:
        sessions = await self.get_user_sessions(user_id, limit=20)
        session_ids = [s["id"] for s in sessions]
        if not session_ids:
            return []
        cursor = self.message_collection.find(
            {"session_id": {"$in": session_ids}, "role": "user"},
            {"content": 1},
        ).sort("created_at", -1).limit(40)
        docs = await cursor.to_list(length=40)
        seen = set()
        questions = []
        for doc in docs:
            text = (doc.get("content") or "").strip()
            key = text.lower()
            if len(text) < 8 or key in seen:
                continue
            seen.add(key)
            questions.append(text)
            if len(questions) >= limit:
                break
        return questions

    async def get_feedback_counts(self) -> Dict[str, int]:
        pipeline = [
            {"$match": {"role": "assistant", "feedback": {"$in": ["up", "down"]}}},
            {"$group": {"_id": "$feedback", "count": {"$sum": 1}}},
        ]
        counts = {"up": 0, "down": 0}
        async for row in self.message_collection.aggregate(pipeline):
            if row["_id"] in counts:
                counts[row["_id"]] = row["count"]
        return counts

    async def get_average_latency_ms(self, sample_limit: int = 200) -> Optional[float]:
        cursor = self.message_collection.find(
            {"role": "assistant", "latency_ms": {"$gt": 0}},
            {"latency_ms": 1},
        ).sort("created_at", -1).limit(sample_limit)
        docs = await cursor.to_list(length=sample_limit)
        values = [d.get("latency_ms") for d in docs if isinstance(d.get("latency_ms"), (int, float))]
        if not values:
            return None
        return sum(values) / len(values)
