"""Custom Topics - Tự định nghĩa topics để phân loại"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.model_base import BareBaseModel


class CustomTopic(BareBaseModel):
    __tablename__ = "custom_topics"
    
    # Basic info
    name = Column(String(255), nullable=False, unique=True, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)  # URL-friendly name
    description = Column(Text)
    
    # Keywords cho classification
    keywords = Column(JSONB, nullable=False)  # ["từ khóa 1", "từ khóa 2", ...]
    keywords_weight = Column(Float, default=1.0)  # Trọng số keywords trong scoring
    
    # Example documents để train embedding
    example_docs = Column(JSONB)  # ["Câu ví dụ 1", "Câu ví dụ 2", ...]
    example_weight = Column(Float, default=1.0)  # Trọng số examples
    
    # Negative keywords (must NOT contain)
    negative_keywords = Column(JSONB)  # ["từ loại trừ 1", ...]
    
    # Classification settings
    classification_method = Column(String(50), default='hybrid')  # keyword, embedding, hybrid, llm
    min_confidence = Column(Float, default=0.5)  # Ngưỡng confidence tối thiểu
    
    # Display settings
    color = Column(String(7), default='#3B82F6')  # Hex color cho UI
    icon = Column(String(50))  # Icon name (emoji hoặc icon class)
    display_order = Column(Integer, default=0)  # Thứ tự hiển thị
    
    # Parent-child relationship (hỗ trợ topics lồng nhau)
    parent_id = Column(Integer, ForeignKey('custom_topics.id'), nullable=True)
    parent = relationship('CustomTopic', remote_side='CustomTopic.id', backref='children')
    
    # Metadata
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Statistics (cached)
    article_count = Column(Integer, default=0)  # Số bài đã phân loại
    last_classified_at = Column(DateTime)


class ArticleCustomTopic(BareBaseModel):
    """
    Mapping giữa Article và CustomTopic
    1 article có thể thuộc nhiều topics
    """
    __tablename__ = "article_custom_topics"
    
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey('custom_topics.id'), nullable=False, index=True)
    
    # Classification result
    confidence = Column(Float, nullable=False, index=True)  # 0.0 - 1.0
    method = Column(String(50))  # keyword, embedding, hybrid, llm, manual
    
    # Score breakdown (for debugging)
    keyword_score = Column(Float)
    embedding_score = Column(Float)
    llm_score = Column(Float)
    
    # Manual override
    is_manual = Column(Boolean, default=False)  # User manually assigned
    manual_by = Column(String(100))  # Who assigned
    
    # Metadata
    classified_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    article = relationship('Article', backref='custom_topics')
    topic = relationship('CustomTopic', backref='articles')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('article_id', 'topic_id', name='uq_article_custom_topic'),
    )


class TopicClassificationLog(BareBaseModel):
    """
    Log lịch sử phân loại (để audit và improve model)
    """
    __tablename__ = "topic_classification_logs"
    
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey('custom_topics.id'), nullable=False, index=True)
    
    # Result
    confidence = Column(Float, nullable=False)
    method = Column(String(50))
    accepted = Column(Boolean, default=True)  # Có được accept hay reject
    
    # Scores detail
    scores_detail = Column(JSONB)  # {"keyword": 0.3, "embedding": 0.8, "final": 0.65}
    
    # Timing
    processing_time_ms = Column(Integer)  # Thời gian xử lý (ms)
    classified_at = Column(DateTime, server_default=func.now(), index=True)
    
    # Relationships
    article = relationship('Article')
    topic = relationship('CustomTopic')


class TopicTemplate(BareBaseModel):
    """
    Template mẫu để tạo topics nhanh
    Ví dụ: template "News Category" có sẵn Politics, Economy, Sports, ...
    """
    __tablename__ = "topic_templates"
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)  # news, social_media, academic, etc.
    
    # Template data
    topics_data = Column(JSONB, nullable=False)  # List of topic definitions
    
    # Metadata
    is_public = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_by = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
