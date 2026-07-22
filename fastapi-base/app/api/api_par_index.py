"""
PAR Index API - Public Administration Reform Index CRUD endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.core.database import get_db
from app.models.model_indicator_details import PARIndexDetail

router = APIRouter(prefix="/api/par-index", tags=["par_index_detail"])


class PARIndexCreate(BaseModel):
    province: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[int] = None
    par_index_score: Optional[float] = None
    ranking: Optional[int] = None
    improved_procedures: Optional[int] = None
    digital_services_rate: Optional[float] = None
    citizen_satisfaction: Optional[float] = None
    data_status: Optional[str] = "extracted"
    data_source: Optional[str] = None
    document_type: Optional[str] = "external"


class PARIndexResponse(BaseModel):
    id: int
    province: Optional[str]
    year: Optional[int]
    par_index_score: Optional[float]
    ranking: Optional[int]
    digital_services_rate: Optional[float]
    data_status: Optional[str]
    document_type: Optional[str]
    
    class Config:
        from_attributes = True


class PARIndexListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    data: list[PARIndexResponse]


@router.get("", response_model=PARIndexListResponse)
def list_par_index(
    year: Optional[int] = None,
    province: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List PAR index data"""
    query = db.query(PARIndexDetail)
    
    if year:
        query = query.filter(PARIndexDetail.year == year)
    if province:
        query = query.filter(PARIndexDetail.province == province)
    
    total = query.count()
    items = query.order_by(desc(PARIndexDetail.year)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
        "data": items
    }


@router.get("/by-id/{id}", response_model=PARIndexResponse)
def get_par_index(id: int, db: Session = Depends(get_db)):
    """Get PAR index by ID"""
    record = db.query(PARIndexDetail).filter(PARIndexDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@router.post("", response_model=PARIndexResponse)
def create_or_update_par_index(data: PARIndexCreate, db: Session = Depends(get_db)):
    """Create or update PAR index data"""
    query = db.query(PARIndexDetail).filter(
        PARIndexDetail.province == data.province,
        PARIndexDetail.year == data.year
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
    
    new_record = PARIndexDetail(**data.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.delete("/by-id/{id}")
def delete_par_index(id: int, db: Session = Depends(get_db)):
    """Delete PAR index record"""
    record = db.query(PARIndexDetail).filter(PARIndexDetail.id == id).first()
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
    Extract PAR Index từ database sources sử dụng LLM
    
    Sources:
    - 'articles': Bảng articles
    - 'important_posts': Bảng important_posts  
    - 'both': Extract từ cả 2 bảng
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from call_llm.extract_par_index import extract_par_index
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
        
        # Get all politics posts (can't filter year/quarter in SQL as they're not columns)
        query = db.query(ImportantPost).filter(ImportantPost.type_newspaper == 'politics')
        posts = query.limit(limit * 3).all()
        
        posts_results = []
        for post in posts:
            try:
                # Parse year/quarter from published_date string
                post_year, post_quarter = parse_year_quarter_from_date(post.published_date)
                
                if year and post_year != year:
                    continue
                if quarter and post_quarter != quarter:
                    continue
                
                if len(posts_results) >= limit:
                    break
                
                data = extract_par_index(
                    content=post.content,
                    url=post.url,
                    province=post.dvhc or "Hưng Yên"
                )
                
                if data:
                    data['document_type'] = post.document_type or 'external'
                    data['data_source'] = f"important_posts:{post.id}"
                    insert_query = text("""
                        INSERT INTO par_index_detail 
                        (province, year, quarter, par_index_score, ranking, improved_procedures,
                         digital_services_rate, citizen_satisfaction, data_status, data_source, document_type)
                        VALUES (:province, :year, :quarter, :par_index_score, :ranking, :improved_procedures,
                                :digital_services_rate, :citizen_satisfaction, :data_status, :data_source, :document_type)
                        ON CONFLICT (province, year) DO UPDATE SET
                            par_index_score = EXCLUDED.par_index_score,
                            ranking = EXCLUDED.ranking,
                            improved_procedures = EXCLUDED.improved_procedures,
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
                data = extract_par_index(
                    content=article.content,
                    url=article.url if hasattr(article, 'url') else None,
                    province=getattr(article, 'dvhc', 'Hưng Yên')
                )
                
                if data:
                    data['document_type'] = getattr(article, 'document_type', 'external')
                    data['data_source'] = f"articles:{article.id}"
                    insert_query = text("""
                        INSERT INTO par_index_detail 
                        (province, year, quarter, par_index_score, ranking, improved_procedures,
                         digital_services_rate, citizen_satisfaction, data_status, data_source, document_type)
                        VALUES (:province, :year, :quarter, :par_index_score, :ranking, :improved_procedures,
                                :digital_services_rate, :citizen_satisfaction, :data_status, :data_source, :document_type)
                        ON CONFLICT (province, year) DO UPDATE SET
                            par_index_score = EXCLUDED.par_index_score,
                            ranking = EXCLUDED.ranking,
                            improved_procedures = EXCLUDED.improved_procedures,
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
