"""
Script to fill domain column in articles table
Extract domain from URL or infer from source
"""
import sys
import os
from urllib.parse import urlparse
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL"""
    if not url:
        return None
    
    # Handle relative URLs
    if url.startswith('/'):
        return None
    
    # Handle full URLs
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain if domain else None
    except:
        return None


def infer_domain_from_source(source: str) -> str:
    """Infer domain from source name"""
    if not source:
        return None
    
    source = source.lower().strip()
    
    # Common mappings
    mappings = {
        'vnexpress': 'vnexpress.net',
        'vn express': 'vnexpress.net',
        'tuổi trẻ': 'tuoitre.vn',
        'tuoi tre': 'tuoitre.vn',
        'thanh niên': 'thanhnien.vn',
        'thanh nien': 'thanhnien.vn',
        'dân trí': 'dantri.com.vn',
        'dan tri': 'dantri.com.vn',
        'vietnamnet': 'vietnamnet.vn',
        'báo mới': 'baomoi.com',
        'bao moi': 'baomoi.com',
        'zing news': 'zingnews.vn',
        'zingnews': 'zingnews.vn',
        'kenh14': 'kenh14.vn',
        'soha': 'soha.vn',
        'cafef': 'cafef.vn',
        'cafebiz': 'cafebiz.vn',
        'vietstock': 'vietstock.vn',
        'nhandan': 'nhandan.vn',
        'nhân dân': 'nhandan.vn',
        'báo hưng yên': 'baohungyen.vn',
        'bao hung yen': 'baohungyen.vn',
        'hưng yên': 'baohungyen.vn',
        'hung yen': 'baohungyen.vn',
    }
    
    for key, domain in mappings.items():
        if key in source:
            return domain
    
    return None


def fill_domains():
    """Fill missing domains in articles table"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Get articles with missing domain
        result = conn.execute(text("""
            SELECT id, url, source, domain 
            FROM articles 
            WHERE domain IS NULL OR domain = ''
            ORDER BY id
        """))
        
        articles = result.fetchall()
        logger.info(f"Found {len(articles)} articles with missing domain")
        
        updated = 0
        failed = 0
        
        for article in articles:
            article_id, url, source, current_domain = article
            
            # Try to extract from URL
            domain = extract_domain_from_url(url)
            
            # If URL is relative, try to infer from source
            if not domain and source:
                domain = infer_domain_from_source(source)
            
            if domain:
                try:
                    conn.execute(
                        text("UPDATE articles SET domain = :domain WHERE id = :id"),
                        {"domain": domain, "id": article_id}
                    )
                    conn.commit()
                    updated += 1
                    logger.info(f"  Updated article {article_id}: domain = {domain}")
                except Exception as e:
                    logger.error(f"  Failed to update article {article_id}: {e}")
                    failed += 1
            else:
                logger.warning(f"  Could not determine domain for article {article_id} (url={url[:50]}, source={source})")
                failed += 1
        
        logger.info(f"\nCompleted: Updated {updated}, Failed {failed}")


if __name__ == "__main__":
    fill_domains()
