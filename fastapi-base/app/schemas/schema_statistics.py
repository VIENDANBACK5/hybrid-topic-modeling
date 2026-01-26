from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EconomicStatisticsBase(BaseModel):
    dvhc: str = Field(..., description="Đơn vị hành chính")
    source_post_id: Optional[int] = None
    source_url: Optional[str] = None
    period: Optional[str] = None
    year: Optional[int] = None
    total_production_value: Optional[float] = Field(None, description="Tổng giá trị sản xuất (tỷ đồng)")
    growth_rate: Optional[float] = Field(None, description="Tốc độ tăng trưởng (%)")
    total_budget_revenue: Optional[float] = Field(None, description="Tổng thu ngân sách (tỷ đồng)")
    budget_collection_efficiency: Optional[float] = Field(None, description="Hiệu suất thu ngân sách (%)")
    notes: Optional[str] = None
    extraction_metadata: Optional[str] = None


class EconomicStatisticsCreate(EconomicStatisticsBase):
    pass


class EconomicStatisticsUpdate(BaseModel):
    dvhc: Optional[str] = None
    source_post_id: Optional[int] = None
    source_url: Optional[str] = None
    period: Optional[str] = None
    year: Optional[int] = None
    total_production_value: Optional[float] = None
    growth_rate: Optional[float] = None
    total_budget_revenue: Optional[float] = None
    budget_collection_efficiency: Optional[float] = None
    notes: Optional[str] = None
    extraction_metadata: Optional[str] = None


class EconomicStatisticsResponse(EconomicStatisticsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PoliticalStatisticsBase(BaseModel):
    dvhc: str = Field(..., description="Đơn vị hành chính")
    source_post_id: Optional[int] = None
    source_url: Optional[str] = None
    period: Optional[str] = None
    year: Optional[int] = None
    party_organization_count: Optional[int] = Field(None, description="Số tổ chức Đảng")
    party_member_count: Optional[int] = Field(None, description="Số lượng Đảng viên")
    party_size_description: Optional[str] = Field(None, description="Mô tả quy mô Đảng bộ")
    new_party_members: Optional[int] = None
    party_cells_count: Optional[int] = Field(None, description="Số chi bộ")
    notes: Optional[str] = None
    extraction_metadata: Optional[str] = None


class PoliticalStatisticsCreate(PoliticalStatisticsBase):
    pass


class PoliticalStatisticsUpdate(BaseModel):
    dvhc: Optional[str] = None
    source_post_id: Optional[int] = None
    source_url: Optional[str] = None
    period: Optional[str] = None
    year: Optional[int] = None
    party_organization_count: Optional[int] = None
    party_member_count: Optional[int] = None
    party_size_description: Optional[str] = None
    new_party_members: Optional[int] = None
    party_cells_count: Optional[int] = None
    notes: Optional[str] = None
    extraction_metadata: Optional[str] = None


class PoliticalStatisticsResponse(PoliticalStatisticsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
