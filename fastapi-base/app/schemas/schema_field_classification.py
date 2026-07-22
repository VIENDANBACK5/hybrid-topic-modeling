from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List, Dict
from datetime import datetime, date


class FieldBase(BaseModel):
    name: str = Field(..., description="Tên lĩnh vực")
    description: Optional[str] = Field(None, description="Mô tả lĩnh vực")
    keywords: List[str] = Field(default_factory=list, description="Từ khóa phân loại")
    order_index: int = Field(default=0, description="Thứ tự hiển thị")


class FieldCreate(FieldBase):
    pass


class FieldUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    order_index: Optional[int] = None


class FieldResponse(FieldBase):
    id: int
    created_at: float
    updated_at: float
    
    class Config:
        from_attributes = True


class ArticleFieldClassificationBase(BaseModel):
    article_id: int
    field_id: int
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    matched_keywords: List[str] = Field(default_factory=list)
    classification_method: str = Field(default="keyword")


class ArticleFieldClassificationCreate(ArticleFieldClassificationBase):
    pass


class ArticleFieldClassificationResponse(ArticleFieldClassificationBase):
    id: int
    created_at: float
    updated_at: float
    
    class Config:
        from_attributes = True


class FieldStatisticsResponse(BaseModel):
    id: int
    field_id: int
    field_name: str
    total_articles: int
    articles_today: int
    articles_this_week: int
    articles_this_month: int
    avg_likes: float
    avg_shares: float
    avg_comments: float
    total_engagement: int
    source_distribution: Optional[Dict[str, int]] = None
    province_distribution: Optional[Dict[str, int]] = None
    stats_date: float
    created_at: float
    updated_at: float
    
    class Config:
        from_attributes = True


class ClassificationRequest(BaseModel):
    article_ids: Optional[List[int]] = Field(None, description="Danh sách ID bài viết cần phân loại. Nếu None, phân loại tất cả")
    force_reclassify: bool = Field(default=False, description="Có phân loại lại các bài đã được phân loại hay không")
    method: str = Field(default="auto", description="Phương pháp phân loại: auto (keyword + LLM), keyword, llm")


class ClassificationStatsResponse(BaseModel):
    total_articles: int
    classified_articles: int
    unclassified_articles: int
    field_distribution: Dict[str, int]  # {field_name: article_count}
    method_stats: Optional[Dict[str, int]] = None  # {method_name: count}
    classification_time: float  # Thời gian xử lý (seconds)


class FieldDistributionItem(BaseModel):
    field_id: int
    field_name: str
    article_count: int
    percentage: float


class FieldDistributionResponse(BaseModel):
    total_articles: int
    fields: List[FieldDistributionItem]
    last_updated: float


class FieldSummaryResponse(BaseModel):
    id: int
    field_id: int
    field_name: str
    summary_period: str
    period_start: float
    period_end: float
    summary_date: date
    total_articles: int
    avg_engagement: float
    top_sources: Optional[Dict[str, int]] = None
    key_topics: Optional[List[str]] = None
    summary_text: Optional[str] = None
    sentiment_overview: Optional[Dict[str, int]] = None
    top_articles: Optional[List[Dict]] = None
    trending_keywords: Optional[List[str]] = None
    generation_method: str
    model_used: Optional[str] = None
    created_at: float
    updated_at: float
    
    @field_serializer('summary_date')
    def serialize_date(self, value: date):
        return value.isoformat() if value else None
    
    class Config:
        from_attributes = True


class CreateSummaryRequest(BaseModel):
    field_ids: Optional[List[int]] = Field(None, description="Danh sách ID lĩnh vực. Nếu None, tạo cho tất cả")
    period: str = Field(default="daily", description="Kỳ tóm tắt: daily, weekly, monthly")
    target_date: Optional[str] = Field(None, description="Ngày tạo summary (YYYY-MM-DD). Mặc định: hôm nay")
    model: str = Field(default="gpt-3.5-turbo", description="Model OpenAI")

