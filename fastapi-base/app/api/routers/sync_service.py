"""
🔄 SYNC SERVICE - API Endpoints để đồng bộ data từ nguồn ngoài

Endpoints:
- POST /sync/trigger - Chạy sync ngay lập tức (one-time)
- POST /sync/schedule - Lên lịch sync tự động
- GET /sync/status - Xem trạng thái sync
- POST /sync/config - Cập nhật config source API
- GET /sync/configs - Xem tất cả configs
- DELETE /sync/config/{id} - Xóa config
- DELETE /sync/clear-data - Xóa data test trong DB
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Security
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import requests
import logging
from enum import Enum

from app.core.database import get_db
from app.core.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["🔄 Data Sync"])


# ============================================
# MODELS & SCHEMAS
# ============================================

class SyncStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncConfigCreate(BaseModel):
    """Config để kết nối tới API nguồn"""
    name: str = Field(..., description="Tên nguồn data (VD: Facebook API, News Portal)")
    source_api_base: str = Field(..., description="Base URL (VD: http://192.168.30.28:8000)")
    endpoint: str = Field(default="/api/articles", description="Endpoint để lấy data")
    enabled: bool = Field(default=True, description="Bật/tắt sync từ nguồn này")
    
    # Sync options
    batch_size: int = Field(default=20, ge=1, le=100)
    skip_duplicates: bool = Field(default=True)
    analyze_sentiment: bool = Field(default=True)
    
    # Auth (nếu cần)
    auth_type: Optional[str] = Field(None, description="bearer, basic, api_key")
    auth_token: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    
    # Extra params
    query_params: Optional[Dict[str, Any]] = None


class SyncConfigResponse(SyncConfigCreate):
    id: int
    created_at: datetime
    last_sync_at: Optional[datetime] = None
    total_synced: int = 0
    
    class Config:
        from_attributes = True


class SyncTriggerRequest(BaseModel):
    """Request để trigger sync thủ công"""
    config_id: Optional[int] = Field(None, description="ID của config (None = dùng config mặc định)")
    source_api_base: Optional[str] = Field(None, description="Override source API base URL")
    endpoint: Optional[str] = Field(None, description="Override endpoint")
    limit: Optional[int] = Field(None, description="Giới hạn số docs (None = all)")
    batch_size: Optional[int] = Field(default=20)
    skip_duplicates: bool = True
    analyze_sentiment: bool = True


class SyncStatusResponse(BaseModel):
    status: SyncStatus
    config_id: Optional[int] = None
    config_name: Optional[str] = None
    source_api: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress
    total_fetched: int = 0
    total_saved: int = 0
    total_skipped: int = 0
    total_sentiment: int = 0
    
    # Error info
    error: Optional[str] = None
    
    # Timing
    elapsed_seconds: Optional[float] = None
    rate_per_second: Optional[float] = None


# ============================================
# IN-MEMORY STATE (có thể chuyển sang Redis)
# ============================================

_sync_state: SyncStatusResponse = SyncStatusResponse(
    status=SyncStatus.IDLE
)

_sync_configs: Dict[int, SyncConfigResponse] = {}
_next_config_id = 1


# ============================================
# HELPER FUNCTIONS
# ============================================

def fetch_from_source_api(
    source_api_base: str,
    endpoint: str,
    limit: Optional[int] = None,
    offset: int = 0,
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    auth_token: Optional[str] = None,
    auth_type: Optional[str] = None
) -> Dict[str, Any]:
    """Lấy data từ API nguồn"""
    url = f"{source_api_base}{endpoint}"
    
    # Build query params
    query_params = params or {}
    if limit:
        query_params['limit'] = limit
    if offset:
        query_params['offset'] = offset
    
    # Build headers
    req_headers = headers or {}
    if auth_token:
        if auth_type == "bearer":
            req_headers['Authorization'] = f"Bearer {auth_token}"
        elif auth_type == "api_key":
            req_headers['X-API-Key'] = auth_token
    
    logger.info(f"📡 Fetching from {url}")
    
    # Retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=query_params, headers=req_headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"Fetch attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"All fetch attempts failed: {e}")
                raise


def transform_document(raw_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Transform document từ API nguồn sang format chuẩn"""
    content = (
        raw_doc.get('content') or 
        raw_doc.get('body') or 
        raw_doc.get('text') or 
        raw_doc.get('description') or
        ""
    )
    
    url = (
        raw_doc.get('url') or 
        raw_doc.get('link') or 
        raw_doc.get('source_url') or
        raw_doc.get('id', f"doc_{hash(str(raw_doc))}")
    )
    
    title = (
        raw_doc.get('title') or 
        raw_doc.get('headline') or
        content[:100] if content else "Untitled"
    )
    
    published = raw_doc.get('published_date') or raw_doc.get('created_at') or raw_doc.get('date')
    
    # Extract engagement
    engagement = {}
    for field in ['likes', 'shares', 'comments', 'views', 'reactions']:
        value = raw_doc.get(field) or raw_doc.get(f"{field}_count")
        if value is not None:
            engagement[field] = value
    
    # Extract social account
    social_account = {}
    for field in ['platform', 'social_platform', 'account_name', 'account_id']:
        if field in raw_doc:
            key = field.replace('social_', '')
            social_account[key] = raw_doc[field]
    
    # Extract location
    location = {}
    if isinstance(raw_doc.get('location'), dict):
        location = raw_doc['location']
    else:
        for field in ['province', 'district', 'ward']:
            if field in raw_doc:
                location[field] = raw_doc[field]
    
    # Build metadata
    metadata = {
        "title": title,
        "published": published,
        "author": raw_doc.get('author'),
        "category": raw_doc.get('category'),
        "tags": raw_doc.get('tags'),
        "images": raw_doc.get('images'),
        "description": raw_doc.get('description'),
        "language": raw_doc.get('language', 'vi'),
    }
    
    if engagement:
        metadata['engagement'] = engagement
    if social_account:
        metadata['social_account'] = social_account
    if location:
        metadata['location'] = location
    
    # Detect source type
    source_type = "web"
    if 'facebook.com' in url or social_account.get('platform') == 'facebook':
        source_type = "facebook"
    elif 'youtube.com' in url or social_account.get('platform') == 'youtube':
        source_type = "youtube"
    elif 'tiktok.com' in url or social_account.get('platform') == 'tiktok':
        source_type = "tiktok"
    elif raw_doc.get('source_type'):
        source_type = raw_doc['source_type']
    
    return {
        "source": source_type,
        "source_id": url,
        "content": content,
        "metadata": metadata
    }


