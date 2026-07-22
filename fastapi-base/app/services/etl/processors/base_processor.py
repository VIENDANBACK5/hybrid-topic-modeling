"""
Base Processor - Lop co so cho cac processor

Tich hop tu DataNormalizer va cac utils cu:
- Timestamp parsing tu nhieu format
- Platform detection patterns
- Text cleaning va normalization
- Vietnamese news domain detection
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Platform detection patterns (from data_normalizer.py)
PLATFORM_PATTERNS = {
    'facebook': [r'facebook\.com', r'fb\.com', r'm\.facebook\.com'],
    'youtube': [r'youtube\.com', r'youtu\.be'],
    'tiktok': [r'tiktok\.com', r'vm\.tiktok\.com'],
    'twitter': [r'twitter\.com', r'x\.com'],
    'instagram': [r'instagram\.com'],
    'threads': [r'threads\.net'],
}

# Vietnamese news domains
VN_NEWS_DOMAINS = {
    'vnexpress.net', 'dantri.com.vn', 'thanhnien.vn', 'tuoitre.vn', 
    'vietnamnet.vn', 'baomoi.com', 'zing.vn', 'kenh14.vn',
    'soha.vn', 'cafef.vn', 'cafebiz.vn', 'genk.vn'
}


class BaseProcessor(ABC):
    """Base class cho tat ca processors"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    @property
    @abstractmethod
    def data_type(self) -> str:
        """Return data type name"""
        pass
    
    @abstractmethod
    def extract_content(self, record: Dict) -> str:
        """Extract main content from record"""
        pass
    
    @abstractmethod
    def extract_title(self, record: Dict) -> str:
        """Extract title from record"""
        pass
    
    @abstractmethod
    def extract_engagement(self, record: Dict) -> Dict[str, int]:
        """Extract engagement metrics"""
        pass
    
    @abstractmethod
    def extract_author(self, record: Dict) -> Dict[str, Any]:
        """Extract author info"""
        pass
    
    def process(self, record: Dict) -> Tuple[Dict, bool, List[str], List[str]]:
        """
        Process a single record into standardized format
        
        Returns:
            (processed_record, is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        try:
            # Extract basic fields
            url = record.get('url', '')
            if not url:
                self.errors.append("Missing URL")
                return {}, False, self.errors, self.warnings
            
            content = self.extract_content(record)
            if not content or len(content.strip()) < 10:
                self.errors.append("Content too short or missing")
                return {}, False, self.errors, self.warnings
            
            title = self.extract_title(record)
            engagement = self.extract_engagement(record)
            author = self.extract_author(record)
            
            # Parse timestamps
            published_at = self._parse_timestamp(record)
            
            # Clean content
            cleaned_content = self._clean_text(content)
            cleaned_title = self._clean_text(title) if title else None
            
            # Build standardized record
            processed = {
                # Source info
                'url': url,
                'source_type': self.data_type,  # facebook, tiktok, threads, newspaper
                'source': url,
                'domain': self._extract_domain(url),
                'social_platform': self.data_type if self.data_type in ['facebook', 'tiktok', 'threads'] else None,
                
                # Content
                'title': cleaned_title,
                'content': cleaned_content,
                'word_count': len(cleaned_content.split()),
                
                # Timestamps
                'published_date': published_at.timestamp() if published_at else None,
                'published_datetime': published_at,
                
                # Engagement
                'likes_count': engagement.get('likes', 0),
                'shares_count': engagement.get('shares', 0),
                'comments_count': engagement.get('comments', 0),
                'views_count': engagement.get('views', 0),
                'reactions': engagement.get('reactions'),
                
                # Author
                'account_id': author.get('id'),
                'account_name': author.get('name'),
                'account_url': author.get('url'),
                
                # Post metadata
                'post_id': self._extract_post_id(record),
                'post_type': self._extract_post_type(record),
                
                # Original metadata
                'raw_metadata': record.get('meta_data', {}),
                
                # Processing flags
                'is_cleaned': True,
                'data_type': self.data_type,
            }
            
            # Add type-specific fields
            processed.update(self._extract_type_specific(record))
            
            return processed, True, self.errors, self.warnings
            
        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)
            self.errors.append(f"Processing error: {str(e)}")
            return {}, False, self.errors, self.warnings
    
    def process_batch(self, records: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Process a batch of records
        
        Returns:
            (processed_records, statistics)
        """
        processed = []
        stats = {
            'total': len(records),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        seen_urls = set()
        
        for record in records:
            url = record.get('url', '')
            
            # Skip duplicates within batch
            if url in seen_urls:
                stats['failed'] += 1
                continue
            seen_urls.add(url)
            
            result, is_valid, errors, warnings = self.process(record)
            
            if is_valid:
                processed.append(result)
                stats['success'] += 1
            else:
                stats['failed'] += 1
                if errors:
                    stats['errors'].extend(errors[:3])  # Limit errors
        
        return processed, stats
    
    def _parse_timestamp(self, record: Dict) -> Optional[datetime]:
        """
        Parse timestamp from various formats
        Supported: Unix timestamp, ISO format, common date formats
        """
        # Try meta_data.timestamp first (most common)
        meta = record.get('meta_data', {})
        ts = (
            meta.get('timestamp') or 
            meta.get('datetime') or 
            meta.get('time') or
            record.get('created_at') or
            record.get('published_at')
        )
        
        if not ts:
            return None
        
        try:
            # Unix timestamp (int or float)
            if isinstance(ts, (int, float)):
                return datetime.fromtimestamp(ts)
            
            # String formats
            if isinstance(ts, str):
                # ISO format (most common in APIs)
                try:
                    # Handle 'Z' timezone indicator
                    clean_ts = ts.replace('Z', '+00:00')
                    # Handle milliseconds in ISO format like "2025-11-28T18:14:05.000Z"
                    if '.' in clean_ts:
                        clean_ts = clean_ts.split('.')[0]
                        if '+' not in clean_ts:
                            clean_ts += '+00:00'
                    return datetime.fromisoformat(clean_ts)
                except:
                    pass
                
                # Try common formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%d/%m/%Y %H:%M:%S',
                    '%d/%m/%Y',
                    '%m/%d/%y',
                    '%Y/%m/%d',
                    '%d-%m-%Y %H:%M:%S',
                    '%d-%m-%Y',
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(ts, fmt)
                    except:
                        continue
            
            # Already datetime
            if isinstance(ts, datetime):
                return ts
                
        except Exception as e:
            self.warnings.append(f"Failed to parse timestamp: {ts}")
        
        return None
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text content for processing
        Preserves Vietnamese characters and common punctuation
        """
        if not text:
            return ""
        
        # Remove HTML tags if any
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep Vietnamese characters
        # Vietnamese: \u00C0-\u024F (Latin Extended), \u1E00-\u1EFF (Vietnamese specific)
        text = re.sub(r'[^\w\s\u00C0-\u024F\u1E00-\u1EFF.,!?;:\-\'\"()@#]', '', text)
        
        return text.strip()
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL, removing www prefix"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return re.sub(r'^www\.', '', domain)
        except:
            return ""
    
    def _detect_platform_from_url(self, url: str) -> Optional[str]:
        """Detect social platform from URL patterns"""
        if not url:
            return None
        for platform, patterns in PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return platform
        return None
    
    def _is_vietnamese_news(self, url: str) -> bool:
        """Check if URL is from Vietnamese news site"""
        domain = self._extract_domain(url)
        return domain in VN_NEWS_DOMAINS
    
    def _extract_post_id(self, record: Dict) -> Optional[str]:
        """Extract post ID"""
        meta = record.get('meta_data', {})
        return meta.get('post_id') or str(record.get('id', ''))
    
    def _extract_post_type(self, record: Dict) -> Optional[str]:
        """Extract post type"""
        meta = record.get('meta_data', {})
        return meta.get('type') or meta.get('post_type')
    
    def _extract_type_specific(self, record: Dict) -> Dict:
        """Override in subclasses for type-specific fields"""
        return {}
