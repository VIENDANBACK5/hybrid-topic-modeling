import asyncio
import json
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    feedparser = None
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import httpx
from bs4 import BeautifulSoup
from scrapy import Spider
from scrapy.crawler import CrawlerRunner
from scrapy.http import Response
from twisted.internet import asyncioreactor
import logging
import re
import io
from urllib.parse import urlparse, urljoin
from .content_extractor import extract_document

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    @abstractmethod
    async def fetch(self, source: str, **kwargs) -> List[Dict]:
        pass


class SimpleSpider(Spider):
    name = 'simple'
    
    def __init__(self, start_url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [start_url]
        self.results = []
    
    def parse(self, response: Response):
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        title = soup.find('title')
        title_text = title.get_text().strip() if title else ''
        
        body = soup.find('body')
        body_text = body.get_text(separator=' ', strip=True) if body else soup.get_text(separator=' ', strip=True)
        
        self.results.append({
            'source': 'web',
            'source_id': response.url,
            'raw_content': body_text,
            'metadata': {
                'title': title_text,
                'url': response.url,
                'status_code': response.status
            }
        })


class WebFetcher(BaseFetcher):
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    async def fetch(self, url: str, **kwargs) -> List[Dict]:
        try:
            # Controls
            max_pages = kwargs.get('max_pages', 100)
            max_depth = kwargs.get('max_depth', 3)
            follow_links = kwargs.get('follow_links', False)
            min_length = kwargs.get('min_length', 300)
            delay_ms = kwargs.get('delay_ms', 0)
            respect_robots = kwargs.get('respect_robots', False)
            use_sitemap = kwargs.get('use_sitemap', False)
            allowed_patterns: Optional[List[str]] = kwargs.get('allowed_patterns')
            blocked_patterns: Optional[List[str]] = kwargs.get('blocked_patterns')
            url_pattern = kwargs.get('url_pattern', None)  # legacy: simple substring filter

            # Headers override
            extra_headers = kwargs.get('headers')
            headers = {**self.headers, **(extra_headers or {})}
            
            results = []
            visited = set()
            to_visit: List[Tuple[str, int]] = [(url, 0)]
            crawled_urls = set()
            base_domain = urlparse(url).netloc

            # Robots.txt
            rp = None
            if respect_robots:
                try:
                    import urllib.robotparser as robotparser
                    rp = robotparser.RobotFileParser()
                    robots_url = f"{urlparse(url).scheme}://{base_domain}/robots.txt"
                    rp.set_url(robots_url)
                    async with httpx.AsyncClient(timeout=self.timeout, verify=False) as rc:
                        r = await rc.get(robots_url, headers=headers)
                        if r.status_code == 200:
                            rp.parse(r.text.splitlines())
                except Exception:
                    rp = None

            # Sitemap seeding
            if use_sitemap:
                try:
                    sitemaps = []
                    robots_url = f"{urlparse(url).scheme}://{base_domain}/robots.txt"
                    async with httpx.AsyncClient(timeout=self.timeout, verify=False) as rc:
                        r = await rc.get(robots_url, headers=headers)
                        if r.status_code == 200:
                            for line in r.text.splitlines():
                                if line.lower().startswith('sitemap:'):
                                    sm = line.split(':', 1)[1].strip()
                                    sitemaps.append(sm)
                    # Parse each sitemap (simple XML parse for <loc>)
                    import xml.etree.ElementTree as ET
                    urls_from_sitemap = []
                    async with httpx.AsyncClient(timeout=self.timeout, verify=False) as rc:
                        for sm in sitemaps:
                            try:
                                rs = await rc.get(sm, headers=headers)
                                if rs.status_code != 200:
                                    continue
                                it = ET.iterparse(io.StringIO(rs.text))
                                for _, el in it:
                                    if el.tag.endswith('loc') and el.text:
                                        urls_from_sitemap.append(el.text.strip())
                            except Exception:
                                continue
                    # Seed
                    for u in urls_from_sitemap[: max(0, max_pages // 2)]:
                        to_visit.append((u, 0))
                except Exception:
                    pass
            
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, verify=False) as client:
                page_count = 0
                
                while to_visit and page_count < max_pages:
                    current_url, depth = to_visit.pop(0)
                    
                    if current_url in visited:
                        continue
                    
                    visited.add(current_url)
                    page_count += 1
                    
                    try:
                        if rp and not rp.can_fetch(headers.get('User-Agent', '*'), current_url):
                            logger.info(f"Robots.txt disallow: {current_url}")
                            continue

                        response = await client.get(current_url, headers=headers)
                        response.raise_for_status()
                        ct = response.headers.get('content-type', '')
                        if 'text/html' not in ct:
                            logger.debug(f"Skip non-HTML: {current_url} ({ct})")
                            continue
                        
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Follow links
                        if follow_links and depth < max_depth:
                            links_found = 0
                            for a in soup.find_all('a', href=True):
                                href = a['href']
                                full_url = urljoin(current_url, href)
                                parsed = urlparse(full_url)
                                if parsed.netloc != base_domain:
                                    continue
                                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                                if parsed.query:
                                    clean_url += f"?{parsed.query}"

                                # Filters
                                allow_ok = True
                                if allowed_patterns:
                                    allow_ok = any(p in clean_url for p in allowed_patterns)
                                if url_pattern and allow_ok:
                                    allow_ok = (url_pattern in clean_url)
                                if blocked_patterns and allow_ok:
                                    if any(p in clean_url for p in blocked_patterns):
                                        allow_ok = False
                                if not allow_ok:
                                    continue

                                if clean_url not in visited and (clean_url, depth+1) not in to_visit:
                                    to_visit.append((clean_url, depth + 1))
                                    links_found += 1
                            logger.info(f"Tìm thấy {links_found} link mới trong {current_url}")
                        
                        # Extract content & metadata (generic)
                        text, meta = extract_document(response.text, url=current_url, response_headers=response.headers)
                        content_len = len(text or '')

                        if content_len >= min_length and current_url not in crawled_urls:
                            crawled_urls.add(current_url)
                            results.append({
                                'source': 'web',
                                'source_id': current_url,
                                'raw_content': text,
                                'metadata': {
                                    **meta,
                                    'status_code': response.status_code,
                                    'content_length': content_len
                                }
                            })
                            logger.info(f"Đã crawl bài {len(results)}: {current_url} ({content_len} chars)")
                        else:
                            logger.debug(f"Bỏ qua {current_url}: nội dung ngắn ({content_len} chars) hoặc trùng")
                        
                    except Exception as e:
                        logger.warning(f"Lỗi khi fetch {current_url}: {e}")
                        continue
                    finally:
                        if delay_ms:
                            await asyncio.sleep(max(0, delay_ms) / 1000)
                
                logger.info(f"Hoàn tất crawl: {len(results)} bài, đã thăm {page_count} trang")
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi crawl {url}: {e}")
            return []


class RSSFetcher(BaseFetcher):
    async def fetch(self, feed_url: str, **kwargs) -> List[Dict]:
        if not FEEDPARSER_AVAILABLE:
            raise ImportError("feedparser module is not installed. Install it with: pip install feedparser")
        try:
            feed = feedparser.parse(feed_url)
            
            results = []
            for entry in feed.entries:
                content = entry.get('content', [{}])[0].get('value', '') or entry.get('summary', '')
                
                results.append({
                    'source': 'rss',
                    'source_id': entry.get('id', entry.get('link', '')),
                    'raw_content': content,
                    'metadata': {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'author': entry.get('author', '')
                    }
                })
            
            return results
        except Exception as e:
            logger.error(f"Error fetching RSS {feed_url}: {e}")
            return []


class FileFetcher(BaseFetcher):
    async def fetch(self, file_path: str, **kwargs) -> List[Dict]:
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if path.suffix == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    return [
                        {
                            'source': 'file',
                            'source_id': f"{file_path}#{i}",
                            'raw_content': item.get('content', item.get('text', str(item))),
                            'metadata': {'file': file_path, 'index': i}
                        }
                        for i, item in enumerate(data)
                    ]
                else:
                    return [{
                        'source': 'file',
                        'source_id': file_path,
                        'raw_content': data.get('content', data.get('text', str(data))),
                        'metadata': {'file': file_path}
                    }]
            
            elif path.suffix in ['.txt', '.md']:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return [{
                    'source': 'file',
                    'source_id': file_path,
                    'raw_content': content,
                    'metadata': {'file': file_path, 'type': path.suffix}
                }]
            
            else:
                raise ValueError(f"Unsupported file type: {path.suffix}")
        
        except Exception as e:
            logger.error(f"Error fetching file {file_path}: {e}")
            return []


class APIFetcher(BaseFetcher):
    def __init__(self, headers: Optional[Dict] = None):
        self.headers = headers or {}
    
    async def fetch(self, api_url: str, **kwargs) -> List[Dict]:
        try:
            import httpx
            method = kwargs.get('method', 'GET')
            params = kwargs.get('params', {})
            data = kwargs.get('data', {})
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.request(
                    method,
                    api_url,
                    headers=self.headers,
                    params=params,
                    json=data,
                    timeout=30.0
                )
                response.raise_for_status()
                
                json_data = response.json()
                
                if isinstance(json_data, list):
                    return [
                        {
                            'source': 'api',
                            'source_id': f"{api_url}#{i}",
                            'raw_content': json.dumps(item, ensure_ascii=False),
                            'metadata': {'api_url': api_url, 'index': i}
                        }
                        for i, item in enumerate(json_data)
                    ]
                else:
                    return [{
                        'source': 'api',
                        'source_id': api_url,
                        'raw_content': json.dumps(json_data, ensure_ascii=False),
                        'metadata': {'api_url': api_url}
                    }]
        
        except Exception as e:
            logger.error(f"Error fetching API {api_url}: {e}")
            return []
