"""FDI Schema - Pydantic models"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FDICreate(BaseModel):
    """Schema tạo FDI"""
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
    
    # FDI specific fields
    registered_capital: Optional[float] = None
    new_projects_capital: Optional[float] = None
    disbursed_capital: Optional[float] = None
    disbursement_rate: Optional[float] = None
    total_projects: Optional[int] = None
    new_projects: Optional[int] = None
    manufacturing_fdi: Optional[float] = None
    japan_fdi: Optional[float] = None
    korea_fdi: Optional[float] = None
    fdi_employment: Optional[int] = None
    
    data_status: str = 'estimated'
    data_source: Optional[str] = None


class FDIResponse(BaseModel):
    """Schema response FDI"""
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
    
    registered_capital: Optional[float] = None
    new_projects_capital: Optional[float] = None
    disbursed_capital: Optional[float] = None
    disbursement_rate: Optional[float] = None
    total_projects: Optional[int] = None
    new_projects: Optional[int] = None
    
    data_status: Optional[str] = None
    data_source: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class FDIListResponse(BaseModel):
    """Schema list response"""
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    data: list[FDIResponse]
