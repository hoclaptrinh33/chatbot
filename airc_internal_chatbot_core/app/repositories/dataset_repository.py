"""
Dataset Repository - Data access cho datasets
"""
from app.repositories.base_repository import BaseRepository
from app.models.database import Collections
from datetime import datetime
from typing import Optional, List


class DatasetRepository(BaseRepository):
    """Repository cho Dataset operations"""
    
    def __init__(self, db):
        super().__init__(db, Collections.DATASETS)
    
    async def create_dataset(
        self,
        name: str,
        # config removed
        owner_id: str,
        visibility: str = "private"
    ) -> dict:
        """
        Tạo dataset mới
        
        Args:
            name: Tên dataset
            owner_id: ID của user tạo dataset
            visibility: private/public
        """
        doc = {
            "name": name,
            # "config": config, # Removed
            "owner_id": owner_id,
            "visibility": visibility,
            "shared_with": [],  # List of user IDs
            "created_at": datetime.utcnow()
        }
        doc_id = await self.insert_one(doc)
        doc["id"] = doc_id
        return doc
    
    async def get_by_id(self, dataset_id: str) -> Optional[dict]:
        """Lấy dataset theo ID"""
        oid = self.to_object_id(dataset_id)
        if not oid:
            return None
        doc = await self.find_one({"_id": oid})
        return self.serialize_doc(doc)
    
    async def get_all(self) -> List[dict]:
        """Lấy tất cả datasets"""
        docs = await self.find_many({})
        return self.serialize_docs(docs)
    
    async def get_by_owner(self, owner_id: str) -> List[dict]:
        """
        Lấy datasets của owner
        
        Args:
            owner_id: ID của owner
        """
        docs = await self.find_many({"owner_id": owner_id})
        return self.serialize_docs(docs)
    
    async def get_shared_with_user(self, user_id: str) -> List[dict]:
        """
        Lấy datasets được share với user
        
        Args:
            user_id: ID của user
        """
        docs = await self.find_many({"shared_with": user_id})
        return self.serialize_docs(docs)
    
    async def share_dataset(self, dataset_id: str, user_ids: List[str]) -> bool:
        """
        Share dataset với users
        
        Args:
            dataset_id: ID của dataset
            user_ids: List of user IDs to share with
        """
        oid = self.to_object_id(dataset_id)
        if not oid:
            return False
        
        result = await self.collection.update_one(
            {"_id": oid},
            {"$set": {"shared_with": user_ids}}
        )
        return result.matched_count > 0
    
    async def delete_dataset(self, dataset_id: str) -> bool:
        """Xóa dataset"""
        oid = self.to_object_id(dataset_id)
        if not oid:
            return False
        return await self.delete_one({"_id": oid})

    async def update_dataset(self, dataset_id: str, data: dict) -> Optional[dict]:
        """Cập nhật dataset"""
        oid = self.to_object_id(dataset_id)
        if not oid:
            return None
            
        result = await self.update_one({"_id": oid}, data)
        if result:
            return await self.get_by_id(dataset_id)
        return None
