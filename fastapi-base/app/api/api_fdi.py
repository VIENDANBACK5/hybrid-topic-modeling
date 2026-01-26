"""
FDI API - CRUD endpoints
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.model_fdi_detail import FDIDetail
from app.schemas.schema_fdi import (
    FDICreate,
    FDIResponse,
    FDIListResponse
)

router = APIRouter(prefix="/api/fdi", tags=["FDI"])


@router.get("", response_model=FDIListResponse)
def list_fdi(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    province: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List FDI data with filters"""
    query = db.query(FDIDetail)
    
    if year:
        query = query.filter(FDIDetail.year == year)
    if quarter:
        query = query.filter(FDIDetail.quarter == quarter)
    if province:
        query = query.filter(FDIDetail.province == province)
    
    total = query.count()
    items = query.order_by(desc(FDIDetail.year), FDIDetail.quarter).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
        "data": items
    }


@router.get("/{id}", response_model=FDIResponse)
def get_fdi(id: int, db: Session = Depends(get_db)):
    """Get FDI by ID"""
    record = db.query(FDIDetail).filter(FDIDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@router.post("", response_model=FDIResponse)
def create_or_update_fdi(data: FDICreate, db: Session = Depends(get_db)):
    """Create or update FDI data (upsert)"""
    query = db.query(FDIDetail).filter(
        FDIDetail.province == data.province,
        FDIDetail.year == data.year
    )
    if data.quarter:
        query = query.filter(FDIDetail.quarter == data.quarter)
    else:
        query = query.filter(FDIDetail.quarter.is_(None))
    
    existing = query.first()
    
    if existing:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(existing, key, value)
        existing.last_updated = datetime.now()
        db.commit()
        db.refresh(existing)
        return existing
    
    new_record = FDIDetail(**data.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.delete("/{id}")
def delete_fdi(id: int, db: Session = Depends(get_db)):
    """Delete FDI record"""
    record = db.query(FDIDetail).filter(FDIDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    
    db.delete(record)
    db.commit()
    return {"message": f"Deleted id={id}"}
