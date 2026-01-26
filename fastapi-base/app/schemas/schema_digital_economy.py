"""Digital Economy Schema - Pydantic models"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DigitalEconomyCreate(BaseModel):
    """Schema tạo Digital Economy"""
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
    
    # Digital Economy specific fields
    digital_economy_gdp: Optional[float] = None
    digital_economy_gdp_share: Optional[float] = None
    ecommerce_revenue: Optional[float] = None
    ecommerce_users: Optional[int] = None
    digital_payment_volume: Optional[float] = None
    digital_companies: Optional[int] = None
    internet_penetration: Optional[float] = None
    
    data_status: str = 'estimated'
    data_source: Optional[str] = None


class DigitalEconomyResponse(BaseModel):
    """Schema response Digital Economy"""
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
    
    digital_economy_gdp: Optional[float] = None
    digital_economy_gdp_share: Optional[float] = None
    ecommerce_revenue: Optional[float] = None
    ecommerce_users: Optional[int] = None
    digital_payment_volume: Optional[float] = None
    
    data_status: Optional[str] = None
    data_source: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DigitalEconomyListResponse(BaseModel):
    """Schema list response"""
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    data: list[DigitalEconomyResponse]
