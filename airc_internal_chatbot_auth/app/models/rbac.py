"""
RBAC Models - Pydantic schemas cho Permission, Role, và assignments

Các models:
- Permission: Atomic permissions
- Role: User roles
- RolePermission: Role-Permission mapping
- UserRole: User-Role assignment
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ==================== PERMISSION ====================

class PermissionBase(BaseModel):
    """Base Permission schema"""
    name: str = Field(..., description="Tên hiển thị của permission")
    code: str = Field(..., description="Mã định danh duy nhất (resource:action:scope)")
    resource: str = Field(..., description="Resource type (users, datasets, chat, etc.)")
    action: str = Field(..., description="Action verb (view, create, update, delete, etc.)")
    scope: Optional[str] = Field(None, description="Access scope (own, any, all, shared)")
    description: Optional[str] = Field(None, description="Mô tả chi tiết")


class PermissionCreate(PermissionBase):
    """Tạo Permission mới"""
    is_system: bool = Field(default=False, description="System permission không thể xóa")


class PermissionUpdate(BaseModel):
    """Cập nhật Permission"""
    name: Optional[str] = None
    description: Optional[str] = None
    # code, resource, action, scope không cho phép sửa


class PermissionResponse(PermissionBase):
    """Permission response"""
    id: str = Field(alias="_id")
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime] = None  # Optional vì có thể chưa được update
    
    class Config:
        populate_by_name = True
        from_attributes = True


# ==================== ROLE ====================

class RoleBase(BaseModel):
    """Base Role schema"""
    name: str = Field(..., description="Tên hiển thị của role")
    code: str = Field(..., description="Mã định danh (lowercase, no spaces)")
    description: Optional[str] = Field(None, description="Mô tả vai trò")


class RoleCreate(RoleBase):
    """Tạo Role mới"""
    is_system: bool = Field(default=False, description="System role không thể xóa")


class RoleUpdate(BaseModel):
    """Cập nhật Role"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    # code không cho phép sửa


class RoleResponse(RoleBase):
    """Role response"""
    id: str = Field(alias="_id")
    is_system: bool
    is_active: bool = True  # Default True
    permission_count: int = Field(default=0, description="Số lượng permissions (aggregated)")
    created_at: datetime
    updated_at: Optional[datetime] = None  # Optional vì có thể chưa được update
    
    class Config:
        populate_by_name = True
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """Role kèm danh sách permissions"""
    permissions: List[PermissionResponse]


# ==================== ROLE-PERMISSION MAPPING ====================

class GrantPermissionsRequest(BaseModel):
    """Grant permissions to role"""
    permission_ids: List[str] = Field(..., description="Danh sách permission IDs")


class RevokePermissionRequest(BaseModel):
    """Revoke permission from role"""
    permission_id: str


# ==================== USER-ROLE ASSIGNMENT ====================

class AssignRoleRequest(BaseModel):
    """Assign role to user"""
    role_id: str = Field(..., description="Role ID để assign")
    expires_at: Optional[datetime] = Field(None, description="Thời gian hết hạn (temporary role)")


class UserRoleResponse(BaseModel):
    """User-Role assignment response"""
    id: str = Field(alias="_id")
    user_id: str
    role: RoleResponse
    assigned_at: datetime
    assigned_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        from_attributes = True


# ==================== PERMISSION CHECK ====================

class PermissionCheckRequest(BaseModel):
    """Request để check permission"""
    permission_code: str = Field(..., description="Permission code to check")
    resource_owner_id: Optional[str] = Field(None, description="Owner ID for :own scope check")



class PermissionCheckResponse(BaseModel):
    """Response của permission check"""
    has_permission: bool
    message: Optional[str] = None


class PermissionMatrixResponse(BaseModel):
    """Response cho Permission Matrix UI"""
    roles: List[RoleResponse]
    permissions: List[PermissionResponse]
    matrix: dict  # role_code -> list[permission_code]
