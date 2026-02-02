"""
Input Validators - Production-ready input validation
"""
import re
from typing import Optional
from pydantic import validator, field_validator
from app.models.user import UserCreate
import logging

logger = logging.getLogger(__name__)


class ValidationPatterns:
    """Common validation regex patterns"""
    
    # Email: RFC 5322 simplified
    EMAIL = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    # Password requirements:
    # - At least 8 characters
    # - At least 1 uppercase letter
    # - At least 1 lowercase letter
    # - At least 1 digit
    # - At least 1 special character
    PASSWORD_STRONG = re.compile(
        r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    )
    
    # Password minimum (for backwards compatibility)
    PASSWORD_MIN = re.compile(r'^.{8,}$')
    
    # Username/Name: Letters, numbers, spaces, Vietnamese characters
    NAME = re.compile(
        r'^[\w\s\u00C0-\u024F\u1E00-\u1EFF]{2,100}$'
    )
    
    # Student ID: Alphanumeric
    STUDENT_ID = re.compile(r'^[A-Za-z0-9]{5,20}$')
    
    # Phone: Vietnamese phone numbers
    PHONE_VN = re.compile(r'^(0|\+84)[0-9]{9,10}$')


class InputValidator:
    """Utility class for input validation"""
    
    # Common SQL injection keywords to block
    SQL_KEYWORDS = {
        'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'exec', 'execute', 'union', 'fetch', 'declare', 'truncate'
    }
    
    # XSS patterns
    XSS_PATTERNS = [
        '<script', 'javascript:', 'onerror=', 'onload=', 'onclick=',
        '<iframe', '<object', '<embed', 'expression('
    ]
    
    @classmethod
    def validate_email(cls, email: str) -> tuple[bool, str]:
        """
        Validate email format
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not email:
            return False, "Email không được để trống"
        
        email = email.strip().lower()
        
        if len(email) > 254:
            return False, "Email quá dài (tối đa 254 ký tự)"
        
        if not ValidationPatterns.EMAIL.match(email):
            return False, "Định dạng email không hợp lệ"
        
        # Check for suspicious content
        if cls._has_injection(email):
            logger.warning(f"[VALIDATION] Suspicious email input: {email[:50]}")
            return False, "Email chứa ký tự không hợp lệ"
        
        return True, ""
    
    @classmethod
    def validate_password(cls, password: str, require_strong: bool = True) -> tuple[bool, str]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            require_strong: Require strong password (uppercase, lowercase, digit, special char)
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not password:
            return False, "Mật khẩu không được để trống"
        
        if len(password) < 8:
            return False, "Mật khẩu phải có ít nhất 8 ký tự"
        
        if len(password) > 128:
            return False, "Mật khẩu quá dài (tối đa 128 ký tự)"
        
        if require_strong:
            errors = []
            
            if not re.search(r'[a-z]', password):
                errors.append("ít nhất 1 chữ thường")
            
            if not re.search(r'[A-Z]', password):
                errors.append("ít nhất 1 chữ hoa")
            
            if not re.search(r'\d', password):
                errors.append("ít nhất 1 chữ số")
            
            if not re.search(r'[@$!%*?&]', password):
                errors.append("ít nhất 1 ký tự đặc biệt (@$!%*?&)")
            
            if errors:
                return False, f"Mật khẩu phải có: {', '.join(errors)}"
        
        # Check for common weak passwords
        common_passwords = {
            'password', '12345678', 'qwerty123', 'admin123', 'letmein',
            'welcome1', 'password1', 'Password1', 'Password123'
        }
        
        if password.lower() in common_passwords or password in common_passwords:
            return False, "Mật khẩu quá phổ biến, vui lòng chọn mật khẩu khác"
        
        return True, ""
    
    @classmethod
    def validate_name(cls, name: str, field_name: str = "Tên") -> tuple[bool, str]:
        """
        Validate name/username
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not name:
            return False, f"{field_name} không được để trống"
        
        name = name.strip()
        
        if len(name) < 2:
            return False, f"{field_name} phải có ít nhất 2 ký tự"
        
        if len(name) > 100:
            return False, f"{field_name} quá dài (tối đa 100 ký tự)"
        
        # Check for suspicious content
        if cls._has_injection(name):
            logger.warning(f"[VALIDATION] Suspicious name input: {name[:50]}")
            return False, f"{field_name} chứa ký tự không hợp lệ"
        
        return True, ""
    
    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """
        Sanitize string input by removing/escaping dangerous characters
        """
        if not value:
            return value
        
        # Strip whitespace
        value = value.strip()
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Escape HTML entities
        html_escapes = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;',
        }
        
        for char, escape in html_escapes.items():
            value = value.replace(char, escape)
        
        return value
    
    @classmethod
    def _has_injection(cls, value: str) -> bool:
        """Check if value contains potential injection patterns"""
        value_lower = value.lower()
        
        # Check SQL keywords with word boundaries
        for keyword in cls.SQL_KEYWORDS:
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, value_lower):
                return True
        
        # Check XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if pattern.lower() in value_lower:
                return True
        
        return False


def create_validated_user_create():
    """
    Factory function to create UserCreate model with enhanced validation.
    Call this to get a validated user registration model.
    """
    from pydantic import BaseModel, EmailStr, Field, field_validator
    from typing import Optional
    
    class ValidatedUserCreate(BaseModel):
        """User registration with production validation"""
        
        email: EmailStr = Field(..., description="Email address")
        password: str = Field(..., min_length=8, max_length=128)
        full_name: str = Field(..., min_length=2, max_length=100)
        student_id: Optional[str] = Field(None, max_length=20)
        
        @field_validator('email')
        @classmethod
        def validate_email_format(cls, v):
            is_valid, error = InputValidator.validate_email(v)
            if not is_valid:
                raise ValueError(error)
            return v.lower().strip()
        
        @field_validator('password')
        @classmethod
        def validate_password_strength(cls, v):
            # For production, require strong passwords
            is_valid, error = InputValidator.validate_password(v, require_strong=False)
            if not is_valid:
                raise ValueError(error)
            return v
        
        @field_validator('full_name')
        @classmethod
        def validate_full_name(cls, v):
            is_valid, error = InputValidator.validate_name(v, "Họ tên")
            if not is_valid:
                raise ValueError(error)
            return InputValidator.sanitize_string(v)
        
        @field_validator('student_id')
        @classmethod
        def validate_student_id(cls, v):
            if v is None:
                return v
            v = v.strip().upper()
            if not ValidationPatterns.STUDENT_ID.match(v):
                raise ValueError("Mã sinh viên không hợp lệ (5-20 ký tự chữ và số)")
            return v
    
    return ValidatedUserCreate
