from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON
from datetime import datetime
from app.models.model_base import BareBaseModel


class CrawlHistory(BareBaseModel):
    """
    Track crawl history to avoid re-crawling same URLs
    Enables incremental crawling strategy
    """
    __tablename__ = "crawl_history"
    
    # URL being tracked
    url = Column(String(2048), unique=True, nullable=False, index=True)
    
    # Domain extracted from URL
    domain = Column(String(256), nullable=False, index=True)
    
    # Category/section of the site (e.g., 'chinh-tri', 'kinh-te')
    category = Column(String(256), index=True)
    
    # URL pattern (for pattern-based filtering)
    url_pattern = Column(String(512))
    
    # Crawl status
    status = Column(String(50), default="pending")  # pending, success, failed, skipped
    
    # When first discovered
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # When last crawled
    last_crawled_at = Column(DateTime)
    
    # When last checked (even if not crawled)
    last_checked_at = Column(DateTime, default=datetime.utcnow)
    
    # Number of times crawled
    crawl_count = Column(Integer, default=0)
    
    # Whether article exists in articles table
    has_article = Column(Boolean, default=False)
    
    # Article ID if exists
    article_id = Column(Integer)
    
    # Whether this is a listing page (vs article page)
    is_listing = Column(Boolean, default=False)
    
    # Number of child links found on this page
    child_links_count = Column(Integer, default=0)
    
    # Error message if failed
    error_message = Column(String(1024))
    
    # Metadata from page (publish date, author, etc)
    page_metadata = Column(JSON)
    
    # Crawl parameters used
    crawl_params = Column(JSON)
    
    def __repr__(self):
        return f"<CrawlHistory(url={self.url[:50]}..., status={self.status})>"
