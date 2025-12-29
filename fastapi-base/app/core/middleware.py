"""
API middleware for performance monitoring and caching
"""
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.performance import perf_monitor

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track API performance"""
    
    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.perf_counter()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.perf_counter() - start_time
        
        # Record metrics
        endpoint = f"{request.method} {request.url.path}"
        perf_monitor.record(endpoint, duration)
        
        # Add performance header
        response.headers["X-Process-Time"] = f"{duration:.3f}"
        
        # Log slow requests
        if duration > 1.0:  # > 1 second
            logger.warning(f"⚠️  Slow request: {endpoint} took {duration:.3f}s")
        
        return response


class CacheHeaderMiddleware(BaseHTTPMiddleware):
    """Add cache control headers"""
    
    def __init__(self, app: ASGIApp, default_ttl: int = 300):
        super().__init__(app)
        self.default_ttl = default_ttl
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add cache headers for GET requests
        if request.method == "GET":
            # Check if endpoint is cacheable
            if any(path in request.url.path for path in ['/topics', '/dashboard', '/stats']):
                response.headers["Cache-Control"] = f"public, max-age={self.default_ttl}"
                response.headers["ETag"] = self._generate_etag(request.url.path)
        
        return response
    
    def _generate_etag(self, path: str) -> str:
        """Generate simple ETag"""
        import hashlib
        return hashlib.md5(f"{path}:{time.time() // self.default_ttl}".encode()).hexdigest()[:16]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Log request
        logger.info(f"→ {request.method} {request.url.path}")
        
        # Process
        try:
            response = await call_next(request)
            logger.info(f"← {request.method} {request.url.path} - {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"✗ {request.method} {request.url.path} - Error: {e}")
            raise
