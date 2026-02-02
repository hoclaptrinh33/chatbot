"""
Rate Limiter - Production-ready rate limiting cho Auth Service
Sử dụng in-memory storage hoặc Redis cho distributed systems
"""
import time
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration cho rate limiting"""
    # Số request tối đa trong window
    max_requests: int = 100
    # Thời gian window (seconds)
    window_seconds: int = 60
    # Số request burst cho phép
    burst_limit: int = 20
    # Thời gian burst window (seconds)
    burst_window: int = 1


@dataclass
class RateLimitEntry:
    """Entry lưu thông tin rate limit của một client"""
    requests: int = 0
    window_start: float = field(default_factory=time.time)
    burst_requests: int = 0
    burst_start: float = field(default_factory=time.time)
    blocked_until: float = 0


class InMemoryRateLimiter:
    """
    In-memory rate limiter với sliding window algorithm.
    Phù hợp cho single-instance deployment.
    Cho distributed systems, sử dụng Redis-based rate limiter.
    """
    
    def __init__(self):
        self._store: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = asyncio.Lock()
        
        # Endpoint-specific configurations
        self._endpoint_configs: Dict[str, RateLimitConfig] = {
            # Auth endpoints - stricter limits
            "/auth/login": RateLimitConfig(max_requests=10, window_seconds=60, burst_limit=5, burst_window=10),
            "/auth/register": RateLimitConfig(max_requests=10, window_seconds=60, burst_limit=5, burst_window=10),
            "/auth/verify": RateLimitConfig(max_requests=200, window_seconds=60, burst_limit=50, burst_window=1),
            # Default for other endpoints
            "default": RateLimitConfig(max_requests=100, window_seconds=60, burst_limit=20, burst_window=1),
        }
        
        # Blocked IPs cache (for brute force protection)
        self._blocked_ips: Dict[str, float] = {}
        
        # Failed login attempts tracking
        self._failed_logins: Dict[str, int] = defaultdict(int)
        
    def _get_client_key(self, request: Request) -> str:
        """Generate unique key for client identification"""
        # Prefer X-Forwarded-For for clients behind proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Combine IP with path for endpoint-specific limiting
        path = request.url.path
        key = f"{client_ip}:{path}"
        return key
    
    def _get_ip_key(self, request: Request) -> str:
        """Get client IP only (for blocking)"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _get_config(self, path: str) -> RateLimitConfig:
        """Get rate limit config for path"""
        return self._endpoint_configs.get(path, self._endpoint_configs["default"])
    
    async def is_blocked(self, request: Request) -> Tuple[bool, Optional[int]]:
        """Check if client is temporarily blocked"""
        ip = self._get_ip_key(request)
        
        async with self._lock:
            if ip in self._blocked_ips:
                blocked_until = self._blocked_ips[ip]
                now = time.time()
                
                if now < blocked_until:
                    retry_after = int(blocked_until - now)
                    return True, retry_after
                else:
                    # Block expired
                    del self._blocked_ips[ip]
                    if ip in self._failed_logins:
                        del self._failed_logins[ip]
        
        return False, None
    
    async def record_failed_login(self, request: Request):
        """Record failed login attempt for brute force protection"""
        ip = self._get_ip_key(request)
        
        async with self._lock:
            self._failed_logins[ip] += 1
            failed_count = self._failed_logins[ip]
            
            # Progressive blocking
            if failed_count >= 10:
                # Block for 1 hour after 10 failures
                self._blocked_ips[ip] = time.time() + 3600
                logger.warning(f"[RATE_LIMIT] IP {ip} blocked for 1 hour after {failed_count} failed logins")
            elif failed_count >= 5:
                # Block for 5 minutes after 5 failures
                self._blocked_ips[ip] = time.time() + 300
                logger.warning(f"[RATE_LIMIT] IP {ip} blocked for 5 minutes after {failed_count} failed logins")
    
    async def reset_failed_logins(self, request: Request):
        """Reset failed login counter on successful login"""
        ip = self._get_ip_key(request)
        async with self._lock:
            if ip in self._failed_logins:
                del self._failed_logins[ip]
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict]:
        """
        Check if request should be rate limited.
        
        Returns:
            Tuple[bool, Dict]: (is_allowed, headers)
            - is_allowed: True if request is allowed
            - headers: Rate limit headers to include in response
        """
        key = self._get_client_key(request)
        path = request.url.path
        config = self._get_config(path)
        now = time.time()
        
        async with self._lock:
            entry = self._store[key]
            
            # Reset window if expired
            if now - entry.window_start >= config.window_seconds:
                entry.requests = 0
                entry.window_start = now
            
            # Reset burst window if expired
            if now - entry.burst_start >= config.burst_window:
                entry.burst_requests = 0
                entry.burst_start = now
            
            # Check burst limit
            if entry.burst_requests >= config.burst_limit:
                remaining = 0
                retry_after = int(config.burst_window - (now - entry.burst_start)) + 1
                headers = {
                    "X-RateLimit-Limit": str(config.max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(entry.window_start + config.window_seconds)),
                    "Retry-After": str(retry_after)
                }
                return False, headers
            
            # Check window limit
            if entry.requests >= config.max_requests:
                remaining = 0
                retry_after = int(config.window_seconds - (now - entry.window_start)) + 1
                headers = {
                    "X-RateLimit-Limit": str(config.max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(entry.window_start + config.window_seconds)),
                    "Retry-After": str(retry_after)
                }
                return False, headers
            
            # Increment counters
            entry.requests += 1
            entry.burst_requests += 1
            
            remaining = config.max_requests - entry.requests
            headers = {
                "X-RateLimit-Limit": str(config.max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(entry.window_start + config.window_seconds))
            }
            
            return True, headers
    
    async def cleanup(self):
        """Cleanup expired entries (run periodically)"""
        now = time.time()
        async with self._lock:
            expired_keys = [
                key for key, entry in self._store.items()
                if now - entry.window_start > 3600  # 1 hour old
            ]
            for key in expired_keys:
                del self._store[key]
            
            # Cleanup blocked IPs
            expired_blocks = [
                ip for ip, until in self._blocked_ips.items()
                if now > until
            ]
            for ip in expired_blocks:
                del self._blocked_ips[ip]
                if ip in self._failed_logins:
                    del self._failed_logins[ip]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware for rate limiting"""
    
    def __init__(self, app, rate_limiter: InMemoryRateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Check if IP is blocked - CHỈ áp dụng cho /auth/login
        if request.url.path == "/auth/login":
            is_blocked, retry_after = await self.rate_limiter.is_blocked(request)
            if is_blocked:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Tài khoản của bạn đã bị tạm khóa do đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {retry_after} giây.",
                        "retry_after": retry_after,
                        "error_code": "BRUTE_FORCE_BLOCKED"
                    },
                    headers={"Retry-After": str(retry_after)}
                )
        
        # Check rate limit
        is_allowed, headers = await self.rate_limiter.check_rate_limit(request)
        
        if not is_allowed:
            retry_after = int(headers.get("Retry-After", 60))
            path = request.url.path
            
            # Custom messages cho từng endpoint
            if path == "/auth/register":
                detail = f"Bạn đã đăng ký quá nhiều lần. Vui lòng đợi {retry_after} giây trước khi thử lại."
                error_code = "REGISTER_RATE_LIMIT"
            elif path == "/auth/login":
                detail = f"Bạn đã đăng nhập quá nhiều lần. Vui lòng đợi {retry_after} giây trước khi thử lại."
                error_code = "LOGIN_RATE_LIMIT"
            else:
                detail = f"Quá nhiều yêu cầu. Vui lòng thử lại sau {retry_after} giây."
                error_code = "RATE_LIMIT"
                
            logger.warning(f"[RATE_LIMIT] Rate limit exceeded for {path} from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": detail,
                    "retry_after": retry_after,
                    "error_code": error_code
                },
                headers=headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# Singleton instance
rate_limiter = InMemoryRateLimiter()
