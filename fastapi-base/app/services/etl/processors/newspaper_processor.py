"""
Newspaper Processor - Xu ly data tu Newspaper/News sites

Newspaper response format (estimated based on typical news API):
{
    "url": "https://baohungyen.vn/...",
    "title": "Tieu de bai bao",
    "id": 1234,
    "updated_at": 1767163175.7024,
    "meta_data": {
        "author": "Tac gia",
        "published_date": "2025-12-25",
        "category": "Chinh tri",
        "tags": ["tag1", "tag2"],
        "images": ["url1", "url2"],
        "description": "Mo ta ngan",
        ...
    },
    "content": "Noi dung bai bao day du",
    "data_type": "newspaper",
    "created_at": 1767163175.702328
}
"""
from typing import Dict, List, Any, Optional
from .base_processor import BaseProcessor
from datetime import datetime
from urllib.parse import urlparse
import logging
import re

logger = logging.getLogger(__name__)


class NewspaperProcessor(BaseProcessor):
    """Processor for Newspaper/News data"""
    
    @property
    def data_type(self) -> str:
        return "newspaper"
    
    def extract_content(self, record: Dict) -> str:
        """Extract content from news article"""
        content = record.get('content', '')
        
        if not content:
            meta = record.get('meta_data', {})
            content = meta.get('body') or meta.get('text') or meta.get('description', '')
        
        return content
    
    def extract_title(self, record: Dict) -> str:
        """Extract title from news article"""
        title = record.get('title', '')
        
        if not title:
            meta = record.get('meta_data', {})
            title = meta.get('headline') or meta.get('title', '')
        
        return title
    
    def extract_engagement(self, record: Dict) -> Dict[str, int]:
        """Extract engagement metrics from news article"""
        meta = record.get('meta_data', {})
        
        return {
            'likes': meta.get('likes', 0) or meta.get('reactions', 0),
            'shares': meta.get('shares', 0),
            'comments': meta.get('comments', 0) or meta.get('comments_count', 0),
            'views': meta.get('views', 0) or meta.get('view_count', 0),
            'reactions': None
        }
    
    def extract_author(self, record: Dict) -> Dict[str, Any]:
        """Extract author info from news article"""
        meta = record.get('meta_data', {})
        
        author = meta.get('author', '')
        if isinstance(author, dict):
            return {
                'id': author.get('id'),
                'name': author.get('name'),
                'url': author.get('url'),
                'profile_picture': None,
                'title': author.get('title')
            }
        
        return {
            'id': None,
            'name': author if isinstance(author, str) else None,
            'url': None,
            'profile_picture': None,
            'title': None
        }
    
    def _parse_timestamp(self, record: Dict) -> Optional[datetime]:
        """
        Parse timestamp from news article
        Priority: time_int (Unix) > created_at > published_at
        """
        meta = record.get('meta_data', {})
        
        # Priority 1: time_int (Unix timestamp - most reliable)
        time_int = meta.get('time_int') or record.get('time_int')
        if time_int and isinstance(time_int, (int, float)):
            try:
                return datetime.fromtimestamp(time_int)
            except:
                logger.warning(f"Invalid time_int: {time_int}")
        
        # Priority 2: created_at (format: YYYY-MM-DD HH:MM:SS)
        created_at = meta.get('created_at') or record.get('created_at')
        if created_at:
            dt = self._try_parse_datetime(created_at, prefer_format='%Y-%m-%d %H:%M:%S')
            if dt:
                return dt
        
        # Priority 3: published_at (format: DD-MM-YYYY HH:MM:SS)
        published_at = meta.get('published_at') or record.get('published_at')
        if published_at:
            dt = self._try_parse_datetime(published_at, prefer_format='%d-%m-%Y %H:%M:%S')
            if dt:
                return dt
        
        # Priority 4: Other fields
        for field in ['published_date', 'publish_date', 'date', 'timestamp']:
            value = meta.get(field) or record.get(field)
            if value:
                dt = self._try_parse_datetime(value)
                if dt:
                    return dt
        
        return super()._parse_timestamp(record)
    
    def _try_parse_datetime(self, value, prefer_format: Optional[str] = None) -> Optional[datetime]:
        """
        Try to parse datetime from various formats
        prefer_format: Format to try first
        """
        if not value:
            return None
        
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value)
            
            if isinstance(value, datetime):
                return value
            
            if isinstance(value, str):
                # Try preferred format first
                if prefer_format:
                    try:
                        return datetime.strptime(value, prefer_format)
                    except:
                        pass
                
                # ISO format
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    pass
                
                # Common formats - extended to handle DD-MM-YYYY
                formats = [
                    '%Y-%m-%d %H:%M:%S',  # 2018-10-14 20:47:13
                    '%d-%m-%Y %H:%M:%S',  # 14-10-2018 20:47:13 (newspaper format)
                    '%d/%m/%Y %H:%M:%S',
                    '%Y-%m-%d',
                    '%d-%m-%Y',           # 14-10-2018
                    '%d/%m/%Y',
                    '%Y/%m/%d',
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(value, fmt)
                    except:
                        continue
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{value}': {e}")
        
        return None
    
    def _extract_type_specific(self, record: Dict) -> Dict:
        """Extract Newspaper-specific fields"""
        meta = record.get('meta_data', {})
        url = record.get('url', '')
        
        # Extract domain as source name
        source_name = None
        try:
            parsed = urlparse(url)
            source_name = parsed.netloc.replace('www.', '')
        except:
            pass
        
        # Extract category
        category = meta.get('category') or meta.get('section') or meta.get('rubric')
        
        # Extract tags
        tags = meta.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]
        
        # Extract images
        images = meta.get('images', [])
        if not images and meta.get('image'):
            images = [meta.get('image')]
        if not images and meta.get('thumbnail'):
            images = [meta.get('thumbnail')]
        
        return {
            'category': category,
            'tags': tags if tags else None,
            'images': images if images else None,
            'summary': meta.get('description') or meta.get('summary') or meta.get('excerpt'),
            'post_type': 'article',
            'source_name': source_name,
        }


def get_newspaper_processor() -> NewspaperProcessor:
    """Factory function"""
    return NewspaperProcessor()