def send_to_ingest_api(
    documents: List[Dict[str, Any]],
    skip_duplicates: bool = True,
    analyze_sentiment: bool = True
) -> Dict[str, Any]:
    """Gửi documents tới API /ingest"""
    from app.api.routers.topic_service import IngestRequest
    from app.models import Article, SentimentAnalysis
    from app.services.sentiment import get_sentiment_analyzer
    from app.services.classification import get_category_classifier
    from app.services.etl.data_normalizer import normalize_and_validate
    
    # Giả lập logic từ ingest endpoint (hoặc gọi trực tiếp)
    # Ở đây tôi sẽ import và gọi trực tiếp thay vì HTTP call
    saved = 0
    skipped = 0
    sentiment_saved = 0
    
    analyzer = get_sentiment_analyzer() if analyze_sentiment else None
    classifier = get_category_classifier()
    
    from app.core.database import SessionLocal
    db = SessionLocal()
    
    try:
        for doc in documents:
            try:
                # Normalize
                normalized, is_valid, errors, warnings = normalize_and_validate(doc)
                if not is_valid:
                    skipped += 1
                    continue
                
                # Check duplicate
                if skip_duplicates:
                    existing = db.query(Article).filter(Article.url == normalized['url']).first()
                    if existing:
                        skipped += 1
                        continue
                
                # Extract metadata
                metadata = normalized['metadata']
                published_date = None
                published_datetime = None
                published_str = metadata.get("published")
                if published_str:
                    try:
                        if isinstance(published_str, (int, float)):
                            published_date = float(published_str)
                            published_datetime = datetime.fromtimestamp(published_date)
                        else:
                            published_datetime = datetime.fromisoformat(str(published_str).replace('Z', '+00:00'))
                            published_date = published_datetime.timestamp()
                    except:
                        pass
                
                # Classification
                classification = classifier.classify(normalized['content'], metadata.get("title"))
                final_category = metadata.get("category") or classification.category
                
                # Extract engagement
                engagement = metadata.get("engagement", {})
                likes = engagement.get("likes", 0)
                shares = engagement.get("shares", 0)
                comments = engagement.get("comments", 0)
                views = engagement.get("views", 0)
                
                engagement_rate = None
                if views > 0:
                    engagement_rate = (likes + shares + comments) / views
                
                social = metadata.get("social_account", {})
                location = metadata.get("location", {})
                
                # Create article
                article = Article(
                    url=normalized['url'],
                    source_type=normalized['source_type'],
                    source=normalized['url'],
                    domain=normalized['domain'],
                    title=metadata.get("title"),
                    content=normalized['content'],
                    summary=metadata.get("description"),
                    author=metadata.get("author"),
                    published_date=published_date,
                    category=final_category,
                    tags=metadata.get("tags"),
                    images=metadata.get("images"),
                    likes_count=likes,
                    shares_count=shares,
                    comments_count=comments,
                    views_count=views,
                    engagement_rate=engagement_rate,
                    social_platform=normalized['platform'],
                    account_name=social.get("account_name"),
                    province=location.get("province"),
                    is_cleaned=True,
                    raw_metadata=metadata
                )
                
                db.add(article)
                db.flush()
                saved += 1
                
                # Sentiment analysis
                if analyzer:
                    result = analyzer.analyze(normalized['content'])
                    sentiment_record = SentimentAnalysis(
                        article_id=article.id,
                        source_url=normalized['url'],
                        source_domain=normalized['domain'],
                        title=metadata.get("title"),
                        emotion=result.emotion,
                        emotion_vi=result.emotion_vi,
                        emotion_icon=result.icon,
                        sentiment_group=result.group,
                        sentiment_group_vi=result.group_vi,
                        confidence=result.confidence,
                        emotion_scores=result.all_scores,
                        category=final_category,
                        published_date=published_datetime,
                        content_snippet=normalized['content'][:200]
                    )
                    db.add(sentiment_record)
                    sentiment_saved += 1
            
            except Exception as e:
                logger.error(f"Error processing document: {e}", exc_info=True)
                skipped += 1
        
        try:
            db.commit()
            logger.info(f"Batch committed: {saved} saved, {skipped} skipped")
        except Exception as e:
            logger.error(f"Failed to commit batch: {e}", exc_info=True)
            db.rollback()
            raise
        
    finally:
        db.close()
    
    return {
        "saved": saved,
        "skipped": skipped,
        "sentiment_analyzed": sentiment_saved
    }


