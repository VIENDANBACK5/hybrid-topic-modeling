"""IIP (Industrial Production Index) Schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class IIPBase(BaseModel):
    """Base IIP schema"""
    province: str = "Hưng Yên"
    period_type: str = "quarter"
    year: int
    quarter: Optional[int] = None
    month: Optional[int] = None
    
    actual_value: Optional[float] = None
    forecast_value: Optional[float] = None
    
    change_yoy: Optional[float] = None
    change_qoq: Optional[float] = None
    change_mom: Optional[float] = None
    change_prev_period: Optional[float] = None
    
    data_status: Optional[str] = "estimated"
    data_source: Optional[str] = None


class IIPResponse(IIPBase):
    """IIP response with ID"""
    id: int
    last_updated: Optional[datetime] = None
    period_label: Optional[str] = None
    
    class Config:
        from_attributes = True


class IIPExtractRequest(BaseModel):
    """Request to extract IIP from text"""
    text: str = Field(..., description="Text chứa thông tin IIP")
    year: int = Field(2025, description="Năm")
    quarter: Optional[int] = Field(None, description="Quý (1-4)")
    month: Optional[int] = Field(None, description="Tháng (1-12)")
    data_source: Optional[str] = Field(None, description="Nguồn")
    use_llm: bool = Field(True, description="Dùng LLM")
    force_update: bool = Field(True, description="Update nếu tồn tại")


class IIPListResponse(BaseModel):
    """List response"""
    total: int
    items: List[IIPResponse]
