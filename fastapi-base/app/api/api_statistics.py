from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.model_economic_statistics import EconomicStatistics
from app.models.model_political_statistics import PoliticalStatistics
from app.schemas.schema_statistics import (
    EconomicStatisticsCreate,
    EconomicStatisticsUpdate,
    EconomicStatisticsResponse,
    PoliticalStatisticsCreate,
    PoliticalStatisticsUpdate,
    PoliticalStatisticsResponse
)
import time

router = APIRouter()


# Economic Statistics Endpoints
@router.post("/economic", response_model=EconomicStatisticsResponse, status_code=201)
def create_economic_statistics(
    data: EconomicStatisticsCreate,
    db: Session = Depends(get_db)
):
    """Create new economic statistics record."""
    try:
        db_obj = EconomicStatistics(**data.model_dump())
        db_obj.created_at = time.time()
        db_obj.updated_at = time.time()
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        return db_obj
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating record: {str(e)}")


@router.get("/economic", response_model=List[EconomicStatisticsResponse])
def list_economic_statistics(
    dvhc: Optional[str] = None,
    year: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List economic statistics with filters."""
    query = db.query(EconomicStatistics)
    
    if dvhc:
        query = query.filter(EconomicStatistics.dvhc.ilike(f"%{dvhc}%"))
    if year:
        query = query.filter(EconomicStatistics.year == year)
    
    results = query.order_by(EconomicStatistics.created_at.desc()).offset(skip).limit(limit).all()
    return results


@router.get("/economic/{stat_id}", response_model=EconomicStatisticsResponse)
def get_economic_statistics(stat_id: int, db: Session = Depends(get_db)):
    """Get economic statistics by ID."""
    result = db.query(EconomicStatistics).filter(EconomicStatistics.id == stat_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Record not found")
    return result


@router.put("/economic/{stat_id}", response_model=EconomicStatisticsResponse)
def update_economic_statistics(
    stat_id: int,
    data: EconomicStatisticsUpdate,
    db: Session = Depends(get_db)
):
    """Update economic statistics record."""
    db_obj = db.query(EconomicStatistics).filter(EconomicStatistics.id == stat_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Record not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db_obj.updated_at = time.time()
    db.commit()
    db.refresh(db_obj)
    
    return db_obj


@router.delete("/economic/{stat_id}")
def delete_economic_statistics(stat_id: int, db: Session = Depends(get_db)):
    """Delete economic statistics record."""
    db_obj = db.query(EconomicStatistics).filter(EconomicStatistics.id == stat_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Record not found")
    
    db.delete(db_obj)
    db.commit()
    
    return {"message": "Record deleted successfully"}


# Political Statistics Endpoints
@router.post("/political", response_model=PoliticalStatisticsResponse, status_code=201)
def create_political_statistics(
    data: PoliticalStatisticsCreate,
    db: Session = Depends(get_db)
):
    """Create new political statistics record."""
    try:
        db_obj = PoliticalStatistics(**data.model_dump())
        db_obj.created_at = time.time()
        db_obj.updated_at = time.time()
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        return db_obj
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating record: {str(e)}")


@router.get("/political", response_model=List[PoliticalStatisticsResponse])
def list_political_statistics(
    dvhc: Optional[str] = None,
    year: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List political statistics with filters."""
    query = db.query(PoliticalStatistics)
    
    if dvhc:
        query = query.filter(PoliticalStatistics.dvhc.ilike(f"%{dvhc}%"))
    if year:
        query = query.filter(PoliticalStatistics.year == year)
    
    results = query.order_by(PoliticalStatistics.created_at.desc()).offset(skip).limit(limit).all()
    return results


@router.get("/political/{stat_id}", response_model=PoliticalStatisticsResponse)
def get_political_statistics(stat_id: int, db: Session = Depends(get_db)):
    """Get political statistics by ID."""
    result = db.query(PoliticalStatistics).filter(PoliticalStatistics.id == stat_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Record not found")
    return result


@router.put("/political/{stat_id}", response_model=PoliticalStatisticsResponse)
def update_political_statistics(
    stat_id: int,
    data: PoliticalStatisticsUpdate,
    db: Session = Depends(get_db)
):
    """Update political statistics record."""
    db_obj = db.query(PoliticalStatistics).filter(PoliticalStatistics.id == stat_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Record not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db_obj.updated_at = time.time()
    db.commit()
    db.refresh(db_obj)
    
    return db_obj


@router.delete("/political/{stat_id}")
def delete_political_statistics(stat_id: int, db: Session = Depends(get_db)):
    """Delete political statistics record."""
    db_obj = db.query(PoliticalStatistics).filter(PoliticalStatistics.id == stat_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Record not found")
    
    db.delete(db_obj)
    db.commit()
    
    return {"message": "Record deleted successfully"}
