"""
Schemas for ImportantPost model
Bài viết báo chí đặc biệt quan trọng
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ImportantPostBase(BaseModel):
    """Base schema for ImportantPost"""
    url: str = Field(..., max_length=2048, description="URL bài viết gốc")
    title: str = Field(..., max_length=1024, description="Tiêu đề bài viết")
    content: str = Field(..., description="Nội dung đầy đủ bài viết")
    data_type: str = Field(default="newspaper", max_length=50, description="Loại dữ liệu")
    type_newspaper: Optional[str] = Field(None, max_length=100, description="Phân loại báo: medical, economic, social, etc.")


class ImportantPostCreate(ImportantPostBase):
    """Schema for creating a new ImportantPost"""
    original_id: Optional[int] = Field(None, description="ID từ hệ thống nguồn")
    original_created_at: Optional[float] = Field(None, description="Thời gian tạo từ hệ thống nguồn")
    original_updated_at: Optional[float] = Field(None, description="Thời gian cập nhật từ hệ thống nguồn")
    
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Metadata từ nguồn")
    author: Optional[str] = Field(None, max_length=512, description="Tác giả")
    published_date: Optional[str] = Field(None, max_length=100, description="Ngày xuất bản")
    dvhc: Optional[str] = Field(None, max_length=256, description="Đơn vị hành chính")
    
    statistics: Optional[List[str]] = Field(None, description="Danh sách số liệu thống kê")
    organizations: Optional[List[str]] = Field(None, description="Danh sách tổ chức")
    
    is_featured: Optional[int] = Field(1, description="Đánh dấu nổi bật (1=featured, 0=normal)")
    importance_score: Optional[float] = Field(None, ge=0, le=10, description="Điểm quan trọng (0-10)")
    
    tags: Optional[List[str]] = Field(None, description="Tags phân loại")
    categories: Optional[List[str]] = Field(None, description="Danh mục liên quan")

    @field_validator('is_featured')
    @classmethod
    def validate_is_featured(cls, v):
        if v not in [0, 1]:
            raise ValueError('is_featured must be 0 or 1')
        return v


class ImportantPostUpdate(BaseModel):
    """Schema for updating an ImportantPost"""
    title: Optional[str] = Field(None, max_length=1024)
    content: Optional[str] = None
    type_newspaper: Optional[str] = Field(None, max_length=100)
    
    meta_data: Optional[Dict[str, Any]] = None
    author: Optional[str] = Field(None, max_length=512)
    published_date: Optional[str] = Field(None, max_length=100)
    dvhc: Optional[str] = Field(None, max_length=256)
    
    statistics: Optional[List[str]] = None
    organizations: Optional[List[str]] = None
    
    is_featured: Optional[int] = None
    importance_score: Optional[float] = Field(None, ge=0, le=10)
    
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None

    @field_validator('is_featured')
    @classmethod
    def validate_is_featured(cls, v):
        if v is not None and v not in [0, 1]:
            raise ValueError('is_featured must be 0 or 1')
        return v


class ImportantPostResponse(ImportantPostBase):
    """Schema for ImportantPost response"""
    id: int
    created_at: float
    updated_at: float
    
    original_id: Optional[int] = None
    original_created_at: Optional[float] = None
    original_updated_at: Optional[float] = None
    
    meta_data: Optional[Dict[str, Any]] = None
    author: Optional[str] = None
    published_date: Optional[str] = None
    dvhc: Optional[str] = None
    
    statistics: Optional[List[str]] = None
    organizations: Optional[List[str]] = None
    
    is_featured: Optional[int] = 1
    importance_score: Optional[float] = None
    
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None

    class Config:
        from_attributes = True


class ImportantPostListResponse(BaseModel):
    """Schema for list of ImportantPosts with pagination"""
    items: List[ImportantPostResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ImportantPostStatsResponse(BaseModel):
    """Schema for ImportantPost statistics"""
    total_posts: int
    by_type: Dict[str, int]
    by_featured: Dict[str, int]
    avg_importance_score: Optional[float] = None
    recent_posts: List[ImportantPostResponse]
