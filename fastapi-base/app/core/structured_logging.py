"""
Structured logging with JSON format
"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data['extra'] = record.extra
        
        # Add context fields
        for attr in ['request_id', 'user_id', 'endpoint', 'duration']:
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)
        
        return json.dumps(log_data, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    """Add request context to log records"""
    
    def __init__(self):
        super().__init__()
        self.request_id = None
        self.endpoint = None
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context fields to record"""
        if self.request_id:
            record.request_id = self.request_id
        if self.endpoint:
            record.endpoint = self.endpoint
        return True


def setup_structured_logging(
    log_level: str = 'INFO',
    log_file: Path = None,
    json_format: bool = False
):
    """
    Setup structured logging
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        json_format: Use JSON format for logs
    """
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    handlers.append(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers
    )
    
    # Add context filter
    context_filter = RequestContextFilter()
    for handler in handlers:
        handler.addFilter(context_filter)
    
    return context_filter


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context: Any
):
    """
    Log message with context
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error)
        message: Log message
        **context: Additional context fields
    """
    extra = {'extra': context} if context else {}
    getattr(logger, level.lower())(message, extra=extra)


# Convenience functions
def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status: int,
    duration: float,
    **extra
):
    """Log HTTP request"""
    log_with_context(
        logger,
        'info',
        f"{method} {path} - {status}",
        method=method,
        path=path,
        status=status,
        duration_ms=round(duration * 1000, 2),
        **extra
    )


def log_error_with_trace(
    logger: logging.Logger,
    error: Exception,
    context: Dict[str, Any] = None
):
    """Log error with full trace and context"""
    log_with_context(
        logger,
        'error',
        f"Error: {str(error)}",
        error_type=type(error).__name__,
        error_message=str(error),
        **(context or {})
    )
