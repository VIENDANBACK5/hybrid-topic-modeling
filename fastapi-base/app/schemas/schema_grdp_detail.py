"""GRDP Schema - Timeseries Format"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class GRDPDetailCreate(BaseModel):
    """Schema tạo GRDP"""
    province: str
    period_type: str = 'year'
    year: int
    quarter: Optional[int] = None
    
    actual_value: Optional[float] = None
    forecast_value: Optional[float] = None
    
    change_yoy: Optional[float] = None
    change_qoq: Optional[float] = None
    change_prev_period: Optional[float] = None
    
    data_status: str = 'estimated'
    data_source: Optional[str] = None


class GRDPDetailResponse(BaseModel):
    """Schema response GRDP"""
    id: int
    province: str
    period_type: str
    year: int
    quarter: Optional[int] = None
    
    actual_value: Optional[float] = None
    forecast_value: Optional[float] = None
    
    change_yoy: Optional[float] = None
    change_qoq: Optional[float] = None
    change_prev_period: Optional[float] = None
    
    data_status: Optional[str] = None
    data_source: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    period_label: Optional[str] = None
    
    class Config:
        from_attributes = True


class GRDPDetailListResponse(BaseModel):
    """Schema list response"""
    total: int
    page: int
    page_size: int
    total_pages: int
    data: List[GRDPDetailResponse]


class GRDPExtractRequest(BaseModel):
    """Request để extract GRDP từ text"""
    text: str = Field(..., description="Nội dung text chứa thông tin GRDP")
    year: int = Field(2025, description="Năm của data GRDP")
    quarter: Optional[int] = Field(None, description="Quý (1-4), None nếu là cả năm")
    data_source: Optional[str] = Field(None, description="Nguồn dữ liệu (URL hoặc tên file)")
    use_llm: bool = Field(True, description="Có dùng LLM để extract không")
    force_update: bool = Field(True, description="Có update nếu đã tồn tại không")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": """Tổng sản phẩm trên địa bàn tỉnh (GRDP) 9 tháng năm 2025 ước đạt 114.792 tỷ đồng, tăng 8,01% so với cùng kỳ năm 2024. 
Phân theo quý: sơ bộ quý I tăng 8,80%; quý II tăng 7,40%; ước tính quý III tăng 7,93%.
Về quy mô kinh tế (GRDP theo giá hiện hành) 9 tháng năm 2025 ước đạt 219.846 tỷ đồng.""",
                "year": 2025,
                "quarter": None,
                "data_source": "https://thongkehungyen.nso.gov.vn/tinh-hinh-kinh-te-xa-hoi/14",
                "use_llm": True,
                "force_update": True
            }
        }


class GRDPCrawlRequest(BaseModel):
    """DEPRECATED: Use GRDPExtractRequest instead"""
    url: str = Field(..., description="URL của trang web chứa data GRDP")
    year: int = Field(..., description="Năm của data GRDP")
    quarter: Optional[int] = Field(None, description="Quý (1-4), None nếu là cả năm")
    text_content: Optional[str] = Field(None, description="Nội dung text (nếu trang web render JS)")
    use_llm: bool = Field(True, description="Có dùng LLM để extract không")
    force_update: bool = Field(True, description="Có update nếu đã tồn tại không")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://thongkehungyen.nso.gov.vn/tinh-hinh-kinh-te-xa-hoi/14",
                "year": 2025,
                "quarter": 3,
                "text_content": "Tổng sản phẩm trên địa bàn tỉnh (GRDP) 9 tháng năm 2025 ước đạt 114.792 tỷ đồng, tăng 8,01%...",
                "use_llm": True,
                "force_update": True
            }
        }
