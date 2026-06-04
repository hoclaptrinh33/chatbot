"""
Chatbot Controller - API endpoints cho chatbot configuration
**ADMIN ONLY CREATE PERMISSION**
"""
from fastapi import APIRouter, Depends, HTTPException
from app.models.chatbot_schemas import (
    ChatbotCreate,
    ChatbotUpdate,
    ChatbotResponse,
    ChatbotAssignDatasetsRequest
)
from app.models.schemas import SuccessResponse
from app.services.chatbot_service import ChatbotService
from app.api.dependencies import get_chatbot_service, get_current_user
from app.models.auth import User
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=ChatbotResponse, status_code=201)
async def create_chatbot(
    payload: ChatbotCreate,
    current_user: User = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Tạo chatbot mới - ADMIN ONLY
    
    Permission: Admin only
    """
    try:
        chatbot = await chatbot_service.create_chatbot(
            creator_id=current_user.user_id,
            creator_role=current_user.role,
            data=payload
        )
        return ChatbotResponse(**chatbot)
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating chatbot")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[ChatbotResponse])
async def list_chatbots(
    current_user: User = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Lấy danh sách chatbots available theo user/phòng ban.
    
    - Admin: see all chatbots
    - Non-admin: see chatbots theo allow-list user_id hoặc department
    """
    try:
        chatbots = await chatbot_service.get_available_chatbots(
            user_id=current_user.user_id,
            user_role=current_user.role,
            user_department=current_user.department
        )
        return [ChatbotResponse(**cb) for cb in chatbots]
    
    except Exception as e:
        logger.exception("Error listing chatbots")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chatbot_id}", response_model=ChatbotResponse)
async def get_chatbot(
    chatbot_id: str,
    current_user: User = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """Lấy chatbot detail (permission check theo user/phòng ban)."""
    try:
        chatbot = await chatbot_service.get_chatbot(
            chatbot_id=chatbot_id,
            user_role=current_user.role,
            user_id=current_user.user_id,
            user_department=current_user.department
        )
        
        if not chatbot:
            raise HTTPException(status_code=404, detail="Chatbot not found")
        
        return ChatbotResponse(**chatbot)
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting chatbot")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{chatbot_id}", response_model=ChatbotResponse)
async def update_chatbot(
    chatbot_id: str,
    payload: ChatbotUpdate,
    current_user: User = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Cập nhật chatbot - Owner hoặc Admin
    """
    try:
        chatbot = await chatbot_service.update_chatbot(
            chatbot_id=chatbot_id,
            user_id=current_user.user_id,
            user_role=current_user.role,
            data=payload
        )
        
        if not chatbot:
            raise HTTPException(status_code=404, detail="Chatbot not found")
        
        return ChatbotResponse(**chatbot)
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating chatbot")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chatbot_id}", response_model=SuccessResponse)
async def delete_chatbot(
    chatbot_id: str,
    current_user: User = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Xóa chatbot - Owner hoặc Admin
    """
    try:
        success = await chatbot_service.delete_chatbot(
            chatbot_id=chatbot_id,
            user_id=current_user.user_id,
            user_role=current_user.role
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Chatbot not found")
        
        return SuccessResponse(
            status="success",
            message=f"Chatbot {chatbot_id} deleted successfully"
        )
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting chatbot")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chatbot_id}/datasets", response_model=ChatbotResponse)
async def assign_datasets(
    chatbot_id: str,
    payload: ChatbotAssignDatasetsRequest,
    current_user: User = Depends(get_current_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Gán datasets cho chatbot - Owner hoặc Admin
    """
    try:
        chatbot = await chatbot_service.assign_datasets(
            chatbot_id=chatbot_id,
            dataset_ids=payload.dataset_ids,
            user_id=current_user.user_id,
            user_role=current_user.role
        )
        
        return ChatbotResponse(**chatbot)
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error assigning datasets")
        raise HTTPException(status_code=500, detail=str(e))
