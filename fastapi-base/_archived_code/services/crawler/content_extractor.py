import json
from typing import Dict, Optional, Tuple, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime


def _try_trafilatura(html: str, url: Optional[str] = None) -> Optional[str]:
    try:
        import trafilatura  # type: ignore
        text = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
        if text and isinstance(text, str):
            return text.strip()
    except Exception:
        pass
    return None


def _try_readability(html: str) -> Optional[str]:
    try:
        from readability import Document  # type: ignore
        doc = Document(html)
        summary_html = doc.summary(html_partial=True)
        soup = BeautifulSoup(summary_html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return text.strip() if text else None
    except Exception:
        return None


def _extract_basic_text(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'noscript']):
        tag.decompose()
    body = soup.find('body')
    return (body.get_text(separator=' ', strip=True) if body else soup.get_text(separator=' ', strip=True)).strip()


def _get_meta(soup: BeautifulSoup, name: str, attr: str = 'property') -> Optional[str]:
    tag = soup.find('meta', attrs={attr: name})
    if tag and tag.get('content'):
        return tag['content'].strip()
    return None


def _parse_json_ld(soup: BeautifulSoup) -> Dict:
    data: Dict = {}
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            payload = json.loads(script.string or '{}')
            candidates = payload if isinstance(payload, list) else [payload]
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                t = item.get('@type', '')
                if isinstance(t, list):
                    t = t[0] if t else ''
                if t in ('NewsArticle', 'Article', 'BlogPosting'):
                    if 'datePublished' in item:
                        data['published'] = item['datePublished']
                    if 'headline' in item:
                        data['title'] = item['headline']
                    if 'author' in item:
                        data['author'] = item['author'] if isinstance(item['author'], str) else str(item['author'])
                    if 'keywords' in item:
                        data['keywords'] = item['keywords']
        except Exception:
            continue
    return data


def extract_document(html: str, url: Optional[str] = None, response_headers: Optional[Dict] = None) -> Tuple[str, Dict]:
    """
    Trích xuất nội dung và metadata từ HTML theo cách tổng quát.
    Ưu tiên: trafilatura -> readability -> BeautifulSoup basic.
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Title
    title = _get_meta(soup, 'og:title') or (soup.title.get_text().strip() if soup.title else '')
    description = _get_meta(soup, 'og:description') or _get_meta(soup, 'description', attr='name') or ''
    published = _get_meta(soup, 'article:published_time') or ''
    canonical = None
    link_tag = soup.find('link', rel=lambda x: x and 'canonical' in str(x).lower())
    if link_tag and link_tag.get('href') and url:
        canonical = urljoin(url, link_tag['href'])

    json_ld = _parse_json_ld(soup)
    if not title and json_ld.get('title'):
        title = json_ld['title']
    if not published and json_ld.get('published'):
        published = json_ld['published']

    # Content extraction
    text = _try_trafilatura(html, url=url) or _try_readability(html) or _extract_basic_text(soup)

    # Extract detailed metadata
    # Page type detection
    page_type = _detect_page_type(url, soup)
    
    # Extract headings
    h1_list = [h1.get_text(strip=True) for h1 in soup.find_all('h1') if h1.get_text(strip=True)]
    h2_list = [h2.get_text(strip=True) for h2 in soup.find_all('h2') if h2.get_text(strip=True)]
    h3_list = [h3.get_text(strip=True) for h3 in soup.find_all('h3') if h3.get_text(strip=True)]
    
    # Extract paragraphs
    paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
    
    # Extract images
    images = _extract_images(soup, url)
    
    # Extract videos
    videos = _extract_videos(soup, url)
    
    # Extract internal links
    internal_links = _extract_internal_links(soup, url)
    
    # Crawled timestamp
    crawled_at = datetime.utcnow().isoformat()

    metadata = {
        'title': title or '',
        'url': url or '',
        'canonical_url': canonical or '',
        'description': description,
        'published': published,
        'content_type': (response_headers or {}).get('content-type', '') if response_headers else '',
        # Extended metadata
        'page_type': page_type,
        'meta_description': description,
        'h1': h1_list[:10],  # Limit to first 10
        'h2': h2_list[:20],  # Limit to first 20
        'h3': h3_list[:30],  # Limit to first 30
        'crawled_at': crawled_at,
        'paragraphs': paragraphs[:50],  # Limit to first 50 paragraphs
        'images': images[:100],  # Limit to first 100 images
        'videos': videos[:20],  # Limit to first 20 videos
        'internal_links': internal_links[:100],  # Limit to first 100 links
    }

    return text, metadata


def _detect_page_type(url: Optional[str], soup: BeautifulSoup) -> str:
    """Detect the type of the page based on URL and content."""
    if not url:
        return "other"
    
    url_lower = url.lower()
    
    # Check URL patterns
    if url_lower.endswith('/') and url_lower.count('/') <= 3:
        return "home"
    if '/blog/' in url_lower or '/post/' in url_lower or '/article/' in url_lower:
        return "blog"
    if '/product/' in url_lower or '/shop/' in url_lower:
        return "product"
    if '/category/' in url_lower or '/tag/' in url_lower:
        return "category"
    if '/about' in url_lower:
        return "about"
    if '/contact' in url_lower:
        return "contact"
    
    # Check for article schema
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
            if isinstance(data, dict):
                schema_type = data.get('@type', '')
                if 'Article' in schema_type or 'NewsArticle' in schema_type:
                    return "article"
        except:
            pass
    
    return "other"


def _extract_images(soup: BeautifulSoup, base_url: Optional[str]) -> List[Dict]:
    """Extract images with their metadata."""
    images = []
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src and base_url:
            src = urljoin(base_url, src)
        
        if src:
            images.append({
                'src': src,
                'alt': img.get('alt'),
                'title': img.get('title')
            })
    
    return images


def _extract_videos(soup: BeautifulSoup, base_url: Optional[str]) -> List[Dict]:
    """Extract videos from various sources."""
    videos = []
    
    # YouTube iframes
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '')
        if 'youtube.com' in src or 'youtu.be' in src:
            videos.append({
                'type': 'youtube',
                'url': src,
                'text': iframe.get_text(strip=True)
            })
    
    # Video tags
    for video in soup.find_all('video'):
        src = video.get('src')
        if not src:
            source = video.find('source')
            if source:
                src = source.get('src')
        
        if src and base_url:
            src = urljoin(base_url, src)
        
        if src:
            videos.append({
                'type': 'video',
                'url': src,
                'text': video.get_text(strip=True)
            })
    
    # Links to video platforms
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(platform in href for platform in ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com']):
            videos.append({
                'type': 'link',
                'url': href,
                'text': a.get_text(strip=True)
            })
    
    return videos


def _extract_internal_links(soup: BeautifulSoup, base_url: Optional[str]) -> List[str]:
    """Extract internal links from the page."""
    if not base_url:
        return []
    
    from urllib.parse import urlparse
    base_domain = urlparse(base_url).netloc
    
    internal_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        
        # Skip anchors and javascript
        if href.startswith('#') or href.startswith('javascript:'):
            continue
        
        # Convert to absolute URL
        absolute_url = urljoin(base_url, href)
        
        # Check if internal
        link_domain = urlparse(absolute_url).netloc
        if link_domain == base_domain:
            internal_links.append(absolute_url)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for link in internal_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    return unique_links
