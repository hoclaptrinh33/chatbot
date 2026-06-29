"""
Pydantic Schemas - DTOs cho request/response validation
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from app.models.enums import FileStatus, DatasetFileStatus


# ==================== Dataset Schemas ====================

# DatasetConfig removed - using system defaults
# class DatasetConfig(BaseModel): ...


class DatasetCreate(BaseModel):
    """
    Request: Tạo dataset mới
    Dataset chỉ là container chứa files, không có config.
    Config (embedding, chunking) thuộc về Chatbot.
    """
    name: str = Field(..., min_length=3, max_length=200, description="Tên dataset")
    description: Optional[str] = Field(default=None, max_length=500, description="Mô tả dataset")
    visibility: str = Field(default="shared", description="Quyền truy cập: private/shared/public")
    chatbot_ids: Optional[List[str]] = Field(default=None, description="Danh sách chatbot IDs để gán dataset")


class DatasetResponse(BaseModel):
    """Response: Dataset"""
    id: str
    name: str
    description: Optional[str] = None
    # config: DatasetConfig  <-- Removed
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== File Schemas ====================

class FileUploadResponse(BaseModel):
    """Response: Upload file"""
    id: str
    name: str
    size: int
    mime_type: str
    status: FileStatus
    uploaded_at: datetime


class FileResponse(BaseModel):
    """Response: File info"""
    id: str
    name: str
    size: int
    mime_type: str
    status: FileStatus
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    error: Optional[str] = None


# ==================== Dataset File Schemas ====================

class AddFilesToDatasetRequest(BaseModel):
    """Request: Thêm files vào dataset"""
    file_ids: List[str] = Field(..., min_length=1)


class DatasetFileResponse(BaseModel):
    """Response: Dataset file"""
    id: str
    dataset_id: str
    file_id: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    status: DatasetFileStatus
    is_enabled: bool = True
    chunk_count: int = 0
    created_at: datetime
    processed_at: Optional[datetime] = None


class ToggleDatasetFileRequest(BaseModel):
    """Request: Bật/tắt dataset file"""
    enabled: bool


# ==================== Chat Schemas ====================

class ChatMessage(BaseModel):
    """Chat message trong history"""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request: Hỏi đáp với RAG"""
    question: str = Field(..., min_length=1)
    dataset_ids: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    chatbot_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = None


class SearchResult(BaseModel):
    """Kết quả tìm kiếm từ vector DB"""
    vector_id: Union[int, str]
    score: float
    text: str
    file_id: str
    dataset_file_id: str
    chunk_index: int
    cite: str


class DatasetSearchResult(BaseModel):
    """Kết quả tìm kiếm theo dataset"""
    dataset_id: str
    dataset_name: Optional[str]
    results: List[SearchResult]


class ChatResponse(BaseModel):
    """Response: Chat answer"""
    status: str = "success"
    question: str
    answer: str
    sources: List[DatasetSearchResult]
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    debug: Optional[Dict[str, Any]] = None  # RAG performance metrics


# ==================== Chunk Schemas ====================

class ChunkResponse(BaseModel):
    """Response: Chunk"""
    id: str
    dataset_id: str
    dataset_file_id: str
    file_id: Optional[str] = None
    chunk_index: int
    text: str
    vector_id: Optional[Union[int, str]] = None


# ==================== Generic Response ====================

class SuccessResponse(BaseModel):
    """Generic success response"""
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Generic error response"""
    status: str = "error"
    message: str
    detail: Optional[str] = None


# ==================== Session & History Schemas ====================

class ChatSessionCreate(BaseModel):
    """Request: Tạo phiên chat mới"""
    name: str = Field(..., min_length=1, description="Tên phiên chat")
    parent_id: Optional[str] = Field(default=None, description="ID của session cha nếu đây là nhánh rẽ")
    branch_message_index: Optional[int] = Field(default=None, description="Index của tin nhắn bắt đầu rẽ nhánh")


class ChatSessionUpdate(BaseModel):
    """Request: Cập nhật phiên chat"""
    name: str = Field(..., min_length=1)


class ChatSessionResponse(BaseModel):
    """Response: Thông tin phiên chat"""
    id: str
    user_id: str
    name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    parent_id: Optional[str] = None
    branch_message_index: Optional[int] = None


class ChatMessageCreate(BaseModel):
    """Request: Tạo tin nhắn mới (thường dùng nội bộ hoặc test)"""
    session_id: str
    role: str = Field(..., description="'user' hoặc 'assistant'")
    content: str


class ChatMessageResponse(BaseModel):
    """Response: Tin nhắn trong lịch sử"""
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime
    