def run_sync_task(
    config: Optional[SyncConfigResponse],
    source_api_base: str,
    endpoint: str,
    limit: Optional[int],
    batch_size: int,
    skip_duplicates: bool,
    analyze_sentiment: bool,
    headers: Optional[Dict] = None,
    auth_token: Optional[str] = None,
    auth_type: Optional[str] = None,
    query_params: Optional[Dict] = None
):
    """Background task để chạy sync"""
    global _sync_state
    
    # Update state
    _sync_state = SyncStatusResponse(
        status=SyncStatus.RUNNING,
        config_id=config.id if config else None,
        config_name=config.name if config else None,
        source_api=source_api_base,
        started_at=datetime.now()
    )
    
    try:
        total_fetched = 0
        total_saved = 0
        total_skipped = 0
        total_sentiment = 0
        offset = 0
        
        import time
        start_time = time.time()
        
        while True:
            # Calculate fetch limit
            fetch_limit = batch_size
            if limit:
                remaining = limit - total_fetched
                if remaining <= 0:
                    break
                fetch_limit = min(batch_size, remaining)
            
            # Fetch from source API
            try:
                data = fetch_from_source_api(
                    source_api_base=source_api_base,
                    endpoint=endpoint,
                    limit=fetch_limit,
                    offset=offset,
                    params=query_params,
                    headers=headers,
                    auth_token=auth_token,
                    auth_type=auth_type
                )
            except Exception as e:
                logger.error(f"Failed to fetch: {e}")
                raise
            
            # Extract documents
            if isinstance(data, dict):
                raw_docs = data.get('data', data.get('items', data.get('results', [])))
                has_more = data.get('has_more', False)
            elif isinstance(data, list):
                raw_docs = data
                has_more = len(raw_docs) == fetch_limit
            else:
                break
            
            if not raw_docs:
                break
            
            # Transform
            transformed_docs = []
            for raw_doc in raw_docs:
                try:
                    transformed = transform_document(raw_doc)
                    transformed_docs.append(transformed)
                except Exception as e:
                    logger.warning(f"Transform failed: {e}")
            
            if not transformed_docs:
                break
            
            # Send to ingest
            result = send_to_ingest_api(
                documents=transformed_docs,
                skip_duplicates=skip_duplicates,
                analyze_sentiment=analyze_sentiment
            )
            
            # Update counters
            total_saved += result.get('saved', 0)
            total_skipped += result.get('skipped', 0)
            total_sentiment += result.get('sentiment_analyzed', 0)
            total_fetched += len(raw_docs)
            offset += len(raw_docs)
            
            # Update state
            elapsed = time.time() - start_time
            _sync_state.total_fetched = total_fetched
            _sync_state.total_saved = total_saved
            _sync_state.total_skipped = total_skipped
            _sync_state.total_sentiment = total_sentiment
            _sync_state.elapsed_seconds = elapsed
            _sync_state.rate_per_second = total_fetched / elapsed if elapsed > 0 else 0
            
            # Check if done
            if not has_more or (limit and total_fetched >= limit):
                break
        
        # Completed
        _sync_state.status = SyncStatus.COMPLETED
        _sync_state.completed_at = datetime.now()
        
        # Update config last sync
        if config:
            config.last_sync_at = datetime.now()
            config.total_synced += total_saved
        
        logger.info(f"✅ Sync completed: fetched={total_fetched}, saved={total_saved}")
        
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}", exc_info=True)
        _sync_state.status = SyncStatus.FAILED
        _sync_state.error = str(e)
        _sync_state.completed_at = datetime.now()


