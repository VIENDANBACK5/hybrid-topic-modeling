"""
GRDP API - 5 Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging
import math

from app.core.database import get_db
from app.models.model_grdp_detail import GRDPDetail
from app.schemas.schema_grdp_detail import (
    GRDPDetailCreate,
    GRDPDetailResponse,
    GRDPDetailListResponse,
)
from app.services.grdp import GRDPDataExtractor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/grdp", tags=["GRDP"])


@router.get("", response_model=GRDPDetailListResponse)
def list_grdp(
    province: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """Danh sách GRDP với filter và phân trang"""
    query = db.query(GRDPDetail)
    if province:
        query = query.filter(GRDPDetail.province.ilike(f"%{province}%"))
    if year:
        query = query.filter(GRDPDetail.year == year)
    if quarter:
        query = query.filter(GRDPDetail.quarter == quarter)
    
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    
    items = query.order_by(GRDPDetail.year.desc()).offset(offset).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "data": items
    }


@router.get("/{grdp_id}", response_model=GRDPDetailResponse)
def get_grdp(grdp_id: int, db: Session = Depends(get_db)):
    """Lấy GRDP theo ID"""
    grdp = db.query(GRDPDetail).filter(GRDPDetail.id == grdp_id).first()
    if not grdp:
        raise HTTPException(status_code=404, detail="GRDP không tồn tại")
    return grdp


@router.post("", response_model=GRDPDetailResponse, status_code=201)
def upsert_grdp(data: GRDPDetailCreate, force_update: bool = True, db: Session = Depends(get_db)):
    """Tạo/Cập nhật GRDP"""
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
        if force_update:
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            existing.last_updated = datetime.now()
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(status_code=409, detail="GRDP đã tồn tại")
    
    new_grdp = GRDPDetail(**data.model_dump())
    db.add(new_grdp)
    db.commit()
    db.refresh(new_grdp)
    return new_grdp


@router.delete("/{grdp_id}")
def delete_grdp(grdp_id: int, db: Session = Depends(get_db)):
    """Xóa GRDP"""
    grdp = db.query(GRDPDetail).filter(GRDPDetail.id == grdp_id).first()
    if not grdp:
        raise HTTPException(status_code=404, detail="GRDP không tồn tại")
    db.delete(grdp)
    db.commit()
    return {"deleted_id": grdp_id}


@router.post("/extract")
def extract_grdp(
    year: int = Query(..., ge=2020, le=2030),
    quarter: Optional[int] = Query(None, ge=1, le=4),
    use_llm: bool = True,
    force_update: bool = True,
    db: Session = Depends(get_db)
):
    """Auto extract GRDP: BM25 → Chunking → LLM → Validate → Save"""
    try:
        extractor = GRDPDataExtractor(db)
        grdp = extractor.get_or_extract_grdp(year, quarter, use_llm, force_update)
        
        if not grdp:
            return {"status": "no_data", "extracted": False}
        
        return {"status": "success", "extracted": True, "data": GRDPDetailResponse.model_validate(grdp)}
    except Exception as e:
        logger.error(f"Extract error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
