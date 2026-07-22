"""
Configuration constants for the application
Centralize all magic numbers and hardcoded values
"""
from typing import Dict, Any


class CrawlerConfig:
    """Crawler configuration"""
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_PAGES = 100
    DEFAULT_MAX_DEPTH = 3
    DEFAULT_DELAY_MS = 0
    DEFAULT_MAX_CONCURRENT = 10
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    MIN_CONTENT_LENGTH = 300
    MAX_RETRIES = 3


class TopicModelConfig:
    """Topic modeling configuration"""
    DEFAULT_MIN_TOPIC_SIZE = 10
    DEFAULT_N_NEIGHBORS = 15
    DEFAULT_N_COMPONENTS = 5
    DEFAULT_MIN_DIST = 0.0
    DEFAULT_TOP_N_WORDS = 10
    MIN_DOCUMENTS = 2
    DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # Model auto-load priority
    MODEL_PRIORITY = [
        "vietnamese_phrases_final",
        "vietnamese_phrases_v2",
        "vietnamese_phrases_v1",
        "vietnamese_model_v2",
        "full_data_model_openai",
        "full_data_model"
    ]


class CacheConfig:
    """Cache configuration"""
    DEFAULT_TTL = 300  # 5 minutes
    TOPICS_TTL = 600   # 10 minutes
    DASHBOARD_TTL = 300  # 5 minutes
    MODEL_TTL = 3600   # 1 hour
    LONG_TTL = 7200    # 2 hours


class DatabaseConfig:
    """Database configuration"""
    DEFAULT_POOL_SIZE = 10
    DEFAULT_MAX_OVERFLOW = 20
    DEFAULT_POOL_TIMEOUT = 30
    DEFAULT_POOL_RECYCLE = 3600
    BATCH_SIZE = 100


class PerformanceConfig:
    """Performance thresholds"""
    SLOW_REQUEST_THRESHOLD = 1.0  # seconds
    MAX_BATCH_SIZE = 100
    DEFAULT_MAX_WORKERS = 5


class ResilienceConfig:
    """Resilience configuration"""
    RETRY_MAX_ATTEMPTS = 3
    RETRY_DELAY = 1.0  # seconds
    RETRY_BACKOFF = 2.0
    
    CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 60  # seconds
    
    DEFAULT_TIMEOUT = 30  # seconds


class ETLConfig:
    """ETL configuration"""
    MIN_WORD_LENGTH = 2
    MAX_REPEATED_CHARS = 2
    MIN_SENTENCE_LENGTH = 10
    DEDUP_SIMILARITY_THRESHOLD = 0.9


class APIConfig:
    """API configuration"""
    MAX_PAGE_SIZE = 100
    DEFAULT_PAGE_SIZE = 20
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 60  # seconds


class LoggingConfig:
    """Logging configuration"""
    DEFAULT_LEVEL = 'INFO'
    JSON_FORMAT = False
    LOG_FILE = 'logs/app.log'


# Export all configs as dict for easy access
ALL_CONFIGS: Dict[str, Any] = {
    'crawler': {
        'timeout': CrawlerConfig.DEFAULT_TIMEOUT,
        'max_pages': CrawlerConfig.DEFAULT_MAX_PAGES,
        'max_concurrent': CrawlerConfig.DEFAULT_MAX_CONCURRENT,
        'max_retries': CrawlerConfig.MAX_RETRIES,
    },
    'topic_model': {
        'min_topic_size': TopicModelConfig.DEFAULT_MIN_TOPIC_SIZE,
        'embedding_model': TopicModelConfig.DEFAULT_EMBEDDING_MODEL,
        'model_priority': TopicModelConfig.MODEL_PRIORITY,
    },
    'cache': {
        'default_ttl': CacheConfig.DEFAULT_TTL,
        'topics_ttl': CacheConfig.TOPICS_TTL,
        'dashboard_ttl': CacheConfig.DASHBOARD_TTL,
    },
    'database': {
        'pool_size': DatabaseConfig.DEFAULT_POOL_SIZE,
        'max_overflow': DatabaseConfig.DEFAULT_MAX_OVERFLOW,
        'batch_size': DatabaseConfig.BATCH_SIZE,
    },
    'resilience': {
        'retry_attempts': ResilienceConfig.RETRY_MAX_ATTEMPTS,
        'circuit_breaker_threshold': ResilienceConfig.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        'timeout': ResilienceConfig.DEFAULT_TIMEOUT,
    },
    'performance': {
        'slow_threshold': PerformanceConfig.SLOW_REQUEST_THRESHOLD,
        'max_workers': PerformanceConfig.DEFAULT_MAX_WORKERS,
    }
}


def get_config(category: str = None) -> Dict[str, Any]:
    """
    Get configuration
    
    Args:
        category: Optional category (crawler, topic_model, etc.)
                 If None, returns all configs
    
    Returns:
        Configuration dict
    """
    if category:
        return ALL_CONFIGS.get(category, {})
    return ALL_CONFIGS
