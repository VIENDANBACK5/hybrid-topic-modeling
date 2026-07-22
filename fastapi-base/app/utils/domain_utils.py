"""
Domain extraction utility
Tự động extract domain từ URL hoặc infer từ source/platform
"""
from urllib.parse import urlparse
from typing import Optional


def extract_domain(
    url: Optional[str] = None,
    source: Optional[str] = None,
    platform: Optional[str] = None,
    account_name: Optional[str] = None
) -> Optional[str]:
    """
    Extract domain từ URL hoặc infer từ source/platform
    
    Args:
        url: URL của article
        source: Source name/URL
        platform: Social platform (facebook, youtube, etc.)
        account_name: Tên account/page
    
    Returns:
        Domain string hoặc None
    """
    # 1. Try extract from URL
    if url:
        domain = _extract_from_url(url)
        if domain:
            return domain
    
    # 2. Try extract from source
    if source:
        domain = _extract_from_url(source)
        if domain:
            return domain
        
        # Try infer from source name
        domain = _infer_from_source_name(source)
        if domain:
            return domain
    
    # 3. Use platform as domain
    if platform:
        platform_domains = {
            'facebook': 'facebook.com',
            'youtube': 'youtube.com',
            'tiktok': 'tiktok.com',
            'twitter': 'twitter.com',
            'instagram': 'instagram.com',
            'threads': 'threads.net',
        }
        if platform.lower() in platform_domains:
            return platform_domains[platform.lower()]
    
    # 4. Use account_name as domain for social media
    if account_name and platform in ['facebook', 'tiktok', 'youtube']:
        return account_name
    
    return None


def _extract_from_url(url: str) -> Optional[str]:
    """Extract domain from URL"""
    if not url:
        return None
    
    # Handle relative URLs
    if url.startswith('/'):
        return None
    
    # Handle malformed URLs
    if url.startswith('https:///') or url.startswith('http:///'):
        return None
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        if not domain:
            return None
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Remove port
        if ':' in domain:
            domain = domain.split(':')[0]
        
        return domain
    except:
        return None


def _infer_from_source_name(source: str) -> Optional[str]:
    """Infer domain from source name"""
    if not source:
        return None
    
    source_lower = source.lower().strip()
    
    # Common Vietnamese news sources
    mappings = {
        # Major news
        'vnexpress': 'vnexpress.net',
        'vn express': 'vnexpress.net',
        'tuổi trẻ': 'tuoitre.vn',
        'tuoi tre': 'tuoitre.vn',
        'thanh niên': 'thanhnien.vn',
        'thanh nien': 'thanhnien.vn',
        'dân trí': 'dantri.com.vn',
        'dan tri': 'dantri.com.vn',
        'vietnamnet': 'vietnamnet.vn',
        'viet nam net': 'vietnamnet.vn',
        'báo mới': 'baomoi.com',
        'bao moi': 'baomoi.com',
        'zing news': 'zingnews.vn',
        'zingnews': 'zingnews.vn',
        
        # Entertainment & lifestyle
        'kenh14': 'kenh14.vn',
        'soha': 'soha.vn',
        'genk': 'genk.vn',
        '2sao': '2sao.vn',
        
        # Business & finance
        'cafef': 'cafef.vn',
        'cafebiz': 'cafebiz.vn',
        'vietstock': 'vietstock.vn',
        'ndh': 'ndh.vn',
        
        # Government & official
        'nhandan': 'nhandan.vn',
        'nhân dân': 'nhandan.vn',
        'vov': 'vov.vn',
        'vov.vn': 'vov.vn',
        'vtv': 'vtv.vn',
        
        # Local news - Hưng Yên
        'báo hưng yên': 'baohungyen.vn',
        'bao hung yen': 'baohungyen.vn',
        'hưng yên': 'baohungyen.vn',
        'hung yen': 'baohungyen.vn',
        'baohungyen': 'baohungyen.vn',
    }
    
    for key, domain in mappings.items():
        if key in source_lower:
            return domain
    
    return None


def ensure_domain(article_data: dict) -> dict:
    """
    Ensure article data has domain field filled
    Tự động fill nếu thiếu
    
    Args:
        article_data: Dict chứa thông tin article
    
    Returns:
        article_data với domain đã được fill
    """
    if not article_data.get('domain'):
        article_data['domain'] = extract_domain(
            url=article_data.get('url'),
            source=article_data.get('source'),
            platform=article_data.get('social_platform') or article_data.get('platform'),
            account_name=article_data.get('account_name')
        )
    
    return article_data
