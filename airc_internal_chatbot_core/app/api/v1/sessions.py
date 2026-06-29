from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.api import dependencies
from app.api.dependencies import get_current_user
from app.models.schemas import ChatSessionResponse as ChatSession, ChatSessionCreate, ChatSessionUpdate, ChatMessageResponse, ChatMessageCreate
from app.repositories.session_repository import SessionRepository
from app.models.auth import User

router = APIRouter()

@router.post("/", response_model=ChatSession, status_code=status.HTTP_200_OK)
async def create_session(
    session_in: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(dependencies.get_session_repo)
):
    return await session_repo.create_session(
        current_user.id,
        session_in.name,
        session_in.parent_id,
        session_in.branch_message_index
    )

@router.get("/", response_model=List[ChatSession], status_code=status.HTTP_200_OK)
async def get_user_sessions(
    limit: int = 50,
    skip: int = 0,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(dependencies.get_session_repo)
):
    """
    List all chat sessions for the current user.
    """
    return await session_repo.get_user_sessions(current_user.id, limit=limit, skip=skip)

@router.get("/{session_id}", response_model=ChatSession, status_code=status.HTTP_200_OK)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(dependencies.get_session_repo)
):
    """
    Get a specific chat session.
    """
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    return session

@router.patch("/{session_id}", response_model=ChatSession, status_code=status.HTTP_200_OK)
async def update_session(
    session_id: str,
    session_update: ChatSessionUpdate,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(dependencies.get_session_repo)
):
    """
    Update a chat session (e.g. rename).
    """
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this session")
    
    updated_session = await session_repo.update_session(session_id, session_update.dict(exclude_unset=True))
    if not updated_session:
         raise HTTPException(status_code=404, detail="Session not found after update")
    return updated_session

@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(dependencies.get_session_repo)
):
    """
    Delete a chat session.
    """
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this session")
    
    success = await session_repo.delete_session(session_id)
    if not success:
         raise HTTPException(status_code=500, detail="Failed to delete session")
    return {"message": "Session deleted successfully"}

@router.get("/{session_id}/messages", response_model=List[ChatMessageResponse], status_code=status.HTTP_200_OK)
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(dependencies.get_session_repo)
):
    """
    Get messages history for a session.
    """
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access messages of this session")
    
    return await session_repo.get_messages(session_id, limit=limit)


@router.post("/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    session_id: str,
    message_in: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(dependencies.get_session_repo)
):
    """
    Add a message to the session history.
    """
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Allow user to add message (user or bot role if implementing client-side orchestration)
    # Ideally should validate user permissions
    if session["user_id"] != current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized")

    return await session_repo.add_message(session_id, message_in.role, message_in.content)
