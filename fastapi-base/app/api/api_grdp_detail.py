"""
GRDP Detail API - Timeseries Format
5 endpoints: List, Get, Create, Delete, Extract
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.model_grdp_detail import GRDPDetail
from app.schemas.schema_grdp_detail import (
    GRDPDetailCreate, 
    GRDPDetailResponse, 
    GRDPDetailListResponse
)
from app.services.grdp.grdp_service import GRDPDataExtractor

router = APIRouter(prefix="/api/grdp", tags=["grdp_detail"])


# ==========================================
# 1. LIST + FILTER
# ==========================================
@router.get("", response_model=GRDPDetailListResponse)
def list_grdp(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    period_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List GRDP data with filters"""
    query = db.query(GRDPDetail)
    
    if year:
        query = query.filter(GRDPDetail.year == year)
    if quarter:
        query = query.filter(GRDPDetail.quarter == quarter)
    if period_type:
        query = query.filter(GRDPDetail.period_type == period_type)
    
    total = query.count()
    items = query.order_by(desc(GRDPDetail.year), GRDPDetail.quarter).offset(skip).limit(limit).all()
    
    return {"total": total, "items": items}


# ==========================================
# 2. GET BY ID
# ==========================================
@router.get("/{id}", response_model=GRDPDetailResponse)
def get_grdp(id: int, db: Session = Depends(get_db)):
    """Get GRDP by ID"""
    record = db.query(GRDPDetail).filter(GRDPDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record


# ==========================================
# 3. CREATE/UPDATE (UPSERT)
# ==========================================
@router.post("", response_model=GRDPDetailResponse)
def create_or_update_grdp(data: GRDPDetailCreate, db: Session = Depends(get_db)):
    """Create or update GRDP data (upsert by year+quarter)"""
    
    # Find existing
    query = db.query(GRDPDetail).filter(
        GRDPDetail.province == data.province,
        GRDPDetail.year == data.year
    )
    if data.quarter:
        query = query.filter(GRDPDetail.quarter == data.quarter)
    else:
        query = query.filter(GRDPDetail.quarter.is_(None))
    
    existing = query.first()
    
    if existing:
        # Update
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(existing, key, value)
        existing.last_updated = datetime.now()
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new
    new_record = GRDPDetail(**data.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


# ==========================================
# 4. DELETE
# ==========================================
@router.delete("/{id}")
def delete_grdp(id: int, db: Session = Depends(get_db)):
    """Delete GRDP record"""
    record = db.query(GRDPDetail).filter(GRDPDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    
    db.delete(record)
    db.commit()
    return {"message": f"Deleted id={id}"}


# ==========================================
# 5. LLM EXTRACT FROM DATABASE SOURCES
# ==========================================
@router.post("/extract-from-db")
def extract_grdp_from_database_sources(
    source: str = Query("important_posts", description="Source table: 'articles' or 'important_posts' or 'both'"),
    year: Optional[int] = Query(None, description="Filter by year"),
    quarter: Optional[int] = Query(None, description="Filter by quarter (1-4)"),
    limit: int = Query(10, description="Max records to process per source"),
    force_update: bool = Query(True, description="Update if exists"),
    db: Session = Depends(get_db)
):
    """
    Extract GRDP từ BẢNG DATABASE (articles hoặc important_posts) sử dụng LLM
    
    ⚠️ NOTE: Extract TẤT CẢ records (cả internal + external documents)
    Document type được giữ nguyên từ source record.
    
    Sources:
    - 'articles': Bảng articles (external news/content)
    - 'important_posts': Bảng important_posts (gov.vn + external sources)
    - 'both': Extract từ cả 2 bảng
    
    Process:
    1. Query table(s) based on source param
    2. Filter: type_newspaper='economic', year, quarter
    3. For each record: LLM extract GRDP
    4. Save to grdp_detail (preserving document_type from source)
    
    Returns: Aggregated results from all sources
    """
    if source not in ['articles', 'important_posts', 'both']:
        raise HTTPException(
            status_code=400,
            detail="Invalid source. Must be 'articles', 'important_posts', or 'both'"
        )
    
    extractor = GRDPDataExtractor(db)
    all_results = {
        'total_records': 0,
        'extracted': 0,
        'failed': 0,
        'sources': {}
    }
    
    # Process Articles
    if source in ['articles', 'both']:
        from app.models.article import Article
        
        query = db.query(Article).filter(Article.type_newspaper == 'economy')
        articles = query.limit(limit).all()
        
        articles_results = []
        for article in articles:
            try:
                data = extractor.extract_from_text(
                    text=article.content,
                    year=year or article.year if hasattr(article, 'year') else year,
                    quarter=quarter,
                    use_llm=True
                )
                
                if data and (data.get('actual_value') or data.get('change_yoy')):
                    data['data_source'] = f"articles:{article.id}"
                    # articles table doesn't have document_type, infer from source_type or default to external
                    data['document_type'] = getattr(article, 'document_type', 'external')
                    record = extractor.save(data, force_update=force_update)
                    articles_results.append({
                        "source_id": article.id,
                        "record_id": record.id,
                        "year": record.year,
                        "quarter": record.quarter
                    })
                    all_results['extracted'] += 1
            except Exception as e:
                articles_results.append({
                    "source_id": article.id,
                    "error": str(e)
                })
                all_results['failed'] += 1
        
        all_results['sources']['articles'] = {
            'total': len(articles),
            'extracted': len([r for r in articles_results if 'record_id' in r]),
            'failed': len([r for r in articles_results if 'error' in r]),
            'results': articles_results
        }
        all_results['total_records'] += len(articles)
    
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
                
                data = extractor.extract_from_text(
                    text=post.content,
                    year=post_year or year,
                    quarter=post_quarter or quarter,
                    use_llm=True
                )
                
                if data and (data.get('actual_value') or data.get('change_yoy')):
                    data['data_source'] = f"important_posts:{post.id}"
                    # Use actual document_type from important_post record (internal/external/null)
                    # Only default to 'external' if document_type is None or empty string
                    data['document_type'] = post.document_type if post.document_type else 'external'
                    record = extractor.save(data, force_update=force_update)
                    posts_results.append({
                        "source_id": post.id,
                        "record_id": record.id,
                        "year": record.year,
                        "quarter": record.quarter,
                        "url": post.url
                    })
                    all_results['extracted'] += 1
            except Exception as e:
                posts_results.append({
                    "source_id": post.id,
                    "error": str(e)
                })
                all_results['failed'] += 1
        
        all_results['sources']['important_posts'] = {
            'total': len(posts),
            'extracted': len([r for r in posts_results if 'record_id' in r]),
            'failed': len([r for r in posts_results if 'error' in r]),
            'results': posts_results
        }
        all_results['total_records'] += len(posts)
    
    return all_results




# ==========================================
# 6. BATCH CRAWL FROM OFFICIAL SOURCES
# ==========================================
@router.post("/crawl-official")
def crawl_all_official_sources(
    use_llm: bool = Query(True, description="Use LLM for extraction"),
    force_update: bool = Query(True, description="Update existing records"),
    db: Session = Depends(get_db)
):
    """
    Crawl TẤT CẢ nguồn chính thức:
    - https://thongkehungyen.nso.gov.vn (Playwright - JS rendered)
    - https://hungyen.gov.vn (Requests - static HTML)
    
    ETL Pipeline đầy đủ:
    1. Smart fetch theo loại trang
    2. Enhanced parsing với tables
    3. Multi-layer extraction
    4. Validation
    5. Auto-fill missing fields từ dữ liệu có sẵn
    
    Returns: Danh sách records đã crawl
    """
    from app.services.grdp.grdp_service import OFFICIAL_SOURCES
    
    extractor = GRDPDataExtractor(db)
    results = []
    errors = []
    
    for source_key, source_info in OFFICIAL_SOURCES.items():
        try:
            print(f"\n{'='*60}")
            print(f" Processing: {source_key}")
            print(f" URL: {source_info['url']}")
            print(f" Type: {source_info['type']}")
            print(f"{'='*60}\n")
            
            # Extract from source
            data = extractor.extract_from_official(
                source_key=source_key,
                use_llm=use_llm
            )
            
            if data and (data.get('actual_value') or data.get('change_yoy')):
                # Save to database
                record = extractor.save(data, force_update=force_update)
                results.append({
                    "source": source_key,
                    "url": source_info['url'],
                    "status": "success",
                    "record_id": record.id,
                    "year": record.year,
                    "quarter": record.quarter,
                    "actual_value": record.actual_value,
                    "change_yoy": record.change_yoy
                })
            else:
                errors.append({
                    "source": source_key,
                    "url": source_info['url'],
                    "status": "no_data",
                    "message": "No GRDP data found in content"
                })
                
        except Exception as e:
            errors.append({
                "source": source_key,
                "url": source_info.get('url', ''),
                "status": "error",
                "message": str(e)
            })
    
    return {
        "total_sources": len(OFFICIAL_SOURCES),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }
