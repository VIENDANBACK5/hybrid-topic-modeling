"""
Caching layer for Pipeline MXH
Supports in-memory cache and Redis (if available)
"""
import json
import hashlib
import logging
from typing import Any, Optional, Callable
from functools import wraps
from datetime import timedelta
import asyncio

logger = logging.getLogger(__name__)

# In-memory cache
_memory_cache = {}
_cache_ttl = {}


class CacheManager:
    """Simple cache manager with TTL support"""
    
    def __init__(self, use_redis: bool = False):
        self.use_redis = use_redis
        self.redis_client = None
        
        if use_redis:
            try:
                import redis
                from app.core.config import settings
                self.redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    decode_responses=True
                )
                logger.info("Redis cache enabled")
            except (ImportError, Exception) as e:
                logger.warning(f"Redis not available, using memory cache: {e}")
                self.use_redis = False
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                return json.loads(value) if value else None
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                return None
        else:
            # Memory cache
            import time
            if key in _memory_cache:
                if key in _cache_ttl and _cache_ttl[key] < time.time():
                    # Expired
                    del _memory_cache[key]
                    del _cache_ttl[key]
                    return None
                return _memory_cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL (seconds)"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    key, 
                    ttl, 
                    json.dumps(value, ensure_ascii=False)
                )
                return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                return False
        else:
            # Memory cache
            import time
            _memory_cache[key] = value
            _cache_ttl[key] = time.time() + ttl
            return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
                return False
        else:
            if key in _memory_cache:
                del _memory_cache[key]
            if key in _cache_ttl:
                del _cache_ttl[key]
            return True
    
    def clear(self) -> bool:
        """Clear all cache"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.flushdb()
                return True
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
                return False
        else:
            _memory_cache.clear()
            _cache_ttl.clear()
            return True
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        count = 0
        if self.use_redis and self.redis_client:
            try:
                keys = self.redis_client.keys(f"*{pattern}*")
                if keys:
                    count = self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis invalidate error: {e}")
        else:
            # Memory cache pattern matching
            to_delete = [k for k in _memory_cache.keys() if pattern in k]
            for k in to_delete:
                del _memory_cache[k]
                if k in _cache_ttl:
                    del _cache_ttl[k]
            count = len(to_delete)
        
        logger.info(f"Invalidated {count} cache keys matching '{pattern}'")
        return count


# Global cache instance
cache_manager = CacheManager(use_redis=False)


def cached(ttl: int = 300, prefix: str = "default"):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        prefix: Cache key prefix
    
    Usage:
        @cached(ttl=600, prefix="topics")
        def get_topics():
            return expensive_operation()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = cache_manager._make_key(prefix, *args, **kwargs)
            
            # Try cache first
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {prefix}")
                return cached_value
            
            # Call function
            logger.debug(f"Cache miss: {prefix}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, result, ttl=ttl)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = cache_manager._make_key(prefix, *args, **kwargs)
            
            # Try cache first
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {prefix}")
                return cached_value
            
            # Call function
            logger.debug(f"Cache miss: {prefix}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, result, ttl=ttl)
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invalidate_cache(pattern: str = ""):
    """
    Invalidate cache by pattern
    
    Usage:
        # After training new model
        invalidate_cache("topics")
    """
    if pattern:
        return cache_manager.invalidate_pattern(pattern)
    else:
        return cache_manager.clear()
