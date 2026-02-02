"""
Base Repository - CRUD operations chung cho tất cả repositories
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
from bson import ObjectId
from bson.errors import InvalidId
import logging

logger = logging.getLogger(__name__)


class BaseRepository:
    """Repository base class với CRUD operations cơ bản"""
    
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.db = db
        self.collection = db[collection_name]
    
    async def find_one(self, filter_dict: dict) -> Optional[dict]:
        """Tìm một document"""
        return await self.collection.find_one(filter_dict)
    
    async def find_many(
        self, 
        filter_dict: dict, 
        skip: int = 0, 
        limit: int = 100,
        sort: Optional[List[tuple]] = None
    ) -> List[dict]:
        """Tìm nhiều documents"""
        cursor = self.collection.find(filter_dict).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        return await cursor.to_list(length=limit)
    
    async def count_documents(self, filter_dict: dict) -> int:
        """Đếm số documents"""
        return await self.collection.count_documents(filter_dict)
    
    async def insert_one(self, document: dict) -> str:
        """Tạo một document mới"""
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)
    
    async def update_one(self, filter_dict: dict, update_dict: dict) -> bool:
        """Cập nhật một document"""
        result = await self.collection.update_one(filter_dict, {"$set": update_dict})
        return result.matched_count > 0
    
    async def delete_one(self, filter_dict: dict) -> bool:
        """Xóa một document"""
        result = await self.collection.delete_one(filter_dict)
        return result.deleted_count > 0
    
    async def delete_many(self, filter_dict: dict) -> int:
        """Xóa nhiều documents"""
        result = await self.collection.delete_many(filter_dict)
        return result.deleted_count
    
    @staticmethod
    def to_object_id(id_str: str) -> Optional[ObjectId]:
        """Convert string ID sang ObjectId"""
        try:
            return ObjectId(id_str)
        except (InvalidId, TypeError):
            return None
    
    @staticmethod
    def serialize_doc(doc: Optional[dict]) -> Optional[dict]:
        """Serialize document: _id -> id"""
        if not doc:
            return None
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc
    
    @staticmethod
    def serialize_docs(docs: List[dict]) -> List[dict]:
        """Serialize list of documents"""
        return [BaseRepository.serialize_doc(d) for d in docs]
