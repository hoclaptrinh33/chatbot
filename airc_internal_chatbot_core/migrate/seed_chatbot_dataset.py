"""
Seed Chatbot & Dataset cho Core Service

Script này tạo:
1. Sample datasets cho thử nghiệm
2. Sample chatbot với cấu hình RAG
3. Gán chatbot cho users (teacher, student)

Lưu ý:
- Chạy SAU KHI đã seed Auth database (để có user IDs)
- Mỗi non-admin user chỉ được gán 1 chatbot

Chạy script:
    python migrate/seed_chatbot_dataset.py

Hoặc trong Docker:
    docker exec airc_core python migrate/seed_chatbot_dataset.py
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

from pymongo import MongoClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class CoreDataSeeder:
    """Seeder cho Core database (datasets, chatbots)"""
    
    def __init__(
        self, 
        core_mongodb_url: str = "mongodb://localhost:27017",
        core_db_name: str = "airc_chatbot",
        auth_mongodb_url: str = "mongodb://localhost:27017",
        auth_db_name: str = "airc_auth_db"
    ):
        self.core_mongodb_url = core_mongodb_url
        self.core_db_name = core_db_name
        self.auth_mongodb_url = auth_mongodb_url
        self.auth_db_name = auth_db_name
        
        self.core_client: Optional[MongoClient] = None
        self.auth_client: Optional[MongoClient] = None
        self.core_db = None
        self.auth_db = None
    
    def connect(self):
        """Kết nối tới MongoDB"""
        logger.info(f"🔌 Connecting to Core DB: {self.core_mongodb_url}/{self.core_db_name}")
        self.core_client = MongoClient(self.core_mongodb_url)
        self.core_db = self.core_client[self.core_db_name]
        
        logger.info(f"🔌 Connecting to Auth DB: {self.auth_mongodb_url}/{self.auth_db_name}")
        self.auth_client = MongoClient(self.auth_mongodb_url)
        self.auth_db = self.auth_client[self.auth_db_name]
        
        # Test connections
        self.core_client.admin.command('ping')
        self.auth_client.admin.command('ping')
        logger.info("✅ Connected to both databases\n")
    
    def close(self):
        """Đóng kết nối"""
        if self.core_client:
            self.core_client.close()
        if self.auth_client:
            self.auth_client.close()
        logger.info("🔌 Connections closed")
    
    def get_user_ids(self) -> Dict[str, str]:
        """Lấy user IDs từ Auth DB"""
        users = {}
        
        # Lấy admin
        admin = self.auth_db.users.find_one({"email": "admin@airc.edu.vn"})
        if admin:
            users["admin"] = str(admin["_id"])
        
        # Lấy teacher
        teacher = self.auth_db.users.find_one({"email": "nguyen.van.a@airc.edu.vn"})
        if teacher:
            users["teacher"] = str(teacher["_id"])
        
        # Lấy student
        student = self.auth_db.users.find_one({"email": "sv01@student.airc.edu.vn"})
        if student:
            users["student"] = str(student["_id"])
        
        logger.info(f"👥 Found users: {list(users.keys())}")
        return users
    
    def clear_existing_data(self):
        """Xóa dữ liệu cũ"""
        logger.info("🗑️  Clearing existing chatbots and datasets...")
        
        self.core_db.chatbots.delete_many({})
        self.core_db.datasets.delete_many({})
        self.core_db.files.delete_many({})
        self.core_db.dataset_files.delete_many({})
        
        logger.info("✅ Cleared existing data\n")
    
    def seed_datasets(self, user_ids: Dict[str, str]) -> List[str]:
        """Tạo sample datasets"""
        logger.info("📚 Creating sample datasets...")
        
        admin_id = user_ids.get("admin", "unknown")
        teacher_id = user_ids.get("teacher", "unknown")
        
        datasets = [
            {
                "name": "Tài liệu Toán học",
                "description": "Bộ tài liệu về toán học cơ bản và nâng cao",
                "visibility": "shared",
                "owner_id": admin_id,
                "status": "ready",
                "file_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": None
            },
            {
                "name": "Tài liệu Tiếng Anh",
                "description": "Giáo trình và bài tập tiếng Anh",
                "visibility": "shared",
                "owner_id": admin_id,
                "status": "ready",
                "file_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": None
            },
            {
                "name": "Quy định học vụ",
                "description": "Các quy định, quy chế về học vụ và đào tạo",
                "visibility": "public",
                "owner_id": admin_id,
                "status": "ready",
                "file_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": None
            },
            {
                "name": "Dataset của Teacher",
                "description": "Dataset tạo bởi giảng viên",
                "visibility": "private",
                "owner_id": teacher_id,
                "status": "ready",
                "file_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": None
            }
        ]
        
        result = self.core_db.datasets.insert_many(datasets)
        dataset_ids = [str(id) for id in result.inserted_ids]
        
        logger.info(f"✅ Created {len(dataset_ids)} datasets")
        for i, ds in enumerate(datasets):
            logger.info(f"   - {ds['name']} (ID: {dataset_ids[i][:8]}...)")
        
        return dataset_ids
    
    def seed_chatbots(self, user_ids: Dict[str, str], dataset_ids: List[str]) -> List[str]:
        """Tạo sample chatbots với assignment logic"""
        logger.info("\n🤖 Creating sample chatbots...")
        
        admin_id = user_ids.get("admin", "unknown")
        teacher_id = user_ids.get("teacher")
        student_id = user_ids.get("student")
        
        chatbots = [
            # Chatbot 1: Trợ lý học tập - Gán cho Teacher
            {
                "name": "Trợ lý Học tập",
                "description": "Chatbot hỗ trợ học tập, giải đáp thắc mắc về các môn học",
                "icon": None,
                "config": {
                    "model": "models/gemini-2.5-flash",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "system_prompt": "Bạn là trợ lý học tập thông minh. Hãy giúp học sinh giải đáp các câu hỏi về kiến thức một cách dễ hiểu, có ví dụ minh họa.",
                    "reranker": "Semantic",
                    "top_k": 5,
                    "similarity_threshold": 0.5,
                    "search_mode": "hybrid"
                },
                "dataset_ids": dataset_ids[:2] if len(dataset_ids) >= 2 else dataset_ids,  # Toán + Anh
                "allowed_roles": ["teacher", "admin"],
                "allowed_user_ids": [teacher_id] if teacher_id else [],  # Gán cho teacher
                "visibility": "public",
                "owner_id": admin_id,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": None
            },
            # Chatbot 2: Hỗ trợ học vụ - Gán cho Student
            {
                "name": "Hỗ trợ Học vụ",
                "description": "Chatbot giải đáp các thắc mắc về quy định, thủ tục học vụ",
                "icon": None,
                "config": {
                    "model": "models/gemini-2.5-flash",
                    "temperature": 0.5,
                    "max_tokens": 1024,
                    "system_prompt": "Bạn là trợ lý học vụ của trường. Hãy giải đáp các câu hỏi về quy định, thủ tục một cách chính xác và thân thiện.",
                    "reranker": "Semantic",
                    "top_k": 3,
                    "similarity_threshold": 0.6,
                    "search_mode": "hybrid"
                },
                "dataset_ids": [dataset_ids[2]] if len(dataset_ids) >= 3 else [],  # Quy định học vụ
                "allowed_roles": ["student", "admin"],
                "allowed_user_ids": [student_id] if student_id else [],  # Gán cho student
                "visibility": "public",
                "owner_id": admin_id,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": None
            },
            # Chatbot 3: Admin bot - Không gán cho ai cả (Admin dùng)
            {
                "name": "Admin Assistant",
                "description": "Chatbot dành riêng cho Admin, có quyền truy cập toàn bộ tài liệu",
                "icon": None,
                "config": {
                    "model": "models/gemini-2.5-pro",
                    "temperature": 0.3,
                    "max_tokens": 4096,
                    "system_prompt": "Bạn là trợ lý AI cao cấp cho quản trị viên. Hãy phân tích và trả lời chi tiết mọi câu hỏi.",
                    "reranker": "CrossEncoder",
                    "top_k": 10,
                    "similarity_threshold": 0.4,
                    "search_mode": "hybrid"
                },
                "dataset_ids": dataset_ids,  # Tất cả datasets
                "allowed_roles": ["admin"],
                "allowed_user_ids": [],  # Không gán cụ thể, admin luôn thấy
                "visibility": "private",
                "owner_id": admin_id,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": None
            }
        ]
        
        result = self.core_db.chatbots.insert_many(chatbots)
        chatbot_ids = [str(id) for id in result.inserted_ids]
        
        logger.info(f"✅ Created {len(chatbot_ids)} chatbots")
        for i, cb in enumerate(chatbots):
            assigned_to = cb.get("allowed_user_ids", [])
            assigned_str = f"(Assigned: {len(assigned_to)} users)" if assigned_to else "(No specific assignment)"
            logger.info(f"   - {cb['name']} {assigned_str}")
        
        return chatbot_ids
    
    def verify_data(self):
        """Kiểm tra dữ liệu đã tạo"""
        logger.info("\n" + "=" * 80)
        logger.info("✅ CORE DATABASE SEEDING COMPLETED!")
        logger.info("=" * 80)
        
        datasets_count = self.core_db.datasets.count_documents({})
        chatbots_count = self.core_db.chatbots.count_documents({})
        
        logger.info(f"\n📊 Statistics:")
        logger.info(f"   - Datasets: {datasets_count}")
        logger.info(f"   - Chatbots: {chatbots_count}")
        
        # Show chatbot assignments
        logger.info(f"\n🤖 Chatbot Assignments:")
        logger.info("   " + "-" * 60)
        
        chatbots = list(self.core_db.chatbots.find())
        for cb in chatbots:
            name = cb["name"]
            allowed_users = cb.get("allowed_user_ids", [])
            
            if allowed_users:
                # Lookup user emails
                user_emails = []
                for uid in allowed_users:
                    from bson import ObjectId
                    user = self.auth_db.users.find_one({"_id": ObjectId(uid)})
                    if user:
                        user_emails.append(user["email"])
                
                logger.info(f"   {name}:")
                for email in user_emails:
                    logger.info(f"      → {email}")
            else:
                logger.info(f"   {name}: (Admin only / No specific user)")
        
        logger.info("   " + "-" * 60)
        
        # Important note
        logger.info(f"\n⚠️  LƯU Ý:")
        logger.info("   - Mỗi Teacher/Student chỉ được gán 1 chatbot")
        logger.info("   - Admin có thể dùng tất cả chatbots")
        logger.info("   - Để đổi chatbot cho user, cần xóa assignment cũ trước")
        
        logger.info("\n" + "=" * 80 + "\n")
    
    def run(self, clear_existing: bool = True):
        """Chạy seeding"""
        try:
            self.connect()
            
            # Get user IDs from Auth DB
            user_ids = self.get_user_ids()
            
            if not user_ids:
                logger.error("❌ No users found! Please run Auth seed first.")
                return
            
            if clear_existing:
                self.clear_existing_data()
            
            # Seed data
            dataset_ids = self.seed_datasets(user_ids)
            chatbot_ids = self.seed_chatbots(user_ids, dataset_ids)
            
            self.verify_data()
            
        except Exception as e:
            logger.error(f"\n❌ Seeding failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.close()


def main():
    """Main entry point"""
    # Auto-detect environment
    in_docker = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')
    
    if in_docker:
        mongodb_url = "mongodb://mongodb:27017"
        logger.info("🐳 Running inside Docker container")
    else:
        mongodb_url = "mongodb://localhost:27017"
        logger.info("💻 Running on host machine")
    
    seeder = CoreDataSeeder(
        core_mongodb_url=mongodb_url,
        core_db_name="airc_chatbot",
        auth_mongodb_url=mongodb_url,
        auth_db_name="airc_auth_db"
    )
    
    seeder.run(clear_existing=True)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  AIRC CORE DATABASE SEEDER (Chatbots & Datasets)")
    print("=" * 80 + "\n")
    
    main()
