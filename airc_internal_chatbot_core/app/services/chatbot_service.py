"""
Chatbot Service - Business logic cho Chatbot management
** ADMIN ONLY create permission **
"""
from app.repositories.chatbot_repository import ChatbotRepository
from app.repositories.dataset_repository import DatasetRepository
from app.models.chatbot_schemas import ChatbotCreate, ChatbotUpdate
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ChatbotService:
    """Service layer cho chatbot operations với RBAC"""
    
    def __init__(
        self,
        chatbot_repo: ChatbotRepository,
        dataset_repo: DatasetRepository
    ):
        self.chatbot_repo = chatbot_repo
        self.dataset_repo = dataset_repo
    
    async def create_chatbot(
        self,
        creator_id: str,
        creator_role: str,
        data: ChatbotCreate
    ) -> dict:
        """
        Tạo chatbot mới - ADMIN ONLY
        
        Args:
            creator_id: User ID của người tạo
            creator_role: Role của người tạo
            data: ChatbotCreate schema
            
        Raises:
            PermissionError: Nếu role không phải admin
            ValueError: Nếu dataset không tồn tại
        """
        # CRITICAL: Chỉ ADMIN được tạo chatbot
        if creator_role != "admin":
            raise PermissionError("Only admin can create chatbots")
        
        # Validate datasets exist
        for dataset_id in data.dataset_ids:
            dataset = await self.dataset_repo.get_by_id(dataset_id)
            if not dataset:
                raise ValueError(f"Dataset not found: {dataset_id}")
        
        # Convert config to dict
        config_dict = data.config.model_dump() if data.config else {}
        
        # Create chatbot
        chatbot = await self.chatbot_repo.create_chatbot(
            name=data.name,
            description=data.description,
            icon=data.icon,
            config=config_dict,
            dataset_ids=data.dataset_ids,
            allowed_roles=data.allowed_roles,
            visibility=data.visibility,
            owner_id=creator_id
        )
        
        logger.info(f"[CHATBOT] Created chatbot={chatbot['id']} by admin={creator_id}")
        return chatbot
    
    async def get_available_chatbots(
        self,
        user_id: str,
        user_role: str
    ) -> List[dict]:
        """
        Lấy chatbots available cho user dựa trên role (RBAC filtering)
        
        Logic:
        - Admin: Thấy tất cả chatbots
        - Teacher/Student: Chỉ thấy chatbots có allowed_roles chứa role của họ
        
        Args:
            user_id: User ID
            user_role: User role (admin, teacher, student)
        """
        # Admin sees all chatbots
        if user_role == "admin":
            chatbots = await self.chatbot_repo.get_all(is_active=True)
        else:
            # Non-admin: Lấy chatbots mà role được phép
            chatbots = await self.chatbot_repo.get_available_for_role(role=user_role)
        
        # ✅ SYNC FIX: Normalize dataset_ids to ensure UI gets consistent array
        for chatbot in chatbots:
            if "dataset_ids" not in chatbot or chatbot["dataset_ids"] is None:
                chatbot["dataset_ids"] = []
        
        return chatbots
    
    async def get_chatbot(
        self,
        chatbot_id: str,
        user_role: str,
        user_id: str
    ) -> Optional[dict]:
        """
        Lấy chatbot detail - check permission
        
        Logic:
        - Admin: xem tất cả
        - Others: chỉ xem chatbot mà họ có quyền access
        """
        chatbot = await self.chatbot_repo.get_by_id(chatbot_id)
        if not chatbot:
            return None
        
        # ✅ SYNC FIX: Normalize dataset_ids
        if "dataset_ids" not in chatbot or chatbot["dataset_ids"] is None:
            chatbot["dataset_ids"] = []
        
        # Admin bypass
        if user_role == "admin":
            return chatbot
        
        # Check RBAC - chỉ theo role
        if user_role not in chatbot.get("allowed_roles", []):
            raise PermissionError("You don't have permission to view this chatbot")
        
        return chatbot
    
    async def update_chatbot(
        self,
        chatbot_id: str,
        user_id: str,
        user_role: str,
        data: ChatbotUpdate
    ) -> Optional[dict]:
        """
        Cập nhật chatbot - Owner hoặc Admin
        """
        chatbot = await self.chatbot_repo.get_by_id(chatbot_id)
        if not chatbot:
            return None
        
        # Permission check: Owner or Admin
        is_owner = chatbot["owner_id"] == user_id
        is_admin = user_role == "admin"
        
        if not (is_owner or is_admin):
            raise PermissionError("Only chatbot owner or admin can update")
        
        # Validate datasets if updating
        if data.dataset_ids is not None:
            for dataset_id in data.dataset_ids:
                dataset = await self.dataset_repo.get_by_id(dataset_id)
                if not dataset:
                    raise ValueError(f"Dataset not found: {dataset_id}")
        
        # Build update dict (exclude None values)
        update_data = data.model_dump(exclude_none=True)
        
        # Convert config if present (already a dict from model_dump above)
        # if "config" in update_data and update_data["config"]:
        #     # update_data["config"] is already a dict because data.model_dump() captures it
        #     pass
        
        # Update
        await self.chatbot_repo.update_chatbot(chatbot_id, update_data)
        
        # Return updated chatbot
        return await self.chatbot_repo.get_by_id(chatbot_id)
    
    async def delete_chatbot(
        self,
        chatbot_id: str,
        user_id: str,
        user_role: str
    ) -> bool:
        """
        Xóa chatbot - Owner hoặc Admin only
        """
        chatbot = await self.chatbot_repo.get_by_id(chatbot_id)
        if not chatbot:
            return False
        
        # Permission check
        is_owner = chatbot["owner_id"] == user_id
        is_admin = user_role == "admin"
        
        if not (is_owner or is_admin):
            raise PermissionError("Only chatbot owner or admin can delete")
        
        return await self.chatbot_repo.delete_chatbot(chatbot_id)
    
    async def assign_datasets(
        self,
        chatbot_id: str,
        dataset_ids: List[str],
        user_id: str,
        user_role: str
    ) -> dict:
        """
        Gán datasets cho chatbot - Owner/Admin
        """
        chatbot = await self.chatbot_repo.get_by_id(chatbot_id)
        if not chatbot:
            raise ValueError("Chatbot not found")
        
        # Permission check
        is_owner = chatbot["owner_id"] == user_id
        is_admin = user_role == "admin"
        
        if not (is_owner or is_admin):
            raise PermissionError("Only chatbot owner or admin can assign datasets")
        
        # Validate all datasets exist
        for dataset_id in dataset_ids:
            dataset = await self.dataset_repo.get_by_id(dataset_id)
            if not dataset:
                raise ValueError(f"Dataset not found: {dataset_id}")
        
        # Update
        await self.chatbot_repo.assign_datasets(chatbot_id, dataset_ids)
        
        # Return updated chatbot
        return await self.chatbot_repo.get_by_id(chatbot_id)

    async def get_roles_with_chatbot_assigned(
        self,
        exclude_chatbot_id: Optional[str] = None
    ) -> List[str]:
        """
        Lấy danh sách roles đã được assign chatbot
        
        Args:
            exclude_chatbot_id: Loại trừ chatbot này (dùng khi update)
            
        Returns:
            List roles đã có chatbot (trừ admin vì admin được nhiều)
        """
        return await self.chatbot_repo.get_roles_with_chatbot_assigned(exclude_chatbot_id)
