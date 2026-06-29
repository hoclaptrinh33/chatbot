"""
RBAC Service - Quản lý phân quyền dựa trên Role-Based Access Control

Service này implement RBAC pattern với database-driven permissions:
- Permissions được lưu trong database, không hardcode
- Hỗ trợ dynamic permission management qua API
- Cache permissions để tối ưu performance
- Support role hierarchy (admin có tất cả quyền)

Design Pattern: Service Layer Pattern
- Tách biệt business logic khỏi API layer
- Dependency Injection qua RBACRepository
- Single Responsibility: Chỉ xử lý RBAC logic
"""
from typing import List, Optional
from app.repositories.rbac_repository import RBACRepository
from app.models.rbac import PermissionResponse
import logging

logger = logging.getLogger(__name__)


class RBACService:
    """
    Service xử lý RBAC với database-driven permissions
    
    Responsibilities:
    - Check user permissions
    - Manage permission cache
    - Handle role hierarchy logic
    
    Design Decisions:
    - Admin role có tất cả permissions (bypass check)
    - Cache in-memory để giảm database queries
    - Permissions được aggregate từ tất cả roles của user
    """
    
    def __init__(self, rbac_repo: RBACRepository):
        """
        Khởi tạo RBAC Service với Dependency Injection
        
        Args:
            rbac_repo: Repository để access RBAC data từ database
        """
        self.rbac_repo = rbac_repo
        self._cache = {}  # In-memory cache: {cache_key: data}
    
    async def can_manage_system(self, user_id: str) -> bool:
        """
        Kiểm tra user có quyền quản lý hệ thống không
        
        Business Logic:
        1. Admin role: Tự động có quyền (bypass tất cả checks)
        2. Other roles: Kiểm tra có permission "system:manage" hoặc "rbac:*"
        
        Args:
            user_id: User ID cần kiểm tra
            
        Returns:
            True nếu user có quyền quản lý system, False nếu không
        """
        # Get user's primary role
        user_role_code = await self._get_user_role_code(user_id)
        
        # Admin role tự động có tất cả quyền
        if user_role_code == "admin":
            logger.debug(f"User {user_id} is admin - granted system:manage")
            return True
        
        # Check if user has explicit permission
        permissions = await self.get_user_permissions(user_id)
        permission_codes = [p.code for p in permissions]
        
        has_permission = (
            "system:manage" in permission_codes or
            "rbac:manage_roles" in permission_codes or
            "rbac:manage_permissions" in permission_codes
        )
        
        logger.debug(f"User {user_id} system:manage check: {has_permission}")
        return has_permission
    
    async def check_permission(
        self,
        user_id: str,
        permission_code: str,
        resource_owner_id: Optional[str] = None
    ) -> bool:
        """
        Kiểm tra user có permission cụ thể không
        
        Args:
            user_id: User ID
            permission_code: Permission code (e.g., "datasets:create")
            resource_owner_id: Optional owner ID (for :own scope)
            
        Returns:
            True nếu user có permission
        """
        # Get user's role
        user_role_code = await self._get_user_role_code(user_id)
        
        # Admin bypass tất cả checks
        if user_role_code == "admin":
            return True
        
        # Get user permissions
        permissions = await self.get_user_permissions(user_id)
        permission_codes = [p.code for p in permissions]
        
        # Check exact match
        if permission_code in permission_codes:
            # If permission has :own scope, check ownership
            if ":own" in permission_code and resource_owner_id:
                return user_id == resource_owner_id
            return True
        
        # Check wildcard permissions (e.g., "datasets:*" matches "datasets:create")
        base_resource = permission_code.split(":")[0]
        wildcard = f"{base_resource}:*"
        if wildcard in permission_codes:
            return True
        
        return False
    
    async def get_user_permissions(self, user_id: str) -> List[PermissionResponse]:
        """
        Lấy tất cả permissions của user
        
        Args:
            user_id: User ID
            
        Returns:
            List of PermissionResponse
        """
        # Check cache
        cache_key = f"user_perms:{user_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Get user's roles
        roles = await self.rbac_repo.get_user_roles(user_id)
        
        # Collect all permissions from all roles
        all_permissions = []
        seen_codes = set()
        
        for role in roles:
            # Get role with permissions
            role_with_perms = await self.rbac_repo.get_role_with_permissions(str(role.id))
            if role_with_perms and role_with_perms.permissions:
                for perm in role_with_perms.permissions:
                    if perm.code not in seen_codes:
                        all_permissions.append(perm)
                        seen_codes.add(perm.code)
        
        # Cache result
        self._cache[cache_key] = all_permissions
        
        return all_permissions
    
    async def _get_user_role_code(self, user_id: str) -> Optional[str]:
        """
        Lấy role code của user (admin, teacher, student)
        
        Args:
            user_id: User ID
            
        Returns:
            Role code hoặc None
        """
        roles = await self.rbac_repo.get_user_roles(user_id)
        if not roles:
            return None
        
        # Return first role (users typically have one primary role)
        return roles[0].code
    
    def invalidate_user_cache(self, user_id: str):
        """
        Xóa cache của user khi roles/permissions thay đổi
        
        Args:
            user_id: User ID
        """
        cache_key = f"user_perms:{user_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"Invalidated cache for user {user_id}")
    
    def invalidate_role_cache(self, role_id: str):
        """
        Xóa tất cả cache khi role permissions thay đổi
        
        Args:
            role_id: Role ID
        """
        # Simple approach: clear all cache
        # In production, should track which users have this role
        self._cache.clear()
        logger.debug(f"Invalidated all cache due to role {role_id} change")

    async def get_permission_matrix(self) -> dict:
        """
        Lấy matrix quyền hạn để hiển thị UI
        
        Returns:
            dict: {
                "roles": [RoleResponse],
                "permissions": [PermissionResponse],
                "matrix": {
                    "role_code_1": ["perm_code_1", "perm_code_2"],
                    "role_code_2": ["perm_code_1"]
                }
            }
        """
        # 1. Get all roles
        roles = await self.rbac_repo.get_all_roles()
        
        # 2. Get all permissions
        permissions = await self.rbac_repo.get_all_permissions()
        
        # 3. Build matrix map: role_code -> [permission_codes]
        matrix = {}
        processed_roles = []
        
        try:
            for role in roles:
                # Load specific role with permissions
                role_full = await self.rbac_repo.get_role_with_permissions(str(role.id))
                
                if role_full:
                    processed_roles.append(role_full)
                    if role_full.permissions:
                        matrix[role.code] = [p.code for p in role_full.permissions]
                    else:
                        matrix[role.code] = []
                else:
                    # Fallback if specific load fails
                    processed_roles.append(role)
                    matrix[role.code] = []
                    
            return {
                "roles": processed_roles,
                "permissions": permissions,
                "matrix": matrix
            }
        except Exception as e:
            logger.error(f"Error generating permission matrix: {e}", exc_info=True)
            raise e
