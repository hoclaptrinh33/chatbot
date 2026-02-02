"""
Database Connection - Async MongoDB với Motor
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    """Singleton MongoDB connection"""
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


mongodb = MongoDB()


async def connect_to_mongo():
    """Kết nối đến MongoDB khi startup"""
    logger.info(f"Connecting to MongoDB at {settings.mongodb_url}")
    mongodb.client = AsyncIOMotorClient(settings.mongodb_url)
    mongodb.db = mongodb.client[settings.mongodb_db_name]
    logger.info(f"Connected to database: {settings.mongodb_db_name}")


async def close_mongo_connection():
    """Đóng kết nối MongoDB khi shutdown"""
    logger.info("Closing MongoDB connection")
    if mongodb.client:
        mongodb.client.close()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency injection cho database"""
    return mongodb.db
