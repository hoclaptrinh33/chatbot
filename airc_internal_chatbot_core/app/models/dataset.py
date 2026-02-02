"""
Dataset Models
Pydantic models cho Dataset management
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DatasetStatus(str, Enum):
    """Dataset processing status"""
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class FileInfo(BaseModel):
    """File information in dataset"""
    filename: str
    path: str
    size: int
    uploaded_at: datetime


class DatasetBase(BaseModel):
    """Base dataset schema"""
    name: str
    description: Optional[str] = None
    visibility: str = "private"  # private/public


class DatasetCreate(BaseModel):
    """
    Schema for creating dataset.
    Dataset là container đơn giản, không chứa config.
    Config (embedding, chunking, reranker) thuộc về Chatbot.
    """
    name: str = Field(..., min_length=3, max_length=200, description="Tên dataset")
    description: Optional[str] = Field(default=None, max_length=500, description="Mô tả dataset")
    visibility: str = Field(
        default="private", 
        pattern="^(private|public)$",
        description="Quyền truy cập"
    )
    chatbot_ids: Optional[List[str]] = Field(default=None, description="Danh sách chatbot IDs để gán dataset")


class DatasetUpdate(BaseModel):
    """Schema for updating dataset"""
    name: Optional[str] = None
    description: Optional[str] = None


class DatasetInDB(DatasetBase):
    """Dataset schema in database"""
    id: str
    owner_id: str
    files: List[FileInfo] = []
    shared_with: List[str] = []  # List of user IDs
    status: DatasetStatus = DatasetStatus.PROCESSING
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DatasetResponse(DatasetBase):
    """Dataset response schema"""
    id: str
    owner_id: str
    file_count: int
    status: DatasetStatus
    is_shared: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ShareDatasetRequest(BaseModel):
    """Request to share dataset"""
    student_ids: List[str] = []  # Empty = share with all students
    

class UploadResponse(BaseModel):
    """Upload response"""
    dataset_id: str
    name: str
    file_count: int
    status: str
