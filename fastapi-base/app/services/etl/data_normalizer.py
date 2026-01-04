"""
Data Normalizer & Validator
Chuẩn hóa và validate data từ nhiều nguồn khác nhau (web, Facebook, TikTok, YouTube, etc.)
"""
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Platform detection patterns
PLATFORM_PATTERNS = {
    'facebook': [
        r'facebook\.com',
        r'fb\.com',
        r'm\.facebook\.com',
        r'web\.facebook\.com'
    ],
    'youtube': [
        r'youtube\.com',
        r'youtu\.be',
        r'm\.youtube\.com'
    ],
    'tiktok': [
        r'tiktok\.com',
        r'vm\.tiktok\.com'
    ],
    'twitter': [
        r'twitter\.com',
        r'x\.com',
        r't\.co'
    ],
    'instagram': [
        r'instagram\.com',
        r'instagr\.am'
    ],
    'zalo': [
        r'zalo\.me',
        r'chat\.zalo\.me'
    ],
    'linkedin': [
        r'linkedin\.com'
    ],
    'threads': [
        r'threads\.net'
    ]
}

# Vietnamese news domains
VN_NEWS_DOMAINS = {
    'vnexpress.net', 'dantri.com.vn', 'thanhnien.vn', 'tuoitre.vn', 
    'vietnamnet.vn', 'baomoi.com', 'zing.vn', 'kenh14.vn',
    'soha.vn', 'cafef.vn', 'cafebiz.vn', 'genk.vn'
}


