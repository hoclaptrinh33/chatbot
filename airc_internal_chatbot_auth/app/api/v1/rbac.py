"""
RBAC Management API - Endpoints cho quản lý Permissions, Roles, và Assignments

Endpoints:
- Permissions: CRUD operations
- Roles: CRUD với permission assignments
- User-Role: Assignment và removal
- Permission queries: Get user permissions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Annotated
from app.models.rbac import *
from app.repositories.rbac_repository import RBACRepository
from app.services.rbac_service import RBACService
from app.api.dependencies import get_current_user, get_rbac_repository, get_rbac_service, get_auth_service, security
from app.models.user import UserInDB
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rbac", tags=["RBAC Management"])


# ==================== DEPENDENCIES ====================

async def require_system_manage(
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Dependency: Yêu cầu system:manage permission
    
    Chỉ admin mới có quyền quản lý RBAC
    
    Logic:
    - Check role từ current_user object (đã được populate bởi get_current_user)
    - Admin role: Có quyền
    - Other roles: Raise 403 Forbidden
    """
    # Check if user is admin
    if current_user.role != "admin":
        logger.warning(f"User {current_user.email} (role: {current_user.role}) attempted to access admin endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ system admin mới có quyền này"
        )
    
    logger.info(f"Admin access granted for {current_user.email}")
    return current_user



# ==================== PERMISSIONS ====================

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    include_system: bool = True,
    _admin = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository)
):
    """
    Lấy danh sách tất cả permissions
    
    **Quyền yêu cầu**: system:manage
    
    Query params:
    - include_system: Bao gồm system permissions (default True)
    
    Returns:
        List of permissions
    """
    permissions = await repo.get_all_permissions(include_system=include_system)
    return permissions


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission: PermissionCreate,
    current_user: UserInDB = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository)
):
    """
    Tạo permission mới
    
    **Quyền yêu cầu**: system:manage
    
    Body:
    - name: Tên hiển thị
    - code: Unique code (resource:action:scope)
    - resource: Resource type
    - action: Action verb
    - scope: Optional scope (own, any, all, shared)
    - description: Mô tả
    - is_system: System permission (default False)
    
    Returns:
        Created permission
    """
    # Check duplicate code
    existing = await repo.get_permission_by_code(permission.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Permission code '{permission.code}' đã tồn tại"
        )
    
    created = await repo.create_permission(permission, str(current_user.id))
    logger.info(f"User {current_user.email} created permission: {permission.code}")

    # Auto-grant to Admin role to keep Matrix consistent
    try:
        admin_role = await repo.get_role_by_code("admin")
        if admin_role:
            await repo.grant_permissions_to_role(
                role_id=str(admin_role.id),
                permission_ids=[str(created.id)],
                granted_by=str(current_user.id)
            )
            logger.info(f"Auto-granted permission {permission.code} to Admin role")
    except Exception as e:
        logger.error(f"Failed to auto-grant permission to Admin: {e}")

    return created


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: str,
    _admin = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository)
):
    """Lấy chi tiết permission"""
    permission = await repo.get_permission_by_id(permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission không tồn tại")
    return permission


@router.patch("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: str,
    update_data: PermissionUpdate,
    _admin = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository)
):
    """
    Cập nhật permission
    
    Note: Chỉ cho phép sửa name và description
    """
    updated = await repo.update_permission(permission_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Permission không tồn tại")
    return updated


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: str,
    current_user: UserInDB = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Xóa permission
    
    Note: Chỉ xóa được non-system permissions
    """
    success = await repo.delete_permission(permission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa system permission hoặc permission không tồn tại"
        )
    
    # Clear cache vì permission đã bị xóa
    rbac_service.invalidate_role_cache(permission_id)
    
    logger.info(f"User {current_user.email} deleted permission: {permission_id}")
    return None


# ==================== ROLES ====================

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    include_inactive: bool = False,
    repo: RBACRepository = Depends(get_rbac_repository)
):
    """
    Lấy danh sách roles (PUBLIC endpoint)
    
    **Quyền**: PUBLIC - Không cần authentication
    Note: Endpoint này phải public để support role selection UI và setup scripts
    
    Query params:
    - include_inactive: Bao gồm inactive roles (default False)
    """
    roles = await repo.get_all_roles(include_inactive=include_inactive)
    return roles


@router.get("/roles/{role_id}", response_model=RoleWithPermissions)
async def get_role(
    role_id: str,
    current_user: UserInDB = Depends(get_current_user),
    repo: RBACRepository = Depends(get_rbac_repository)
):
    """
    Lấy role với danh sách permissions
    
    **Quyền**: Tất cả user
    """
    role = await repo.get_role_with_permissions(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role không tồn tại")
    return role


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role: RoleCreate,
    current_user: UserInDB = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository)
):
    """
    Tạo role mới
    
    **Quyền yêu cầu**: system:manage
    """
    # Check duplicate code
    if role.code.lower() == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tạo role 'admin' vì đây là role hệ thống mặc định"
        )
    
    existing = await repo.get_role_by_code(role.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role code '{role.code}' đã tồn tại"
        )
    
    created = await repo.create_role(role, str(current_user.id))
    logger.info(f"User {current_user.email} created role: {role.code}")
    return created


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    update_data: RoleUpdate,
    _admin = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository)
):
    """Cập nhật role"""
    updated = await repo.update_role(role_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Role không tồn tại")
    return updated


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    current_user: UserInDB = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Xóa role
    
    Note: Chỉ xóa được non-system roles
    Also xóa tất cả role_permissions và user_roles
    """
    # Prevent deleting admin role
    role = await repo.get_role_by_id(role_id)
    if role and role.code == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa role Admin mặc định"
        )

    success = await repo.delete_role(role_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa system role hoặc role không tồn tại"
        )
    
    # Clear cache
    rbac_service.invalidate_role_cache(role_id)
    
    logger.info(f"User {current_user.email} deleted role: {role_id}")
    return None


