"""
Chat Controller - API endpoints cho RAG chatbot
"""
from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.models.auth import User, Permission
from app.services import ChatService
from app.api.dependencies import get_chat_service, get_current_user, require_permission
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    current_user: User = Depends(require_permission(Permission.CHAT_USE)),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    RAG Chatbot endpoint
    
    - **question**: Câu hỏi của user
    - **dataset_ids**: List của dataset IDs để search (optional)
    - **history**: Chat history (optional)
    """
    try:
        # DEBUG: Log incoming request
        logger.info(f"[CHAT API] Request received - question: '{request.question[:50]}...', chatbot_id: {request.chatbot_id}, dataset_ids: {request.dataset_ids}, user: {current_user.user_id}")
        
        # Convert history từ Pydantic models
        history = None
        if request.history:
            history = [msg.dict() for msg in request.history]
        
        # Build User Context for RBAC
        # CRITICAL FIX: Normalize role to lowercase string (e.g., "admin", "teacher", "student")
        # Extract from UserRole enum safely
        if hasattr(current_user.role, "value"):
            role_str = current_user.role.value.lower()
        else:
            role_str = str(current_user.role).lower()
            # Handle case where str(enum) returns "UserRole.ADMIN"
            if "." in role_str:
                role_str = role_str.split(".")[-1]
        
        user_ctx = {
            "role": role_str, 
            "id": current_user.user_id
        }

        result = await chat_service.ask_question(
            question=request.question,
            dataset_ids=request.dataset_ids,
            history=history,
            session_id=request.session_id,
            chatbot_id=request.chatbot_id,
            user_context=user_ctx
        )
        
        return ChatResponse(
            status="success",
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            errors=result.get("errors", []),
            debug=result.get("debug")  # RAG performance metrics
        )
    
    except PermissionError as pe:
        logger.warning(f"Permission Denied: {pe}")
        raise HTTPException(
            status_code=403,
            detail=str(pe)
        )

    except Exception as e:
        logger.exception("Error in ask endpoint")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(e)}"
        )
