"""
Performance monitoring and optimization utilities
"""
import time
import logging
import functools
from typing import Callable, Any
from contextlib import contextmanager
import asyncio

logger = logging.getLogger(__name__)


@contextmanager
def timer(name: str):
    """Context manager for timing code blocks"""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    logger.info(f"⏱  {name}: {elapsed:.3f}s")


def measure_time(func: Callable) -> Callable:
    """Decorator to measure function execution time"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            logger.info(f"⏱  {func.__name__}: {elapsed:.3f}s")
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            logger.info(f"⏱  {func.__name__}: {elapsed:.3f}s")
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class PerformanceMonitor:
    """Track API performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'request_count': 0,
            'total_time': 0.0,
            'endpoints': {}
        }
    
    def record(self, endpoint: str, duration: float):
        """Record endpoint performance"""
        self.metrics['request_count'] += 1
        self.metrics['total_time'] += duration
        
        if endpoint not in self.metrics['endpoints']:
            self.metrics['endpoints'][endpoint] = {
                'count': 0,
                'total_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0
            }
        
        ep = self.metrics['endpoints'][endpoint]
        ep['count'] += 1
        ep['total_time'] += duration
        ep['min_time'] = min(ep['min_time'], duration)
        ep['max_time'] = max(ep['max_time'], duration)
    
    def get_stats(self):
        """Get performance statistics"""
        stats = {
            'total_requests': self.metrics['request_count'],
            'total_time': round(self.metrics['total_time'], 2),
            'avg_time': round(
                self.metrics['total_time'] / max(1, self.metrics['request_count']), 
                3
            ),
            'endpoints': {}
        }
        
        for endpoint, data in self.metrics['endpoints'].items():
            stats['endpoints'][endpoint] = {
                'count': data['count'],
                'avg_time': round(data['total_time'] / max(1, data['count']), 3),
                'min_time': round(data['min_time'], 3),
                'max_time': round(data['max_time'], 3)
            }
        
        return stats
    
    def reset(self):
        """Reset all metrics"""
        self.metrics = {
            'request_count': 0,
            'total_time': 0.0,
            'endpoints': {}
        }


# Global performance monitor
perf_monitor = PerformanceMonitor()


async def batch_process(items: list, func: Callable, batch_size: int = 10, max_workers: int = 5):
    """
    Process items in batches with concurrency control
    
    Args:
        items: List of items to process
        func: Async function to process each item
        batch_size: Number of items per batch
        max_workers: Max concurrent workers
    
    Returns:
        List of results
    """
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_workers)
        
        async def process_with_semaphore(item):
            async with semaphore:
                return await func(item)
        
        # Process batch concurrently
        batch_results = await asyncio.gather(
            *[process_with_semaphore(item) for item in batch],
            return_exceptions=True
        )
        
        results.extend(batch_results)
    
    return results


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_calls: int, time_window: int):
        """
        Args:
            max_calls: Maximum calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def is_allowed(self) -> bool:
        """Check if call is allowed"""
        now = time.time()
        
        # Remove old calls outside time window
        self.calls = [t for t in self.calls if now - t < self.time_window]
        
        # Check if limit reached
        if len(self.calls) >= self.max_calls:
            return False
        
        # Add current call
        self.calls.append(now)
        return True
    
    def reset(self):
        """Reset rate limiter"""
        self.calls.clear()
