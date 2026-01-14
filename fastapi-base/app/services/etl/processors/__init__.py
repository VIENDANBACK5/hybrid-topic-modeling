"""
Processors Package - Xu ly data theo tung loai

Cung cap cac processor rieng biet cho tung data type:
- FacebookProcessor: Xu ly data tu Facebook
- TikTokProcessor: Xu ly data tu TikTok
- ThreadsProcessor: Xu ly data tu Threads
- NewspaperProcessor: Xu ly data tu bao chi

Usage:
    from app.services.etl.processors import get_processor
    
    processor = get_processor('facebook')
    processed, stats = processor.process_batch(records)
"""

from .base_processor import BaseProcessor
from .facebook_processor import FacebookProcessor, get_facebook_processor
from .tiktok_processor import TikTokProcessor, get_tiktok_processor
from .threads_processor import ThreadsProcessor, get_threads_processor
from .newspaper_processor import NewspaperProcessor, get_newspaper_processor

# Processor registry
_PROCESSORS = {
    'facebook': get_facebook_processor,
    'tiktok': get_tiktok_processor,
    'threads': get_threads_processor,
    'newspaper': get_newspaper_processor,
}


def get_processor(data_type: str) -> BaseProcessor:
    """
    Get processor for a specific data type
    
    Args:
        data_type: One of 'facebook', 'tiktok', 'threads', 'newspaper'
    
    Returns:
        Appropriate processor instance
    
    Raises:
        ValueError: If data_type is not supported
    """
    if data_type not in _PROCESSORS:
        raise ValueError(f"Unknown data type: {data_type}. Supported: {list(_PROCESSORS.keys())}")
    
    return _PROCESSORS[data_type]()


def get_supported_types() -> list:
    """Get list of supported data types"""
    return list(_PROCESSORS.keys())


__all__ = [
    'BaseProcessor',
    'FacebookProcessor',
    'TikTokProcessor', 
    'ThreadsProcessor',
    'NewspaperProcessor',
    'get_processor',
    'get_supported_types',
]