# ============================================
# API ENDPOINTS
# ============================================

@router.post("/trigger", response_model=SyncStatusResponse)
async def trigger_sync(
    request: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Security(verify_api_key)
):
    """
    🚀 TRIGGER SYNC NGAY LẬP TỨC
    
    Chạy sync data từ API nguồn (one-time)
    
    - Có thể dùng config đã lưu (config_id)
    - Hoặc override config trực tiếp
    - Chạy background, không block
    
    Example:
    ```json
    {
      "source_api_base": "http://192.168.30.28:8000",
      "endpoint": "/api/articles",
      "limit": 100,
      "batch_size": 20
    }
    ```
    """
    global _sync_state
    
    # Check if already running
    if _sync_state.status == SyncStatus.RUNNING:
        raise HTTPException(400, "Sync đang chạy, vui lòng đợi hoàn thành")
    
    # Get config
    config = None
    if request.config_id:
        config = _sync_configs.get(request.config_id)
        if not config:
            raise HTTPException(404, f"Config ID {request.config_id} không tồn tại")
        
        if not config.enabled:
            raise HTTPException(400, f"Config '{config.name}' đã bị tắt")
    
    # Determine source API
    source_api_base = request.source_api_base or (config.source_api_base if config else None)
    endpoint = request.endpoint or (config.endpoint if config else "/api/articles")
    
    if not source_api_base:
        raise HTTPException(400, "source_api_base is required")
    
    # Get other configs
    batch_size = request.batch_size or (config.batch_size if config else 20)
    headers = config.headers if config else None
    auth_token = config.auth_token if config else None
    auth_type = config.auth_type if config else None
    query_params = config.query_params if config else None
    
    # Start background task
    background_tasks.add_task(
        run_sync_task,
        config=config,
        source_api_base=source_api_base,
        endpoint=endpoint,
        limit=request.limit,
        batch_size=batch_size,
        skip_duplicates=request.skip_duplicates,
        analyze_sentiment=request.analyze_sentiment,
        headers=headers,
        auth_token=auth_token,
        auth_type=auth_type,
        query_params=query_params
    )
    
    return SyncStatusResponse(
        status=SyncStatus.RUNNING,
        config_id=config.id if config else None,
        config_name=config.name if config else None,
        source_api=source_api_base,
        started_at=datetime.now()
    )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """
    📊 XEM TRẠNG THÁI SYNC HIỆN TẠI
    
    - Đang chạy hay idle?
    - Progress bao nhiêu?
    - Tốc độ xử lý?
    """
    return _sync_state


