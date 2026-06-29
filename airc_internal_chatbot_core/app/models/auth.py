from enum import Enum
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

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
    
    # RBAC Management
    RBAC_MANAGE_ROLES = "rbac:manage_roles"
    RBAC_MANAGE_PERMISSIONS = "rbac:manage_permissions"


class User(BaseModel):
    """User Model cho Core Service"""
    id: str = "unknown"
    user_id: str # Alias for id, used in Core logic
    email: str
    full_name: str
    role: UserRole = UserRole.STUDENT
    is_active: bool = True
