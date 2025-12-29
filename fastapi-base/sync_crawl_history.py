"""
Sync existing articles into crawl_history table
Run once to populate history from existing data
"""
import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.model_article import Article
from app.services.srv_crawl_history import CrawlHistoryService

def sync_articles_to_history():
    db = SessionLocal()
    try:
        # Get all articles
        articles = db.query(Article).all()
        print(f"Found {len(articles)} articles to sync")
        
        urls_to_discover = [article.url for article in articles]
        
        # Use discover_urls to register them
        result = CrawlHistoryService.discover_urls(
            db=db,
            urls=urls_to_discover,
            source_domain="baohungyen.vn"
        )
        
        print(f"Sync results: {result}")
        
        # Get stats
        stats = CrawlHistoryService.get_stats(db, "baohungyen.vn")
        print(f"\nCrawl history stats:")
        print(f"  Total URLs: {stats['total_urls']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Success: {stats['success']}")
        print(f"  Articles: {stats['articles']}")
        print(f"  Categories: {stats['categories']}")
        
    finally:
        db.close()

if __name__ == "__main__":
    sync_articles_to_history()
