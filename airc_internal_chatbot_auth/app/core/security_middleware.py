"""
Security Middleware - Production-ready security headers và request validation
"""
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import logging
import re

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Thêm security headers cho production deployment.
    Bảo vệ chống XSS, clickjacking, MIME-type sniffing, etc.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # Strict Transport Security (for HTTPS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Remove server identification headers
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Thêm unique request ID cho mỗi request để tracking và debugging.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Store in request state for logging
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} started "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} completed "
            f"status={response.status_code} time={process_time:.4f}s"
        )
        
        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Sanitize và validate input data để ngăn chặn injection attacks.
    """
    
    # Patterns cần chặn
    SQL_INJECTION_PATTERNS = [
        r"(\s|^)(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|FETCH|DECLARE)(\s|$)",
        r"(--)|(;)|(/\*)|(\*/)",
        r"(\s|^)(OR|AND)\s+\d+\s*=\s*\d+",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
    ]
    
    # Compiled patterns for performance
    SQL_REGEX = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
    XSS_REGEX = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]
    
    async def dispatch(self, request: Request, call_next):
        # Skip for health checks and docs
        if request.url.path in ["/health", "/", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Check query parameters
        for key, value in request.query_params.items():
            if self._is_suspicious(str(value)):
                logger.warning(
                    f"[SECURITY] Suspicious query param blocked: {key}={value[:50]}... "
                    f"from {request.client.host}"
                )
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid input detected"}
                )
        
        return await call_next(request)
    
    def _is_suspicious(self, value: str) -> bool:
        """Check if value contains suspicious patterns"""
        for pattern in self.SQL_REGEX:
            if pattern.search(value):
                return True
        
        for pattern in self.XSS_REGEX:
            if pattern.search(value):
                return True
        
        return False


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Giới hạn kích thước request body để ngăn DoS attacks.
    """
    
    MAX_BODY_SIZE = 1024 * 1024  # 1MB default
    
    def __init__(self, app, max_body_size: int = None):
        super().__init__(app)
        self.max_body_size = max_body_size or self.MAX_BODY_SIZE
    
    async def dispatch(self, request: Request, call_next):
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        
        if content_length:
            if int(content_length) > self.max_body_size:
                logger.warning(
                    f"[SECURITY] Request too large: {content_length} bytes "
                    f"from {request.client.host}"
                )
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"}
                )
        
        return await call_next(request)
