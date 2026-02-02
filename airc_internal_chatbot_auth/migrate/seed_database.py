"""
Unified Database Seed Script - Khởi tạo toàn bộ database cho Auth Service

Script này tạo:
1. Collections và indexes
2. RBAC roles và permissions
3. Sample users (admin, teacher, student)

Chạy script:
    python seed_database.py

Hoặc chạy từ host vào Docker MongoDB:
    docker exec -it airc_chatbot_mongodb mongosh airc_auth_db --eval "db.dropDatabase()"
    python seed_database.py

Credentials sau khi seed:
    - admin@airc.edu.vn / Pass123
    - nguyen.van.a@airc.edu.vn / Pass123  
    - sv01@student.airc.edu.vn / Pass123
"""
import os
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from pymongo import MongoClient
from passlib.context import CryptContext

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Password hashing context - PHẢI GIỐNG VỚI AUTH SERVICE
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class DatabaseSeeder:
    """
    Unified seeder cho toàn bộ Auth database (Synchronous version for reliability)
    """
    
    def __init__(self, mongodb_url: str = "mongodb://localhost:27017", db_name: str = "airc_auth_db"):
        """
        Khởi tạo seeder
        
        Args:
            mongodb_url: MongoDB connection URL
            db_name: Database name
        """
        self.mongodb_url = mongodb_url
        self.db_name = db_name
        self.client: Optional[MongoClient] = None
        self.db = None
    
    def connect(self):
        """Kết nối tới MongoDB"""
        logger.info(f"🔌 Connecting to MongoDB: {self.mongodb_url}/{self.db_name}")
        try:
            self.client = MongoClient(self.mongodb_url)
            self.db = self.client[self.db_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB successfully\n")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise

    def close(self):
        """Đóng kết nối"""
        if self.client:
            self.client.close()
            logger.info("🔌 Connection closed")
    
    def drop_existing_data(self):
        """Xóa dữ liệu cũ (nếu có)"""
        logger.info("🗑️  Dropping existing collections...")
        
        collections = self.db.list_collection_names()
        for collection in collections:
            self.db[collection].drop()
            logger.info(f"   - Dropped: {collection}")
        
        logger.info("✅ Existing data cleared\n")
    
    def create_collections_and_indexes(self):
        """Tạo collections và indexes"""
        logger.info("📦 Creating collections and indexes...")
        
        # Users collection
        self.db.users.create_index("email", unique=True)
        logger.info("   - users: email index (unique)")
        
        # Roles collection
        self.db.roles.create_index("code", unique=True)
        logger.info("   - roles: code index (unique)")
        
        # Permissions collection
        self.db.permissions.create_index("code", unique=True)
        logger.info("   - permissions: code index (unique)")
        
        # User-Role mapping
        self.db.user_roles.create_index([("user_id", 1), ("role_id", 1)], unique=True)
        logger.info("   - user_roles: user_id + role_id index (unique)")
        
        # Role-Permission mapping
        self.db.role_permissions.create_index([("role_id", 1), ("permission_id", 1)], unique=True)
        logger.info("   - role_permissions: role_id + permission_id index (unique)")
        
        logger.info("✅ Collections and indexes created\n")
    
    def seed_roles(self) -> Dict[str, any]:
        """Tạo system roles"""
        logger.info("👥 Creating system roles...")
        
        roles = [
            {
                "name": "Administrator",
                "code": "admin",
                "description": "Quản trị viên hệ thống - Full access",
                "is_system": True,
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Teacher",
                "code": "teacher",
                "description": "Giảng viên - Tạo dataset, upload tài liệu, chat với bot",
                "is_system": True,
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Student",
                "code": "student",
                "description": "Sinh viên - Chỉ chat với bot",
                "is_system": True,
                "is_active": True,
                "created_at": datetime.utcnow()
            }
        ]
        
        result = self.db.roles.insert_many(roles)
        logger.info(f"✅ Created {len(result.inserted_ids)} roles\n")
        
        return {role["code"]: role_id for role, role_id in zip(roles, result.inserted_ids)}
    
    def seed_permissions(self) -> Dict[str, any]:
        """Tạo system permissions"""
        logger.info("🔐 Creating system permissions...")
        
        permissions = [
            # User management
            {"name": "View Users", "code": "users:view", "resource": "users", "action": "view", "description": "Xem danh sách users"},
            {"name": "Create User", "code": "users:create", "resource": "users", "action": "create", "description": "Tạo user mới"},
            {"name": "Update User", "code": "users:update", "resource": "users", "action": "update", "description": "Cập nhật user"},
            {"name": "Delete User", "code": "users:delete", "resource": "users", "action": "delete", "description": "Xóa user"},
            
            # RBAC management
            {"name": "Manage Roles", "code": "rbac:manage_roles", "resource": "rbac", "action": "manage", "description": "Quản lý roles"},
            {"name": "Manage Permissions", "code": "rbac:manage_permissions", "resource": "rbac", "action": "manage", "description": "Quản lý permissions"},
            
            # Dataset management
            {"name": "View Datasets", "code": "datasets:view", "resource": "datasets", "action": "view", "description": "Xem datasets"},
            {"name": "Create Dataset", "code": "datasets:create", "resource": "datasets", "action": "create", "description": "Tạo dataset"},
            {"name": "Update Dataset", "code": "datasets:update", "resource": "datasets", "action": "update", "description": "Cập nhật dataset"},
            {"name": "Delete Dataset", "code": "datasets:delete", "resource": "datasets", "action": "delete", "description": "Xóa dataset"},
            {"name": "Share Dataset", "code": "datasets:share", "resource": "datasets", "action": "share", "description": "Chia sẻ dataset"},

            # Chatbot management (Updated to match FE)
            {"name": "Create Chatbot", "code": "chatbots:create", "resource": "chatbots", "action": "create", "description": "Tạo chatbot mới"},
            {"name": "Use Chatbot", "code": "chatbots:use", "resource": "chatbots", "action": "use", "description": "Sử dụng chatbot để chat"},
            {"name": "Manage Own Chatbots", "code": "chatbots:manage:own", "resource": "chatbots", "action": "manage:own", "description": "Quản lý chatbot của mình"},
            {"name": "Manage Any Chatbots", "code": "chatbots:manage:any", "resource": "chatbots", "action": "manage:any", "description": "Quản lý tất cả chatbot (Admin)"},

            # Legacy/Helper (Optional, keep for backward compat if needed, or remove)
            # {"name": "Chat with Bot", "code": "chatbot:chat", ...}, 

            # AI Model management
            {"name": "View Models", "code": "model:view", "resource": "model", "action": "view", "description": "Xem danh sách models"},
            {"name": "Train Model", "code": "model:train", "resource": "model", "action": "train", "description": "Huấn luyện model mới"},
        ]
        
        # Add metadata
        for perm in permissions:
            perm["is_system"] = True
            perm["created_at"] = datetime.utcnow()
        
        # Clear existing permissions to avoid dupes if not dropped
        # self.db.permissions.delete_many({}) # Handled by drop_existing
        
        result = self.db.permissions.insert_many(permissions)
        logger.info(f"✅ Created {len(result.inserted_ids)} permissions\n")
        
        return {perm["code"]: perm_id for perm, perm_id in zip(permissions, result.inserted_ids)}
    
    def assign_permissions_to_roles(self, role_ids: dict, permission_ids: dict):
        """Gán permissions cho roles"""
        logger.info("🔗 Assigning permissions to roles...")
        
        # Check if helper permissions exist
        def get_perm(code):
            return permission_ids.get(code)

        # Admin: ALL permissions (Full Access)
        admin_perms = list(permission_ids.values())
        
        # Teacher: Tạo dataset, upload tài liệu, chat với bot (KHÔNG tạo chatbot)
        teacher_perms = [
            get_perm("datasets:view"),
            get_perm("datasets:create"),
            get_perm("datasets:update"),
            get_perm("datasets:delete"),
            get_perm("datasets:share"),

            get_perm("chatbots:use"),  # Chỉ sử dụng chatbot để chat
        ]
        # Remove None values
        teacher_perms = [p for p in teacher_perms if p]

        # Student: Chỉ chat với bot
        student_perms = [
            get_perm("chatbots:use"),
        ]
        # Remove None values
        student_perms = [p for p in student_perms if p]

        # Create role-permission mappings
        mappings = []
        
        def add_mapping(role_key, perms):
            if role_key not in role_ids:
                logger.warning(f"Role {role_key} not found for permission assignment")
                return
                
            for perm_id in perms:
                mappings.append({
                    "role_id": role_ids[role_key],
                    "permission_id": perm_id,
                    "created_at": datetime.utcnow()
                })

        add_mapping("admin", admin_perms)
        add_mapping("teacher", teacher_perms)
        add_mapping("student", student_perms)
        
        if mappings:
            self.db.role_permissions.insert_many(mappings)
            logger.info(f"✅ Assigned {len(mappings)} permissions to roles\n")
        else:
            logger.warning("⚠️ No permissions assigned (check role/perm codes)")

    def seed_users(self, role_ids: Dict[str, any]):
        """
        Tạo sample users
        
        QUAN TRỌNG: Password phải là "Pass123" để match với test script!
        """
        logger.info("👤 Creating sample users...")
        
        # Password PHẢI là "Pass123" - giống test script!
        password = "Pass123"
        hashed_password = pwd_context.hash(password)
        
        # Verify hash ngay lập tức
        if not pwd_context.verify(password, hashed_password):
            raise ValueError("❌ Password hash verification failed!")
        
        users = [
            {
                "email": "admin@airc.edu.vn",
                "full_name": "Admin AIRC",
                "hashed_password": hashed_password,
                "role_code": "admin",
                "is_active": True,
                "is_verified": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "email": "nguyen.van.a@airc.edu.vn",
                "full_name": "TS. Nguyễn Văn A",
                "hashed_password": hashed_password,
                "role_code": "teacher",
                "is_active": True,
                "is_verified": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "email": "sv01@student.airc.edu.vn",
                "full_name": "Hoàng Quốc Bảo",
                "hashed_password": hashed_password,
                "role_code": "student",
                "is_active": True,
                "is_verified": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        # Insert users và assign roles
        for user in users:
            role_code = user.pop("role_code")
            
            if role_code not in role_ids:
                logger.error(f"❌ Role {role_code} not found for user {user['email']}")
                continue
                
            try:
                # Insert user
                result = self.db.users.insert_one(user)
                user_id = result.inserted_id
                
                # Assign role
                self.db.user_roles.insert_one({
                    "user_id": user_id,
                    "role_id": role_ids[role_code],
                    "assigned_at": datetime.utcnow()
                })
                
                logger.info(f"   - Created: {user['email']} ({role_code})")
            except Exception as e:
                logger.error(f"   ❌ Failed to create {user['email']}: {e}")
        
        logger.info(f"✅ User creation completed\n")
    
    def verify_data(self):
        """Verify dữ liệu đã seed"""
        logger.info("=" * 80)
        logger.info("✅ DATABASE SEEDING COMPLETED!")
        logger.info("=" * 80)
        
        # Count documents
        users_count = self.db.users.count_documents({})
        roles_count = self.db.roles.count_documents({})
        permissions_count = self.db.permissions.count_documents({})
        
        logger.info(f"\n📊 Statistics:")
        logger.info(f"   - Users: {users_count}")
        logger.info(f"   - Roles: {roles_count}")
        logger.info(f"   - Permissions: {permissions_count}")
        
        # Show login credentials
        logger.info(f"\n🔑 Login Credentials (Password: Pass123):")
        logger.info("   " + "-" * 76)
        logger.info(f"   {'Email':<35} {'Role':<15} {'Password':<15}")
        logger.info("   " + "-" * 76)
        
        users = list(self.db.users.find().limit(100))
        for user in users:
            # Get role
            user_role = self.db.user_roles.find_one({"user_id": user["_id"]})
            if user_role:
                role = self.db.roles.find_one({"_id": user_role["role_id"]})
                role_name = role["code"] if role else "unknown"
            else:
                role_name = "no role"
            
            logger.info(f"   {user['email']:<35} {role_name:<15} Pass123")
        
        logger.info("   " + "-" * 76)
        logger.info(f"\n🎉 Ready to test! Run: python tester/test_complete_47_apis.py")
        logger.info("=" * 80 + "\n")
    
    def run(self, drop_existing: bool = True):
        """
        Chạy toàn bộ seeding process
        
        Args:
            drop_existing: Có xóa dữ liệu cũ không (default: True)
        """
        try:
            self.connect()
            
            if drop_existing:
                self.drop_existing_data()
            
            self.create_collections_and_indexes()
            
            role_ids = self.seed_roles()
            permission_ids = self.seed_permissions()
            self.assign_permissions_to_roles(role_ids, permission_ids)
            self.seed_users(role_ids)
            
            self.verify_data()
            
        except Exception as e:
            logger.error(f"\n❌ Seeding failed: {e}")
            traceback.print_exc()
            raise
        finally:
            self.close()

def main():
    """Main entry point"""
    # Ưu tiên dùng environment variable MONGODB_URL
    mongodb_url = os.getenv('MONGODB_URL')
    
    if not mongodb_url:
        # Auto-detect environment: Docker hoặc localhost
        in_docker = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')
        
        if in_docker:
            # Trong Docker container, dùng service name
            mongodb_url = "mongodb://mongodb:27017"
            logger.info("🐳 Running inside Docker container")
        else:
            # Chạy từ host machine
            mongodb_url = "mongodb://localhost:27017"
            logger.info("💻 Running on host machine")
    else:
        logger.info(f"📡 Using MONGODB_URL from environment")
    
    db_name = os.getenv('MONGODB_DB_NAME', 'airc_auth_db')
    
    seeder = DatabaseSeeder(
        mongodb_url=mongodb_url,
        db_name=db_name
    )
    
    seeder.run(drop_existing=True)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  AIRC AUTH DATABASE SEEDER (SYNC)")
    print("=" * 80 + "\n")
    
    main()
