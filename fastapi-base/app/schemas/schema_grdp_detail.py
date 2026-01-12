"""
GRDP Detail Schemas - Pydantic models for API validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class GRDPDetailBase(BaseModel):
    """Base schema cho GRDP Detail"""
    
    # Foreign key (optional)
    economic_indicator_id: Optional[int] = Field(None, description="ID liên kết với bảng economic_indicators")
    
    # 1. Nhóm định danh & thời gian
    province: str = Field(..., description="Tỉnh/thành phố (VD: Hưng Yên)", max_length=100)
    year: int = Field(..., description="Năm thống kê (VD: 2025)", ge=2000, le=2100)
    quarter: Optional[int] = Field(None, description="Quý (1-4), NULL = cả năm", ge=1, le=4)
    
    # 2. Nhóm giá trị kinh tế
    grdp_current_price: Optional[float] = Field(None, description="GRDP theo giá hiện hành (tỷ VNĐ)", ge=0)
    grdp_per_capita: Optional[float] = Field(None, description="GRDP bình quân/người (triệu VNĐ)", ge=0)
    
    # 3. Nhóm tăng trưởng
    growth_rate: Optional[float] = Field(None, description="Tốc độ tăng trưởng so cùng kỳ (%)")
    
    # 4. Nhóm cơ cấu ngành kinh tế
    agriculture_sector_pct: Optional[float] = Field(None, description="Tỷ trọng nông - lâm - thủy sản (%)", ge=0, le=100)
    industry_sector_pct: Optional[float] = Field(None, description="Tỷ trọng công nghiệp - xây dựng (%)", ge=0, le=100)
    service_sector_pct: Optional[float] = Field(None, description="Tỷ trọng dịch vụ (%)", ge=0, le=100)
    
    # 5. Nhóm so sánh & xếp hạng
    rank_national: Optional[int] = Field(None, description="Xếp hạng toàn quốc", ge=1, le=63)
    
    # 6. Nhóm dự báo
    forecast_year_end: Optional[float] = Field(None, description="Dự báo GRDP cả năm (tỷ VNĐ)", ge=0)
    
    # 7. Nhóm trạng thái & nguồn dữ liệu
    data_status: str = Field("official", description="Trạng thái: official/estimated/forecast")
    data_source: Optional[str] = Field(None, description="Nguồn dữ liệu", max_length=255)
    last_updated: Optional[datetime] = Field(None, description="Thời điểm cập nhật gần nhất")
    
    @field_validator('data_status')
    @classmethod
    def validate_data_status(cls, v):
        """Validate data_status phải là một trong các giá trị cho phép"""
        allowed = ['official', 'estimated', 'forecast']
        if v not in allowed:
            raise ValueError(f'data_status phải là một trong: {", ".join(allowed)}')
        return v
    
    @field_validator('province')
    @classmethod
    def validate_province(cls, v):
        """Chuẩn hóa tên tỉnh"""
        if v:
            return v.strip()
        return v


class GRDPDetailCreate(GRDPDetailBase):
    """Schema để tạo mới GRDP Detail"""
    pass


class GRDPDetailUpdate(BaseModel):
    """Schema để cập nhật GRDP Detail - tất cả fields đều optional"""
    
    economic_indicator_id: Optional[int] = None
    
    province: Optional[str] = Field(None, max_length=100)
    year: Optional[int] = Field(None, ge=2000, le=2100)
    quarter: Optional[int] = Field(None, ge=1, le=4)
    
    grdp_current_price: Optional[float] = Field(None, ge=0)
    grdp_per_capita: Optional[float] = Field(None, ge=0)
    
    growth_rate: Optional[float] = None
    
    agriculture_sector_pct: Optional[float] = Field(None, ge=0, le=100)
    industry_sector_pct: Optional[float] = Field(None, ge=0, le=100)
    service_sector_pct: Optional[float] = Field(None, ge=0, le=100)
    
    rank_national: Optional[int] = Field(None, ge=1, le=63)
    
    forecast_year_end: Optional[float] = Field(None, ge=0)
    
    data_status: Optional[str] = None
    data_source: Optional[str] = Field(None, max_length=255)
    last_updated: Optional[datetime] = None
    
    @field_validator('data_status')
    @classmethod
    def validate_data_status(cls, v):
        """Validate data_status nếu có"""
        if v is not None:
            allowed = ['official', 'estimated', 'forecast']
            if v not in allowed:
                raise ValueError(f'data_status phải là một trong: {", ".join(allowed)}')
        return v


class GRDPDetailResponse(GRDPDetailBase):
    """Schema response cho GRDP Detail"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    period_label: Optional[str] = Field(None, description="Nhãn thời gian (VD: Quý 1/2025)")
    
    class Config:
        from_attributes = True


class GRDPDetailListResponse(BaseModel):
    """Schema response cho danh sách GRDP"""
    total: int = Field(..., description="Tổng số bản ghi")
    page: int = Field(..., description="Trang hiện tại")
    page_size: int = Field(..., description="Số bản ghi mỗi trang")
    total_pages: int = Field(..., description="Tổng số trang")
    data: list[GRDPDetailResponse] = Field(..., description="Danh sách GRDP")


class GRDPDetailStats(BaseModel):
    """Schema cho thống kê GRDP"""
    province: str
    year: int
    quarter: Optional[int] = None
    
    total_records: int = Field(..., description="Tổng số bản ghi")
    avg_grdp: Optional[float] = Field(None, description="GRDP trung bình")
    avg_growth_rate: Optional[float] = Field(None, description="Tốc độ tăng trưởng trung bình")
    avg_per_capita: Optional[float] = Field(None, description="GRDP/người trung bình")
    
    latest_grdp: Optional[float] = Field(None, description="GRDP mới nhất")
    latest_growth_rate: Optional[float] = Field(None, description="Tăng trưởng mới nhất")


class GRDPComparisonResponse(BaseModel):
    """Schema cho so sánh GRDP giữa các tỉnh"""
    year: int
    quarter: Optional[int] = None
    
    top_provinces: list[dict] = Field(..., description="Top tỉnh có GRDP cao nhất")
    top_growth: list[dict] = Field(..., description="Top tỉnh tăng trưởng cao nhất")
    sector_analysis: dict = Field(..., description="Phân tích cơ cấu ngành")
