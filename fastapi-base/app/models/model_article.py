from sqlalchemy import Column, Integer, String, Text, Float, Boolean, JSON
from app.models.model_base import BareBaseModel


class Article(BareBaseModel):
    """Model lưu các bài viết đã crawl"""
    __tablename__ = "articles"

    # Thông tin nguồn
    url = Column(String(2048), unique=True, nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # web, rss, file, api
    source = Column(String(512), nullable=False, index=True)  # URL gốc hoặc source name
    domain = Column(String(256), index=True)  # baohungyen.vn, vnexpress.net, etc.
    
    # Nội dung
    title = Column(String(1024))
    content = Column(Text)
    summary = Column(Text)
    author = Column(String(256))
    published_date = Column(Float)  # timestamp
    
    # Metadata
    category = Column(String(256), index=True)
    tags = Column(JSON)  # List[str]
    images = Column(JSON)  # List[str]
    videos = Column(JSON)  # List[str]
    
    # === ENGAGEMENT METRICS ===
    likes_count = Column(Integer, default=0)  # Số lượt thích
    shares_count = Column(Integer, default=0)  # Số lượt chia sẻ
    comments_count = Column(Integer, default=0)  # Số bình luận
    views_count = Column(Integer, default=0)  # Số lượt xem
    reactions = Column(JSON)  # {"like": 100, "love": 50, "haha": 10, "wow": 5, "sad": 3, "angry": 2}
    engagement_rate = Column(Float)  # (likes + shares + comments) / views
    
    # === SOCIAL ACCOUNT INFO ===
    social_platform = Column(String(50), index=True)  # facebook, tiktok, youtube, twitter, instagram
    account_id = Column(String(256))  # ID tài khoản/page
    account_name = Column(String(512))  # Tên hiển thị
    account_url = Column(String(1024))  # Link tài khoản
    account_type = Column(String(50))  # page, profile, group, channel
    account_followers = Column(Integer)  # Số followers/subscribers
    
    # === POST METADATA ===
    post_id = Column(String(256), index=True)  # ID bài post (FB post ID, TikTok video ID, etc.)
    post_type = Column(String(50))  # status, photo, video, link, article, livestream
    post_language = Column(String(10))  # vi, en, etc.
    
    # === LOCATION DATA ===
    province = Column(String(100), index=True)  # Tỉnh/Thành phố
    district = Column(String(100))  # Quận/Huyện
    ward = Column(String(100))  # Phường/Xã
    location_text = Column(String(512))  # Raw location text
    coordinates = Column(JSON)  # {"lat": 20.6, "lon": 106.1}
    
    # Xử lý
    is_cleaned = Column(Boolean, default=False)
    is_deduped = Column(Boolean, default=False)
    word_count = Column(Integer)
    
    # Topic modeling
    topic_id = Column(Integer, index=True, nullable=True)
    topic_name = Column(String(512), nullable=True)
    topic_probability = Column(Float, nullable=True)
    
    # Crawl metadata
    crawl_params = Column(JSON)  # params used for crawling
    raw_metadata = Column(JSON)  # original metadata from crawler
