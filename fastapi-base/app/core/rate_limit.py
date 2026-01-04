"""
Rate Limiting Middleware for FastAPI
Prevents API abuse by limiting requests per IP
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import time
from typing import Dict, Tuple


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter
    For production, use Redis or similar distributed cache
    """
    
    def __init__(self, app, calls: int = 10, period: int = 60):
        super().__init__(app)
        self.calls = calls  # Number of calls allowed
        self.period = period  # Time period in seconds
        self.requests: Dict[str, list] = defaultdict(list)
        
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/api/v1/sync/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host
        
        # Clean old requests
        now = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.period
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.calls} requests per {self.period} seconds."
            )
        
        # Record this request
        self.requests[client_ip].append(now)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.calls - len(self.requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))
        
        return response


class TokenBucketRateLimiter:
    """
    More sophisticated token bucket rate limiter
    Allows bursts while maintaining average rate
    """
    
    def __init__(self, rate: float = 10.0, capacity: int = 20):
        self.rate = rate  # tokens per second
        self.capacity = capacity  # max tokens
        self.buckets: Dict[str, Tuple[float, float]] = {}  # {ip: (tokens, last_update)}
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        
        if client_ip not in self.buckets:
            self.buckets[client_ip] = (self.capacity - 1, now)
            return True
        
        tokens, last_update = self.buckets[client_ip]
        
        # Add tokens based on time passed
        time_passed = now - last_update
        tokens = min(self.capacity, tokens + time_passed * self.rate)
        
        if tokens < 1:
            return False
        
        # Consume token
        self.buckets[client_ip] = (tokens - 1, now)
        return True
    
    def get_wait_time(self, client_ip: str) -> float:
        """Get seconds to wait before next request"""
        if client_ip not in self.buckets:
            return 0.0
        
        tokens, _ = self.buckets[client_ip]
        if tokens >= 1:
            return 0.0
        
        return (1 - tokens) / self.rate


# Global rate limiter instance
rate_limiter = TokenBucketRateLimiter(rate=10.0, capacity=20)


async def rate_limit_dependency(request: Request):
    """
    Dependency to add rate limiting to specific endpoints
    
    Usage:
    @router.post("/endpoint", dependencies=[Depends(rate_limit_dependency)])
    """
    client_ip = request.client.host
    
    if not rate_limiter.is_allowed(client_ip):
        wait_time = rate_limiter.get_wait_time(client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please wait {wait_time:.1f} seconds.",
            headers={"Retry-After": str(int(wait_time) + 1)}
        )
