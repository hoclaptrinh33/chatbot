"""
Auth API Endpoints - Authentication routes với RBAC
Production-ready với rate limiting và input validation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.api.dependencies import (
    get_auth_service, 
    get_current_user, 
    get_admin_user,
    get_admin_user,
    require_permission,
    get_rbac_service
)
from app.services.auth_service import AuthService
from app.models.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    LoginRequest,
    Token,
    TokenData,
    UserInDB,
    Permission
)
from app.core.rate_limiter import rate_limiter
from app.core.validators import InputValidator
from typing import Annotated, List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_data: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Đăng ký user mới (default role: STUDENT)
    
    Args:
        request: FastAPI request object
        user_data: User registration data
        auth_service: AuthService instance
        
    Returns:
        JWT Token
    """
    # Validate email format
    is_valid, email_error = InputValidator.validate_email(user_data.email)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=email_error
        )
    
    # Validate password strength
    is_valid, password_error = InputValidator.validate_password(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=password_error
        )
    
    # Validate full name
    is_valid, name_error = InputValidator.validate_name(user_data.full_name)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=name_error
        )
    
    # Sanitize inputs
    user_data.email = InputValidator.sanitize_string(user_data.email.lower().strip())
    user_data.full_name = InputValidator.sanitize_string(user_data.full_name.strip())
    
    try:
        token = await auth_service.register(user_data)
        logger.info(f"User registered successfully: {user_data.email}")
        return token
    except ValueError as e:
        error_msg = str(e)
        # Translate common errors to Vietnamese - use exact match
        if "đã được đăng ký" in error_msg or "already registered" in error_msg.lower():
            detail = "Email này đã được đăng ký. Vui lòng sử dụng email khác hoặc đăng nhập."
        else:
            # Return the error message directly (already in Vietnamese from service)
            detail = error_msg
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đăng ký thất bại do lỗi hệ thống. Vui lòng thử lại sau."
        )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    credentials: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Đăng nhập với brute force protection
    
    Args:
        request: FastAPI request object
        credentials: Email và password
        auth_service: AuthService instance
        
    Returns:
        JWT Token
    """
    # Get client IP for logging
    client_ip = request.client.host if request.client else "unknown"
    
    # Check brute force protection (via rate limiter)
    is_blocked, block_seconds = await rate_limiter.is_blocked(request)
    if is_blocked:
        logger.warning(f"Login blocked for {credentials.email} from {client_ip} - brute force protection")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau {block_seconds} giây.",
            headers={"Retry-After": str(block_seconds)}
        )
    
    # Validate email format
    is_valid, email_error = InputValidator.validate_email(credentials.email)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=email_error or "Email không hợp lệ"
        )
    
    try:
        token = await auth_service.login(credentials.email, credentials.password)
        
        # Clear failed login attempts on success
        await rate_limiter.reset_failed_logins(request)
        
        logger.info(f"Login successful: {credentials.email} from {client_ip}")
        return token
        
    except ValueError as e:
        # Record failed login attempt
        await rate_limiter.record_failed_login(request)
        
        error_msg = str(e)
        logger.warning(f"Login failed for {credentials.email} from {client_ip}: {error_msg}")
        
        # Return specific Vietnamese error message from service
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đăng nhập thất bại do lỗi hệ thống. Vui lòng thử lại sau."
        )


@router.post("/verify")
async def verify_token(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    payload: dict  # Accept token from request body
):
    """
    Verify JWT token (for inter-service communication)
    
    Core service và các services khác gọi endpoint này để validate tokens.
    Endpoint này accept token từ request body.
    
    Args:
        payload: Request body containing {"token": "jwt_token_string"}
        
    Returns:
        User data nếu token valid
        
    Raises:
        HTTPException 401: Nếu token invalid, expired, hoặc user không tồn tại
    """
    # Extract token from payload
    token = payload.get("token")
    
    # Validate token parameter
    if not token:
        logger.warning("Token verification called without token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is required"
        )
    
    try:
        # Verify token bằng JWT service
        token_data = auth_service.verify_token(token)
        
        if not token_data:
            logger.warning(f"Token verification failed: invalid or expired token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Get user from database để verify user vẫn tồn tại và active
        # Use service method to get role info as well
        user = await auth_service.get_user_by_id(token_data.user_id)
        
        if not user:
            logger.warning(f"Token valid but user not found: {token_data.user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Access attributes differently depending if it's dict or UserInDB object
        # AuthService.get_user_by_id returns UserInDB (Pydantic model)
        is_active = user.is_active
        if not is_active:
            logger.warning(f"Token valid but user inactive: {token_data.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Return user data cho Core service
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Token verification error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    payload: dict,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Yêu cầu đặt lại mật khẩu (Dummy endpoint)
    """
    # TODO: Implement send email logic
    return {"message": "Password reset email sent"}

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
):
    """
    Lấy thông tin user hiện tại
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@router.get("/me/permissions", response_model=List[str])
async def get_my_permissions(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    rbac_service: Annotated["RBACService", Depends(get_rbac_service)]
):
    """
    Lấy danh sách permissions của user hiện tại
    Frontend dùng endpoint này để ẩn/hiện UI elements
    
    Returns:
        List of permission strings
    """
    permissions = await rbac_service.get_user_permissions(current_user.id)
    return [p.code for p in permissions]


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: Annotated[UserInDB, Depends(get_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Lấy danh sách tất cả users (Admin only)
    
    Returns:
        List of users
    """
    users = await auth_service.get_all_users()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at
        ) for u in users
    ]
    
@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    user_data: UserCreate,
    current_user: Annotated[UserInDB, Depends(get_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Admin tạo user mới
    """
    try:
        user = await auth_service.create_user_admin(user_data)
        return UserResponse(
            id=str(user["id"]),
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(status_code=500, detail="Could not create user")


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: str,
    user_update: UserUpdate,
    current_user: Annotated[UserInDB, Depends(get_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Admin update user"""
    try:
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided")
            
        success = await auth_service.update_user_admin(user_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
            
        updated_user = await auth_service.get_user_by_id(user_id)
        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            full_name=updated_user.full_name,
            role=updated_user.role,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at
        )
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(status_code=500, detail="Could not update user")


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_admin(
    user_id: str,
    current_user: Annotated[UserInDB, Depends(get_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Admin delete user"""
    try:
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")
            
        success = await auth_service.delete_user_admin(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(status_code=500, detail="Could not delete user")




