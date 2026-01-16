"""
API Endpoints for AQI (Air Quality Index) Data
Lấy dữ liệu từ AQICN API thay vì extract từ articles
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.aqi_service import AQIService

router = APIRouter(prefix="/api/aqi", tags=["AQI - Air Quality"])


# =============================================================================
# SCHEMAS
# =============================================================================

class AQIFetchRequest(BaseModel):
    """Request for fetching AQI data"""
    province: str = Field("Hưng Yên", description="Tỉnh/thành phố")
    limit_stations: Optional[int] = Field(None, description="Giới hạn số trạm đo")
    store_mode: str = Field(
        "historical", 
        description="latest = cập nhật record hiện tại, historical = lưu record mới với timestamp"
    )


class AQIFetchResponse(BaseModel):
    """Response for AQI fetch"""
    province: str
    stations_processed: int
    records_created: int
    records_updated: int
    errors: list[str]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/fetch-and-fill", response_model=AQIFetchResponse)
async def fetch_and_fill_aqi_data(
    request: AQIFetchRequest,
    db: Session = Depends(get_db)
):
    """
    Lấy dữ liệu AQI từ AQICN API và fill vào bảng air_quality_detail
    
    - **province**: Tỉnh/thành phố (mặc định: Hưng Yên)
    - **limit_stations**: Giới hạn số trạm đo (None = tất cả)
    - **store_mode**: 
        - "historical" (mặc định): Lưu record mới mỗi lần fetch để có nhiều data points theo thời gian (dùng cho Superset)
        - "latest": Chỉ cập nhật record mới nhất của quarter hiện tại
    
    API Source: https://aqicn.org/data-platform/api/
    
    Dữ liệu bao gồm:
    - AQI Score (Chỉ số chất lượng không khí)
    - PM2.5, PM10, NO2, SO2, CO, O3
    - Good days percentage (Tỷ lệ ngày không khí tốt)
    - Timestamp (last_updated) để vẽ biểu đồ theo thời gian
    """
    service = AQIService(db)
    
    try:
        result = await service.fetch_and_fill_aqi_data(
            province=request.province,
            limit_stations=request.limit_stations,
            store_mode=request.store_mode
        )
        
        return AQIFetchResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching AQI data: {str(e)}"
        )


@router.get("/latest/{province}")
async def get_latest_aqi(
    province: str,
    db: Session = Depends(get_db)
):
    """
    Lấy dữ liệu AQI mới nhất của tỉnh
    """
    from app.models.model_indicator_details import AirQualityDetail
    
    latest = db.query(AirQualityDetail).filter(
        AirQualityDetail.province == province
    ).order_by(
        AirQualityDetail.year.desc(),
        AirQualityDetail.quarter.desc().nullsfirst()
    ).first()
    
    if not latest:
        raise HTTPException(
            status_code=404,
            detail=f"No AQI data found for province: {province}"
        )
    
    return {
        "province": latest.province,
        "year": latest.year,
        "quarter": latest.quarter,
        "month": latest.month,
        "aqi_score": latest.aqi_score,
        "pm25": latest.pm25,
        "pm10": latest.pm10,
        "good_days_pct": latest.good_days_pct,
        "data_source": latest.data_source,
        "updated_at": latest.updated_at
    }


@router.get("/stats")
async def get_aqi_stats(db: Session = Depends(get_db)):
    """
    Thống kê tổng quan dữ liệu AQI trong DB
    """
    from app.models.model_indicator_details import AirQualityDetail
    from sqlalchemy import func
    
    stats = db.query(
        func.count(AirQualityDetail.id).label('total_records'),
        func.count(func.distinct(AirQualityDetail.province)).label('provinces'),
        func.max(AirQualityDetail.year).label('latest_year'),
        func.avg(AirQualityDetail.aqi_score).label('avg_aqi')
    ).first()
    
    return {
        "total_records": stats.total_records,
        "provinces_covered": stats.provinces,
        "latest_year": stats.latest_year,
        "average_aqi": round(stats.avg_aqi, 2) if stats.avg_aqi else None
    }
