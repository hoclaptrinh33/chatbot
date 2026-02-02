"""
Chatbot Repository - Data access layer cho chatbots
Handles CRUD operations và RBAC filtering
"""
from app.repositories.base_repository import BaseRepository
from app.models.database import Collections
from datetime import datetime
from typing import Optional, List, Dict, Any


class ChatbotRepository(BaseRepository):
    """Repository cho Chatbot operations với RBAC"""
    
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
            allowed_roles: Roles được phép sử dụng
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
    
    async def get_available_for_role(
        self,
        role: str
    ) -> List[dict]:
        """
        Lấy chatbots available cho role (RBAC filtering)
        
        Logic:
        - allowed_roles phải chứa role của user
        - is_active = True
        """
        query = {
            "is_active": True,
            "allowed_roles": role  # MongoDB tự kiểm tra role trong array
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

    async def get_roles_with_chatbot_assigned(self, exclude_chatbot_id: Optional[str] = None) -> List[str]:
        """
        Lấy danh sách roles đã được gán chatbot
        
        Logic: Mỗi role (student, teacher) chỉ được gán 1 chatbot.
        Admin là ngoại lệ - có thể dùng nhiều chatbot.
        
        Args:
            exclude_chatbot_id: Loại trừ chatbot này (dùng khi update)
            
        Returns:
            List roles đã có chatbot (trừ admin)
        """
        query = {
            "allowed_roles": {"$exists": True, "$ne": []},
            "is_active": True
        }
        
        if exclude_chatbot_id:
            oid = self.to_object_id(exclude_chatbot_id)
            if oid:
                query["_id"] = {"$ne": oid}
        
        docs = await self.find_many(query)
        
        # Collect all roles from all chatbots (exclude admin)
        roles = set()
        for doc in docs:
            allowed_roles = doc.get("allowed_roles", [])
            if allowed_roles:
                # Admin có thể dùng nhiều chatbot nên không count
                for role in allowed_roles:
                    if role.lower() != "admin":
                        roles.add(role.lower())
        
        return list(roles)
