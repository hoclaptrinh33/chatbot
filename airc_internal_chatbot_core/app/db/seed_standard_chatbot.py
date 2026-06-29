import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import connect_to_mongo, mongodb
from app.repositories.chatbot_repository import ChatbotRepository
from app.repositories.dataset_repository import DatasetRepository
from app.models.chatbot_schemas import ChatbotConfigModel

async def seed():
    print("🌱 Starting database seed...")
    await connect_to_mongo()
    
    # Direct access to db from singleton
    db = mongodb.db
    if db is None:
        print("❌ Error: Database connection failed (db is None)")
        return

    chatbot_repo = ChatbotRepository(db)
    dataset_repo = DatasetRepository(db)

    print("Seeding AIRC Standard Chatbots (Role Separation)...")
    
    # 1. Ensure Standard Dataset Exists
    dataset_name = "General Knowledge"
    dataset_id = None
    
    existing_ds = await db.datasets.find_one({"name": dataset_name})
    
    if existing_ds:
        dataset_id = str(existing_ds["_id"])
        print(f"✅ Dataset '{dataset_name}' already exists ({dataset_id})")
    else:
        print(f"➕ Creating dataset '{dataset_name}'...")
        new_ds = await dataset_repo.create_dataset(
            name=dataset_name,
            owner_id="system"
        )
        dataset_id = new_ds["id"]
        print(f"✅ Created dataset '{dataset_name}' ({dataset_id})")

    valid_dataset_ids = [dataset_id] if dataset_id else []
    
    # 2. Define Bots
    bots = [
        {
            "name": "AIRC Student Helper",
            "description": "Trợ lý học tập dành riêng cho sinh viên.",
            "dataset_ids": valid_dataset_ids,
            "allowed_roles": ["student"], # STRICTLY STUDENT
            "config": {
                "model": "gemma-4-26b-qat",
                "temperature": 0.7,
                "system_prompt": "Bạn là trợ lý ảo hỗ trợ sinh viên AIRC. Hãy giải thích kỹ thuật một cách dễ hiểu, tập trung vào kiến thức cơ bản.",
                "search_mode": "hybrid", 
                "top_k": 3,
                "max_tokens": 2048,
                "reranker": "Semantic",
                "similarity_threshold": 0.5
            },
            "visibility": "private", 
            "owner_id": "system",
            "is_active": True,
            "updated_at": datetime.utcnow()
        },
        {
            "name": "AIRC Teacher Assistant",
            "description": "Hỗ trợ giảng viên soạn giáo án và nghiên cứu.",
            "dataset_ids": valid_dataset_ids,
            "allowed_roles": ["teacher"], # STRICTLY TEACHER
            "config": {
                "model": "qwen-3.6-35b",
                "temperature": 0.5,
                "system_prompt": "Bạn là trợ lý ảo hỗ trợ giảng viên AIRC. Hãy cung cấp thông tin chuyên sâu, trích dẫn tài liệu chính xác và hỗ trợ soạn thảo nội dung học thuật.",
                "search_mode": "hybrid", 
                "top_k": 5,
                "max_tokens": 2048,
                "reranker": "Semantic",
                "similarity_threshold": 0.5
            },
            "visibility": "private",
            "owner_id": "system",
            "is_active": True,
            "updated_at": datetime.utcnow()
        },
        {
            "name": "AIRC System Admin",
            "description": "Quản trị viên hệ thống.",
            "dataset_ids": valid_dataset_ids, # Admin sees all
            "allowed_roles": ["admin"], # STRICTLY ADMIN
            "config": {
                "model": "qwen-3.6-35b",
                "temperature": 0.1,
                "system_prompt": "Bạn là trợ lý quản trị hệ thống. Trả lời ngắn gọn, súc tích và chính xác.",
                "search_mode": "hybrid", 
                "top_k": 5,
                "max_tokens": 2048,
                "reranker": "Semantic",
                "similarity_threshold": 0.5
            },
            "visibility": "private", 
            "owner_id": "system",
            "is_active": True,
            "updated_at": datetime.utcnow()
        }
    ]
    
    for bot_data in bots:
        # Pydantic validation
        config_model = ChatbotConfigModel(**bot_data["config"])
        bot_data["config"] = config_model.model_dump()

        # Use find_one from BaseRepository
        existing = await chatbot_repo.find_one({"name": bot_data["name"]})
        
        if existing:
            print(f"🔄 Chatbot '{bot_data['name']}' already exists. Updating...")
            update_data = {k: v for k, v in bot_data.items() if k != "_id"}
            # Use update_one from BaseRepository
            await chatbot_repo.update_one({"_id": existing["_id"]}, update_data)
            print(f"✅ Updated Chatbot '{bot_data['name']}'")
        else:
            print(f"➕ Creating Chatbot '{bot_data['name']}'...")
            bot_data["created_at"] = datetime.utcnow()
            # Use insert_one from BaseRepository
            await chatbot_repo.insert_one(bot_data)
            print(f"✅ Created Chatbot '{bot_data['name']}'")
            
    print("🌱 Seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
