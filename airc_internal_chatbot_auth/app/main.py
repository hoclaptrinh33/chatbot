"""
FastAPI Main Application - Auth Service
Production-ready với Rate Limiting, Security Headers, và Input Validation
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.core import settings, connect_to_mongo, close_mongo_connection
from app.core.rate_limiter import RateLimitMiddleware, rate_limiter
from app.core.security_middleware import (
    SecurityHeadersMiddleware,
    RequestIDMiddleware,
    InputSanitizationMiddleware,
    RequestSizeLimitMiddleware
)
from app.api.v1 import auth, rbac  # Import RBAC router

# Setup logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Auth Service starting up...")
    await connect_to_mongo()
    logger.info("✓ MongoDB connected")
    logger.info("✓ Rate limiter initialized")
    logger.info("✓ Security middleware enabled")
    logger.info("Auth Service startup complete - Production Ready!")
    
    yield
    
    # Shutdown
    logger.info("Auth Service shutting down...")
    await rate_limiter.cleanup()  # Cleanup rate limiter
    await close_mongo_connection()
    logger.info("Auth Service shutdown complete")


# Determine environment
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
    # Disable docs in production if needed
    docs_url="/docs" if not IS_PRODUCTION else None,
    redoc_url="/redoc" if not IS_PRODUCTION else None,
)

# ═══════════════════════════════════════════════════════════════
# MIDDLEWARE STACK (order matters - last added = first executed)
# ═══════════════════════════════════════════════════════════════

# 1. CORS middleware (must be first for preflight requests)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if IS_PRODUCTION else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
)

# 2. Request Size Limit (DoS protection)
app.add_middleware(RequestSizeLimitMiddleware, max_body_size=1024 * 1024)  # 1MB

# 3. Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# 4. Request ID (for tracing)
app.add_middleware(RequestIDMiddleware)

# 5. Input Sanitization
app.add_middleware(InputSanitizationMiddleware)

# 6. Rate Limiting (outermost - first check)
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

# Include Routers with /api prefix to match ingress
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(rbac.router, prefix="/api", tags=["RBAC Management"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AIRC Auth Service",
        "version": "1.0.0",
        "status": "running",
        "environment": "production" if IS_PRODUCTION else "development"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth"}
