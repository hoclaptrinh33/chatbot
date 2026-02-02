from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core import settings, connect_to_mongo, close_mongo_connection
from app.api.v1 import chat, datasets, files
from app.api.v1 import sessions, chatbots, stats
from app.services.embedding_service import embedding_service
from app.services.rerank_service import rerank_service
from app.services.llm_service import llm_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("[STARTUP] Connecting to MongoDB...")
    await connect_to_mongo()
    logger.info("[STARTUP] MongoDB connected")
    
    # Warmup: Preload AI models to prevent cold start
    logger.info("[STARTUP] Preloading AI models (Embedding, Reranker)...")
    try:
        # Preload embedding model
        embedding_service.preload_models()
        logger.info("[STARTUP] ✓ Embedding models loaded")
        
        # Preload reranker model
        rerank_service.preload_models()
        logger.info("[STARTUP] ✓ Reranker models loaded")
        
        # Configure LLM service (just API key check, no model download)
        llm_service._configure()
        logger.info("[STARTUP] ✓ LLM service configured")
        
        logger.info("[STARTUP] 🚀 All AI models ready - Cold start resolved!")
    except Exception as e:
        logger.error(f"[STARTUP] ⚠️ Model preload failed: {e} - First request will be slower")
    
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["Datasets"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])
app.include_router(chatbots.router, prefix="/api/v1/chatbots", tags=["Chatbots"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