@router.post("/config", response_model=SyncConfigResponse)
async def create_sync_config(
    config: SyncConfigCreate,
    api_key: str = Security(verify_api_key)
):
    """
    💾 LƯU CONFIG CHO API NGUỒN
    
    Lưu config để tái sử dụng, không cần nhập lại mỗi lần
    
    Example:
    ```json
    {
      "name": "Facebook API",
      "source_api_base": "http://192.168.30.28:8000",
      "endpoint": "/api/posts",
      "enabled": true,
      "batch_size": 50,
      "auth_type": "bearer",
      "auth_token": "your-token-here"
    }
    ```
    """
    global _next_config_id
    
    config_response = SyncConfigResponse(
        id=_next_config_id,
        created_at=datetime.now(),
        **config.dict()
    )
    
    _sync_configs[_next_config_id] = config_response
    _next_config_id += 1
    
    return config_response


@router.get("/configs", response_model=List[SyncConfigResponse])
async def list_sync_configs():
    """
    📋 XEM TẤT CẢ CONFIGS ĐÃ LƯU
    """
    return list(_sync_configs.values())


@router.patch("/config/{config_id}/toggle")
async def toggle_sync_config(config_id: int, enabled: bool):
    """
    🔄 BẬT/TẮT CONFIG
    
    - enabled=true: Bật sync từ nguồn này
    - enabled=false: Tắt (không sync nữa)
    """
    config = _sync_configs.get(config_id)
    if not config:
        raise HTTPException(404, f"Config ID {config_id} không tồn tại")
    
    config.enabled = enabled
    
    return {
        "status": "success",
        "config_id": config_id,
        "enabled": enabled,
        "message": f"Config '{config.name}' đã {'bật' if enabled else 'tắt'}"
    }


@router.delete("/config/{config_id}")
async def delete_sync_config(
    config_id: int,
    api_key: str = Security(verify_api_key)
):
    """
    🗑️ XÓA CONFIG
    """
    if config_id not in _sync_configs:
        raise HTTPException(404, f"Config ID {config_id} không tồn tại")
    
    config = _sync_configs.pop(config_id)
    
    return {
        "status": "success",
        "message": f"Đã xóa config '{config.name}'"
    }


@router.delete("/clear-data")
async def clear_test_data(
    table: Optional[str] = None,
    confirm: bool = False,
    db: Session = Depends(get_db),
    api_key: str = Security(verify_api_key)
):
    """
    🗑️ XÓA DATA TEST TRONG DATABASE
    
    ⚠️ CẢNH BÁO: Xóa vĩnh viễn, không thể khôi phục!
    
    Parameters:
    - table: Tên bảng cụ thể (articles, sentiment_analysis, statistics, etc.)
             Nếu None = xóa TẤT CẢ
    - confirm: PHẢI set = true để xác nhận xóa
    
    Các bảng có thể xóa:
    - articles: Bảng bài viết gốc
    - sentiment_analysis: Bảng phân tích cảm xúc
    - daily_snapshots: Thống kê theo ngày
    - trend_reports: Báo cáo xu hướng
    - hot_topics: Chủ đề nóng
    - keyword_stats: Thống kê từ khóa
    - topic_mentions: Thống kê topic mentions
    - website_stats: Thống kê theo website
    - social_stats: Thống kê social media
    - trend_alerts: Cảnh báo xu hướng
    - hashtag_stats: Thống kê hashtag
    - viral_content: Nội dung viral
    - category_trends: Xu hướng theo danh mục
    - all: XÓA TẤT CẢ
    
    Example:
    ```bash
    # Xóa chỉ bảng articles
    DELETE /sync/clear-data?table=articles&confirm=true
    
    # Xóa tất cả
    DELETE /sync/clear-data?table=all&confirm=true
    ```
    """
    from app.models import (
        Article, 
        SentimentAnalysis,
        DailySnapshot,
        TrendReport,
        HotTopic,
        KeywordStats,
        TopicMentionStats,
        WebsiteActivityStats,
        SocialActivityStats,
        TrendAlert,
        HashtagStats,
        ViralContent,
        CategoryTrendStats
    )
    
    if not confirm:
        raise HTTPException(
            400, 
            "⚠️ Phải set confirm=true để xác nhận xóa data. "
            "Data sẽ bị xóa vĩnh viễn và không thể khôi phục!"
        )
    
    # Map table names
    table_map = {
        "articles": Article,
        "sentiment_analysis": SentimentAnalysis,
        "daily_snapshots": DailySnapshot,
        "trend_reports": TrendReport,
        "hot_topics": HotTopic,
        "keyword_stats": KeywordStats,
        "topic_mentions": TopicMentionStats,
        "website_stats": WebsiteActivityStats,
        "social_stats": SocialActivityStats,
        "trend_alerts": TrendAlert,
        "hashtag_stats": HashtagStats,
        "viral_content": ViralContent,
        "category_trends": CategoryTrendStats,
    }
    
    deleted = {}
    
    try:
        if table and table != "all":
            # Xóa bảng cụ thể
            if table not in table_map:
                raise HTTPException(
                    400, 
                    f"Bảng '{table}' không hợp lệ. "
                    f"Các bảng có thể xóa: {', '.join(table_map.keys())}, all"
                )
            
            model = table_map[table]
            count = db.query(model).count()
            db.query(model).delete()
            db.commit()
            
            deleted[table] = count
            logger.warning(f"🗑️ Deleted {count} rows from {table}")
            
            return {
                "status": "success",
                "message": f"Đã xóa {count} rows từ bảng '{table}'",
                "deleted": deleted
            }
        
        else:
            # Xóa TẤT CẢ (theo thứ tự để tránh foreign key error)
            # Xóa theo thứ tự: statistics tables trước, sau đó sentiment, cuối cùng articles
            
            order = [
                # Statistics tables (không có foreign key)
                "trend_alerts",
                "hashtag_stats",
                "viral_content",
                "category_trends",
                "daily_snapshots",
                "trend_reports",
                "hot_topics",
                "keyword_stats",
                "topic_mentions",
                "website_stats",
                "social_stats",
                # Main tables (có foreign key)
                "sentiment_analysis",  # Foreign key to articles
                "articles",  # Base table
            ]
            
            for table_name in order:
                if table_name in table_map:
                    model = table_map[table_name]
                    try:
                        count = db.query(model).count()
                        if count > 0:
                            db.query(model).delete()
                            deleted[table_name] = count
                            logger.warning(f"🗑️ Deleted {count} rows from {table_name}")
                    except Exception as e:
                        logger.error(f"Error deleting {table_name}: {e}")
                        # Continue với bảng khác
            
            db.commit()
            
            total_deleted = sum(deleted.values())
            
            return {
                "status": "success",
                "message": f"Đã xóa TOÀN BỘ data test ({total_deleted} rows)",
                "deleted": deleted,
                "total_rows_deleted": total_deleted
            }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to clear data: {e}", exc_info=True)
        raise HTTPException(500, f"Lỗi khi xóa data: {str(e)}")


