"""PII (Provincial Industrial Index) Schema - Pydantic models"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PIICreate(BaseModel):
    """Schema tạo PII"""
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
    
    # PII specific fields
    pii_overall: Optional[float] = None
    pii_growth_rate: Optional[float] = None
    industrial_output_value: Optional[float] = None
    mining_index: Optional[float] = None
    manufacturing_index: Optional[float] = None
    electricity_index: Optional[float] = None
    food_processing_index: Optional[float] = None
    textile_index: Optional[float] = None
    electronics_index: Optional[float] = None
    state_owned_pii: Optional[float] = None
    private_pii: Optional[float] = None
    fdi_pii: Optional[float] = None
    labor_productivity: Optional[float] = None
    industrial_enterprises: Optional[int] = None
    industrial_workers: Optional[int] = None
    
    data_status: str = 'estimated'
    data_source: Optional[str] = None


class PIIResponse(BaseModel):
    """Schema response PII"""
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
    
    pii_overall: Optional[float] = None
    pii_growth_rate: Optional[float] = None
    industrial_output_value: Optional[float] = None
    manufacturing_index: Optional[float] = None
    
    data_status: Optional[str] = None
    data_source: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PIIListResponse(BaseModel):
    """Schema list response"""
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    data: list[PIIResponse]