# ==================== ROLE-PERMISSION MAPPING ====================

@router.post("/roles/{role_id}/permissions", status_code=status.HTTP_204_NO_CONTENT)
async def grant_permissions_to_role(
    role_id: str,
    request: GrantPermissionsRequest,
    current_user: UserInDB = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Grant permissions to role
    
    **Quyền yêu cầu**: system:manage
    
    Body:
    - permission_ids: List of permission IDs to grant
    """
    # Verify role exists
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role không tồn tại")
    
    # Verify all permissions exist
    for pid in request.permission_ids:
        perm = await repo.get_permission_by_id(pid)
        if not perm:
            raise HTTPException(
                status_code=400,
                detail=f"Permission {pid} không tồn tại"
            )
    
    # Set/Replace permissions (Full update)
    await repo.set_role_permissions(
        role_id, 
        request.permission_ids,
        str(current_user.id)
    )
    
    # Invalidate cache
    rbac_service.invalidate_role_cache(role_id)
    
    logger.info(f"User {current_user.email} set {len(request.permission_ids)} permissions for role {role_id}")
    return None


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_permission_from_role(
    role_id: str,
    permission_id: str,
    current_user: UserInDB = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Revoke permission from role
    
    **Quyền yêu cầu**: system:manage
    """
    # Check if role is admin
    role = await repo.get_role_by_id(role_id)
    if role and role.code == "admin":
        raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail="Không thể xóa quyền của Admin (Admin luôn có full quyền)"
        )

    success = await repo.revoke_permission_from_role(role_id, permission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mapping không tồn tại")
    
    # Invalidate cache
    rbac_service.invalidate_role_cache(role_id)
    
    logger.info(f"User {current_user.email} revoked permission {permission_id} from role {role_id}")
    return None


# ==================== USER-ROLE ASSIGNMENT ====================

@router.post("/users/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role_to_user(
    user_id: str,
    request: AssignRoleRequest,
    current_user: UserInDB = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Assign role to user
    
    **Quyền yêu cầu**: system:manage (hoặc users:update)
    
    Body:
    - role_id: Role ID to assign
    - expires_at: Optional expiration datetime (for temporary roles)
    """
    # Verify role exists
    role = await repo.get_role_by_id(request.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role không tồn tại")
    
    # Prevent assigning admin role manually
    if role.code == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể gán role Admin thủ công. Admin là tài khoản duy nhất."
        )
    
    # Assign role
    await repo.assign_role_to_user(
        user_id,
        request.role_id,
        str(current_user.id),
        request.expires_at
    )
    
    # Invalidate user cache
    rbac_service.invalidate_user_cache(user_id)
    
    logger.info(f"User {current_user.email} assigned role {request.role_id} to user {user_id}")
    return None


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: str,
    role_id: str,
    current_user: UserInDB = Depends(require_system_manage),
    repo: RBACRepository = Depends(get_rbac_repository),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Remove role from user
    
    **Quyền yêu cầu**: system:manage
    """
    # Check if role is admin
    role = await repo.get_role_by_id(role_id)
    if role and role.code == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể gỡ role Admin (Safety Lock)"
        )

    success = await repo.remove_role_from_user(user_id, role_id)
    if not success:
        raise HTTPException(status_code=404, detail="User không có role này")
    
    # Invalidate user cache
    rbac_service.invalidate_user_cache(user_id)
    
    logger.info(f"User {current_user.email} removed role {role_id} from user {user_id}")
    return None


@router.get("/users/{user_id}/roles", response_model=List[RoleResponse])
async def get_user_roles(
    user_id: str,
    current_user: UserInDB = Depends(get_current_user),
    repo: RBACRepository = Depends(get_rbac_repository)
):
    """
    Lấy tất cả roles của user
    
    **Quyền**: User chỉ xem được roles của chính mình (hoặc admin xem tất cả)
    """
    # Valid permission check: Admin OR Self
    if str(current_user.id) != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền xem thông tin người khác"
        )
    
    roles = await repo.get_user_roles(user_id)
    return roles