@router.get("/health")
async def health_check():
    """
    🏥 HEALTH CHECK - Kiểm tra trạng thái hệ thống
    """
    from sqlalchemy import text
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check database
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"
    
    # Check sentiment analyzer
    try:
        from app.services.sentiment import get_sentiment_analyzer
        analyzer = get_sentiment_analyzer()
        health_status["checks"]["sentiment_analyzer"] = "ok"
    except Exception as e:
        health_status["checks"]["sentiment_analyzer"] = f"error: {str(e)}"
    
    # Check sync status
    health_status["checks"]["sync_service"] = _sync_state.status.value
    
    return health_status


@router.get("/db-stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """
    📊 XEM SỐ LƯỢNG DATA TRONG CÁC BẢNG
    
    Kiểm tra có bao nhiêu rows trong mỗi bảng trước khi xóa
    """
    from app.models import (
        Article, 
        SentimentAnalysis,
        DailySnapshot,
        TrendReport,
        HotTopic,
        KeywordStats,
        TopicMentionStats,
        WebsiteActivityStats,
        SocialActivityStats,
        TrendAlert,
        HashtagStats,
        ViralContent,
        CategoryTrendStats
    )
    
    stats = {}
    total = 0
    
    tables = {
        "articles": Article,
        "sentiment_analysis": SentimentAnalysis,
        "daily_snapshots": DailySnapshot,
        "trend_reports": TrendReport,
        "hot_topics": HotTopic,
        "keyword_stats": KeywordStats,
        "topic_mentions": TopicMentionStats,
        "website_stats": WebsiteActivityStats,
        "social_stats": SocialActivityStats,
        "trend_alerts": TrendAlert,
        "hashtag_stats": HashtagStats,
        "viral_content": ViralContent,
        "category_trends": CategoryTrendStats,
    }
    
    for table_name, model in tables.items():
        try:
            count = db.query(model).count()
            stats[table_name] = count
            total += count
        except Exception as e:
            stats[table_name] = f"Error: {str(e)}"
    
    return {
        "status": "success",
        "tables": stats,
        "total_rows": total
    }
