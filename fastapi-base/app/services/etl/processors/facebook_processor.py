"""
Facebook Processor - Xu ly data tu Facebook

Facebook response format:
{
    "url": "https://www.facebook.com/permalink.php?...",
    "title": "Noi dung post",
    "id": 8440,
    "updated_at": 1767163175.7024,
    "meta_data": {
        "post_id": "877658211885687",
        "type": "post",
        "url": "...",
        "message": "Noi dung",
        "message_rich": "Noi dung voi emoji",
        "timestamp": 1766644190,
        "comments_count": 2,
        "reactions_count": 28,
        "reshare_count": 0,
        "reactions": {"angry": 0, "care": 0, "haha": 0, "like": 28, "love": 0, "sad": 0, "wow": 0},
        "author": {"id": "...", "name": "...", "url": "...", "profile_picture_url": "..."},
        "album_preview": [...],
        "video_files": null,
        ...
    },
    "content": "Noi dung post",
    "data_type": "facebook",
    "created_at": 1767163175.702328
}
"""
from typing import Dict, List, Any, Optional
from .base_processor import BaseProcessor
import logging

logger = logging.getLogger(__name__)


class FacebookProcessor(BaseProcessor):
    """Processor for Facebook data"""
    
    @property
    def data_type(self) -> str:
        return "facebook"
    
    def extract_content(self, record: Dict) -> str:
        """Extract content from Facebook post"""
        # Priority: content > meta_data.message > meta_data.message_rich > title
        content = record.get('content', '')
        if content:
            return content
        
        meta = record.get('meta_data', {})
        return meta.get('message') or meta.get('message_rich') or record.get('title', '')
    
    def extract_title(self, record: Dict) -> str:
        """Extract title - Facebook posts don't have separate title"""
        content = self.extract_content(record)
        # Use first 100 chars as title
        if content:
            title = content[:100]
            if len(content) > 100:
                title += '...'
            return title
        return record.get('title', '')
    
    def extract_engagement(self, record: Dict) -> Dict[str, int]:
        """Extract engagement metrics from Facebook"""
        meta = record.get('meta_data', {})
        
        reactions = meta.get('reactions', {})
        total_reactions = meta.get('reactions_count', 0)
        
        # If reactions_count not provided, sum individual reactions
        if not total_reactions and reactions:
            total_reactions = sum(reactions.values())
        
        return {
            'likes': total_reactions,  # Facebook uses reactions as likes
            'shares': meta.get('reshare_count', 0),
            'comments': meta.get('comments_count', 0),
            'views': 0,  # Facebook doesn't provide views for regular posts
            'reactions': reactions if reactions else None
        }
    
    def extract_author(self, record: Dict) -> Dict[str, Any]:
        """Extract author info from Facebook"""
        meta = record.get('meta_data', {})
        author = meta.get('author', {})
        
        return {
            'id': author.get('id'),
            'name': author.get('name'),
            'url': author.get('url'),
            'profile_picture': author.get('profile_picture_url'),
            'title': meta.get('author_title')
        }
    
    def _extract_type_specific(self, record: Dict) -> Dict:
        """Extract Facebook-specific fields"""
        meta = record.get('meta_data', {})
        
        # Extract media info
        album = meta.get('album_preview', [])
        images = []
        videos = []
        
        if album:
            for item in album:
                if item.get('type') == 'photo':
                    images.append(item.get('image_file_uri'))
                elif item.get('type') == 'video':
                    videos.append(item.get('url'))
        
        # Single image/video
        if meta.get('image'):
            images.append(meta.get('image'))
        if meta.get('video'):
            videos.append(meta.get('video'))
        
        return {
            'images': images if images else None,
            'videos': videos if videos else None,
            'post_type': meta.get('type', 'post'),
            'external_url': meta.get('external_url'),
            'attached_post_url': meta.get('attached_post_url'),
        }


def get_facebook_processor() -> FacebookProcessor:
    """Factory function"""
    return FacebookProcessor()
