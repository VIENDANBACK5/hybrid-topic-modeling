"""
Digital Economy API - CRUD endpoints
Pattern: Following GRDP detail API structure
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.model_digital_economy_detail import DigitalEconomyDetail
from app.schemas.schema_digital_economy import (
    DigitalEconomyCreate,
    DigitalEconomyResponse,
    DigitalEconomyListResponse
)

router = APIRouter(prefix="/api/digital-economy", tags=["Digital Economy"])


@router.get("", response_model=DigitalEconomyListResponse)
def list_digital_economy(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    province: Optional[str] = None,
    period_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List Digital Economy data with filters"""
    query = db.query(DigitalEconomyDetail)
    
    if year:
        query = query.filter(DigitalEconomyDetail.year == year)
    if quarter:
        query = query.filter(DigitalEconomyDetail.quarter == quarter)
    if province:
        query = query.filter(DigitalEconomyDetail.province == province)
    if period_type:
        query = query.filter(DigitalEconomyDetail.period_type == period_type)
    
    total = query.count()
    items = query.order_by(desc(DigitalEconomyDetail.year), DigitalEconomyDetail.quarter).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
        "data": items
    }


@router.get("/{id}", response_model=DigitalEconomyResponse)
def get_digital_economy(id: int, db: Session = Depends(get_db)):
    """Get Digital Economy by ID"""
    record = db.query(DigitalEconomyDetail).filter(DigitalEconomyDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@router.post("", response_model=DigitalEconomyResponse)
def create_or_update_digital_economy(data: DigitalEconomyCreate, db: Session = Depends(get_db)):
    """Create or update Digital Economy data (upsert by year+quarter+province)"""
    
    # Find existing
    query = db.query(DigitalEconomyDetail).filter(
        DigitalEconomyDetail.province == data.province,
        DigitalEconomyDetail.year == data.year
    )
    if data.quarter:
        query = query.filter(DigitalEconomyDetail.quarter == data.quarter)
    else:
        query = query.filter(DigitalEconomyDetail.quarter.is_(None))
    
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
    new_record = DigitalEconomyDetail(**data.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.delete("/{id}")
def delete_digital_economy(id: int, db: Session = Depends(get_db)):
    """Delete Digital Economy record"""
    record = db.query(DigitalEconomyDetail).filter(DigitalEconomyDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    
    db.delete(record)
    db.commit()
    return {"message": f"Deleted id={id}"}
