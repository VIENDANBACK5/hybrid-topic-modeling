"""
Simple API Key Authentication Middleware
For production, use JWT tokens with proper user management
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from typing import Optional
import os

# API Key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Get API key from environment or use default (change in production!)
VALID_API_KEYS = set(os.getenv("API_KEYS", "dev-key-12345,admin-key-67890").split(","))

# Public endpoints that don't require auth
PUBLIC_ENDPOINTS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/sync/health",
    "/api/v1/sync/status",
    "/api/v1/sync/db-stats",
}


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    Verify API key from request header
    
    Usage in endpoint:
    ```python
    @router.post("/secure-endpoint")
    async def secure_endpoint(api_key: str = Depends(verify_api_key)):
        # Your code here
        pass
    ```
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Add X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key


def is_public_endpoint(path: str) -> bool:
    """Check if endpoint is public"""
    return any(path.startswith(public) for public in PUBLIC_ENDPOINTS)


# Usage example in main.py:
"""
from app.core.auth import verify_api_key
from fastapi import Depends

# Protect all sync endpoints except status/health
@router.post("/trigger")
async def trigger_sync(
    request: SyncTriggerRequest,
    api_key: str = Depends(verify_api_key)  # Add this
):
    # Your code
    pass

# Or use middleware to protect all endpoints
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not is_public_endpoint(request.url.path):
            api_key = request.headers.get("X-API-Key")
            if not api_key or api_key not in VALID_API_KEYS:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized"}
                )
        response = await call_next(request)
        return response

# Add to main.py:
app.add_middleware(AuthMiddleware)
"""
