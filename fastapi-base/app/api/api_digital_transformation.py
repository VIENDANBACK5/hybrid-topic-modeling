"""
Digital Transformation API - CRUD endpoints
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.model_digital_transformation_detail import DigitalTransformationDetail
from app.schemas.schema_digital_transformation import (
    DigitalTransformationCreate,
    DigitalTransformationResponse,
    DigitalTransformationListResponse
)

router = APIRouter(prefix="/api/digital-transformation", tags=["Digital Transformation"])


@router.get("", response_model=DigitalTransformationListResponse)
def list_digital_transformation(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    province: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List Digital Transformation data with filters"""
    query = db.query(DigitalTransformationDetail)
    
    if year:
        query = query.filter(DigitalTransformationDetail.year == year)
    if quarter:
        query = query.filter(DigitalTransformationDetail.quarter == quarter)
    if province:
        query = query.filter(DigitalTransformationDetail.province == province)
    
    total = query.count()
    items = query.order_by(desc(DigitalTransformationDetail.year), DigitalTransformationDetail.quarter).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
        "data": items
    }


@router.get("/{id}", response_model=DigitalTransformationResponse)
def get_digital_transformation(id: int, db: Session = Depends(get_db)):
    """Get Digital Transformation by ID"""
    record = db.query(DigitalTransformationDetail).filter(DigitalTransformationDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@router.post("", response_model=DigitalTransformationResponse)
def create_or_update_digital_transformation(data: DigitalTransformationCreate, db: Session = Depends(get_db)):
    """Create or update Digital Transformation data (upsert)"""
    query = db.query(DigitalTransformationDetail).filter(
        DigitalTransformationDetail.province == data.province,
        DigitalTransformationDetail.year == data.year
    )
    if data.quarter:
        query = query.filter(DigitalTransformationDetail.quarter == data.quarter)
    else:
        query = query.filter(DigitalTransformationDetail.quarter.is_(None))
    
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
    
    new_record = DigitalTransformationDetail(**data.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.delete("/{id}")
def delete_digital_transformation(id: int, db: Session = Depends(get_db)):
    """Delete Digital Transformation record"""
    record = db.query(DigitalTransformationDetail).filter(DigitalTransformationDetail.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    
    db.delete(record)
    db.commit()
    return {"message": f"Deleted id={id}"}
