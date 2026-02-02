"""
File Repository - Data access cho files
"""
from app.repositories.base_repository import BaseRepository
from app.models.database import Collections
from app.models.enums import FileStatus
from datetime import datetime
from typing import Optional, List


class FileRepository(BaseRepository):
    """Repository cho File operations"""
    
    def __init__(self, db):
        super().__init__(db, Collections.FILES)
    
    async def create_file(
        self, 
        name: str, 
        size: int, 
        mime_type: str,
        path: str,
        status: FileStatus = FileStatus.PENDING
    ) -> dict:
        """Tạo file mới"""
        doc = {
            "name": name,
            "size": size,
            "mime_type": mime_type,
            "path": path,
            "status": status.value,
            "uploaded_at": datetime.utcnow()
        }
        doc_id = await self.insert_one(doc)
        doc["id"] = doc_id
        return doc
    
    async def get_by_id(self, file_id: str) -> Optional[dict]:
        """Lấy file theo ID"""
        oid = self.to_object_id(file_id)
        if not oid:
            return None
        doc = await self.find_one({"_id": oid})
        return self.serialize_doc(doc)
    
    async def get_by_ids(self, file_ids: List[str]) -> List[dict]:
        """Lấy nhiều files theo IDs"""
        oids = [self.to_object_id(fid) for fid in file_ids]
        oids = [oid for oid in oids if oid]
        docs = await self.find_many({"_id": {"$in": oids}})
        return self.serialize_docs(docs)
    
    async def update_status(
        self, 
        file_id: str, 
        status: FileStatus,
        error: Optional[str] = None
    ) -> bool:
        """Cập nhật trạng thái file"""
        oid = self.to_object_id(file_id)
        if not oid:
            return False
        
        update_data = {
            "status": status.value,
            "processed_at": datetime.utcnow()
        }
        if error:
            update_data["error"] = error
        
        return await self.update_one({"_id": oid}, update_data)
    
    async def get_ready_files(self) -> List[dict]:
        """Lấy các files đã ready"""
        docs = await self.find_many({"status": FileStatus.READY.value})
        return self.serialize_docs(docs)

    async def get_all(self) -> List[dict]:
        """Lấy tất cả files"""
        docs = await self.find_many({}, sort=[("uploaded_at", -1)])
        return self.serialize_docs(docs)

    async def get_all(self) -> List[dict]:
        """Lấy tất cả files"""
        docs = await self.find_many({}, sort=[("uploaded_at", -1)])
        return self.serialize_docs(docs)
