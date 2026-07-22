"""
Retry logic and circuit breaker for resilient API calls
"""
import asyncio
import logging
from typing import Callable, Optional, TypeVar, Any
from functools import wraps
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'closed'  # closed, open, half_open
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker"""
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half_open'
                logger.info("Circuit breaker: attempting reset (half-open)")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with circuit breaker"""
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half_open'
                logger.info("Circuit breaker: attempting reset (half-open)")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == 'half_open':
            logger.info("Circuit breaker: CLOSED (recovered)")
        self.failure_count = 0
        self.state = 'closed'
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.error(f"Circuit breaker: OPEN after {self.failure_count} failures")
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'
        logger.info("Circuit breaker: manually reset")
    
    def get_state(self) -> dict:
        """Get current state"""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'last_failure': self.last_failure_time.isoformat() if self.last_failure_time else None
        }


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to catch
    
    Usage:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        def unstable_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


async def run_with_timeout(coro, timeout: float):
    """
    Run coroutine with timeout
    
    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
    
    Raises:
        TimeoutError: If coroutine doesn't complete within timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout} seconds")


def with_timeout(timeout: float):
    """
    Decorator to add timeout to async functions
    
    Usage:
        @with_timeout(30.0)
        async def slow_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await run_with_timeout(func(*args, **kwargs), timeout)
        return wrapper
    return decorator


# Global circuit breakers for common services
circuit_breakers = {
    'crawler': CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    'topic_model': CircuitBreaker(failure_threshold=3, recovery_timeout=120),
    'database': CircuitBreaker(failure_threshold=10, recovery_timeout=30),
}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create circuit breaker by name"""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker()
    return circuit_breakers[name]