class DataNormalizer:
    """Normalize data from multiple sources into standard format"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def normalize_document(self, doc: Dict) -> Tuple[Dict, List[str], List[str]]:
        """
        Normalize document from any source to standard format
        
        Returns:
            (normalized_doc, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        normalized = {
            'source_type': None,
            'url': None,
            'domain': None,
            'platform': None,
            'content': None,
            'metadata': {}
        }
        
        try:
            # 1. Detect source type & platform
            source_type, platform = self._detect_source_and_platform(doc)
            normalized['source_type'] = source_type
            normalized['platform'] = platform
            
            # 2. Extract & validate URL
            url = self._extract_url(doc)
            if not url:
                self.errors.append("Missing or invalid URL")
                return normalized, self.errors, self.warnings
            
            normalized['url'] = url
            normalized['domain'] = self._extract_domain(url)
            
            # 3. Normalize content
            content = self._normalize_content(doc)
            if not content:
                self.errors.append("Missing or empty content")
                return normalized, self.errors, self.warnings
            
            normalized['content'] = content
            
            # 4. Normalize metadata
            metadata = self._normalize_metadata(doc, source_type, platform)
            normalized['metadata'] = metadata
            
            # 5. Platform-specific normalization
            if platform:
                normalized = self._apply_platform_specific_rules(normalized, platform)
            
        except Exception as e:
            self.errors.append(f"Normalization error: {str(e)}")
            logger.error(f"Normalization failed: {e}", exc_info=True)
        
        return normalized, self.errors, self.warnings
    
    def _detect_source_and_platform(self, doc: Dict) -> Tuple[str, Optional[str]]:
        """Detect source type and platform"""
        # Check explicit source field
        source = doc.get('source', '').lower()
        
        # Map common source values
        source_mapping = {
            'facebook': ('facebook', 'facebook'),
            'fb': ('facebook', 'facebook'),
            'youtube': ('youtube', 'youtube'),
            'yt': ('youtube', 'youtube'),
            'tiktok': ('tiktok', 'tiktok'),
            'twitter': ('twitter', 'twitter'),
            'instagram': ('instagram', 'instagram'),
            'web': ('web', None),
            'news': ('web', None),
            'rss': ('rss', None),
            'api': ('api', None)
        }
        
        if source in source_mapping:
            return source_mapping[source]
        
        # Detect from URL
        url = self._extract_url(doc)
        if url:
            for platform_name, patterns in PLATFORM_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, url, re.IGNORECASE):
                        return (platform_name, platform_name)
            
            # Check if it's Vietnamese news
            domain = self._extract_domain(url)
            if domain and domain in VN_NEWS_DOMAINS:
                return ('web', None)
        
        # Default
        return ('web', None)
    
    def _extract_url(self, doc: Dict) -> Optional[str]:
        """Extract URL from various possible fields"""
        # Try multiple fields
        url = (
            doc.get('source_id') or 
            doc.get('url') or 
            (doc.get('metadata') or {}).get('url') or
            (doc.get('metadata') or {}).get('canonical_url')
        )
        
        if not url:
            return None
        
        # Validate URL format
        if not isinstance(url, str):
            return None
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        return url
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            domain = re.sub(r'^www\.', '', domain)
            return domain
        except:
            return None
    
    def _normalize_content(self, doc: Dict) -> Optional[str]:
        """Normalize content field"""
        # Try multiple content fields
        content = (
            doc.get('cleaned_content') or
            doc.get('content') or
            doc.get('text') or
            doc.get('raw_content')
        )
        
        if not content:
            return None
        
        # Clean content
        content = str(content).strip()
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Minimum length check
        if len(content) < 10:
            self.warnings.append(f"Content too short ({len(content)} chars)")
        
        return content
    
    def _normalize_metadata(self, doc: Dict, source_type: str, platform: Optional[str]) -> Dict:
        """Normalize metadata from various sources"""
        metadata = doc.get('metadata', {}).copy()
        
        # === REQUIRED FIELDS ===
        
        # Title
        if 'title' not in metadata:
            metadata['title'] = (
                doc.get('title') or
                metadata.get('headline') or
                metadata.get('subject') or
                'Untitled'
            )
        
        # URL
        if 'url' not in metadata:
            metadata['url'] = self._extract_url(doc)
        
        # Published date
        if 'published' not in metadata:
            metadata['published'] = (
                metadata.get('published_time') or
                metadata.get('publish_date') or
                metadata.get('created_time') or
                metadata.get('date') or
                datetime.now().isoformat()
            )
        
        # Crawled time
        if 'crawled_at' not in metadata:
            metadata['crawled_at'] = datetime.now().isoformat()
        
        # === OPTIONAL FIELDS ===
        
        # Author
        if 'author' not in metadata:
            metadata['author'] = (
                doc.get('author') or
                metadata.get('creator') or
                metadata.get('writer')
            )
        
        # Category
        if 'category' not in metadata:
            metadata['category'] = (
                doc.get('category') or
                metadata.get('section') or
                metadata.get('topic')
            )
        
        # Tags
        if 'tags' not in metadata:
            tags = (
                doc.get('tags') or
                metadata.get('keywords') or
                metadata.get('hashtags')
            )
            if tags:
                if isinstance(tags, str):
                    # Split comma-separated or space-separated
                    tags = [t.strip() for t in re.split(r'[,\s]+', tags) if t.strip()]
                metadata['tags'] = tags
        
        # === ENGAGEMENT (for social media) ===
        if platform:
            engagement = metadata.get('engagement', {})
            
            # Normalize engagement field names
            engagement_mapping = {
                'likes': ['likes', 'like_count', 'reaction_count', 'thumbs_up'],
                'shares': ['shares', 'share_count', 'retweet_count', 'reshare'],
                'comments': ['comments', 'comment_count', 'reply_count'],
                'views': ['views', 'view_count', 'play_count', 'impressions']
            }
            
            for standard_key, possible_keys in engagement_mapping.items():
                if standard_key not in engagement:
                    for key in possible_keys:
                        value = (
                            doc.get(key) or
                            metadata.get(key) or
                            engagement.get(key)
                        )
                        if value is not None:
                            try:
                                engagement[standard_key] = int(value)
                                break
                            except (ValueError, TypeError):
                                pass
            
            if engagement:
                metadata['engagement'] = engagement
        
        # === SOCIAL ACCOUNT ===
        if platform:
            social = metadata.get('social_account', {})
            
            # Auto-fill platform if missing
            if 'platform' not in social:
                social['platform'] = platform
            
            # Extract account info from URL if missing
            if not social.get('account_name'):
                account_name = self._extract_account_name(metadata.get('url'), platform)
                if account_name:
                    social['account_name'] = account_name
            
            # Normalize account type
            if 'account_type' in social:
                type_mapping = {
                    'fanpage': 'page',
                    'fan page': 'page',
                    'công khai': 'profile',
                    'group': 'group',
                    'nhóm': 'group'
                }
                account_type = social['account_type'].lower()
                social['account_type'] = type_mapping.get(account_type, account_type)
            
            if social:
                metadata['social_account'] = social
        
        # === LOCATION ===
        location = metadata.get('location', {})
        
        # Normalize province names (standardize)
        if 'province' in location:
            location['province'] = self._normalize_province_name(location['province'])
        
        if location:
            metadata['location'] = location
        
        return metadata
    
    def _apply_platform_specific_rules(self, doc: Dict, platform: str) -> Dict:
        """Apply platform-specific normalization rules"""
        
        if platform == 'facebook':
            # Facebook-specific rules
            doc = self._normalize_facebook(doc)
        elif platform == 'youtube':
            doc = self._normalize_youtube(doc)
        elif platform == 'tiktok':
            doc = self._normalize_tiktok(doc)
        elif platform == 'twitter':
            doc = self._normalize_twitter(doc)
        
        return doc
    
    def _normalize_facebook(self, doc: Dict) -> Dict:
        """Facebook-specific normalization"""
        metadata = doc['metadata']
        
        # Default post_type if not specified
        if 'post_type' not in metadata:
            if metadata.get('images'):
                metadata['post_type'] = 'photo'
            elif metadata.get('videos'):
                metadata['post_type'] = 'video'
            else:
                metadata['post_type'] = 'status'
        
        # Default account_type to page if followers > 1000
        social = metadata.get('social_account', {})
        if social.get('followers', 0) > 1000 and not social.get('account_type'):
            social['account_type'] = 'page'
            metadata['social_account'] = social
        
        return doc
    
    def _normalize_youtube(self, doc: Dict) -> Dict:
        """YouTube-specific normalization"""
        metadata = doc['metadata']
        
        # YouTube posts are always videos
        metadata['post_type'] = 'video'
        
        # Account type is always channel
        social = metadata.get('social_account', {})
        if 'account_type' not in social:
            social['account_type'] = 'channel'
            metadata['social_account'] = social
        
        # Rename subscribers to followers
        engagement = metadata.get('engagement', {})
        if social.get('subscribers') and 'followers' not in social:
            social['followers'] = social['subscribers']
        
        return doc
    
    def _normalize_tiktok(self, doc: Dict) -> Dict:
        """TikTok-specific normalization"""
        metadata = doc['metadata']
        
        # TikTok posts are always videos
        metadata['post_type'] = 'video'
        
        # Map TikTok engagement
        engagement = metadata.get('engagement', {})
        if engagement.get('play_count') and 'views' not in engagement:
            engagement['views'] = engagement['play_count']
        if engagement.get('digg_count') and 'likes' not in engagement:
            engagement['likes'] = engagement['digg_count']
        
        return doc
    
    def _normalize_twitter(self, doc: Dict) -> Dict:
        """Twitter-specific normalization"""
        metadata = doc['metadata']
        
        # Default post_type
        if 'post_type' not in metadata:
            metadata['post_type'] = 'tweet'
        
        # Map retweets to shares
        engagement = metadata.get('engagement', {})
        if engagement.get('retweet_count') and 'shares' not in engagement:
            engagement['shares'] = engagement['retweet_count']
        
        return doc
    
    def _extract_account_name(self, url: str, platform: str) -> Optional[str]:
        """Extract account name from URL"""
        if not url:
            return None
        
        try:
            if platform == 'facebook':
                # https://facebook.com/username or facebook.com/pages/name/123
                match = re.search(r'facebook\.com/([^/?]+)', url)
                if match:
                    return match.group(1)
            elif platform == 'youtube':
                # https://youtube.com/@username or /c/username
                match = re.search(r'youtube\.com/[@c]/([^/?]+)', url)
                if match:
                    return match.group(1)
            elif platform == 'tiktok':
                # https://tiktok.com/@username
                match = re.search(r'tiktok\.com/@([^/?]+)', url)
                if match:
                    return match.group(1)
            elif platform == 'twitter':
                # https://twitter.com/username
                match = re.search(r'(?:twitter|x)\.com/([^/?]+)', url)
                if match:
                    return match.group(1)
        except:
            pass
        
        return None
    
    def _normalize_province_name(self, province: str) -> str:
        """Normalize Vietnamese province name to standard format"""
        if not province:
            return province
        
        # Standard province names mapping
        province_mapping = {
            'hà nội': 'Hà Nội',
            'ha noi': 'Hà Nội',
            'hn': 'Hà Nội',
            'tp hcm': 'Hồ Chí Minh',
            'hcm': 'Hồ Chí Minh',
            'sài gòn': 'Hồ Chí Minh',
            'saigon': 'Hồ Chí Minh',
            'tp.hcm': 'Hồ Chí Minh',
            'đà nẵng': 'Đà Nẵng',
            'da nang': 'Đà Nẵng',
            'hưng yên': 'Hưng Yên',
            'hung yen': 'Hưng Yên',
        }
        
        province_lower = province.lower().strip()
        return province_mapping.get(province_lower, province.title())


