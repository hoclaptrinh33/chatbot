"""
Dataset File Repository - Data access cho dataset_files (join table)
"""
from app.repositories.base_repository import BaseRepository
from app.models.database import Collections
from app.models.enums import DatasetFileStatus
from datetime import datetime
from typing import Optional, List


class DatasetFileRepository(BaseRepository):
    """Repository cho DatasetFile operations"""
    
    def __init__(self, db):
        super().__init__(db, Collections.DATASET_FILES)
    
    async def create_dataset_file(
        self, 
        dataset_id: str, 
        file_id: str
    ) -> dict:
        """Tạo dataset file mới"""
        doc = {
            "dataset_id": dataset_id,
            "file_id": file_id,
            "status": DatasetFileStatus.PENDING.value,
            "chunk_count": 0,
            "is_enabled": True,
            "created_at": datetime.utcnow()
        }
        doc_id = await self.insert_one(doc)
        doc["id"] = str(doc_id)
        del doc["_id"]  # Remove ObjectId to make dict JSON serializable
        return doc
    
    async def get_by_id(self, dataset_file_id: str) -> Optional[dict]:
        """Lấy dataset file theo ID"""
        oid = self.to_object_id(dataset_file_id)
        if not oid:
            return None
        doc = await self.find_one({"_id": oid})
        return self.serialize_doc(doc)
    
    async def get_by_dataset(self, dataset_id: str) -> List[dict]:
        """Lấy tất cả files trong dataset"""
        docs = await self.find_many({"dataset_id": dataset_id})
        return self.serialize_docs(docs)
    
    async def get_enabled_by_dataset(self, dataset_id: str) -> List[dict]:
        """Lấy các files enabled trong dataset"""
        docs = await self.find_many({
            "dataset_id": dataset_id,
            "is_enabled": True
        })
        return self.serialize_docs(docs)
    
    async def update_status(
        self, 
        dataset_file_id: str, 
        status: DatasetFileStatus,
        chunk_count: Optional[int] = None
    ) -> bool:
        """Cập nhật trạng thái dataset file"""
        oid = self.to_object_id(dataset_file_id)
        if not oid:
            return False
        
        update_data = {
            "status": status.value,
            "processed_at": datetime.utcnow()
        }
        if chunk_count is not None:
            update_data["chunk_count"] = chunk_count
        
        return await self.update_one({"_id": oid}, update_data)
    
    async def set_enabled(self, dataset_file_id: str, is_enabled: bool) -> bool:
        """Bật/tắt dataset file"""
        oid = self.to_object_id(dataset_file_id)
        if not oid:
            return False
        return await self.update_one({"_id": oid}, {"is_enabled": is_enabled})
    
    async def delete_by_id(self, dataset_file_id: str) -> bool:
        """Xóa dataset file"""
        oid = self.to_object_id(dataset_file_id)
        if not oid:
            return False
        return await self.delete_one({"_id": oid})
    
    async def delete_by_dataset(self, dataset_id: str) -> int:
        """Xóa tất cả dataset files của dataset"""
        return await self.delete_many({"dataset_id": dataset_id})
