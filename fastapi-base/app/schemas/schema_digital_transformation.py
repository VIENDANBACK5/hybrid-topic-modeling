"""Digital Transformation Schema - Pydantic models"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DigitalTransformationCreate(BaseModel):
    """Schema tạo Digital Transformation"""
    province: str = 'Hưng Yên'
    period_type: str = 'quarter'
    year: int
    quarter: Optional[int] = None
    month: Optional[int] = None
    
    # Core values
    actual_value: Optional[float] = None
    forecast_value: Optional[float] = None
    change_yoy: Optional[float] = None
    change_qoq: Optional[float] = None
    change_mom: Optional[float] = None
    
    # Digital Transformation specific fields
    dx_index: Optional[float] = None
    dx_readiness_index: Optional[float] = None
    egov_index: Optional[float] = None
    online_public_services: Optional[int] = None
    level3_services: Optional[int] = None
    level4_services: Optional[int] = None
    online_service_usage_rate: Optional[float] = None
    cloud_adoption_rate: Optional[float] = None
    sme_dx_adoption: Optional[float] = None
    companies_using_ai: Optional[int] = None
    companies_using_iot: Optional[int] = None
    
    data_status: str = 'estimated'
    data_source: Optional[str] = None


class DigitalTransformationResponse(BaseModel):
    """Schema response Digital Transformation"""
    id: int
    province: str
    period_type: str
    year: int
    quarter: Optional[int] = None
    month: Optional[int] = None
    
    actual_value: Optional[float] = None
    forecast_value: Optional[float] = None
    change_yoy: Optional[float] = None
    change_qoq: Optional[float] = None
    
    dx_index: Optional[float] = None
    dx_readiness_index: Optional[float] = None
    egov_index: Optional[float] = None
    online_public_services: Optional[int] = None
    level3_services: Optional[int] = None
    level4_services: Optional[int] = None
    
    data_status: Optional[str] = None
    data_source: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DigitalTransformationListResponse(BaseModel):
    """Schema list response"""
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    data: list[DigitalTransformationResponse]
