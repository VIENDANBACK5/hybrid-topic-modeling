"""
IIP API - Industrial Production Index CRUD endpoints
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.core.database import get_db
from app.models.model_iip_detail import IIPDetail

router = APIRouter(prefix="/api/iip", tags=["iip_detail"])


# Schemas
class IIPCreate(BaseModel):
    province: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[int] = None
    month: Optional[int] = None
    iip_index: Optional[float] = None
    growth_rate: Optional[float] = None
    mining_index: Optional[float] = None
    manufacturing_index: Optional[float] = None
    electricity_index: Optional[float] = None
    data_status: Optional[str] = "extracted"
    data_source: Optional[str] = None
    document_type: Optional[str] = "external"


class IIPResponse(BaseModel):
    id: int
    province: Optional[str]
    year: Optional[int]
    quarter: Optional[int]
    month: Optional[int]
    iip_index: Optional[float]
    growth_rate: Optional[float]
    mining_index: Optional[float]
    manufacturing_index: Optional[float]
    electricity_index: Optional[float]
    data_status: Optional[str]
    data_source: Optional[str]
    document_type: Optional[str]
    
    class Config:
        from_attributes = True


class IIPListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    data: list[IIPResponse]


@router.get("", response_model=IIPListResponse)
def list_iip(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    province: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List IIP data with filters"""
    query = db.query(IIPDetail)
    
    if year:
        query = query.filter(IIPDetail.year == year)
    if quarter:
        query = query.filter(IIPDetail.quarter == quarter)
    if province:
        query = query.filter(IIPDetail.province == province)
    
    total = query.count()
    items = query.order_by(desc(IIPDetail.year), IIPDetail.quarter).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
        "data": items
    }


@router.get("/by-id/{id}", response_model=IIPResponse)
def get_iip(id: int, db: Session = Depends(get_db)):
    """Get IIP by ID"""
    record = db.query(IIPDetail).filter(IIPDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@router.post("", response_model=IIPResponse)
def create_or_update_iip(data: IIPCreate, db: Session = Depends(get_db)):
    """Create or update IIP data (upsert)"""
    query = db.query(IIPDetail).filter(
        IIPDetail.province == data.province,
        IIPDetail.year == data.year
    )
    if data.quarter:
        query = query.filter(IIPDetail.quarter == data.quarter)
    else:
        query = query.filter(IIPDetail.quarter.is_(None))
    
    existing = query.first()
    
    if existing:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    new_record = IIPDetail(**data.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.delete("/by-id/{id}")
def delete_iip(id: int, db: Session = Depends(get_db)):
    """Delete IIP record"""
    record = db.query(IIPDetail).filter(IIPDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    
    db.delete(record)
    db.commit()
    return {"message": f"Deleted id={id}"}


# ==========================================
# EXTRACTION FROM DATABASE
# ==========================================
@router.post("/extract-from-db")
def extract_from_database_sources(
    source: str = Query("important_posts", description="Source: 'articles', 'important_posts', or 'both'"),
    year: Optional[int] = Query(None, description="Filter by year"),
    quarter: Optional[int] = Query(None, description="Filter by quarter (1-4)"),
    limit: int = Query(10, description="Max records per source"),
    force_update: bool = Query(True, description="Update if exists"),
    db: Session = Depends(get_db)
):
    """
    Extract IIP từ database sources sử dụng LLM
    
    Sources:
    - 'articles': Bảng articles
    - 'important_posts': Bảng important_posts  
    - 'both': Extract từ cả 2 bảng
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from call_llm.extract_iip import extract_iip_data, save_to_iip
    
    if source not in ['articles', 'important_posts', 'both']:
        raise HTTPException(status_code=400, detail="Invalid source")
    
    all_results = {
        'total_records': 0,
        'extracted': 0,
        'failed': 0,
        'sources': {}
    }
    
    # Process Important Posts
    if source in ['important_posts', 'both']:
        from app.models.model_important_post import ImportantPost
        from app.utils.date_parser import parse_year_quarter_from_date
        
        # Get all economic posts (can't filter year/quarter in SQL as they're not columns)
        query = db.query(ImportantPost).filter(ImportantPost.type_newspaper == 'economy')
        posts = query.limit(limit * 3).all()  # Get more to account for filtering
        
        posts_results = []
        for post in posts:
            try:
                # Parse year/quarter from published_date string
                post_year, post_quarter = parse_year_quarter_from_date(post.published_date)
                
                # Filter by year/quarter if specified
                if year and post_year != year:
                    continue
                if quarter and post_quarter != quarter:
                    continue
                
                # Stop if we've processed enough
                if len(posts_results) >= limit:
                    break
                
                data = extract_iip_data(
                    content=post.content,
                    url=post.url,
                    province=post.dvhc or "Hưng Yên"
                )
                
                if data:
                    data['document_type'] = post.document_type or 'external'
                    data['data_source'] = f"important_posts:{post.id}"
                    if save_to_iip(db, data):
                        posts_results.append({
                            "source_id": post.id,
                            "status": "extracted",
                            "url": post.url
                        })
                        all_results['extracted'] += 1
                    else:
                        posts_results.append({"source_id": post.id, "error": "Save failed"})
                        all_results['failed'] += 1
                else:
                    posts_results.append({"source_id": post.id, "status": "no_data"})
            except Exception as e:
                posts_results.append({"source_id": post.id, "error": str(e)})
                all_results['failed'] += 1
        
        all_results['sources']['important_posts'] = {
            'total': len(posts),
            'results': posts_results
        }
        all_results['total_records'] += len(posts)
    
    # Process Articles
    if source in ['articles', 'both']:
        from app.models.article import Article
        
        query = db.query(Article).filter(Article.type_newspaper == 'economy')
        articles = query.limit(limit).all()
        articles_results = []
        
        for article in articles:
            try:
                data = extract_iip_data(
                    content=article.content,
                    url=article.url if hasattr(article, 'url') else None,
                    province=getattr(article, 'dvhc', 'Hưng Yên')
                )
                
                if data:
                    data['document_type'] = getattr(article, 'document_type', 'external')
                    data['data_source'] = f"articles:{article.id}"
                    if save_to_iip(db, data):
                        articles_results.append({
                            "source_id": article.id,
                            "status": "extracted"
                        })
                        all_results['extracted'] += 1
                    else:
                        articles_results.append({"source_id": article.id, "error": "Save failed"})
                        all_results['failed'] += 1
                else:
                    articles_results.append({"source_id": article.id, "status": "no_data"})
            except Exception as e:
                articles_results.append({"source_id": article.id, "error": str(e)})
                all_results['failed'] += 1
        
        all_results['sources']['articles'] = {
            'total': len(articles),
            'results': articles_results
        }
        all_results['total_records'] += len(articles)
    
    return all_results

# ==========================================
# CRAWL FROM OFFICIAL SOURCES
# ==========================================
@router.post("/crawl-official")
def crawl_iip_from_official(
    url: str = Query("https://thongkehungyen.nso.gov.vn", description="URL to crawl"),
    force_update: bool = Query(True, description="Update existing records"),
    db: Session = Depends(get_db)
):
    """
    Crawl IIP data from official statistical website
    
    Default source: https://thongkehungyen.nso.gov.vn
    
    Note: This is a placeholder implementation. Full crawling logic needs to be
    implemented based on the actual website structure.
    
    Returns: List of crawled records with status
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from call_llm.extract_iip import extract_iip_from_crawl, save_to_iip
    
    try:
        # Crawl data from external source
        data_list = extract_iip_from_crawl(url)
        
        if not data_list:
            return {
                "status": "no_data",
                "message": "No IIP data extracted from source. Implementation may be needed.",
                "url": url,
                "total": 0
            }
        
        # Save each record
        results = []
        for data in data_list:
            try:
                if save_to_iip(db, data):
                    results.append({
                        "status": "success",
                        "year": data.get('year'),
                        "month": data.get('month'),
                        "iip_index": data.get('iip_index')
                    })
                else:
                    results.append({
                        "status": "failed",
                        "data": data
                    })
            except Exception as e:
                results.append({
                    "status": "error",
                    "error": str(e),
                    "data": data
                })
        
        return {
            "status": "completed",
            "url": url,
            "total": len(data_list),
            "successful": len([r for r in results if r['status'] == 'success']),
            "failed": len([r for r in results if r['status'] != 'success']),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawling error: {str(e)}")
