"""
Economic Indicators Schemas - Pydantic models for API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date


class EconomicIndicatorBase(BaseModel):
    """Base schema cho Economic Indicator"""
    period_type: str = Field(..., description="Loại kỳ: monthly, quarterly, yearly")
    period_start: date = Field(..., description="Ngày bắt đầu kỳ")
    period_end: date = Field(..., description="Ngày kết thúc kỳ")
    period_label: Optional[str] = Field(None, description="Nhãn kỳ: Tháng 12/2025")
    year: Optional[int] = Field(None, description="Năm")
    month: Optional[int] = Field(None, description="Tháng (1-12)")
    quarter: Optional[int] = Field(None, description="Quý (1-4)")
    
    province: Optional[str] = Field(None, description="Tỉnh/thành phố")
    region: Optional[str] = Field(None, description="Miền: Bắc, Trung, Nam")
    
    detailed_data: Optional[Dict[str, Any]] = Field(None, description="Dữ liệu chi tiết")
    
    data_source: Optional[str] = Field(None, description="Nguồn dữ liệu")
    source_url: Optional[str] = Field(None, description="URL nguồn")
    
    # Liên kết với bài viết nguồn
    source_article_id: Optional[int] = Field(None, description="ID bài viết nguồn từ bảng articles")
    source_article_url: Optional[str] = Field(None, description="URL bài viết nguồn")
    source_article_domain: Optional[str] = Field(None, description="Domain bài viết nguồn")
    
    notes: Optional[str] = Field(None, description="Ghi chú")
    
    # Analysis fields for each indicator group
    grdp_analysis: Optional[str] = Field(None, description="Nhận xét về GRDP")
    iip_analysis: Optional[str] = Field(None, description="Nhận xét về IIP")
    agricultural_analysis: Optional[str] = Field(None, description="Nhận xét về nông nghiệp")
    retail_services_analysis: Optional[str] = Field(None, description="Nhận xét về bán lẻ & dịch vụ")
    export_import_analysis: Optional[str] = Field(None, description="Nhận xét về xuất nhập khẩu")
    investment_analysis: Optional[str] = Field(None, description="Nhận xét về đầu tư")
    budget_analysis: Optional[str] = Field(None, description="Nhận xét về ngân sách")
    labor_analysis: Optional[str] = Field(None, description="Nhận xét về lao động")
    
    summary: Optional[str] = Field(None, description="Tóm tắt tổng quan về tình hình kinh tế kỳ này")
    
    is_verified: Optional[int] = Field(0, description="Đã xác minh: 0=No, 1=Yes")
    is_estimated: Optional[int] = Field(0, description="Ước tính: 0=No, 1=Yes")


class EconomicIndicatorCreate(EconomicIndicatorBase):
    """Schema để tạo mới Economic Indicator"""
    pass


class EconomicIndicatorUpdate(BaseModel):
    """Schema để cập nhật Economic Indicator - tất cả fields đều optional"""
    period_type: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    period_label: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    quarter: Optional[int] = None
    
    province: Optional[str] = None
    region: Optional[str] = None
    
    detailed_data: Optional[Dict[str, Any]] = None
    
    data_source: Optional[str] = None
    source_url: Optional[str] = None
    
    source_article_id: Optional[int] = None
    source_article_url: Optional[str] = None
    source_article_domain: Optional[str] = None
    
    notes: Optional[str] = None
    
    # Analysis fields
    grdp_analysis: Optional[str] = None
    iip_analysis: Optional[str] = None
    agricultural_analysis: Optional[str] = None
    retail_services_analysis: Optional[str] = None
    export_import_analysis: Optional[str] = None
    investment_analysis: Optional[str] = None
    budget_analysis: Optional[str] = None
    labor_analysis: Optional[str] = None
    
    summary: Optional[str] = None
    
    is_verified: Optional[int] = None
    is_estimated: Optional[int] = None


class EconomicIndicatorResponse(EconomicIndicatorBase):
    """Schema response cho Economic Indicator"""
    id: int
    created_at: float
    updated_at: float
    
    class Config:
        from_attributes = True


class EconomicIndicatorQuery(BaseModel):
    """Schema để query Economic Indicators"""
    period_type: Optional[str] = Field(None, description="Loại kỳ: monthly, quarterly, yearly")
    year: Optional[int] = Field(None, description="Năm")
    month: Optional[int] = Field(None, description="Tháng (1-12)")
    quarter: Optional[int] = Field(None, description="Quý (1-4)")
    province: Optional[str] = Field(None, description="Tỉnh/thành phố")
    region: Optional[str] = Field(None, description="Miền")
    
    page: Optional[int] = Field(1, ge=1, description="Trang")
    page_size: Optional[int] = Field(20, ge=1, le=100, description="Số items mỗi trang")
    sort_by: Optional[str] = Field("created_at", description="Sắp xếp theo trường")
    order: Optional[str] = Field("desc", description="Thứ tự: asc, desc")


class EconomicIndicatorGPTRequest(BaseModel):
    """Schema để request GPT tạo dữ liệu kinh tế"""
    indicator_name: str = Field(..., description="Tên chỉ số: grdp, iip, cpi, etc.")
    period_type: str = Field(..., description="Loại kỳ: monthly, quarterly, yearly")
    year: int = Field(..., description="Năm")
    month: Optional[int] = Field(None, description="Tháng (1-12)")
    quarter: Optional[int] = Field(None, description="Quý (1-4)")
    province: Optional[str] = Field(None, description="Tỉnh/thành phố")
    
    additional_context: Optional[str] = Field(None, description="Thông tin thêm cho GPT")


class EconomicIndicatorGPTResponse(BaseModel):
    """Schema response từ GPT"""
    id: int
    indicator_name: str
    indicator_value: Optional[float]
    indicator_unit: Optional[str]
    
    period_type: str
    period_label: Optional[str]
    year: Optional[int]
    month: Optional[int]
    quarter: Optional[int]
    province: Optional[str]
    
    gpt_response: Optional[str]
    gpt_summary: Optional[str]
    
    model_used: Optional[str]
    confidence_score: Optional[float]
    
    created_at: float
    
    class Config:
        from_attributes = True


class EconomicIndicatorSummary(BaseModel):
    """Schema tóm tắt các chỉ số kinh tế"""
    period_label: str
    total_indicators: int
    available_indicators: List[str]
    missing_indicators: List[str]
    
    key_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Các chỉ số chính: grdp_growth, iip_growth, cpi, export_value, etc."
    )
