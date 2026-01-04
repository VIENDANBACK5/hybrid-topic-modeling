"""
Schemas for Custom Topic Classification
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ClassificationMethod(str, Enum):
    """Phương pháp phân loại"""
    KEYWORD = "keyword"
    EMBEDDING = "embedding"
    HYBRID = "hybrid"
    LLM = "llm"
    MANUAL = "manual"


# ============ Custom Topic Schemas ============

class CustomTopicBase(BaseModel):
    """Base schema cho topic"""
    name: str = Field(..., min_length=3, max_length=255, description="Tên topic")
    description: Optional[str] = Field(None, description="Mô tả chi tiết")
    keywords: List[str] = Field(..., min_items=3, description="Danh sách từ khóa (tối thiểu 3)")
    keywords_weight: float = Field(default=1.0, ge=0, le=2, description="Trọng số keywords")
    example_docs: Optional[List[str]] = Field(None, description="Câu văn mẫu")
    example_weight: float = Field(default=1.0, ge=0, le=2)
    negative_keywords: Optional[List[str]] = Field(None, description="Từ khóa loại trừ")
    classification_method: ClassificationMethod = Field(default=ClassificationMethod.HYBRID)
    min_confidence: float = Field(default=0.5, ge=0, le=1, description="Ngưỡng confidence")
    color: str = Field(default="#3B82F6", pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None
    display_order: int = Field(default=0, ge=0)
    parent_id: Optional[int] = None
    is_active: bool = True

    @validator('keywords', 'negative_keywords')
    def validate_keywords(cls, v):
        if v:
            # Lowercase và strip
            return [k.strip().lower() for k in v if k.strip()]
        return v

    @validator('example_docs')
    def validate_examples(cls, v):
        if v:
            return [doc.strip() for doc in v if doc.strip()]
        return v


class CustomTopicCreate(CustomTopicBase):
    """Tạo topic mới"""
    created_by: Optional[str] = None


class CustomTopicUpdate(BaseModel):
    """Cập nhật topic"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    keywords_weight: Optional[float] = Field(None, ge=0, le=2)
    example_docs: Optional[List[str]] = None
    example_weight: Optional[float] = Field(None, ge=0, le=2)
    negative_keywords: Optional[List[str]] = None
    classification_method: Optional[ClassificationMethod] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class CustomTopicResponse(CustomTopicBase):
    """Response topic"""
    id: int
    slug: str
    article_count: int
    last_classified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomTopicDetailResponse(CustomTopicResponse):
    """Response chi tiết topic với children"""
    children: List['CustomTopicResponse'] = []
    parent: Optional['CustomTopicResponse'] = None


# ============ Classification Schemas ============

class ClassificationScores(BaseModel):
    """Chi tiết điểm số phân loại"""
    keyword_score: float = Field(ge=0, le=1)
    embedding_score: Optional[float] = Field(None, ge=0, le=1)
    llm_score: Optional[float] = Field(None, ge=0, le=1)
    final_score: float = Field(ge=0, le=1)


class TopicClassificationResult(BaseModel):
    """Kết quả phân loại 1 topic"""
    topic_id: int
    topic_name: str
    confidence: float = Field(ge=0, le=1)
    method: ClassificationMethod
    scores: Optional[ClassificationScores] = None
    is_accepted: bool  # >= min_confidence


class ArticleClassificationResult(BaseModel):
    """Kết quả phân loại 1 bài viết"""
    article_id: int
    article_title: str
    topics: List[TopicClassificationResult]
    processing_time_ms: int


class ClassifyArticlesRequest(BaseModel):
    """Request phân loại articles"""
    article_ids: Optional[List[int]] = Field(None, description="Danh sách article IDs")
    all_unclassified: bool = Field(False, description="Phân loại tất cả chưa có topic")
    all_articles: bool = Field(False, description="Phân loại lại tất cả")
    topic_ids: Optional[List[int]] = Field(None, description="Chỉ phân loại vào các topics này")
    method: ClassificationMethod = Field(default=ClassificationMethod.HYBRID)
    save_results: bool = Field(True, description="Lưu kết quả vào database")
    min_confidence: Optional[float] = Field(None, ge=0, le=1, description="Override min_confidence")


class BulkClassificationResponse(BaseModel):
    """Response phân loại hàng loạt"""
    total_articles: int
    total_topics: int
    processing_time_ms: int
    results: List[ArticleClassificationResult]
    summary: Dict[str, Any]  # {"saved": 150, "skipped": 50}


# ============ Article Topic Mapping Schemas ============

class ArticleTopicBase(BaseModel):
    """Base mapping"""
    article_id: int
    topic_id: int
    confidence: float = Field(ge=0, le=1)
    method: ClassificationMethod


class ArticleTopicCreate(ArticleTopicBase):
    """Tạo mapping mới"""
    is_manual: bool = False
    manual_by: Optional[str] = None
    keyword_score: Optional[float] = None
    embedding_score: Optional[float] = None
    llm_score: Optional[float] = None


class ArticleTopicResponse(ArticleTopicBase):
    """Response mapping"""
    id: int
    is_manual: bool
    classified_at: datetime
    
    class Config:
        from_attributes = True


class ArticleWithTopicsResponse(BaseModel):
    """Article kèm topics"""
    article_id: int
    title: str
    topics: List[TopicClassificationResult]


class TopicWithArticlesResponse(BaseModel):
    """Topic kèm articles"""
    topic_id: int
    topic_name: str
    total_articles: int
    articles: List[Dict[str, Any]]


# ============ Template Schemas ============

class TopicTemplateData(BaseModel):
    """Data của 1 topic trong template"""
    name: str
    description: str
    keywords: List[str]
    example_docs: Optional[List[str]] = None
    color: str = "#3B82F6"
    icon: Optional[str] = None


class TopicTemplateCreate(BaseModel):
    """Tạo template"""
    name: str = Field(..., min_length=3)
    description: Optional[str] = None
    category: str
    topics_data: List[TopicTemplateData] = Field(..., min_items=1)
    is_public: bool = True
    created_by: Optional[str] = None


class TopicTemplateResponse(BaseModel):
    """Response template"""
    id: int
    name: str
    description: Optional[str]
    category: str
    topics_data: List[TopicTemplateData]
    is_public: bool
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ApplyTemplateRequest(BaseModel):
    """Request áp dụng template"""
    template_id: int
    override_existing: bool = Field(False, description="Ghi đè topics trùng tên")


# ============ Statistics Schemas ============

class TopicStats(BaseModel):
    """Thống kê topic"""
    topic_id: int
    topic_name: str
    article_count: int
    avg_confidence: float
    method_distribution: Dict[str, int]  # {"keyword": 10, "embedding": 20}
    recent_articles: List[Dict[str, Any]]


class ClassificationOverview(BaseModel):
    """Tổng quan hệ thống phân loại"""
    total_topics: int
    active_topics: int
    total_classified_articles: int
    total_unclassified_articles: int
    avg_topics_per_article: float
    classification_methods: Dict[str, int]
    top_topics: List[TopicStats]
