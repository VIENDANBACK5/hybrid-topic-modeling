"""
Crawl History Service - Manage incremental crawling
Tracks URLs, avoids re-crawling, implements smart crawling strategies
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.model_crawl_history import CrawlHistory
from app.models.model_article import Article


class CrawlHistoryService:
    """Service for managing crawl history and incremental crawling"""
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc
    
    @staticmethod
    def extract_category(url: str) -> Optional[str]:
        """Extract category from URL path (e.g., /chinh-tri/...)"""
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split('/') if p]
        if parts and not parts[0].endswith('.html'):
            return parts[0]
        return None
    
    @staticmethod
    def is_article_url(url: str) -> bool:
        """Check if URL looks like an article (vs listing page)"""
        return url.endswith('.html') and '-' in url.split('/')[-1]
    
    @staticmethod
    def discover_urls(
        db: Session,
        urls: List[str],
        source_domain: str,
        source_category: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Register discovered URLs in history
        Returns dict: {url: status} where status is 'new', 'existing', 'article_exists'
        """
        result = {}
        
        for url in urls:
            # Check if URL already in history
            existing = db.query(CrawlHistory).filter(CrawlHistory.url == url).first()
            
            if existing:
                result[url] = 'existing'
                # Update last_checked
                existing.last_checked_at = datetime.utcnow()
                continue
            
            # Check if article already exists
            article_exists = db.query(Article).filter(Article.url == url).first()
            if article_exists:
                # Create history record pointing to existing article
                history = CrawlHistory(
                    url=url,
                    domain=CrawlHistoryService.extract_domain(url),
                    category=CrawlHistoryService.extract_category(url),
                    status='success',
                    has_article=True,
                    article_id=article_exists.id,
                    is_listing=not CrawlHistoryService.is_article_url(url),
                    discovered_at=datetime.utcnow(),
                    last_crawled_at=article_exists.created_at,
                    last_checked_at=datetime.utcnow(),
                    crawl_count=1
                )
                db.add(history)
                result[url] = 'article_exists'
                continue
            
            # New URL - create history record
            history = CrawlHistory(
                url=url,
                domain=source_domain,
                category=source_category or CrawlHistoryService.extract_category(url),
                status='pending',
                has_article=False,
                is_listing=not CrawlHistoryService.is_article_url(url),
                discovered_at=datetime.utcnow(),
                last_checked_at=datetime.utcnow()
            )
            db.add(history)
            result[url] = 'new'
        
        db.commit()
        return result
    
    @staticmethod
    def get_pending_urls(
        db: Session,
        domain: str,
        limit: int = 100,
        category: Optional[str] = None,
        article_only: bool = True
    ) -> List[str]:
        """
        Get URLs that need to be crawled
        """
        query = db.query(CrawlHistory).filter(
            and_(
                CrawlHistory.domain == domain,
                CrawlHistory.status == 'pending',
                CrawlHistory.has_article == False
            )
        )
        
        if category:
            query = query.filter(CrawlHistory.category == category)
        
        if article_only:
            query = query.filter(CrawlHistory.is_listing == False)
        
        # Prioritize: older discoveries first
        query = query.order_by(CrawlHistory.discovered_at.asc())
        
        results = query.limit(limit).all()
        return [r.url for r in results]
    
    @staticmethod
    def mark_crawled(
        db: Session,
        url: str,
        success: bool,
        article_id: Optional[int] = None,
        error_message: Optional[str] = None,
        child_links_count: int = 0,
        page_metadata: Optional[Dict] = None
    ):
        """Mark URL as crawled with results"""
        history = db.query(CrawlHistory).filter(CrawlHistory.url == url).first()
        
        if not history:
            # Create if doesn't exist
            history = CrawlHistory(
                url=url,
                domain=CrawlHistoryService.extract_domain(url),
                category=CrawlHistoryService.extract_category(url),
                is_listing=not CrawlHistoryService.is_article_url(url),
                discovered_at=datetime.utcnow()
            )
            db.add(history)
        
        # Update crawl info
        history.status = 'success' if success else 'failed'
        history.last_crawled_at = datetime.utcnow()
        history.last_checked_at = datetime.utcnow()
        history.crawl_count = (history.crawl_count or 0) + 1
        history.has_article = article_id is not None
        history.article_id = article_id
        history.child_links_count = child_links_count
        history.error_message = error_message
        history.page_metadata = page_metadata
        
        db.commit()
    
    @staticmethod
    def get_stats(db: Session, domain: str) -> Dict:
        """Get crawl statistics for a domain"""
        total = db.query(func.count(CrawlHistory.id)).filter(
            CrawlHistory.domain == domain
        ).scalar()
        
        pending = db.query(func.count(CrawlHistory.id)).filter(
            and_(
                CrawlHistory.domain == domain,
                CrawlHistory.status == 'pending'
            )
        ).scalar()
        
        success = db.query(func.count(CrawlHistory.id)).filter(
            and_(
                CrawlHistory.domain == domain,
                CrawlHistory.status == 'success'
            )
        ).scalar()
        
        failed = db.query(func.count(CrawlHistory.id)).filter(
            and_(
                CrawlHistory.domain == domain,
                CrawlHistory.status == 'failed'
            )
        ).scalar()
        
        articles = db.query(func.count(CrawlHistory.id)).filter(
            and_(
                CrawlHistory.domain == domain,
                CrawlHistory.has_article == True
            )
        ).scalar()
        
        # Get categories
        categories = db.query(
            CrawlHistory.category,
            func.count(CrawlHistory.id).label('count')
        ).filter(
            CrawlHistory.domain == domain
        ).group_by(CrawlHistory.category).all()
        
        return {
            "domain": domain,
            "total_urls": total,
            "pending": pending,
            "success": success,
            "failed": failed,
            "articles": articles,
            "categories": {cat: count for cat, count in categories if cat}
        }
    
    @staticmethod
    def get_urls_needing_recrawl(
        db: Session,
        domain: str,
        days_old: int = 30,
        limit: int = 100
    ) -> List[str]:
        """
        Get URLs that haven't been crawled in X days
        For periodic re-crawling to catch updates
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        query = db.query(CrawlHistory).filter(
            and_(
                CrawlHistory.domain == domain,
                CrawlHistory.status == 'success',
                CrawlHistory.has_article == True,
                CrawlHistory.last_crawled_at < cutoff_date
            )
        ).order_by(CrawlHistory.last_crawled_at.asc()).limit(limit)
        
        return [r.url for r in query.all()]
    
    @staticmethod
    def should_crawl_url(db: Session, url: str, force: bool = False) -> bool:
        """
        Decision: should we crawl this URL?
        Returns True if URL should be crawled
        """
        if force:
            return True
        
        # Check if article already exists
        article = db.query(Article).filter(Article.url == url).first()
        if article:
            return False
        
        # Check crawl history
        history = db.query(CrawlHistory).filter(CrawlHistory.url == url).first()
        if not history:
            return True  # New URL, should crawl
        
        # If pending or failed, should crawl
        if history.status in ['pending', 'failed']:
            return True
        
        # If successful and has article, skip
        if history.status == 'success' and history.has_article:
            return False
        
        return True
