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
    GRDPDetailListResponse,
    GRDPCrawlRequest,
    GRDPExtractRequest
)
from app.services.grdp.grdp_service import GRDPDataExtractor

router = APIRouter(prefix="/api/grdp", tags=["GRDP"])


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
# 5. AUTO EXTRACT FROM ARTICLES (DEPRECATED - use /extract-from-text instead)
# ==========================================
@router.post("/extract-from-articles", response_model=GRDPDetailResponse)
def extract_grdp_from_articles(
    year: int = Query(..., description="Year to extract"),
    quarter: Optional[int] = Query(None, description="Quarter (1-4)"),
    use_llm: bool = Query(True, description="Use LLM or regex"),
    force_update: bool = Query(True, description="Update if exists"),
    db: Session = Depends(get_db)
):
    """Auto-extract GRDP from articles (OLD METHOD - extracts from stored articles table)"""
    extractor = GRDPDataExtractor(db)
    result = extractor.get_or_extract_grdp(
        year=year,
        quarter=quarter,
        use_llm=use_llm,
        force_update=force_update
    )
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"No GRDP data found for {year}"
        )
    
    return result


# ==========================================
# 6. EXTRACT FROM TEXT (NEW SIMPLE API)
# ==========================================
@router.post("/extract", response_model=GRDPDetailResponse)
def extract_grdp_from_text(
    request: GRDPExtractRequest,
    db: Session = Depends(get_db)
):
    """
    Extract GRDP từ text content (đơn giản nhất)
    
    Chỉ cần paste đoạn text chứa thông tin GRDP:
    - "GRDP 9 tháng năm 2025 ước đạt 114.792 tỷ đồng, tăng 8,01%..."
    - "Quý I tăng 8,80%; quý II tăng 7,40%..."
    - "Quy mô kinh tế 219.846 tỷ đồng..."
    
    Hệ thống sẽ tự động:
    1. Extract GRDP value, growth rates
    2. Detect period (9 tháng → Q3, 6 tháng → Q2, etc.)
    3. Extract quarterly breakdown (Q1, Q2, Q3, Q4)
    4. Extract nominal GRDP
    5. Validate data
    6. Save to database
    """
    extractor = GRDPDataExtractor(db)
    
    # Extract data from text
    data = extractor.extract_from_text(
        text=request.text,
        year=request.year,
        quarter=request.quarter,
        use_llm=request.use_llm
    )
    
    if not data:
        raise HTTPException(
            status_code=404,
            detail="Could not extract GRDP data from text"
        )
    
    # Check if data has actual values
    if not data.get('actual_value') and not data.get('change_yoy'):
        raise HTTPException(
            status_code=422,
            detail="No GRDP values found in text. Please check the content."
        )
    
    # Add data source
    if request.data_source:
        data['data_source'] = request.data_source
    else:
        data['data_source'] = 'User provided text'
    
    # Save to database
    result = extractor.save(data, force_update=request.force_update)
    
    return result


# ==========================================
# 7. CRAWL FROM USER URL (DEPRECATED)
# ==========================================
@router.post("/crawl", response_model=GRDPDetailResponse, deprecated=True)
def crawl_grdp_from_url(
    request: GRDPCrawlRequest,
    db: Session = Depends(get_db)
):
    """
    DEPRECATED: Use /extract endpoint instead
    
    Legacy endpoint - sử dụng text_content nếu được cung cấp
    """
    if request.text_content:
        # Convert to extract request
        extract_req = GRDPExtractRequest(
            text=request.text_content,
            year=request.year,
            quarter=request.quarter,
            data_source=request.url,
            use_llm=request.use_llm,
            force_update=request.force_update
        )
        return extract_grdp_from_text(extract_req, db)
    else:
        raise HTTPException(
            status_code=400,
            detail="This endpoint is deprecated. Please use /extract with text parameter."
        )


# ==========================================
# 8. BATCH CRAWL FROM OFFICIAL SOURCES (REMOVED)
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
