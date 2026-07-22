"""
Cadre Statistics API - CRUD endpoints for personnel/staff data
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.core.database import get_db
from app.models.model_indicator_details import CadreStatisticsDetail

router = APIRouter(prefix="/api/cadre-statistics", tags=["cadre_statistics_detail"])


class CadreStatisticsCreate(BaseModel):
    province: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[int] = None
    month: Optional[int] = None
    total_authorized: Optional[int] = None
    provincial_level: Optional[int] = None
    commune_level: Optional[int] = None
    contract_workers: Optional[int] = None
    data_status: Optional[str] = "extracted"
    data_source: Optional[str] = None
    document_type: Optional[str] = "external"


class CadreStatisticsResponse(BaseModel):
    id: int
    province: Optional[str]
    year: Optional[int]
    quarter: Optional[int]
    month: Optional[int]
    total_authorized: Optional[int]
    provincial_level: Optional[int]
    commune_level: Optional[int]
    contract_workers: Optional[int]
    data_status: Optional[str]
    data_source: Optional[str]
    document_type: Optional[str]
    
    class Config:
        from_attributes = True


class CadreStatisticsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    data: list[CadreStatisticsResponse]


@router.get("", response_model=CadreStatisticsListResponse)
def list_cadre_statistics(
    year: Optional[int] = None,
    province: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List cadre statistics with filters"""
    query = db.query(CadreStatisticsDetail)
    
    if year:
        query = query.filter(CadreStatisticsDetail.year == year)
    if province:
        query = query.filter(CadreStatisticsDetail.province == province)
    
    total = query.count()
    items = query.order_by(desc(CadreStatisticsDetail.year)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
        "data": items
    }


@router.get("/by-id/{id}", response_model=CadreStatisticsResponse)
def get_cadre_statistics(id: int, db: Session = Depends(get_db)):
    """Get cadre statistics by ID"""
    record = db.query(CadreStatisticsDetail).filter(CadreStatisticsDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@router.post("", response_model=CadreStatisticsResponse)
def create_or_update_cadre_statistics(data: CadreStatisticsCreate, db: Session = Depends(get_db)):
    """Create or update cadre statistics (upsert)"""
    query = db.query(CadreStatisticsDetail).filter(
        CadreStatisticsDetail.province == data.province,
        CadreStatisticsDetail.year == data.year
    )
    
    existing = query.first()
    
    if existing:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    new_record = CadreStatisticsDetail(**data.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.delete("/by-id/{id}")
def delete_cadre_statistics(id: int, db: Session = Depends(get_db)):
    """Delete cadre statistics record"""
    record = db.query(CadreStatisticsDetail).filter(CadreStatisticsDetail.id == id).first()
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
    Extract Cadre Statistics từ database sources sử dụng LLM
    
    Sources:
    - 'articles': Bảng articles
    - 'important_posts': Bảng important_posts  
    - 'both': Extract từ cả 2 bảng
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from call_llm.extract_cadre_statistics import extract_cadre_statistics
    from sqlalchemy import text
    
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
        
        query = db.query(ImportantPost).filter(ImportantPost.type_newspaper == 'politics')
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
                
                data = extract_cadre_statistics(
                    content=post.content,
                    url=post.url,
                    province=post.dvhc or "Hưng Yên"
                )
                
                if data:
                    data['document_type'] = post.document_type or 'external'
                    data['data_source'] = f"important_posts:{post.id}"
                    # Save to database
                    insert_query = text("""
                        INSERT INTO cadre_statistics_detail 
                        (province, year, quarter, month, total_authorized, provincial_level, 
                         commune_level, contract_workers, data_status, data_source, document_type)
                        VALUES (:province, :year, :quarter, :month, :total_authorized, :provincial_level,
                                :commune_level, :contract_workers, :data_status, :data_source, :document_type)
                        ON CONFLICT (province, year, quarter) DO UPDATE SET
                            total_authorized = EXCLUDED.total_authorized,
                            provincial_level = EXCLUDED.provincial_level,
                            commune_level = EXCLUDED.commune_level,
                            contract_workers = EXCLUDED.contract_workers,
                            data_status = EXCLUDED.data_status,
                            data_source = EXCLUDED.data_source,
                            document_type = EXCLUDED.document_type
                    """)
                    db.execute(insert_query, data)
                    db.commit()
                    posts_results.append({
                        "source_id": post.id,
                        "status": "extracted",
                        "url": post.url
                    })
                    all_results['extracted'] += 1
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
        from app.models.model_article import Article
        
        query = db.query(Article).filter(Article.type_newspaper == 'politics')
        articles = query.limit(limit).all()
        articles_results = []
        
        for article in articles:
            try:
                data = extract_cadre_statistics(
                    content=article.content,
                    url=article.url if hasattr(article, 'url') else None,
                    province=getattr(article, 'dvhc', 'Hưng Yên')
                )
                
                if data:
                    data['document_type'] = getattr(article, 'document_type', 'external')
                    data['data_source'] = f"articles:{article.id}"
                    insert_query = text("""
                        INSERT INTO cadre_statistics_detail 
                        (province, year, quarter, month, total_authorized, provincial_level, 
                         commune_level, contract_workers, data_status, data_source, document_type)
                        VALUES (:province, :year, :quarter, :month, :total_authorized, :provincial_level,
                                :commune_level, :contract_workers, :data_status, :data_source, :document_type)
                        ON CONFLICT (province, year, quarter) DO UPDATE SET
                            total_authorized = EXCLUDED.total_authorized,
                            provincial_level = EXCLUDED.provincial_level,
                            commune_level = EXCLUDED.commune_level,
                            contract_workers = EXCLUDED.contract_workers,
                            data_status = EXCLUDED.data_status,
                            data_source = EXCLUDED.data_source,
                            document_type = EXCLUDED.document_type
                    """)
                    db.execute(insert_query, data)
                    db.commit()
                    articles_results.append({
                        "source_id": article.id,
                        "status": "extracted"
                    })
                    all_results['extracted'] += 1
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
