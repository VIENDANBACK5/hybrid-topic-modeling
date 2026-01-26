"""
PII (Provincial Industrial Index) API - CRUD endpoints
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.model_pii_detail import PIIDetail
from app.schemas.schema_pii import (
    PIICreate,
    PIIResponse,
    PIIListResponse
)

router = APIRouter(prefix="/api/pii", tags=["PII"])


@router.get("", response_model=PIIListResponse)
def list_pii(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    province: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List PII (Provincial Industrial Index) data with filters"""
    query = db.query(PIIDetail)
    
    if year:
        query = query.filter(PIIDetail.year == year)
    if quarter:
        query = query.filter(PIIDetail.quarter == quarter)
    if province:
        query = query.filter(PIIDetail.province == province)
    
    total = query.count()
    items = query.order_by(desc(PIIDetail.year), PIIDetail.quarter).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
        "data": items
    }


@router.get("/{id}", response_model=PIIResponse)
def get_pii(id: int, db: Session = Depends(get_db)):
    """Get PII by ID"""
    record = db.query(PIIDetail).filter(PIIDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@router.post("", response_model=PIIResponse)
def create_or_update_pii(data: PIICreate, db: Session = Depends(get_db)):
    """Create or update PII data (upsert)"""
    query = db.query(PIIDetail).filter(
        PIIDetail.province == data.province,
        PIIDetail.year == data.year
    )
    if data.quarter:
        query = query.filter(PIIDetail.quarter == data.quarter)
    else:
        query = query.filter(PIIDetail.quarter.is_(None))
    
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
    
    new_record = PIIDetail(**data.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.delete("/{id}")
def delete_pii(id: int, db: Session = Depends(get_db)):
    """Delete PII record"""
    record = db.query(PIIDetail).filter(PIIDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    
    db.delete(record)
    db.commit()
    return {"message": f"Deleted id={id}"}
