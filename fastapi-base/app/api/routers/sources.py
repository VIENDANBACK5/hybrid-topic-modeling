from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.model_source import Source
from app.models.model_article import Article
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class SourceCreate(BaseModel):
    """Đơn giản - chỉ cần tên + URL + loại"""
    name: str
    url: str
    type: str  # "news", "social", "forum"
    category: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None  # Khu vực địa phương


class SourceResponse(BaseModel):
    id: int
    name: str
    url: str
    type: str
    category: Optional[str]
    description: Optional[str]
    domain: Optional[str]
    region: Optional[str]
    is_active: bool
    total_articles: int
    last_crawled_at: Optional[str]


class SourcesOverviewResponse(BaseModel):
    """Response tổng hợp theo loại nguồn"""
    news: List[Dict]  # Báo điện tử, websites ban ngành
    social: List[Dict]  # Mạng xã hội
    forum: List[Dict]  # Diễn đàn, fanpage, group địa phương
    stats: Dict  # Thống kê


@router.post("")
async def add_source(request: SourceCreate, db: Session = Depends(get_db)):
    """
    Thêm nguồn thu thập mới
    
    Types:
    - news: Báo điện tử, cổng thông tin, websites ban ngành
    - social: Mạng xã hội (Facebook, Twitter, Instagram...)
    - forum: Diễn đàn, Fanpage, Group địa phương
    
    Example:
        {"name": "Báo Hưng Yên", "url": "https://baohungyen.vn", "type": "news"}
        {"name": "FB Hưng Yên", "url": "https://facebook.com/hungyenpage", "type": "social"}
    """
    try:
        # Check duplicate URL
        existing = db.query(Source).filter(Source.url == request.url).first()
        if existing:
            raise HTTPException(status_code=400, detail="URL already exists")
        
        # Extract domain
        from urllib.parse import urlparse
        domain = urlparse(request.url).netloc if request.url else None
        
        # Create source
        source = Source(
            name=request.name,
            url=request.url,
            type=request.type,
            category=request.category,
            description=request.description,
            domain=domain,
            region=request.region,
            is_active=True
        )
        
        db.add(source)
        db.commit()
        db.refresh(source)
        
        return {
            "status": "success",
            "message": "Source added",
            "source": {
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "type": source.type
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Add source error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_sources_overview(db: Session = Depends(get_db)):
    """
    GỘP TẤT CẢ - Xem nguồn thu thập theo từng loại + thống kê chi tiết
    
    Trả về:
    - news: Danh sách báo điện tử (name, url, số bài, số categories, nguồn con...)
    - social: Danh sách mạng xã hội
    - forum: Danh sách diễn đàn
    - stats: Thống kê tổng quan
    
    Nếu loại nào không có → trả về []
    """
    try:
        # Get all sources
        sources = db.query(Source).filter(Source.is_active == True).all()
        
        # Get article counts per source URL
        article_counts = dict(
            db.query(Article.source, func.count(Article.id))
            .group_by(Article.source)
            .all()
        )
        
        # Group by type
        news_sources = []
        social_sources = []
        forum_sources = []
        
        for source in sources:
            article_count = article_counts.get(source.url, 0)
            
            # Get sub-sources (categories, domains...) từ articles
            articles_from_source = db.query(Article).filter(Article.source == source.url).all()
            
            # Thống kê categories
            categories = {}
            domains = {}
            unique_urls = set()
            
            for art in articles_from_source:
                unique_urls.add(art.url)
                
                if art.category:
                    categories[art.category] = categories.get(art.category, 0) + 1
                
                if art.domain and art.domain != source.domain:
                    domains[art.domain] = domains.get(art.domain, 0) + 1
            
            source_data = {
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "category": source.category,
                "region": source.region,
                "total_articles": article_count,
                "total_unique_urls": len(unique_urls),
                "last_crawled": source.last_crawled_at.isoformat() if source.last_crawled_at else None,
                
                # Thống kê chi tiết
                "categories": [
                    {"name": cat, "count": count} 
                    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)
                ],
                "sub_domains": [
                    {"domain": dom, "count": count}
                    for dom, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)
                ] if domains else []
            }
            
            if source.type == "news":
                news_sources.append(source_data)
            elif source.type == "social":
                social_sources.append(source_data)
            elif source.type == "forum":
                forum_sources.append(source_data)
        
        # Calculate stats
        total_sources = len(sources)
        total_articles = sum(article_counts.values())
        total_unique_urls = db.query(func.count(func.distinct(Article.url))).scalar()
        
        return {
            "news": news_sources if news_sources else [],
            "social": social_sources if social_sources else [],
            "forum": forum_sources if forum_sources else [],
            "stats": {
                "total_sources": total_sources,
                "news_count": len(news_sources),
                "social_count": len(social_sources),
                "forum_count": len(forum_sources),
                "total_articles": total_articles,
                "total_unique_urls": total_unique_urls,
                "articles_per_source": round(total_articles / total_sources, 2) if total_sources > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Get sources error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}")
async def get_source_detail(source_id: int, db: Session = Depends(get_db)):
    """Xem chi tiết 1 nguồn"""
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get articles from this source
        articles = db.query(Article).filter(Article.source == source.url).limit(10).all()
        
        return {
            "id": source.id,
            "name": source.name,
            "url": source.url,
            "type": source.type,
            "category": source.category,
            "description": source.description,
            "domain": source.domain,
            "region": source.region,
            "is_active": source.is_active,
            "total_articles": source.total_articles or len(articles),
            "last_crawled_at": source.last_crawled_at.isoformat() if source.last_crawled_at else None,
            "recent_articles": [
                {
                    "id": art.id,
                    "title": art.title,
                    "url": art.url,
                    "created_at": art.created_at.isoformat() if art.created_at else None
                }
                for art in articles
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get source detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{source_id}")
async def update_source(source_id: int, request: SourceCreate, db: Session = Depends(get_db)):
    """Cập nhật nguồn"""
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.name = request.name
        source.url = request.url
        source.type = request.type
        source.category = request.category
        source.description = request.description
        source.region = request.region
        
        db.commit()
        
        return {"status": "success", "message": "Source updated"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Update source error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{source_id}")
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Xóa nguồn (soft delete - set is_active=False)"""
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        source.is_active = False
        db.commit()
        
        return {"status": "success", "message": "Source deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Delete source error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}/stats")
async def get_source_stats(source_id: int, db: Session = Depends(get_db)):
    """
    Thống kê chi tiết 1 nguồn: 
    - Tổng số bài
    - Số URLs duy nhất
    - Phân tích URL patterns (nguồn con: /chinh-tri, /kinh-te...)
    - Timeline crawl
    """
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get all articles from source
        articles = db.query(Article).filter(Article.source == source.url).all()
        
        # Phân tích URL patterns
        url_patterns = {}
        from urllib.parse import urlparse
        from collections import defaultdict
        
        for art in articles:
            parsed = urlparse(art.url)
            path = parsed.path
            
            # Lấy phần đầu của path (category/section)
            parts = [p for p in path.split('/') if p]
            if parts:
                first_part = parts[0]
                url_patterns[first_part] = url_patterns.get(first_part, 0) + 1
        
        # Timeline
        timeline = defaultdict(int)
        for art in articles:
            if art.created_at:
                try:
                    # Handle both datetime and float
                    if isinstance(art.created_at, float):
                        from datetime import datetime
                        dt = datetime.fromtimestamp(art.created_at)
                        date_str = dt.strftime("%Y-%m-%d")
                    else:
                        date_str = art.created_at.strftime("%Y-%m-%d")
                    timeline[date_str] += 1
                except:
                    pass
        
        return {
            "source": {
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "type": source.type
            },
            "stats": {
                "total_articles": len(articles),
                "unique_urls": len(set(art.url for art in articles)),
                "last_crawled": source.last_crawled_at.isoformat() if source.last_crawled_at else None
            },
            "url_patterns": [
                {"pattern": f"/{pattern}", "count": count}
                for pattern, count in sorted(url_patterns.items(), key=lambda x: x[1], reverse=True)[:20]
            ],
            "timeline": [
                {"date": date, "count": count}
                for date, count in sorted(timeline.items())
            ][-30:]  # Last 30 days
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get source stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_sources_from_articles(db: Session = Depends(get_db)):
    """
    Tự động tạo sources từ articles có sẵn trong DB
    
    Quét tất cả articles, tạo source cho mỗi URL gốc chưa có
    """
    try:
        from urllib.parse import urlparse
        from datetime import datetime
        
        # Get unique sources from articles
        unique_sources = db.query(Article.source).distinct().all()
        
        created = 0
        updated = 0
        
        for (source_url,) in unique_sources:
            if not source_url:
                continue
            
            # Check if source exists
            existing = db.query(Source).filter(Source.url == source_url).first()
            
            if existing:
                # Update stats
                article_count = db.query(Article).filter(Article.source == source_url).count()
                existing.total_articles = article_count
                updated += 1
            else:
                # Create new source
                domain = urlparse(source_url).netloc if source_url else "unknown"
                
                # Auto detect type
                source_type = "news"  # Default
                if any(x in source_url.lower() for x in ["facebook.com", "fb.com", "fb.watch"]):
                    source_type = "social"
                elif any(x in source_url.lower() for x in ["twitter.com", "instagram.com", "tiktok.com", "youtube.com"]):
                    source_type = "social"
                elif any(x in source_url.lower() for x in ["forum", "group", "fanpage"]):
                    source_type = "forum"
                
                # Get article count and latest crawl
                article_count = db.query(Article).filter(Article.source == source_url).count()
                latest_article = db.query(Article).filter(Article.source == source_url).order_by(Article.created_at.desc()).first()
                
                new_source = Source(
                    name=domain,
                    url=source_url,
                    type=source_type,
                    domain=domain,
                    is_active=True,
                    total_articles=article_count,
                    last_crawled_at=latest_article.created_at if latest_article else None
                )
                db.add(new_source)
                created += 1
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Sources synced from articles",
            "created": created,
            "updated": updated,
            "total": created + updated
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Sync sources error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
