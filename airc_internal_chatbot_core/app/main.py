from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.core import settings, connect_to_mongo, close_mongo_connection
from app.core.cors import resolve_cors_origins
from app.api.v1 import chat, datasets, files
from app.api.v1 import sessions, chatbots, stats, voice, settings as system_settings
from app.services.llm_service import llm_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("[STARTUP] Connecting to MongoDB...")
    await connect_to_mongo()
    logger.info("[STARTUP] MongoDB connected")

    # Heavy embedding/rerank models stay lazy on the API process.
    # Set PRELOAD_MODELS=true on the worker (or a dedicated inference box).
    if os.getenv("PRELOAD_MODELS", "false").lower() in {"1", "true", "yes"}:
        logger.info("[STARTUP] PRELOAD_MODELS=true — loading embedding/reranker")
        try:
            from app.services.embedding_service import embedding_service
            from app.services.rerank_service import rerank_service
            embedding_service.preload_models()
            rerank_service.preload_models()
            logger.info("[STARTUP] Embedding and reranker preloaded")
        except Exception as e:
            logger.error(f"[STARTUP] Model preload failed: {e} — first request will be slower")
    else:
        logger.info("[STARTUP] Skipping model preload (PRELOAD_MODELS!=true)")

    try:
        llm_service._configure()
    except Exception as e:
        logger.warning(f"[STARTUP] LLM configure skipped: {e}")
    
    yield
    
    # Shutdown
    logger.info("[SHUTDOWN] Closing MongoDB connection...")
    await close_mongo_connection()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=resolve_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["Datasets"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])
app.include_router(chatbots.router, prefix="/api/v1/chatbots", tags=["Chatbots"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["Voice"])
app.include_router(system_settings.router, prefix="/api/v1/settings", tags=["Settings"])

# Mount static folder cho uploads (phục vụ ảnh bóc tách từ tài liệu)
import os
from fastapi.staticfiles import StaticFiles
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
