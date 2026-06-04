"""
Chatbot Repository - Data access layer cho chatbots
Handles CRUD operations và access filtering theo user/phòng ban
"""
from app.repositories.base_repository import BaseRepository
from app.models.database import Collections
from datetime import datetime
from typing import Optional, List, Dict, Any


class ChatbotRepository(BaseRepository):
    """Repository cho Chatbot operations và access policy theo user/phòng ban."""
    
    def __init__(self, db):
        super().__init__(db, Collections.CHATBOTS)
    
    async def create_chatbot(
        self,
        name: str,
        description: Optional[str],
        icon: Optional[str],
        config: Dict[str, Any],
        dataset_ids: List[str],
        allowed_roles: List[str],
        allowed_user_ids: List[str],
        allowed_departments: List[str],
        visibility: str,
        owner_id: str
    ) -> dict:
        """
        Tạo chatbot mới (ADMIN ONLY)
        
        Args:
            name: Tên chatbot
            description: Mô tả
            config: Cấu hình {model, temperature, system_prompt, max_tokens}
            dataset_ids: Danh sách dataset IDs
            allowed_roles: Legacy roles field để tương thích dữ liệu cũ
            visibility: "public", "private"
            owner_id: User ID của người tạo (Admin)
        """
        doc = {
            "name": name,
            "description": description,
            "icon": icon,
            "config": config,
            "dataset_ids": dataset_ids,
            "allowed_roles": allowed_roles,
            "allowed_user_ids": allowed_user_ids,
            "allowed_departments": allowed_departments,
            "visibility": visibility,
            "owner_id": owner_id,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        
        doc_id = await self.insert_one(doc)
        doc["id"] = str(doc_id)
        return self.serialize_doc(doc)
    
    async def get_by_id(self, chatbot_id: str) -> Optional[dict]:
        """Lấy chatbot theo ID"""
        oid = self.to_object_id(chatbot_id)
        if not oid:
            return None
        doc = await self.find_one({"_id": oid})
        return self.serialize_doc(doc)
    
    async def get_by_owner(self, owner_id: str) -> List[dict]:
        """Lấy tất cả chatbots của owner"""
        docs = await self.find_many(
            {"owner_id": owner_id},
            sort=[("created_at", -1)]
        )
        return self.serialize_docs(docs)
    
    async def get_available_for_user(
        self,
        user_id: str,
        department: Optional[str] = None
    ) -> List[dict]:
        """
        Lấy chatbots available cho user cụ thể.

        Access policy:
        - allowed_user_ids chứa user_id
        - HOẶC allowed_departments chứa department
        - Nếu cả 2 rỗng thì chatbot private (non-admin không truy cập)
        """
        access_conditions: List[Dict[str, Any]] = [
            {"allowed_user_ids": user_id}
        ]

        normalized_department = (department or "").strip()
        if normalized_department:
            access_conditions.append({"allowed_departments": normalized_department})

        query = {
            "is_active": True,
            "$or": access_conditions,
        }

        docs = await self.find_many(query, sort=[("created_at", -1)])
        return self.serialize_docs(docs)
    
    async def get_all(
        self,
        is_active: Optional[bool] = None
    ) -> List[dict]:
        """Lấy tất cả chatbots (Admin only)"""
        query = {}
        if is_active is not None:
            query["is_active"] = is_active
        
        docs = await self.find_many(query, sort=[("created_at", -1)])
        return self.serialize_docs(docs)
    
    async def update_chatbot(
        self,
        chatbot_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Cập nhật chatbot"""
        oid = self.to_object_id(chatbot_id)
        if not oid:
            return False
        
        # Add updated_at timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        return await self.update_one({"_id": oid}, update_data)
    
    async def assign_datasets(
        self,
        chatbot_id: str,
        dataset_ids: List[str]
    ) -> bool:
        """Gán datasets cho chatbot"""
        return await self.update_chatbot(chatbot_id, {"dataset_ids": dataset_ids})
    
    async def delete_chatbot(self, chatbot_id: str) -> bool:
        """Xóa chatbot"""
        oid = self.to_object_id(chatbot_id)
        if not oid:
            return False
        return await self.delete_one({"_id": oid})
    
    async def set_active(self, chatbot_id: str, is_active: bool) -> bool:
        """Bật/tắt chatbot"""
        return await self.update_chatbot(chatbot_id, {"is_active": is_active})
