"""
User Models - Pydantic schemas cho User với RBAC
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """
    Vai trò người dùng trong hệ thống giáo dục
    - ADMIN: Quản trị viên - full access
    - TEACHER: Giảng viên - tạo/quản lý datasets của mình
    - STUDENT: Sinh viên - chỉ xem datasets được share
    """
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class Permission(str, Enum):
    """
    Atomic permissions cho RBAC
    Format: resource:action hoặc resource:action:scope
    """
    # User management
    USERS_VIEW = "users:view"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    
    USERS_DELETE = "users:delete"
    
    # Dataset management
    DATASETS_VIEW_ALL = "datasets:view:all"
    DATASETS_VIEW_SHARED = "datasets:view:shared"
    DATASETS_CREATE = "datasets:create"
    DATASETS_UPDATE_OWN = "datasets:update:own"
    DATASETS_UPDATE_ANY = "datasets:update:any"
    DATASETS_DELETE_OWN = "datasets:delete:own"
    DATASETS_DELETE_ANY = "datasets:delete:any"
    DATASETS_SHARE = "datasets:share"
    
    # Chatbot management
    CHATBOTS_CREATE = "chatbots:create"
    CHATBOTS_USE = "chatbots:use"
    CHATBOTS_MANAGE_OWN = "chatbots:manage:own"
    CHATBOTS_MANAGE_ANY = "chatbots:manage:any"
    
    # Chat
    CHAT_USE = "chat:use"
    CHAT_VIEW_OWN = "chat:view:own"
    CHAT_VIEW_ANY = "chat:view:any"
    
    # Analytics
    ANALYTICS_VIEW = "analytics:view"
    SYSTEM_MANAGE = "system:manage"


# Role to Permissions mapping
ROLE_PERMISSIONS: dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: [
        # Full admin access
        Permission.USERS_VIEW,
        Permission.USERS_CREATE,
        Permission.USERS_UPDATE,
        Permission.USERS_DELETE,
        Permission.DATASETS_VIEW_ALL,
        Permission.DATASETS_CREATE,
        Permission.DATASETS_UPDATE_ANY,
        Permission.DATASETS_DELETE_ANY,
        Permission.DATASETS_SHARE,
        Permission.CHATBOTS_CREATE,
        Permission.CHATBOTS_USE,
        Permission.CHATBOTS_MANAGE_ANY,
        Permission.CHAT_USE,
        Permission.CHAT_VIEW_ANY,
        Permission.ANALYTICS_VIEW,
        Permission.SYSTEM_MANAGE,
    ],
    UserRole.TEACHER: [
        # Teacher: Chat + manage own datasets (via chat interface)
        Permission.DATASETS_VIEW_ALL,  # View all to see what's available
        Permission.DATASETS_CREATE,    # Upload files (in chat interface)
        Permission.DATASETS_UPDATE_OWN, # Edit own datasets
        Permission.DATASETS_DELETE_OWN, # Delete own datasets
        Permission.DATASETS_SHARE,      # Share with students
        Permission.CHATBOTS_USE,        # Use chatbot
        Permission.CHAT_USE,            # Primary function: Chat
        Permission.CHAT_VIEW_OWN,       # View own chat history
    ],
    UserRole.STUDENT: [
        # Student: Chat only with shared datasets
        Permission.DATASETS_VIEW_SHARED, # Only see shared datasets
        Permission.CHATBOTS_USE,         # Use chatbot
        Permission.CHAT_USE,             # Primary function: Chat
        Permission.CHAT_VIEW_OWN,        # View own chat history
    ],
}


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.STUDENT
    is_active: bool = True


class UserCreate(BaseModel):
    """Schema cho tạo user mới"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: UserRole = UserRole.STUDENT


class UserUpdate(BaseModel):
    """Schema cho update user"""
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    """User schema trong database"""
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """User response schema (không trả password)"""
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data trong JWT token"""
    user_id: str
    email: str
    role: str


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str