class DataValidator:
    """Validate normalized data against business rules"""
    
    @staticmethod
    def validate_document(doc: Dict) -> Tuple[bool, List[str]]:
        """
        Validate document
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # Required fields
        if not doc.get('url'):
            errors.append("Missing URL")
        
        if not doc.get('content') or len(doc['content']) < 10:
            errors.append("Content too short or missing")
        
        metadata = doc.get('metadata', {})
        
        if not metadata.get('title'):
            errors.append("Missing title")
        
        if not metadata.get('published'):
            errors.append("Missing published date")
        
        # Validate URL format
        url = doc.get('url')
        if url and not url.startswith(('http://', 'https://')):
            errors.append("Invalid URL format")
        
        # Validate engagement values
        engagement = metadata.get('engagement', {})
        for key in ['likes', 'shares', 'comments', 'views']:
            value = engagement.get(key)
            if value is not None:
                try:
                    if int(value) < 0:
                        errors.append(f"Negative {key} count")
                except (ValueError, TypeError):
                    errors.append(f"Invalid {key} value")
        
        # Validate date format
        published = metadata.get('published')
        if published:
            try:
                if isinstance(published, str):
                    datetime.fromisoformat(published.replace('Z', '+00:00'))
            except:
                errors.append("Invalid published date format")
        
        return len(errors) == 0, errors


def normalize_and_validate(doc: Dict) -> Tuple[Dict, bool, List[str], List[str]]:
    """
    Normalize and validate document
    
    Returns:
        (normalized_doc, is_valid, errors, warnings)
    """
    normalizer = DataNormalizer()
    normalized, norm_errors, warnings = normalizer.normalize_document(doc)
    
    if norm_errors:
        return normalized, False, norm_errors, warnings
    
    is_valid, val_errors = DataValidator.validate_document(normalized)
    
    all_errors = norm_errors + val_errors
    
    return normalized, is_valid, all_errors, warnings
