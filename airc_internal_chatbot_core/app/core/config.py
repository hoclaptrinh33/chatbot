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
    
    # LLM Provider Configuration (OpenAI-compatible / Local or Cloud)
    llm_api_base_url: str = "http://localhost:11434/v1"
    llm_model_name: str = "gemma-4-26b-qat"
    llm_api_key: Optional[str] = "ollama"
    
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
