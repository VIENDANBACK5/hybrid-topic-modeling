"""
Async crawler with parallel fetching
"""
import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from app.core.performance import batch_process
from app.core.resilience import retry, with_timeout

logger = logging.getLogger(__name__)


class AsyncCrawler:
    """Asynchronous web crawler with parallel fetching"""
    
    def __init__(
        self,
        max_concurrent: int = 10,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Args:
            max_concurrent: Maximum concurrent requests
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts
        """
        self.max_concurrent = max_concurrent
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def fetch_url(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Optional[Dict]:
        """
        Fetch single URL
        
        Args:
            session: aiohttp session
            url: URL to fetch
        
        Returns:
            Dict with url, content, status, or None if failed
        """
        try:
            async with session.get(url, timeout=self.timeout) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'text/html' in content_type:
                        text = await response.text()
                        
                        # Parse with BeautifulSoup
                        soup = BeautifulSoup(text, 'html.parser')
                        
                        # Remove scripts, styles
                        for tag in soup(['script', 'style', 'nav', 'footer']):
                            tag.decompose()
                        
                        # Extract content
                        title = soup.find('title')
                        title_text = title.get_text().strip() if title else ''
                        
                        body_text = soup.get_text(separator=' ', strip=True)
                        
                        return {
                            'url': url,
                            'title': title_text,
                            'content': body_text,
                            'status': response.status,
                            'content_length': len(body_text)
                        }
                    else:
                        logger.debug(f"Skipping non-HTML: {url} ({content_type})")
                        return None
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    @retry(max_attempts=3, delay=1.0, exceptions=(aiohttp.ClientError,))
    async def fetch_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Optional[Dict]:
        """Fetch URL with retry logic"""
        return await self.fetch_url(session, url)
    
    async def crawl_urls(
        self,
        urls: List[str],
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """
        Crawl multiple URLs in parallel
        
        Args:
            urls: List of URLs to crawl
            max_pages: Maximum pages to fetch (None = unlimited)
        
        Returns:
            List of crawled documents
        """
        if max_pages:
            urls = urls[:max_pages]
        
        logger.info(f"Starting async crawl of {len(urls)} URLs")
        
        results = []
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        
        async with aiohttp.ClientSession(
            headers=self.headers,
            connector=connector
        ) as session:
            # Create tasks
            tasks = [
                self.fetch_with_retry(session, url)
                for url in urls
            ]
            
            # Execute with progress tracking
            for i, coro in enumerate(asyncio.as_completed(tasks)):
                result = await coro
                if result:
                    results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i + 1}/{len(urls)} URLs fetched")
        
        logger.info(f"Crawl complete: {len(results)}/{len(urls)} successful")
        return results
    
    async def crawl_site(
        self,
        start_url: str,
        max_depth: int = 2,
        max_pages: int = 100,
        same_domain_only: bool = True
    ) -> List[Dict]:
        """
        Crawl entire site starting from URL
        
        Args:
            start_url: Starting URL
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to fetch
            same_domain_only: Only crawl same domain
        
        Returns:
            List of crawled documents
        """
        base_domain = urlparse(start_url).netloc
        visited: Set[str] = set()
        to_visit: List[tuple] = [(start_url, 0)]  # (url, depth)
        results = []
        
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        
        async with aiohttp.ClientSession(
            headers=self.headers,
            connector=connector
        ) as session:
            while to_visit and len(results) < max_pages:
                # Get batch of URLs at current depth
                batch_size = min(self.max_concurrent, max_pages - len(results))
                batch = []
                
                while to_visit and len(batch) < batch_size:
                    url, depth = to_visit.pop(0)
                    
                    if url in visited:
                        continue
                    
                    if depth > max_depth:
                        continue
                    
                    batch.append((url, depth))
                    visited.add(url)
                
                if not batch:
                    break
                
                # Fetch batch
                tasks = [
                    self.fetch_with_retry(session, url)
                    for url, _ in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(batch_results):
                    if isinstance(result, dict) and result:
                        results.append(result)
                        
                        # Extract links for next depth
                        url, depth = batch[i]
                        if depth < max_depth:
                            # Parse links from content (simplified)
                            # In production, parse HTML properly
                            pass
                
                logger.info(f"Crawled {len(results)}/{max_pages} pages (depth {batch[0][1]})")
        
        return results


# Convenience functions
async def async_crawl_urls(urls: List[str], max_concurrent: int = 10) -> List[Dict]:
    """Quick async crawl of URLs"""
    crawler = AsyncCrawler(max_concurrent=max_concurrent)
    return await crawler.crawl_urls(urls)


async def async_crawl_site(
    url: str,
    max_depth: int = 2,
    max_pages: int = 100
) -> List[Dict]:
    """Quick async site crawl"""
    crawler = AsyncCrawler()
    return await crawler.crawl_site(url, max_depth, max_pages)
