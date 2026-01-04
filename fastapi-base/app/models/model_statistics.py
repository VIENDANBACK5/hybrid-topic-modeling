"""
Statistics Models - Các bảng thống kê cho Superset Dashboard
Tự động tính toán và cập nhật từ data đã làm sạch
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Date, JSON, Boolean
from sqlalchemy.sql import func
from app.models.model_base import BareBaseModel


class TrendReport(BareBaseModel):
    """
    Báo cáo xu hướng thảo luận theo tuần/tháng
    Superset: Line chart xu hướng, Bar chart so sánh
    """
    __tablename__ = "trend_reports"
    
    # Thời gian báo cáo
    period_type = Column(String(20), nullable=False, index=True)  # weekly, monthly
    period_start = Column(Date, nullable=False, index=True)  # Ngày bắt đầu kỳ
    period_end = Column(Date, nullable=False)  # Ngày kết thúc kỳ
    period_label = Column(String(50))  # "Tuần 52/2025", "Tháng 12/2025"
    
    # Tổng quan
    total_mentions = Column(Integer, default=0)  # Tổng số đề cập
    total_sources = Column(Integer, default=0)  # Số nguồn unique
    total_topics = Column(Integer, default=0)  # Số chủ đề
    
    # Phân bố cảm xúc
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    positive_ratio = Column(Float)  # % tích cực
    negative_ratio = Column(Float)  # % tiêu cực
    
    # Phân bố emotion chi tiết (JSON)
    emotion_distribution = Column(JSON)  # {"vui_mừng": 10, "phẫn_nộ": 5, ...}
    
    # So sánh với kỳ trước
    mention_change = Column(Float)  # % thay đổi so với kỳ trước
    sentiment_change = Column(Float)  # Thay đổi sentiment score
    
    # Top keywords trong kỳ
    top_keywords = Column(JSON)  # [{"word": "covid", "count": 100}, ...]
    
    # Top sources trong kỳ
    top_sources = Column(JSON)  # [{"domain": "vnexpress.net", "count": 50}, ...]
    
    created_at = Column(DateTime, server_default=func.now())


class HotTopic(BareBaseModel):
    """
    Chủ đề hot / khủng hoảng theo tuần/tháng
    Superset: Heat map, Alert dashboard
    """
    __tablename__ = "hot_topics"
    
    # Thời gian
    period_type = Column(String(20), nullable=False, index=True)  # weekly, monthly
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False)
    
    # Thông tin topic
    topic_id = Column(Integer, index=True)
    topic_name = Column(String(512), index=True)
    topic_keywords = Column(JSON)  # ["từ khóa 1", "từ khóa 2", ...]
    
    # Mức độ hot
    mention_count = Column(Integer, default=0)  # Số lượng đề cập
    mention_velocity = Column(Float)  # Tốc độ tăng trưởng đề cập
    engagement_score = Column(Float)  # Điểm tương tác (nếu có)
    hot_score = Column(Float, index=True)  # Điểm hot tổng hợp
    
    # Phân loại
    is_hot = Column(Boolean, default=False, index=True)  # Chủ đề hot
    is_crisis = Column(Boolean, default=False, index=True)  # Khủng hoảng (nhiều tiêu cực)
    is_trending_up = Column(Boolean, default=False)  # Đang tăng
    is_trending_down = Column(Boolean, default=False)  # Đang giảm
    
    # Cảm xúc
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    crisis_score = Column(Float)  # Điểm khủng hoảng (% tiêu cực * velocity)
    
    # Top emotions cho topic này
    dominant_emotion = Column(String(30))  # Cảm xúc chính
    emotion_distribution = Column(JSON)
    
    # Sample articles
    sample_titles = Column(JSON)  # 5 tiêu đề mẫu
    
    rank = Column(Integer)  # Thứ hạng trong kỳ
    created_at = Column(DateTime, server_default=func.now())


class KeywordStats(BareBaseModel):
    """
    Thống kê từ khóa cho WordCloud
    Superset: WordCloud, Bar chart từ khóa
    """
    __tablename__ = "keyword_stats"
    
    # Thời gian
    period_type = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly, all_time
    period_start = Column(Date, index=True)
    period_end = Column(Date)
    
    # Từ khóa
    keyword = Column(String(256), nullable=False, index=True)
    keyword_normalized = Column(String(256))  # Lowercase, no accent
    
    # Thống kê
    mention_count = Column(Integer, default=0, index=True)  # Số lần xuất hiện
    document_count = Column(Integer, default=0)  # Số bài chứa từ khóa
    
    # Phân bố cảm xúc của từ khóa
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    sentiment_score = Column(Float)  # Điểm cảm xúc trung bình
    
    # Liên kết chủ đề
    related_topics = Column(JSON)  # [{"topic_id": 1, "topic_name": "...", "count": 10}]
    
    # Nguồn chính
    top_sources = Column(JSON)  # [{"domain": "...", "count": 5}]
    
    # WordCloud weight
    weight = Column(Float)  # Trọng số cho WordCloud (normalized)
    
    created_at = Column(DateTime, server_default=func.now())


class TopicMentionStats(BareBaseModel):
    """
    Thống kê số lượng đề cập theo chủ đề
    Superset: Stacked bar chart, Pie chart
    """
    __tablename__ = "topic_mention_stats"
    
    # Thời gian
    period_type = Column(String(20), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date)
    
    # Chủ đề
    topic_id = Column(Integer, index=True)
    topic_name = Column(String(512), index=True)
    category = Column(String(256), index=True)  # Danh mục lớn
    
    # Thống kê đề cập
    total_mentions = Column(Integer, default=0)
    unique_sources = Column(Integer, default=0)
    
    # Phân bố sentiment (3 nhóm)
    positive_mentions = Column(Integer, default=0)
    negative_mentions = Column(Integer, default=0)
    neutral_mentions = Column(Integer, default=0)
    
    # Phân bố emotion chi tiết (15 loại)
    emotion_breakdown = Column(JSON)  # {"vui_mừng": 5, "phẫn_nộ": 3, ...}
    
    # Điểm số
    sentiment_score = Column(Float)  # (positive - negative) / total
    engagement_score = Column(Float)
    
    # So sánh
    mention_change_pct = Column(Float)  # % thay đổi so với kỳ trước
    sentiment_change = Column(Float)
    
    # Ranking
    rank_by_mention = Column(Integer)
    rank_by_negative = Column(Integer)  # Rank theo tiêu cực (quan trọng cho crisis)
    
    created_at = Column(DateTime, server_default=func.now())


class WebsiteActivityStats(BareBaseModel):
    """
    Thống kê các trang web hoạt động nhiều nhất theo chủ đề
    Superset: Horizontal bar chart, Table
    """
    __tablename__ = "website_activity_stats"
    
    # Thời gian
    period_type = Column(String(20), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date)
    
    # Website info
    domain = Column(String(256), nullable=False, index=True)
    website_name = Column(String(256))  # Tên hiển thị
    website_type = Column(String(50), index=True)  # news, blog, forum, government, etc.
    
    # Chủ đề (NULL = tổng hợp tất cả)
    topic_id = Column(Integer, index=True)
    topic_name = Column(String(512))
    category = Column(String(256), index=True)
    
    # Thống kê
    article_count = Column(Integer, default=0, index=True)
    total_mentions = Column(Integer, default=0)
    
    # Sentiment
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    avg_sentiment_score = Column(Float)
    
    # Emotion distribution
    emotion_distribution = Column(JSON)
    dominant_emotion = Column(String(30))
    
    # Activity metrics
    avg_articles_per_day = Column(Float)
    peak_day = Column(Date)  # Ngày hoạt động nhiều nhất
    
    # Ranking
    rank_overall = Column(Integer)  # Rank tổng
    rank_in_topic = Column(Integer)  # Rank trong chủ đề
    
    created_at = Column(DateTime, server_default=func.now())


class SocialActivityStats(BareBaseModel):
    """
    Thống kê các trang mạng xã hội hoạt động nhiều nhất theo chủ đề
    Superset: Social media dashboard
    """
    __tablename__ = "social_activity_stats"
    
    # Thời gian
    period_type = Column(String(20), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date)
    
    # Social platform
    platform = Column(String(50), nullable=False, index=True)  # facebook, youtube, tiktok, twitter, etc.
    account_id = Column(String(256))  # ID tài khoản
    account_name = Column(String(256), index=True)  # Tên hiển thị
    account_url = Column(String(1024))
    
    # Chủ đề (NULL = tổng hợp)
    topic_id = Column(Integer, index=True)
    topic_name = Column(String(512))
    category = Column(String(256), index=True)
    
    # Thống kê nội dung
    post_count = Column(Integer, default=0, index=True)
    total_mentions = Column(Integer, default=0)
    
    # Engagement (nếu có data)
    total_likes = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)
    avg_engagement = Column(Float)
    
    # Sentiment
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    avg_sentiment_score = Column(Float)
    
    # Emotion distribution
    emotion_distribution = Column(JSON)
    dominant_emotion = Column(String(30))
    
    # Reach estimation
    estimated_reach = Column(Integer)  # Ước tính tiếp cận
    influence_score = Column(Float)  # Điểm ảnh hưởng
    
    # Ranking
    rank_in_platform = Column(Integer)  # Rank trong platform
    rank_in_topic = Column(Integer)  # Rank trong chủ đề
    rank_overall = Column(Integer)
    
    created_at = Column(DateTime, server_default=func.now())


class DailySnapshot(BareBaseModel):
    """
    Snapshot hàng ngày - dùng để vẽ timeline chi tiết
    Superset: Daily line charts, Calendar heatmap
    """
    __tablename__ = "daily_snapshots"
    
    snapshot_date = Column(Date, nullable=False, index=True)
    
    # Tổng quan
    total_articles = Column(Integer, default=0)
    total_sources = Column(Integer, default=0)
    
    # Sentiment tổng
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    
    # Emotion breakdown
    emotion_counts = Column(JSON)  # {"vui_mừng": 10, ...}
    
    # Top topics của ngày
    top_topics = Column(JSON)  # [{"topic_id": 1, "name": "...", "count": 50}]
    
    # Top keywords của ngày
    top_keywords = Column(JSON)  # [{"keyword": "...", "count": 100}]
    
    # Top sources của ngày
    top_sources = Column(JSON)  # [{"domain": "...", "count": 30}]
    
    # Alerts
    crisis_topics = Column(JSON)  # Các topic có dấu hiệu khủng hoảng
    trending_up = Column(JSON)  # Topics đang tăng
    trending_down = Column(JSON)  # Topics đang giảm
    
    created_at = Column(DateTime, server_default=func.now())
