"""
Core Configuration - Quản lý cấu hình từ environment variables
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings từ .env file"""
    
    # App
    app_name: str = "AIRC Internal Chatbot"
    debug: bool = False
    
    # MongoDB
    mongodb_url: str
    mongodb_db_name: str = "airc_chatbot"
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    
    # Gemini LLM
    gemini_api_key: str
    gemini_model: str = "models/gemini-2.5-flash"
    
    # Qdrant Vector DB
    qdrant_url: str = "http://qdrant:6333"

    # Redis (Arq background tasks)
    redis_url: str = "redis://localhost:6379/0"
    
    # Auth Service
    auth_service_url: str = "http://localhost:8001"
    
    # Upload
    max_upload_size: int = 209715200  # 200MB
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
