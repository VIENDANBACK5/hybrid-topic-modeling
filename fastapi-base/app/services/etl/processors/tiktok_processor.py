"""
TikTok Processor - Xu ly data tu TikTok

TikTok response format:
{
    "url": "https://www.tiktok.com/@username/video/7580380323100380434",
    "title": "Noi dung video #hashtag1 #hashtag2 created by User with User's nhac nen - User",
    "id": 8580,
    "updated_at": 1767535888.594637,
    "meta_data": {
        "url_video": null,
        "username": "truyenhinhhungyen",
        "views": 46300,
        "views_text": "46.3K",
        "hashtags": ["#titkoknews", "#truyenhinhhungyen"],
        "thumbnail_url": "https://...",
        "badge": null
    },
    "content": "Noi dung video #hashtag1 #hashtag2...",
    "data_type": "tiktok",
    "created_at": 1767535888.59457
}
"""
from typing import Dict, List, Any, Optional
from .base_processor import BaseProcessor
import logging
import re

logger = logging.getLogger(__name__)


class TikTokProcessor(BaseProcessor):
    """Processor for TikTok data"""
    
    @property
    def data_type(self) -> str:
        return "tiktok"
    
    def extract_content(self, record: Dict) -> str:
        """Extract content from TikTok video"""
        content = record.get('content', '') or record.get('title', '')
        
        # Clean up "created by X with X's nhac nen - X" suffix
        content = re.sub(r'\s+created by .+$', '', content)
        
        return content
    
    def extract_title(self, record: Dict) -> str:
        """Extract title from TikTok"""
        title = record.get('title', '')
        
        # Clean up
        title = re.sub(r'\s+created by .+$', '', title)
        
        # Truncate if too long
        if len(title) > 200:
            title = title[:200] + '...'
        
        return title
    
    def extract_engagement(self, record: Dict) -> Dict[str, int]:
        """Extract engagement metrics from TikTok"""
        meta = record.get('meta_data', {})
        
        views = meta.get('views', 0)
        
        # Parse views_text if views not available
        if not views and meta.get('views_text'):
            views = self._parse_views_text(meta.get('views_text'))
        
        return {
            'likes': 0,  # TikTok API doesn't provide likes in this format
            'shares': 0,
            'comments': 0,
            'views': views,
            'reactions': None
        }
    
    def _parse_views_text(self, text: str) -> int:
        """Parse views text like '46.3K' to number"""
        if not text:
            return 0
        
        text = text.upper().strip()
        multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
        
        for suffix, mult in multipliers.items():
            if suffix in text:
                try:
                    num = float(text.replace(suffix, ''))
                    return int(num * mult)
                except:
                    pass
        
        try:
            return int(float(text))
        except:
            return 0
    
    def extract_author(self, record: Dict) -> Dict[str, Any]:
        """Extract author info from TikTok"""
        meta = record.get('meta_data', {})
        url = record.get('url', '')
        
        username = meta.get('username', '')
        
        # Extract username from URL if not in metadata
        if not username and url:
            match = re.search(r'tiktok\.com/@([^/]+)', url)
            if match:
                username = match.group(1)
        
        return {
            'id': username,
            'name': username,
            'url': f"https://www.tiktok.com/@{username}" if username else None,
            'profile_picture': None,
            'title': None
        }
    
    def _extract_type_specific(self, record: Dict) -> Dict:
        """Extract TikTok-specific fields"""
        meta = record.get('meta_data', {})
        
        # Extract hashtags
        hashtags = meta.get('hashtags', [])
        
        # Also extract from content if not in metadata
        content = record.get('content', '') or record.get('title', '')
        if not hashtags and content:
            hashtags = re.findall(r'#(\w+)', content)
        
        return {
            'tags': hashtags if hashtags else None,
            'images': [meta.get('thumbnail_url')] if meta.get('thumbnail_url') else None,
            'videos': [meta.get('url_video')] if meta.get('url_video') else None,
            'post_type': 'video',
            'badge': meta.get('badge'),
        }


def get_tiktok_processor() -> TikTokProcessor:
    """Factory function"""
    return TikTokProcessor()
