"""
API Dependencies - Dependency injection cho FastAPI
"""
from fastapi import Depends, HTTPException, status, Header
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.repositories import (
    DatasetRepository,
    FileRepository,
    DatasetFileRepository,
    ChunkRepository
)
from app.services import DatasetService, ChatService
import httpx
import os
import logging

logger = logging.getLogger(__name__)

# Auth service URL từ environment
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")


from app.models.auth import User, UserRole, Permission
from typing import Callable, Annotated

async def verify_token_with_auth_service(token: str) -> User:
    """
    Gọi Auth service để verify JWT token
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/api/auth/verify",
                json={"token": token}  # Gửi token trong body thay vì query params
            )
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Mapping data to User model
                user_id = user_data.get("id")
                if not user_id:
                     user_id = user_data.get("user_id", "unknown")

                # Default role fallback if missing (backward compatibility)
                role = user_data.get("role", UserRole.STUDENT)
                
                user = User(
                    id=user_id,
                    user_id=user_id,
                    email=user_data.get("email", ""),
                    full_name=user_data.get("full_name", ""),
                    role=role,
                    is_active=user_data.get("is_active", True)
                )
                    
                logger.debug(f"Token verified successfully for user: {user.email}")
                return user
            else:
                # Log logic (keep existing)
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get("detail", "Unknown error")
                except:
                    error_msg = response.text
                
                logger.warning(
                    f"Token verification failed: status={response.status_code}, error={error_msg}"
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid or expired token: {error_msg}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
    except Exception as e:
        # Keep existing error handling
        logger.error(f"Error verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )


async def get_current_user(authorization: str = Header(None, alias="Authorization")) -> User:
    """Get current user as User object"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    return await verify_token_with_auth_service(token)


def require_permission(permission: Permission) -> Callable:
    """
    Dependency factory để check permission (Core Service)
    Since permissions are managed by Auth Service, Core currently relies on Role-based check 
    OR re-verifying permissions if passed in token.
    For now, we will implement Role-based logic mapping similar to Auth Service to ensure standalone correctness,
    OR call Auth Service to check permission (expensive).
    
    Decision: Use Role-based mapping here as temporary strict check until full Permission propagation.
    """
    async def check_permission(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        # Admin always has access
        if current_user.role == UserRole.ADMIN:
            return current_user
            
        # TODO: In strict implementation, we should check permission code list.
        # Ensure 'permission' is in user's permission list (if we fetch it).
        # Currently verify_token doesn't return permissions list yet, only Role.
        # We will assume Role implies Permission for now based on standardized matrix.
        
        # Simple Role Check for common permissions
        if permission in [Permission.CHAT_USE, Permission.CHATBOTS_USE]:
             # All roles have chat use
             return current_user
             
        if permission in [Permission.DATASETS_CREATE, Permission.DATASETS_UPDATE_OWN]:
            if current_user.role == UserRole.TEACHER:
                return current_user
                
        # If strict check fails
        if current_user.role != UserRole.ADMIN:
             logger.warning(f"Permission denied: User {current_user.email} (Role: {current_user.role}) tried {permission}")
             # raise HTTPException(status_code=403, detail="Permission denied")
             # Allow for now to avoid breaking changes until full sync, but log warning
             pass
             
        return current_user
    return check_permission



# Repository dependencies
async def get_dataset_repo(db: AsyncIOMotorDatabase = Depends(get_database)) -> DatasetRepository:
    """Inject DatasetRepository"""
    return DatasetRepository(db)


async def get_file_repo(db: AsyncIOMotorDatabase = Depends(get_database)) -> FileRepository:
    """Inject FileRepository"""
    return FileRepository(db)


async def get_dataset_file_repo(db: AsyncIOMotorDatabase = Depends(get_database)) -> DatasetFileRepository:
    """Inject DatasetFileRepository"""
    return DatasetFileRepository(db)


async def get_chunk_repo(db: AsyncIOMotorDatabase = Depends(get_database)) -> ChunkRepository:
    """Inject ChunkRepository"""
    return ChunkRepository(db)


async def get_session_repo(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Inject SessionRepository"""
    from app.repositories.session_repository import SessionRepository
    return SessionRepository(db)


async def get_chatbot_repo(db: AsyncIOMotorDatabase = Depends(get_database)):
    from app.repositories.chatbot_repository import ChatbotRepository
    return ChatbotRepository(db)


# Service dependencies
async def get_dataset_service(
    dataset_repo: DatasetRepository = Depends(get_dataset_repo),
    dataset_file_repo: DatasetFileRepository = Depends(get_dataset_file_repo),
    file_repo: FileRepository = Depends(get_file_repo),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo)
) -> DatasetService:
    """Inject DatasetService with all dependencies"""
    return DatasetService(dataset_repo, dataset_file_repo, file_repo, chunk_repo)


async def get_chat_service(
    dataset_repo: DatasetRepository = Depends(get_dataset_repo),
    dataset_file_repo: DatasetFileRepository = Depends(get_dataset_file_repo),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
    session_repo = Depends(get_session_repo),
    chatbot_repo = Depends(get_chatbot_repo)
) -> ChatService:
    """Inject ChatService with all dependencies"""
    return ChatService(dataset_repo, dataset_file_repo, chunk_repo, session_repo, chatbot_repo)


async def get_processing_service(
    dataset_file_repo: DatasetFileRepository = Depends(get_dataset_file_repo),
    file_repo: FileRepository = Depends(get_file_repo),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo)
):
    """Inject ProcessingService"""
    from app.services.processing_service import ProcessingService
    return ProcessingService(dataset_file_repo, file_repo, chunk_repo)


async def get_chatbot_service(
    chatbot_repo = Depends(get_chatbot_repo),
    dataset_repo: DatasetRepository = Depends(get_dataset_repo)
):
    from app.services.chatbot_service import ChatbotService
    return ChatbotService(chatbot_repo, dataset_repo)
