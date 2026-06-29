"""
Auth Service - Business logic cho authentication
"""
from passlib.context import CryptContext
from app.repositories.user_repository import UserRepository
from app.services.jwt_service import JWTService
from app.models.user import UserCreate, UserInDB, Token
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class AuthService:
    """Service xử lý authentication logic"""
    
    def __init__(self, user_repo: UserRepository):
        """
        Khởi tạo AuthService
        
        Args:
            user_repo: UserRepository instance
        """
        self.user_repo = user_repo
        self.jwt_service = JWTService()
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password
        
        Args:
            password: Plain password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password
        
        Args:
            plain_password: Plain password
            hashed_password: Hashed password
            
        Returns:
            True nếu password đúng
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    async def register(self, user_data: UserCreate) -> Token:
        """
        Đăng ký user mới
        
        Args:
            user_data: User registration data
            
        Returns:
            JWT Token
            
        Raises:
            ValueError: Nếu email đã tồn tại
        """
        # Kiểm tra email đã tồn tại
        if await self.user_repo.email_exists(user_data.email):
            raise ValueError("Email này đã được đăng ký")
        
        # Hash password
        hashed_password = self.hash_password(user_data.password)
        
        # Tạo user
        user = await self.user_repo.create_user(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role.value
        )
        
        logger.info(f"User registered: {user['email']}")
        
        # Tạo token
        access_token = self.jwt_service.create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user["role"]
        )
        
        return Token(access_token=access_token)
    
    async def login(self, email: str, password: str) -> Token:
        """
        Đăng nhập
        
        Args:
            email: Email
            password: Password
            
        Returns:
            JWT Token
            
        Raises:
            ValueError: Nếu credentials không đúng
        """
        # Lấy user từ DB
        user = await self.user_repo.get_by_email(email)
        print(f"DEBUG: Login attempt for {email}. Found user: {user is not None}", flush=True)
        
        if not user:
            print(f"DEBUG: User {email} not found in DB", flush=True)
            raise ValueError("Email không tồn tại trong hệ thống")
        
        # Verify password
        is_valid = self.verify_password(password, user["hashed_password"])
        if not is_valid:
            print(f"DEBUG: Login failed for {email}: Password mismatch", flush=True)
            raise ValueError("Mật khẩu không chính xác")
        
        # Kiểm tra user active
        if not user.get("is_active", True):
            raise ValueError("Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.")
        
        # Lấy role từ user_roles collection (RBAC pattern)
        # User không có field 'role' trực tiếp, phải query từ user_roles
        user_role_code = await self._get_user_role(user["id"])
        if not user_role_code:
            # Fallback: nếu không tìm thấy role, assign student role
            logger.warning(f"User {email} has no role assigned, defaulting to 'student'")
            user_role_code = "student"
        
        logger.info(f"User logged in: {email} (role: {user_role_code})")
        
        # Tạo token
        access_token = self.jwt_service.create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user_role_code
        )
        
        return Token(access_token=access_token)
    
    async def _get_user_role(self, user_id: str) -> Optional[str]:
        """
        Lấy role code của user từ user_roles collection
        
        Args:
            user_id: User ID
            
        Returns:
            Role code (admin, teacher, student) hoặc None
        """
        from bson import ObjectId
        
        # Get database
        db = self.user_repo.db
        
        # Find user_role mapping
        user_role = await db.user_roles.find_one({"user_id": ObjectId(user_id)})
        if not user_role:
            return None
        
        # Get role document
        role = await db.roles.find_one({"_id": user_role["role_id"]})
        if not role:
            return None
        
        return role.get("code")
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        Lấy user theo ID với role từ user_roles collection
        
        Args:
            user_id: User ID
            
        Returns:
            UserInDB với đầy đủ thông tin bao gồm role
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None
        
        # Lấy role từ user_roles collection (RBAC pattern)
        user_role_code = await self._get_user_role(user_id)
        
        # Thêm role vào user dict
        # Nếu không tìm thấy role, default là "student"
        user["role"] = user_role_code if user_role_code else "student"
        
        return UserInDB(**user)
    
    def verify_token(self, token: str):
        """
        Verify JWT token
        
        Args:
            token: JWT token
            
        Returns:
            TokenData hoặc None
        """
        return self.jwt_service.verify_token(token)
    
    async def get_all_users(self) -> list[UserInDB]:
        """
        Lấy tất cả users (Admin only)
        
        Returns:
            List of UserInDB
        """
        users = await self.user_repo.get_all_users()
        result = []
        for user in users:
            # Populate role from user_roles collection
            # Note: user dict from repo has 'id' (str) instead of '_id' (ObjectId) due to serialization
            try:
                role_code = await self._get_user_role(user["id"])
                user["role"] = role_code if role_code else "student"
            except Exception as e:
                logger.error(f"Error fetching role for user {user.get('id')}: {e}")
                user["role"] = "student"
                
            result.append(UserInDB(**user))
        return result

    async def create_user_admin(self, user_data: UserCreate) -> dict:
        """
        Admin tạo user mới (không cần register flow)
        
        Args:
            user_data: User data
            
        Returns:
            User document
        """
        # Kiểm tra email đã tồn tại
        if await self.user_repo.email_exists(user_data.email):
            raise ValueError("Email already in use")
        
        # Prevent creating admin user
        if user_data.role.value == "admin":
            raise ValueError("Không thể tạo user với quyền Admin. Admin là tài khoản duy nhất.")
        
        # Hash password
        hashed_password = self.hash_password(user_data.password)
        
        # Tạo user
        user = await self.user_repo.create_user(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role.value
        )
        
        # Assign role in user_roles collection
        if user_data.role:
            db = self.user_repo.db
            # Find role by code
            role_doc = await db.roles.find_one({"code": user_data.role.value})
            if role_doc:
                from datetime import datetime
                from bson import ObjectId
                
                await db.user_roles.update_one(
                    {"user_id": user["_id"], "role_id": role_doc["_id"]},
                    {"$set": {
                        "user_id": user["_id"],
                        "role_id": role_doc["_id"],
                        "assigned_at": datetime.utcnow()
                    }},
                    upsert=True
                )
                logger.info(f"Assigned role {user_data.role.value} to new user {user['email']}")
        
        return user

    async def update_user_admin(self, user_id: str, update_data: dict) -> bool:
        """
        Admin update user
        
        Args:
            user_id: User ID
            update_data: Data to update
            
        Returns:
            True if success
        """
        # Nếu có password mới, hash nó
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = self.hash_password(update_data["password"])
            del update_data["password"]
            
        return await self.user_repo.update_user(user_id, update_data)

    async def delete_user_admin(self, user_id: str) -> bool:
        """
        Admin delete user
        
        Args:
            user_id: User ID
            
        Returns:
            True if success
        """
        # TODO: Cleanup user roles assignments? 
        # For now just delete user doc
        return await self.user_repo.delete_user(user_id)

