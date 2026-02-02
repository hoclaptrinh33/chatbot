"""
User Repository - Data access layer cho users collection
"""
from app.repositories.base_repository import BaseRepository
from app.models.database import Collections
from typing import Optional, List
from datetime import datetime


class UserRepository(BaseRepository):
    """Repository cho User operations"""
    
    def __init__(self, db):
        super().__init__(db, Collections.USERS)
    
    async def create_user(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
        role: str = "student"
    ) -> dict:
        """
        Tạo user mới
        
        Args:
            email: Email
            hashed_password: Password đã hash
            full_name: Tên đầy đủ
            role: Vai trò (admin/user)
            
        Returns:
            User document
        """
        doc = {
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "role": role,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        doc_id = await self.insert_one(doc)
        doc["id"] = doc_id
        return doc
    
    async def get_by_id(self, user_id: str) -> Optional[dict]:
        """
        Lấy user theo ID
        
        Args:
            user_id: User ID
            
        Returns:
            User document hoặc None
        """
        oid = self.to_object_id(user_id)
        if not oid:
            return None
        doc = await self.find_one({"_id": oid})
        return self.serialize_doc(doc)
    
    async def get_by_email(self, email: str) -> Optional[dict]:
        """
        Lấy user theo email
        
        Args:
            email: Email
            
        Returns:
            User document hoặc None
        """
        doc = await self.find_one({"email": email})
        return self.serialize_doc(doc)
    
    async def email_exists(self, email: str) -> bool:
        """
        Kiểm tra email đã tồn tại chưa
        
        Args:
            email: Email
            
        Returns:
            True nếu email đã tồn tại
        """
        count = await self.count({"email": email})
        return count > 0
    
    async def update_user(self, user_id: str, update_data: dict) -> bool:
        """
        Update user
        
        Args:
            user_id: User ID
            update_data: Data cần update
            
        Returns:
            True nếu update thành công
        """
        oid = self.to_object_id(user_id)
        if not oid:
            return False
        
        update_data["updated_at"] = datetime.utcnow()
        return await self.update_one({"_id": oid}, update_data)
    
    async def get_all_users(self, limit: int = 100) -> List[dict]:
        """
        Lấy danh sách tất cả users
        
        Args:
            limit: Giới hạn số lượng
            
        Returns:
            List of users
        """
        docs = await self.find_many({}, limit=limit)
        return self.serialize_docs(docs)
    async def delete_user(self, user_id: str) -> bool:
        """
        Xóa user theo ID
        
        Args:
            user_id: User ID
            
        Returns:
            True nếu xóa thành công
        """
        oid = self.to_object_id(user_id)
        if not oid:
            return False
        return await self.delete_one({"_id": oid})
