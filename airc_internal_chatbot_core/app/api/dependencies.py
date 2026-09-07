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


from app.models.auth import User, UserRole, Permission, user_has_permission
from typing import Callable, Annotated, Optional

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
    Strict role→permission check. Admin always passes.
    Other roles must have the permission in ROLE_PERMISSIONS.
    """
    async def check_permission(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if user_has_permission(current_user, permission):
            return current_user

        logger.warning(
            "Permission denied: user=%s role=%s tried=%s",
            current_user.email,
            current_user.role,
            permission,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission.value}",
        )
    return check_permission


async def get_bearer_token(authorization: Optional[str] = Header(None, alias="Authorization")) -> str:
    """Raw JWT for service-to-service forwarding (e.g. Core → Auth)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1]



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
    chatbot_repo = Depends(get_chatbot_repo),
    file_repo: FileRepository = Depends(get_file_repo),
) -> ChatService:
    """Inject ChatService with all dependencies"""
    return ChatService(
        dataset_repo, dataset_file_repo, chunk_repo,
        session_repo, chatbot_repo, file_repo,
    )


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
