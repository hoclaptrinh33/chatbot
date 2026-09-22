"""
Chat Controller - API endpoints cho RAG chatbot
"""
import asyncio
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse, ChatFeedbackRequest, ChatFeedbackResponse
from app.models.auth import User, Permission
from app.services import ChatService
from app.api.dependencies import get_chat_service, require_permission, get_session_repo

logger = logging.getLogger(__name__)

router = APIRouter()


def _user_ctx(current_user: User) -> dict:
    if hasattr(current_user.role, "value"):
        role_str = current_user.role.value.lower()
    else:
        role_str = str(current_user.role).lower()
        if "." in role_str:
            role_str = role_str.split(".")[-1]
    return {"role": role_str, "id": current_user.user_id}


def _history_payload(request: ChatRequest):
    if not request.history:
        return None
    return [msg.dict() for msg in request.history]


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
        logger.info(
            "[CHAT API] Request received - question: '%s...', chatbot_id: %s, user: %s",
            request.question[:50],
            request.chatbot_id,
            current_user.user_id,
        )

        result = await chat_service.ask_question(
            question=request.question,
            dataset_ids=request.dataset_ids,
            history=_history_payload(request),
            session_id=request.session_id,
            chatbot_id=request.chatbot_id,
            user_context=_user_ctx(current_user),
        )

        return ChatResponse(
            status="success",
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            errors=result.get("errors", []),
            debug=result.get("debug"),
            message_id=result.get("message_id"),
        )

    except PermissionError as pe:
        logger.warning(f"Permission Denied: {pe}")
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        logger.exception("Error in ask endpoint")
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")


@router.post("/ask/stream")
async def ask_question_stream(
    request: ChatRequest,
    current_user: User = Depends(require_permission(Permission.CHAT_USE)),
    chat_service: ChatService = Depends(get_chat_service),
):
    """SSE stream: token events then a final done payload with sources."""
    queue: asyncio.Queue = asyncio.Queue()

    async def on_token(token: str) -> None:
        await queue.put(("token", token))

    async def run_pipeline() -> None:
        try:
            result = await chat_service.ask_question(
                question=request.question,
                dataset_ids=request.dataset_ids,
                history=_history_payload(request),
                session_id=request.session_id,
                chatbot_id=request.chatbot_id,
                user_context=_user_ctx(current_user),
                stream_callback=on_token,
            )
            await queue.put(("done", result))
        except PermissionError as pe:
            await queue.put(("error", (403, str(pe))))
        except Exception as exc:
            logger.exception("Error in ask stream endpoint")
            await queue.put(("error", (500, f"Failed to process question: {str(exc)}")))

    async def event_generator():
        task = asyncio.create_task(run_pipeline())
        try:
            while True:
                kind, payload = await queue.get()
                if kind == "token":
                    yield f"data: {json.dumps({'type': 'token', 'text': payload}, ensure_ascii=False)}\n\n"
                elif kind == "done":
                    yield f"data: {json.dumps({'type': 'done', **payload}, ensure_ascii=False, default=str)}\n\n"
                    break
                elif kind == "error":
                    status_code, detail = payload
                    yield f"data: {json.dumps({'type': 'error', 'status': status_code, 'detail': detail}, ensure_ascii=False)}\n\n"
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/feedback", response_model=ChatFeedbackResponse)
async def submit_chat_feedback(
    payload: ChatFeedbackRequest,
    current_user: User = Depends(require_permission(Permission.CHAT_USE)),
    session_repo=Depends(get_session_repo),
):
    message = await session_repo.get_message(payload.message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.get("role") != "assistant":
        raise HTTPException(status_code=400, detail="Chỉ đánh giá được câu trả lời của trợ lý")

    session_id = payload.session_id or message.get("session_id")
    if session_id:
        session = await session_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.get("user_id") != current_user.user_id and session.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Không có quyền đánh giá tin nhắn này")

    updated = await session_repo.set_message_feedback(
        payload.message_id, payload.rating, payload.comment
    )
    if not updated:
        raise HTTPException(status_code=400, detail="Không thể lưu đánh giá")

    return ChatFeedbackResponse(message_id=payload.message_id, rating=payload.rating)


@router.get("/suggestions")
async def get_chat_suggestions(
    current_user: User = Depends(require_permission(Permission.CHAT_USE)),
    session_repo=Depends(get_session_repo),
):
    recent = await session_repo.get_recent_user_questions(current_user.user_id)
    fallback = [
        "Quy chế đào tạo quy định những gì?",
        "Sinh viên cần làm thủ tục gì khi nghỉ học?",
        "Tóm tắt các điều khoản quan trọng trong tài liệu.",
    ]
    seen = {q.lower() for q in recent}
    suggestions = list(recent)
    for item in fallback:
        if item.lower() not in seen:
            suggestions.append(item)
        if len(suggestions) >= 6:
            break
    return {"suggestions": suggestions}
