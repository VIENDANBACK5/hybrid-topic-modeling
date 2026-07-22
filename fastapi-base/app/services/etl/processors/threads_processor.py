"""
Threads Processor - Xu ly data tu Threads

Threads response format:
{
    "url": "https://www.threads.net/@username/post/DRnBwGZgSkA",
    "title": "Noi dung post  Translate",
    "id": 8162,
    "updated_at": 1767163175.7024,
    "meta_data": {
        "username": "honphuc2000",
        "likes": 0,
        "replies": 0,
        "reposts": 0,
        "shares": 0,
        "time": "11/28/25",
        "datetime": "2025-11-28T18:14:05.000Z"
    },
    "content": "Noi dung post  Translate",
    "data_type": "threads",
    "created_at": 1767163175.702328
}
"""
from typing import Dict, List, Any, Optional
from .base_processor import BaseProcessor
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class ThreadsProcessor(BaseProcessor):
    """Processor for Threads data"""
    
    @property
    def data_type(self) -> str:
        return "threads"
    
    def extract_content(self, record: Dict) -> str:
        """Extract content from Threads post"""
        content = record.get('content', '') or record.get('title', '')
        
        # Remove " Translate" suffix that appears in some posts
        content = re.sub(r'\s+Translate\s*$', '', content)
        
        return content
    
    def extract_title(self, record: Dict) -> str:
        """Extract title from Threads"""
        content = self.extract_content(record)
        
        # Use first 100 chars as title
        if content:
            title = content[:100]
            if len(content) > 100:
                title += '...'
            return title
        
        return record.get('title', '')
    
    def extract_engagement(self, record: Dict) -> Dict[str, int]:
        """Extract engagement metrics from Threads"""
        meta = record.get('meta_data', {})
        
        return {
            'likes': meta.get('likes', 0),
            'shares': meta.get('shares', 0) + meta.get('reposts', 0),  # Combine shares + reposts
            'comments': meta.get('replies', 0),  # Threads calls it replies
            'views': 0,  # Threads doesn't provide views
            'reactions': None
        }
    
    def extract_author(self, record: Dict) -> Dict[str, Any]:
        """Extract author info from Threads"""
        meta = record.get('meta_data', {})
        url = record.get('url', '')
        
        username = meta.get('username', '')
        
        # Extract username from URL if not in metadata
        if not username and url:
            match = re.search(r'threads\.net/@([^/]+)', url)
            if match:
                username = match.group(1)
        
        return {
            'id': username,
            'name': username,
            'url': f"https://www.threads.net/@{username}" if username else None,
            'profile_picture': None,
            'title': None
        }
    
    def _parse_timestamp(self, record: Dict) -> Optional[datetime]:
        """Override to handle Threads datetime format"""
        meta = record.get('meta_data', {})
        
        # Try datetime field first (ISO format)
        dt_str = meta.get('datetime')
        if dt_str:
            try:
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except:
                pass
        
        # Try time field (MM/DD/YY format)
        time_str = meta.get('time')
        if time_str:
            try:
                return datetime.strptime(time_str, '%m/%d/%y')
            except:
                pass
        
        # Fall back to base implementation
        return super()._parse_timestamp(record)
    
    def _extract_type_specific(self, record: Dict) -> Dict:
        """Extract Threads-specific fields"""
        meta = record.get('meta_data', {})
        
        return {
            'post_type': 'thread',
            'reposts_count': meta.get('reposts', 0),
        }


def get_threads_processor() -> ThreadsProcessor:
    """Factory function"""
    return ThreadsProcessor()
