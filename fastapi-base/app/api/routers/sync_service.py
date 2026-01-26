"""
SYNC SERVICE - API Endpoints de dong bo data tu nguon ngoai

Endpoints:
- POST /sync/trigger - Chay sync ngay lap tuc (one-time)
- GET /sync/status - Xem trang thai sync
- DELETE /sync/clear-data - Xoa data test trong DB
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Security
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import requests
import logging
import time
from enum import Enum

from app.core.database import get_db
from app.core.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["Sync Service"])


# ============================================
# MODELS & SCHEMAS
# ============================================

class SyncStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncTriggerRequest(BaseModel):
    """Request de trigger sync thu cong"""
    source_api_base: str = Field(..., description="Base URL (VD: http://192.168.30.28:8548)")
    endpoint: str = Field(default="/api/articles", description="Endpoint de lay data")
    limit: Optional[int] = Field(None, description="Gioi han so docs (None = all)")
    batch_size: int = Field(default=20, ge=1, le=100)
    skip_duplicates: bool = True
    analyze_sentiment: bool = True
    headers: Optional[Dict[str, str]] = None
    auth_token: Optional[str] = None
    auth_type: Optional[str] = Field(None, description="bearer, basic, api_key")
    query_params: Optional[Dict[str, Any]] = None


class SyncStatusResponse(BaseModel):
    status: SyncStatus
    source_api: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_fetched: int = 0
    total_saved: int = 0
    total_skipped: int = 0
    total_sentiment: int = 0
    error: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    rate_per_second: Optional[float] = None


# ============================================
# IN-MEMORY STATE
# ============================================

_sync_state: SyncStatusResponse = SyncStatusResponse(status=SyncStatus.IDLE)


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
    """Lay data tu API nguon"""
    url = f"{source_api_base}{endpoint}"
    
    query_params = params or {}
    if limit:
        query_params['limit'] = limit
    if offset:
        query_params['offset'] = offset
    
    req_headers = headers or {}
    if auth_token:
        if auth_type == "bearer":
            req_headers['Authorization'] = f"Bearer {auth_token}"
        elif auth_type == "api_key":
            req_headers['X-API-Key'] = auth_token
    
    logger.info(f"Fetching from {url}")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=query_params, headers=req_headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"Fetch attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(2 ** attempt)
            else:
                logger.error(f"All fetch attempts failed: {e}")
                raise


def transform_document(raw_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Transform document tu API nguon sang format chuan"""
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
    
    engagement = {}
    for field in ['likes', 'shares', 'comments', 'views', 'reactions']:
        value = raw_doc.get(field) or raw_doc.get(f"{field}_count")
        if value is not None:
            engagement[field] = value
    
    social_account = {}
    for field in ['platform', 'social_platform', 'account_name', 'account_id']:
        if field in raw_doc:
            key = field.replace('social_', '')
            social_account[key] = raw_doc[field]
    
    location = {}
    if isinstance(raw_doc.get('location'), dict):
        location = raw_doc['location']
    else:
        for field in ['province', 'district', 'ward']:
            if field in raw_doc:
                location[field] = raw_doc[field]
    
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
    """Gui documents toi API /ingest"""
    from app.models import Article, SentimentAnalysis
    from app.services.sentiment import get_sentiment_analyzer
    from app.services.classification import get_category_classifier
    from app.services.etl.data_normalizer import normalize_and_validate
    from app.core.database import SessionLocal
    from app.utils.domain_utils import ensure_domain
    
    saved = 0
    skipped = 0
    sentiment_saved = 0
    
    analyzer = get_sentiment_analyzer() if analyze_sentiment else None
    classifier = get_category_classifier()
    
    db = SessionLocal()
    
    try:
        for doc in documents:
            try:
                normalized, is_valid, errors, warnings = normalize_and_validate(doc)
                if not is_valid:
                    skipped += 1
                    continue
                
                if skip_duplicates:
                    existing = db.query(Article).filter(Article.url == normalized['url']).first()
                    if existing:
                        skipped += 1
                        continue
                
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
                
                classification = classifier.classify(normalized['content'], metadata.get("title"))
                final_category = metadata.get("category") or classification.category
                
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
                
                # Ensure domain is filled
                article_data = {
                    'url': normalized['url'],
                    'source': normalized['url'],
                    'domain': normalized['domain'],
                    'social_platform': normalized['platform'],
                    'account_name': social.get("account_name")
                }
                article_data = ensure_domain(article_data)
                
                article = Article(
                    url=article_data['url'],
                    source_type=normalized['source_type'],
                    source=article_data['source'],
                    domain=article_data['domain'],
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
    """Background task de chay sync"""
    global _sync_state
    
    _sync_state = SyncStatusResponse(
        status=SyncStatus.RUNNING,
        source_api=source_api_base,
        started_at=datetime.now()
    )
    
    try:
        total_fetched = 0
        total_saved = 0
        total_skipped = 0
        total_sentiment = 0
        offset = 0
        
        start_time = time.time()
        
        while True:
            fetch_limit = batch_size
            if limit:
                remaining = limit - total_fetched
                if remaining <= 0:
                    break
                fetch_limit = min(batch_size, remaining)
            
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
            
            transformed_docs = []
            for raw_doc in raw_docs:
                try:
                    transformed = transform_document(raw_doc)
                    transformed_docs.append(transformed)
                except Exception as e:
                    logger.warning(f"Transform failed: {e}")
            
            if not transformed_docs:
                break
            
            result = send_to_ingest_api(
                documents=transformed_docs,
                skip_duplicates=skip_duplicates,
                analyze_sentiment=analyze_sentiment
            )
            
            total_saved += result.get('saved', 0)
            total_skipped += result.get('skipped', 0)
            total_sentiment += result.get('sentiment_analyzed', 0)
            total_fetched += len(raw_docs)
            offset += len(raw_docs)
            
            elapsed = time.time() - start_time
            _sync_state.total_fetched = total_fetched
            _sync_state.total_saved = total_saved
            _sync_state.total_skipped = total_skipped
            _sync_state.total_sentiment = total_sentiment
            _sync_state.elapsed_seconds = elapsed
            _sync_state.rate_per_second = total_fetched / elapsed if elapsed > 0 else 0
            
            if not has_more or (limit and total_fetched >= limit):
                break
        
        _sync_state.status = SyncStatus.COMPLETED
        _sync_state.completed_at = datetime.now()
        
        logger.info(f"Sync completed: fetched={total_fetched}, saved={total_saved}")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        _sync_state.status = SyncStatus.FAILED
        _sync_state.error = str(e)
        _sync_state.completed_at = datetime.now()


# ============================================
# API ENDPOINTS (3 endpoints)
# ============================================

@router.post("/trigger", response_model=SyncStatusResponse)
async def trigger_sync(
    request: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Security(verify_api_key)
):
    """
    TRIGGER SYNC NGAY LAP TUC
    
    Chay sync data tu API nguon (one-time)
    - Chay background, khong block
    
    Example:
    ```json
    {
      "source_api_base": "http://192.168.30.28:8548",
      "endpoint": "/api/articles",
      "limit": 100,
      "batch_size": 20
    }
    ```
    """
    global _sync_state
    
    if _sync_state.status == SyncStatus.RUNNING:
        raise HTTPException(400, "Sync dang chay, vui long doi hoan thanh")
    
    if not request.source_api_base:
        raise HTTPException(400, "source_api_base is required")
    
    background_tasks.add_task(
        run_sync_task,
        source_api_base=request.source_api_base,
        endpoint=request.endpoint,
        limit=request.limit,
        batch_size=request.batch_size,
        skip_duplicates=request.skip_duplicates,
        analyze_sentiment=request.analyze_sentiment,
        headers=request.headers,
        auth_token=request.auth_token,
        auth_type=request.auth_type,
        query_params=request.query_params
    )
    
    return SyncStatusResponse(
        status=SyncStatus.RUNNING,
        source_api=request.source_api_base,
        started_at=datetime.now()
    )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """
    XEM TRANG THAI SYNC HIEN TAI
    
    - Dang chay hay idle?
    - Progress bao nhieu?
    - Toc do xu ly?
    """
    return _sync_state


@router.delete("/clear-data")
async def clear_test_data(
    table: Optional[str] = None,
    confirm: bool = False,
    db: Session = Depends(get_db),
    api_key: str = Security(verify_api_key)
):
    """
    XOA DATA TEST TRONG DATABASE
    
    CANH BAO: Xoa vinh vien, khong the khoi phuc!
    
    Parameters:
    - table: Ten bang cu the (articles, sentiment_analysis, etc.)
             Neu None = xoa TAT CA
    - confirm: PHAI set = true de xac nhan xoa
    
    Cac bang co the xoa:
    - articles: Bang bai viet goc
    - sentiment_analysis: Bang phan tich cam xuc
    - daily_snapshots: Thong ke theo ngay
    - trend_reports: Bao cao xu huong
    - hot_topics: Chu de nong
    - keyword_stats: Thong ke tu khoa
    - topic_mentions: Thong ke topic mentions
    - website_stats: Thong ke theo website
    - social_stats: Thong ke social media
    - trend_alerts: Canh bao xu huong
    - hashtag_stats: Thong ke hashtag
    - viral_content: Noi dung viral
    - category_trends: Xu huong theo danh muc
    - all: XOA TAT CA
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
            "Phai set confirm=true de xac nhan xoa data. "
            "Data se bi xoa vinh vien va khong the khoi phuc!"
        )
    
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
            if table not in table_map:
                raise HTTPException(
                    400, 
                    f"Bang '{table}' khong hop le. "
                    f"Cac bang co the xoa: {', '.join(table_map.keys())}, all"
                )
            
            model = table_map[table]
            count = db.query(model).count()
            db.query(model).delete()
            db.commit()
            
            deleted[table] = count
            logger.warning(f"Deleted {count} rows from {table}")
            
            return {
                "status": "success",
                "message": f"Da xoa {count} rows tu bang '{table}'",
                "deleted": deleted
            }
        
        else:
            order = [
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
                "sentiment_analysis",
                "articles",
            ]
            
            for table_name in order:
                if table_name in table_map:
                    model = table_map[table_name]
                    try:
                        count = db.query(model).count()
                        if count > 0:
                            db.query(model).delete()
                            deleted[table_name] = count
                            logger.warning(f"Deleted {count} rows from {table_name}")
                    except Exception as e:
                        logger.error(f"Error deleting {table_name}: {e}")
            
            db.commit()
            
            total_deleted = sum(deleted.values())
            
            return {
                "status": "success",
                "message": f"Da xoa TOAN BO data test ({total_deleted} rows)",
                "deleted": deleted,
                "total_rows_deleted": total_deleted
            }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to clear data: {e}", exc_info=True)
        raise HTTPException(500, f"Loi khi xoa data: {str(e)}")
