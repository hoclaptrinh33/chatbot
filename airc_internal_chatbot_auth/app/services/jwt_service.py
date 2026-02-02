"""
JWT Service - Xử lý JWT token operations theo chuẩn RFC 7519
"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
import uuid
from app.core.settings import settings
from app.models.user import TokenData
import logging

logger = logging.getLogger(__name__)


class JWTService:
    """
    Service xử lý JWT token theo chuẩn quốc tế RFC 7519
    
    Standard Claims được sử dụng:
    - sub (subject): User ID
    - iat (issued at): Thời điểm tạo token
    - exp (expiration): Thời điểm hết hạn
    - jti (JWT ID): Unique identifier cho token
    
    Custom Claims:
    - email: Email của user
    - role: Role của user (admin, teacher, student)
    """
    
    @staticmethod
    def create_access_token(user_id: str, email: str, role: str) -> str:
        """
        Tạo JWT access token theo chuẩn RFC 7519
        
        Args:
            user_id: User ID (sẽ được lưu vào claim 'sub')
            email: Email của user
            role: Role của user
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=settings.jwt_expire_minutes)
        
        # Payload theo chuẩn RFC 7519
        payload = {
            # Standard claims
            "sub": user_id,  # Subject (user identifier) - CHUẨN RFC 7519
            "iat": now,      # Issued at
            "exp": expire,   # Expiration time
            "jti": str(uuid.uuid4()),  # JWT ID - unique identifier cho token
            
            # Custom claims
            "email": email,
            "role": role
        }
        
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        logger.debug(f"Created access token for user {user_id} (email: {email}, role: {role})")
        return token
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """
        Tạo refresh token để renew access token
        
        Args:
            user_id: User ID
            
        Returns:
            Refresh token string
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=30)  # Refresh token có thời hạn dài hơn
        
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
            "type": "refresh"  # Đánh dấu đây là refresh token
        }
        
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        return token
    
    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """
        Verify và decode JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData nếu valid, None nếu invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            # Lấy user_id từ claim 'sub' theo chuẩn RFC 7519
            user_id = payload.get("sub")
            if not user_id:
                logger.warning("Token missing 'sub' claim")
                return None
            
            # Hỗ trợ backward compatibility với token cũ dùng 'user_id'
            if not user_id:
                user_id = payload.get("user_id")
                if user_id:
                    logger.warning("Token using deprecated 'user_id' claim, should use 'sub'")
            
            return TokenData(
                user_id=user_id,
                email=payload.get("email"),
                role=payload.get("role")
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None
    
    @staticmethod
    def decode_token_payload(token: str) -> Optional[dict]:
        """
        Decode token payload không verify (dùng cho debug)
        
        Args:
            token: JWT token
            
        Returns:
            Payload dict hoặc None
        """
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            logger.error(f"Decode token failed: {e}")
            return None
