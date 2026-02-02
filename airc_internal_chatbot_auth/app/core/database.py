"""
Database Configuration - MongoDB connection với Motor (async driver)
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)

# Global MongoDB client
_mongo_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo():
    """Kết nối đến MongoDB khi startup"""
    global _mongo_client, _database
    
    try:
        logger.info(f"Connecting to MongoDB: {settings.mongodb_url}")
        _mongo_client = AsyncIOMotorClient(settings.mongodb_url)
        _database = _mongo_client[settings.mongodb_db_name]
        
        # Test connection
        await _mongo_client.admin.command('ping')
        logger.info(f"MongoDB connected successfully: {settings.mongodb_db_name}")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise


async def close_mongo_connection():
    """Đóng kết nối MongoDB khi shutdown"""
    global _mongo_client
    
    if _mongo_client:
        _mongo_client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """
    Lấy database instance
    
    Returns:
        AsyncIOMotorDatabase instance
    
    Raises:
        RuntimeError: Nếu database chưa được khởi tạo
    """
    if _database is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return _database
