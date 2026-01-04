"""
Trend Analysis Models - Phân tích xu hướng đột biến, khủng hoảng
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Date, JSON, Boolean
from sqlalchemy.sql import func
from app.models.model_base import BareBaseModel


class TrendAlert(BareBaseModel):
    """
    Cảnh báo xu hướng đột biến / khủng hoảng
    Superset: Alert dashboard, Real-time monitoring
    """
    __tablename__ = "trend_alerts"
    
    # Thời gian phát hiện
    detected_at = Column(DateTime, server_default=func.now(), index=True)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    
    # Loại cảnh báo
    alert_type = Column(String(30), nullable=False, index=True)  
    # spike: đột biến tăng, drop: đột biến giảm, crisis: khủng hoảng, viral: lan truyền
    
    alert_level = Column(String(20), nullable=False, index=True)  
    # low, medium, high, critical
    
    alert_status = Column(String(20), default='active', index=True)  
    # active, acknowledged, resolved
    
    # Thông tin chủ đề/từ khóa liên quan
    topic_id = Column(Integer, index=True)
    topic_name = Column(String(512))
    category = Column(String(100), index=True)
    keywords = Column(JSON)  # Từ khóa liên quan
    
    # Metrics
    current_count = Column(Integer)  # Số lượng hiện tại
    previous_count = Column(Integer)  # Số lượng kỳ trước
    change_percent = Column(Float)  # % thay đổi
    velocity = Column(Float)  # Tốc độ thay đổi
    
    # Sentiment trong alert
    negative_ratio = Column(Float)  # % tiêu cực
    dominant_emotion = Column(String(30))
    emotion_distribution = Column(JSON)
    
    # Mô tả
    title = Column(String(512))  # Tiêu đề cảnh báo
    description = Column(Text)  # Mô tả chi tiết
    
    # Sample content
    sample_titles = Column(JSON)  # Mẫu tiêu đề bài viết
    sample_urls = Column(JSON)  # URLs mẫu
    
    # Sources
    top_sources = Column(JSON)  # Nguồn chính
    
    created_at = Column(DateTime, server_default=func.now())


class HashtagStats(BareBaseModel):
    """
    Thống kê Hashtag
    Superset: Hashtag cloud, Trending hashtags
    """
    __tablename__ = "hashtag_stats"
    
    # Thời gian
    period_type = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly
    period_start = Column(Date, index=True)
    period_end = Column(Date)
    
    # Hashtag info
    hashtag = Column(String(256), nullable=False, index=True)
    hashtag_normalized = Column(String(256))  # lowercase, no #
    
    # Thống kê
    mention_count = Column(Integer, default=0, index=True)
    unique_sources = Column(Integer, default=0)
    
    # Trend
    previous_count = Column(Integer, default=0)
    change_percent = Column(Float)  # % thay đổi
    is_trending = Column(Boolean, default=False, index=True)
    is_new = Column(Boolean, default=False)  # Mới xuất hiện trong kỳ
    
    # Sentiment
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    sentiment_score = Column(Float)
    
    # Liên kết
    related_topics = Column(JSON)  # Topics liên quan
    related_categories = Column(JSON)  # Categories liên quan
    co_hashtags = Column(JSON)  # Hashtags thường đi cùng
    
    # Ranking
    rank = Column(Integer)
    
    created_at = Column(DateTime, server_default=func.now())


class ViralContent(BareBaseModel):
    """
    Nội dung viral / hot
    Superset: Viral content dashboard
    """
    __tablename__ = "viral_contents"
    
    # Thời gian
    detected_at = Column(DateTime, server_default=func.now(), index=True)
    period_type = Column(String(20), nullable=False, index=True)
    period_start = Column(Date, index=True)
    
    # Content info
    article_id = Column(Integer, index=True)
    title = Column(String(1024))
    url = Column(String(2048))
    source_domain = Column(String(256), index=True)
    content_snippet = Column(Text)
    
    # Classification
    category = Column(String(100), index=True)
    category_vi = Column(String(100))
    topic_id = Column(Integer, index=True)
    topic_name = Column(String(512))
    
    # Viral metrics
    mention_count = Column(Integer, default=0)  # Số lần được nhắc đến
    share_count = Column(Integer, default=0)  # Ước tính share
    engagement_score = Column(Float)  # Điểm tương tác
    viral_score = Column(Float, index=True)  # Điểm viral tổng hợp
    
    # Sentiment
    sentiment_group = Column(String(20))
    emotion = Column(String(30))
    emotion_vi = Column(String(30))
    
    # Spread info
    first_seen = Column(DateTime)
    spread_velocity = Column(Float)  # Tốc độ lan truyền
    peak_time = Column(DateTime)  # Thời điểm đỉnh
    
    # Related
    hashtags = Column(JSON)
    keywords = Column(JSON)
    
    # Ranking
    rank = Column(Integer)
    is_hot = Column(Boolean, default=False, index=True)
    
    created_at = Column(DateTime, server_default=func.now())


class CategoryTrendStats(BareBaseModel):
    """
    Thống kê xu hướng theo danh mục (Giáo dục, Y tế, Giao thông...)
    Superset: Category breakdown charts
    """
    __tablename__ = "category_trend_stats"
    
    # Thời gian
    period_type = Column(String(20), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date)
    
    # Category info
    category = Column(String(100), nullable=False, index=True)
    category_vi = Column(String(100))
    category_icon = Column(String(10))
    
    # Thống kê
    total_mentions = Column(Integer, default=0)
    unique_sources = Column(Integer, default=0)
    unique_articles = Column(Integer, default=0)
    
    # Sentiment breakdown
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    sentiment_score = Column(Float)
    
    # Emotion breakdown
    emotion_distribution = Column(JSON)
    dominant_emotion = Column(String(30))
    
    # Trend comparison
    previous_mentions = Column(Integer, default=0)
    change_percent = Column(Float)
    is_trending_up = Column(Boolean, default=False)
    is_trending_down = Column(Boolean, default=False)
    
    # Top items trong category
    top_keywords = Column(JSON)
    top_topics = Column(JSON)
    top_sources = Column(JSON)
    hot_articles = Column(JSON)  # Bài viết hot trong category
    
    # Alerts
    has_crisis = Column(Boolean, default=False)
    crisis_topics = Column(JSON)
    
    # Ranking
    rank_by_mention = Column(Integer)
    rank_by_growth = Column(Integer)
    
    created_at = Column(DateTime, server_default=func.now())