@router.get("/users/{user_id}/permissions", response_model=List[str])
async def get_user_permissions(
    user_id: str,
    current_user: UserInDB = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Lấy tất cả permission codes của user
    
    **Quyền**: User chỉ xem được permissions của chính mình (hoặc admin xem tất cả)
    
    Returns:
        List of permission codes (strings)
        
    Example response:
        ["users:view", "datasets:create", "datasets:update:own", "chat:use"]
    """
    # Valid permission check: Admin OR Self
    if str(current_user.id) != user_id and current_user.role != "admin":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền xem permissions của người khác"
        )
    
    permissions = await rbac_service.get_user_permissions(user_id)
    permission_codes = [perm.code for perm in permissions]
    
    return permission_codes


@router.post("/users/{user_id}/check-permission", response_model=PermissionCheckResponse)
async def check_user_permission(
    user_id: str,
    request: PermissionCheckRequest,
    current_user: UserInDB = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Check if user có permission cụ thể
    
    **Quyền**: Chỉ admin hoặc chính user đó
    
    Body:
    - permission_code: Permission to check
    - resource_owner_id: Optional owner ID (for :own scope)
    
    Returns:
        has_permission: boolean
        message: Optional explanation
    """
    # Valid permission check: Admin OR Self
    if str(current_user.id) != user_id and current_user.role != "admin":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền kiểm tra permissions của người khác"
        )
    
    has_permission = await rbac_service.check_permission(
        user_id,
        request.permission_code,
        request.resource_owner_id
    )
    
    return PermissionCheckResponse(
        has_permission=has_permission,
        message=f"Permission check: {request.permission_code}"
    )


@router.get("/matrix", response_model=PermissionMatrixResponse)
async def get_permission_matrix(
    current_user: UserInDB = Depends(require_system_manage),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """
    Lấy permission matrix cho UI assignment
    
    Returns:
        roles: Danh sách roles
        permissions: Danh sách permissions
        matrix: Map role_code -> permission_codes
    """
    matrix_data = await rbac_service.get_permission_matrix()
    return PermissionMatrixResponse(**matrix_data)
