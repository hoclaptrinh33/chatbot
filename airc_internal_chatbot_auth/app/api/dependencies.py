"""
API Dependencies - Dependency injection cho FastAPI với RBAC
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.database import get_database
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService
from app.models.user import UserInDB, UserRole, Permission
from typing import Annotated, List, Callable

# Security scheme
security = HTTPBearer()


def get_user_repository() -> UserRepository:
    """Get UserRepository instance"""
    db = get_database()
    return UserRepository(db)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> AuthService:
    """Get AuthService instance"""
    return AuthService(user_repo)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> UserInDB:
    """
    Get current authenticated user từ JWT token
    
    Dependency này extract và verify JWT token từ Authorization header,
    sau đó lấy user data từ database.
    
    Args:
        credentials: JWT token từ Authorization header (Bearer <token>)
        auth_service: AuthService instance
        
    Returns:
        UserInDB object với đầy đủ thông tin user
        
    Raises:
        HTTPException 401: Nếu token invalid, expired, hoặc user không tồn tại
        HTTPException 403: Nếu user account bị disabled
    """
    token = credentials.credentials
    
    # Verify token và lấy token data
    token_data = auth_service.verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user từ database bằng user_id từ token
    # Note: token_data.user_id được extract từ 'sub' claim theo RFC 7519
    user = await auth_service.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check user active status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


def require_permission(permission: str) -> Callable:
    """
    Dependency factory để check permission
    
    Usage:
        @router.get("/admin")
        async def admin_only(
            user: UserInDB = Depends(require_permission("users:view"))
        ):
            ...
    """
    async def check_permission(
        current_user: Annotated[UserInDB, Depends(get_current_user)],
        rbac_service: Annotated["RBACService", Depends(get_rbac_service)]
    ) -> UserInDB:
        # Check system manage permission first for admin
        if current_user.role == "admin":
             return current_user

        # Sử dụng RBAC service để check permission
        has_perm = await rbac_service.check_permission(
            user_id=current_user.id,
            permission_code=permission
        )
        
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}"
            )
        return current_user
    return check_permission


def require_role(allowed_roles: List[UserRole]) -> Callable:
    """
    Dependency factory để check role
    
    Usage:
        @router.get("/teachers-only")
        async def teachers_only(
            user: User = Depends(require_role([UserRole.ADMIN, UserRole.TEACHER]))
        ):
            ...
    """
    async def check_role(
        current_user: Annotated[UserInDB, Depends(get_current_user)]
    ) -> UserInDB:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role.value} not authorized"
            )
        return current_user
    return check_role


async def get_admin_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    """
    Dependency cho admin-only endpoints
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_teacher_or_admin(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    """
    Dependency cho teacher hoặc admin endpoints
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher or Admin access required"
        )
    return current_user


# ==================== NEW: RBAC DEPENDENCIES ====================

def get_rbac_repository() -> "RBACRepository":
    """
    Get RBACRepository instance
    
    Returns:
        RBACRepository for RBAC operations
    """
    from app.repositories.rbac_repository import RBACRepository
    db = get_database()
    return RBACRepository(db)


def get_rbac_service(
    rbac_repo: Annotated["RBACRepository", Depends(get_rbac_repository)]
) -> "RBACService":
    """
    Get RBACService instance
    
    Returns:
        RBACService for permission checking
    """
    from app.services.rbac_service import RBACService
    return RBACService(rbac_repo)
