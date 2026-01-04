"""
Topic Modeling & Sentiment Analysis Service API
Nhận data từ BE khác → Phân tích Sentiment + Phân loại chủ đề + Tự động cập nhật thống kê → Lưu DB

FLOW TỰ ĐỘNG:
1. POST /ingest nhận data
2. Phân tích sentiment (15 sắc thái)
3. Phân loại chủ đề (Giáo dục, Y tế, Giao thông, Hành chính công...)
4. Lưu vào sentiment_analysis
5. TỰ ĐỘNG cập nhật các bảng thống kê cho Superset:
   - trend_reports (xu hướng tuần/tháng)
   - hot_topics (chủ đề hot/khủng hoảng)
   - keyword_stats (từ khóa WordCloud)
   - topic_mention_stats (đề cập theo chủ đề)
   - website_activity_stats (website hoạt động)
   - social_activity_stats (mạng xã hội)
   - daily_snapshots (snapshot hàng ngày)
   - trend_alerts (cảnh báo đột biến/khủng hoảng)
   - hashtag_stats (thống kê hashtag)
   - viral_contents (nội dung hot/viral)
   - category_trend_stats (xu hướng theo danh mục)

Superset chỉ cần connect DB và query các bảng thống kê.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.core.database import get_db
from app.models.model_article import Article
from app.models.model_sentiment import SentimentAnalysis
from app.services.topic.model import TopicModel
from app.services.sentiment.sentiment_service import get_sentiment_analyzer
from app.services.classification import get_category_classifier
import logging
import threading

logger = logging.getLogger(__name__)
router = APIRouter()

# Training lock
_training_lock = threading.Lock()
_training_status = {"is_training": False, "started_at": None}

# Lazy load
_topic_model = None

def get_topic_model():
    global _topic_model
    if _topic_model is None:
        _topic_model = TopicModel()
    return _topic_model


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class DocumentInput(BaseModel):
    """Schema cho mỗi document từ BE"""
    source: str = "web"
    source_id: str  # URL hoặc unique ID
    content: str  # Nội dung đã clean
    raw_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v or len(v.strip()) < 20:
            raise ValueError('Content phải có ít nhất 20 ký tự')
        return v.strip()


class IngestRequest(BaseModel):
    """Request nhận data - tự động phân tích sentiment"""
    documents: List[DocumentInput]
    skip_duplicates: bool = True
    analyze_sentiment: bool = True  # Mặc định phân tích sentiment


class TrainRequest(BaseModel):
    """Request train topic model"""
    min_topic_size: int = 10
    use_vietnamese_tokenizer: bool = True
    enable_topicgpt: bool = False


# ============================================
# API ENDPOINTS
# ============================================

@router.post("/ingest")
async def ingest_documents(request: IngestRequest, db: Session = Depends(get_db)):
    """
    📥 NHẬN DATA + PHÂN TÍCH SENTIMENT
    
    Nhận documents từ BE khác → Phân tích cảm xúc + Phân loại chủ đề → Lưu vào DB
    
    - Lưu articles vào bảng `articles`
    - Phân loại vào danh mục (Giáo dục, Y tế, Giao thông...)
    - Lưu kết quả sentiment vào bảng `sentiment_analysis` (cho Superset)
    - TỰ ĐỘNG cập nhật thống kê và phân tích xu hướng
    
    Input:
    ```json
    {
        "documents": [
            {
                "source": "web",
                "source_id": "https://example.com/article-123",
                "content": "nội dung đã clean...",
                "metadata": {"title": "...", "published": "2025-12-30"}
            }
        ],
        "skip_duplicates": true,
        "analyze_sentiment": true
    }
    ```
    """
    try:
        saved = 0
        skipped = 0
        sentiment_saved = 0
        errors = []
        
        # Get analyzers
        analyzer = get_sentiment_analyzer() if request.analyze_sentiment else None
        classifier = get_category_classifier()
        
        # Import normalizer
        from app.services.etl.data_normalizer import normalize_and_validate
        
        for doc in request.documents:
            try:
                # === STEP 1: NORMALIZE & VALIDATE ===
                doc_dict = {
                    "source": doc.source,
                    "source_id": doc.source_id,
                    "content": doc.content,
                    "metadata": doc.metadata or {}
                }
                
                normalized, is_valid, norm_errors, warnings = normalize_and_validate(doc_dict)
                
                # Log warnings
                if warnings:
                    logger.warning(f"Normalization warnings for {doc.source_id}: {warnings}")
                
                # Skip if invalid
                if not is_valid:
                    errors.append({
                        "url": doc.source_id,
                        "errors": norm_errors
                    })
                    skipped += 1
                    continue
                
                # === STEP 2: CHECK DUPLICATE ===
                if request.skip_duplicates:
                    existing = db.query(Article).filter(
                        Article.url == normalized['url']
                    ).first()
                    if existing:
                        skipped += 1
                        continue
                
                # === STEP 3: EXTRACT FROM NORMALIZED DATA ===
                metadata = normalized['metadata']
                
                # Parse published date
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
                
                # === STEP 4: AUTO CLASSIFICATION ===
                classification = classifier.classify(normalized['content'], metadata.get("title"))
                auto_category = classification.category
                
                # Use metadata category if exists, otherwise use auto
                final_category = metadata.get("category") or auto_category
                
                # === STEP 5: EXTRACT ENGAGEMENT ===
                engagement = metadata.get("engagement", {})
                reactions = engagement.get("reactions", {})
                likes = engagement.get("likes", 0)
                shares = engagement.get("shares", 0)
                comments = engagement.get("comments", 0)
                views = engagement.get("views", 0)
                
                # Calculate engagement rate
                engagement_rate = None
                if views > 0:
                    engagement_rate = (likes + shares + comments) / views
                
                # === STEP 6: EXTRACT SOCIAL & LOCATION ===
                social = metadata.get("social_account", {})
                location = metadata.get("location", {})
                
                # === STEP 7: CREATE ARTICLE WITH NORMALIZED DATA ===
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
                    # Engagement (already normalized)
                    likes_count=likes,
                    shares_count=shares,
                    comments_count=comments,
                    views_count=views,
                    reactions=reactions if reactions else None,
                    engagement_rate=engagement_rate,
                    # Social account (normalized with platform auto-detected)
                    social_platform=normalized['platform'],
                    account_id=social.get("account_id"),
                    account_name=social.get("account_name"),
                    account_url=social.get("account_url"),
                    account_type=social.get("account_type"),
                    account_followers=social.get("followers"),
                    # Post metadata
                    post_id=metadata.get("post_id"),
                    post_type=metadata.get("post_type"),
                    post_language=metadata.get("language", "vi"),
                    # Location (normalized province name)
                    province=location.get("province"),
                    district=location.get("district"),
                    ward=location.get("ward"),
                    location_text=metadata.get("location_text") or location.get("location_text"),
                    coordinates=location.get("coordinates"),
                    # Processing
                    is_cleaned=True,
                    raw_metadata=metadata
                )
                
                db.add(article)
                db.flush()  # Get article.id
                saved += 1
                
                # === STEP 8: SENTIMENT ANALYSIS ===
                if analyzer:
                    result = analyzer.analyze(normalized['content'])
                    
                    # Lưu vào bảng sentiment_analysis cho Superset
                    sentiment_record = SentimentAnalysis(
                        article_id=article.id,
                        source_url=normalized['url'],
                        source_domain=normalized['domain'],
                        title=metadata.get("title"),
                        # Sắc thái chi tiết
                        emotion=result.emotion,
                        emotion_vi=result.emotion_vi,
                        emotion_icon=result.icon,
                        # Group tổng quát
                        sentiment_group=result.group,
                        sentiment_group_vi=result.group_vi,
                        confidence=result.confidence,
                        # Scores cho tất cả emotions
                        emotion_scores=result.all_scores,
                        # Category đã phân loại tự động
                        category=final_category,
                        published_date=published_datetime,
                        content_snippet=normalized['content'][:200] if normalized['content'] else None
                    )
                    db.add(sentiment_record)
                    sentiment_saved += 1
                
            except Exception as e:
                errors.append(f"{doc.source_id}: {str(e)}")
        
        db.commit()
        
        # === TỰ ĐỘNG CẬP NHẬT THỐNG KÊ + PHÂN TÍCH XU HƯỚNG ===
        stats_updated = []
        trends_updated = []
        
        if saved > 0:
            try:
                from app.services.statistics import get_statistics_service
                from app.services.trends import get_trend_service
                
                stats_service = get_statistics_service(db)
                trend_service = get_trend_service(db)
                
                # 1. Cập nhật daily snapshot
                stats_service.create_daily_snapshot()
                stats_updated.append("daily_snapshot")
                
                # 2. Cập nhật weekly stats (nếu có đủ data)
                if db.query(SentimentAnalysis).count() >= 10:
                    stats_service.calculate_trend_report("weekly")
                    stats_service.calculate_hot_topics("weekly")
                    stats_service.calculate_keyword_stats("weekly")
                    stats_service.calculate_topic_mention_stats("weekly")
                    stats_service.calculate_website_stats("weekly")
                    stats_service.calculate_social_stats("weekly")
                    stats_updated.append("weekly_stats")
                
                # 3. Phát hiện xu hướng đột biến/khủng hoảng
                alerts = trend_service.detect_trend_alerts(hours_back=24)
                if alerts:
                    trends_updated.append(f"alerts ({len(alerts)})")
                
                # 4. Thống kê hashtag
                hashtags = trend_service.calculate_hashtag_stats("daily")
                if hashtags:
                    trends_updated.append(f"hashtags ({len(hashtags)})")
                
                # 5. Phát hiện viral content
                viral = trend_service.detect_viral_content("daily")
                if viral:
                    trends_updated.append(f"viral ({len(viral)})")
                
                # 6. Thống kê theo danh mục
                categories = trend_service.calculate_category_trends("daily")
                if categories:
                    trends_updated.append(f"categories ({len(categories)})")
                
                db.commit()
                logger.info(f"Auto-updated: stats={stats_updated}, trends={trends_updated}")
                
            except Exception as e:
                db.rollback()
                logger.warning(f"Could not auto-update: {e}")
        
        # Get article count in separate try/catch
        try:
            article_count = db.query(Article).count()
        except:
            article_count = None
        
        return {
            "status": "success",
            "saved": saved,
            "skipped": skipped,
            "sentiment_analyzed": sentiment_saved,
            "stats_updated": stats_updated,
            "trends_updated": trends_updated,
            "errors": errors[:10] if errors else [],
            "total_in_db": article_count
        }
        
    except Exception as e:
        db.rollback()  # Rollback failed transaction
        logger.error(f"Ingest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train")
async def train_topics(request: TrainRequest, db: Session = Depends(get_db)):
    """
    🤖 TRAIN TOPIC MODEL
    
    Train BERTopic từ data trong DB, cập nhật topic_id vào articles và sentiment_analysis
    """
    global _training_status
    
    if not _training_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409, 
            detail=f"Training đang chạy từ {_training_status.get('started_at')}"
        )
    
    try:
        _training_status = {"is_training": True, "started_at": datetime.now().isoformat()}
        
        # Get articles
        articles = db.query(Article).filter(Article.content.isnot(None)).all()
        
        if len(articles) < 10:
            raise HTTPException(status_code=400, detail=f"Cần ít nhất 10 documents, hiện có {len(articles)}")
        
        # Create and train model
        topic_model = TopicModel(
            min_topic_size=request.min_topic_size,
            use_vietnamese_tokenizer=request.use_vietnamese_tokenizer,
            enable_topicgpt=request.enable_topicgpt
        )
        
        documents = [a.content for a in articles]
        topics, probs = topic_model.fit(documents)
        topic_info = topic_model.get_topic_info()
        
        # Update articles
        for i, (topic_id, article) in enumerate(zip(topics, articles)):
            article.topic_id = int(topic_id)
            article.topic_probability = float(probs[i].max()) if probs[i] is not None else 0.0
            
            topic_data = next((t for t in topic_info['topics'] if t['topic_id'] == topic_id), None)
            if topic_data:
                keywords = [w['word'] for w in topic_data.get('words', [])[:3]]
                article.topic_name = " - ".join(keywords)
            
            # Update sentiment_analysis table too
            sentiment_record = db.query(SentimentAnalysis).filter(
                SentimentAnalysis.article_id == article.id
            ).first()
            if sentiment_record:
                sentiment_record.topic_id = article.topic_id
                sentiment_record.topic_name = article.topic_name
        
        db.commit()
        topic_model.save("default_model")
        
        return {
            "status": "success",
            "total_documents": len(documents),
            "total_topics": len(topic_info['topics']),
            "topics": topic_info['topics']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Train error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _training_status = {"is_training": False, "started_at": None}
        _training_lock.release()


@router.get("/status")
async def get_status(db: Session = Depends(get_db)):
    """📊 XEM TRẠNG THÁI"""
    result = {
        "status": "ok",
        "database": {"connected": False},
        "training": _training_status
    }
    
    try:
        db.execute(text("SELECT 1"))
        result["database"]["connected"] = True
        result["database"]["total_articles"] = db.query(Article).count()
        result["database"]["total_sentiments"] = db.query(SentimentAnalysis).count()
        
        # Sentiment distribution
        from sqlalchemy import func
        sentiment_dist = db.query(
            SentimentAnalysis.sentiment,
            func.count(SentimentAnalysis.id)
        ).group_by(SentimentAnalysis.sentiment).all()
        
        result["sentiment_distribution"] = {s: c for s, c in sentiment_dist}
        
    except Exception as e:
        result["status"] = "database_error"
        result["error"] = str(e)[:100]
    
    return result


@router.get("/topics")
async def get_topics(db: Session = Depends(get_db)):
    """📋 XEM DANH SÁCH TOPICS"""
    from sqlalchemy import func
    
    results = db.query(
        Article.topic_id,
        Article.topic_name,
        func.count(Article.id).label('count')
    ).filter(
        Article.topic_id.isnot(None)
    ).group_by(
        Article.topic_id, Article.topic_name
    ).order_by(
        func.count(Article.id).desc()
    ).all()
    
    return {
        "total_topics": len(results),
        "topics": [{"topic_id": r.topic_id, "name": r.topic_name, "count": r.count} for r in results]
    }


@router.get("/topics-over-time")
async def get_topics_over_time(
    nr_bins: int = 10,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """
    📊 XEM TOPICS THEO THỜI GIAN (Topics Over Time)
    
    Trả về sự phân bố topics qua các khoảng thời gian để vẽ biểu đồ xu hướng.
    
    Args:
        nr_bins: Số khoảng thời gian (default: 10)
        limit: Số documents tối đa (default: 1000)
    
    Returns:
        Dict với timeline của mỗi topic
    """
    try:
        # Get articles with timestamps
        query = text("""
            SELECT id, title, content, published_datetime
            FROM articles
            WHERE content IS NOT NULL 
            AND LENGTH(content) > 100
            AND published_datetime IS NOT NULL
            ORDER BY published_datetime DESC
            LIMIT :limit
        """)
        
        rows = db.execute(query, {"limit": limit}).fetchall()
        
        if not rows:
            return {
                "status": "error",
                "message": "No articles with timestamps found"
            }
        
        # Prepare data
        documents = []
        timestamps = []
        
        for row in rows:
            article_id, title, content, pub_datetime = row
            doc = f"{title or ''}\n{content or ''}"
            documents.append(doc)
            timestamps.append(pub_datetime)
        
        # Get or train topic model
        topic_model = get_topic_model()
        
        if topic_model.topic_model is None:
            # Need to fit first
            logger.info("🔧 Topic model not fitted, fitting now...")
            topic_model.fit(documents, db=None, save_to_db=False)
        
        # Get topics over time
        result = topic_model.get_topics_over_time(
            documents=documents,
            timestamps=timestamps,
            nr_bins=nr_bins
        )
        
        result["total_documents"] = len(documents)
        return result
        
    except Exception as e:
        logger.error(f"❌ Error getting topics over time: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HELPERS
# ============================================

def _extract_domain(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except:
        return None


# ============================================
# STATISTICS ENDPOINTS
# ============================================

@router.post("/force-calculate-stats")
async def force_calculate_statistics(
    period_type: str = "weekly",
    db: Session = Depends(get_db)
):
    """
    🔄 FORCE TÍNH LẠI THỐNG KÊ (Backup - thường không cần gọi)
    
    Thống kê đã được TỰ ĐỘNG cập nhật khi gọi /ingest
    Endpoint này chỉ dùng khi cần tính lại thủ công.
    
    period_type: "weekly" hoặc "monthly"
    """
    from app.services.statistics import get_statistics_service
    from datetime import date
    
    try:
        stats_service = get_statistics_service(db)
        
        if period_type not in ["weekly", "monthly", "daily"]:
            raise HTTPException(status_code=400, detail="period_type phải là weekly, monthly hoặc daily")
        
        result = {
            "period_type": period_type,
            "reference_date": str(date.today()),
            "calculated": []
        }
        
        if period_type == "daily":
            snapshot = stats_service.create_daily_snapshot()
            if snapshot:
                result["calculated"].append("daily_snapshot")
        else:
            # Trend report
            trend = stats_service.calculate_trend_report(period_type)
            if trend:
                result["calculated"].append("trend_report")
            
            # Hot topics
            hot_topics = stats_service.calculate_hot_topics(period_type)
            if hot_topics:
                result["calculated"].append(f"hot_topics ({len(hot_topics)} topics)")
            
            # Keyword stats
            keywords = stats_service.calculate_keyword_stats(period_type)
            if keywords:
                result["calculated"].append(f"keyword_stats ({len(keywords)} keywords)")
            
            # Topic mention stats
            mentions = stats_service.calculate_topic_mention_stats(period_type)
            if mentions:
                result["calculated"].append(f"topic_mention_stats ({len(mentions)} topics)")
            
            # Website stats
            websites = stats_service.calculate_website_stats(period_type)
            if websites:
                result["calculated"].append(f"website_stats ({len(websites)} records)")
            
            # Social stats
            socials = stats_service.calculate_social_stats(period_type)
            if socials:
                result["calculated"].append(f"social_stats ({len(socials)} records)")
        
        db.commit()
        result["status"] = "success"
        return result
        
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/force-update-all-stats")
async def force_update_all_statistics(db: Session = Depends(get_db)):
    """
    🔄 FORCE CẬP NHẬT TẤT CẢ (Backup - thường không cần gọi)
    
    Thống kê đã được TỰ ĐỘNG cập nhật khi gọi /ingest
    Endpoint này chỉ dùng khi cần rebuild toàn bộ thống kê.
    """
    from app.services.statistics import get_statistics_service
    
    try:
        stats_service = get_statistics_service(db)
        result = stats_service.update_all_statistics()
        return result
    except Exception as e:
        logger.error(f"Error updating all statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/trend")
async def get_trend_reports(
    period_type: str = "weekly",
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """📈 XEM BÁO CÁO XU HƯỚNG"""
    from app.models.model_statistics import TrendReport
    from sqlalchemy import desc
    
    reports = db.query(TrendReport).filter(
        TrendReport.period_type == period_type
    ).order_by(desc(TrendReport.period_start)).limit(limit).all()
    
    return {
        "period_type": period_type,
        "count": len(reports),
        "reports": [
            {
                "period_label": r.period_label,
                "period_start": str(r.period_start),
                "period_end": str(r.period_end),
                "total_mentions": r.total_mentions,
                "positive_ratio": r.positive_ratio,
                "negative_ratio": r.negative_ratio,
                "mention_change": r.mention_change,
                "emotion_distribution": r.emotion_distribution,
                "top_keywords": r.top_keywords[:10] if r.top_keywords else [],
                "top_sources": r.top_sources[:5] if r.top_sources else []
            }
            for r in reports
        ]
    }


@router.get("/stats/hot-topics")
async def get_hot_topics(
    period_type: str = "weekly",
    only_crisis: bool = False,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """🔥 XEM CHỦ ĐỀ HOT / KHỦNG HOẢNG"""
    from app.models.model_statistics import HotTopic
    from sqlalchemy import desc
    
    query = db.query(HotTopic).filter(HotTopic.period_type == period_type)
    
    if only_crisis:
        query = query.filter(HotTopic.is_crisis == True)
    
    topics = query.order_by(desc(HotTopic.hot_score)).limit(limit).all()
    
    return {
        "period_type": period_type,
        "count": len(topics),
        "topics": [
            {
                "rank": t.rank,
                "topic_name": t.topic_name,
                "mention_count": t.mention_count,
                "hot_score": t.hot_score,
                "is_hot": t.is_hot,
                "is_crisis": t.is_crisis,
                "crisis_score": t.crisis_score,
                "velocity": t.mention_velocity,
                "dominant_emotion": t.dominant_emotion,
                "positive_count": t.positive_count,
                "negative_count": t.negative_count,
                "sample_titles": t.sample_titles[:3] if t.sample_titles else []
            }
            for t in topics
        ]
    }


@router.get("/stats/keywords")
async def get_keyword_stats(
    period_type: str = "weekly",
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """☁️ THỐNG KÊ TỪ KHÓA (WORDCLOUD)"""
    from app.models.model_statistics import KeywordStats
    from sqlalchemy import desc
    
    keywords = db.query(KeywordStats).filter(
        KeywordStats.period_type == period_type
    ).order_by(desc(KeywordStats.mention_count)).limit(limit).all()
    
    return {
        "period_type": period_type,
        "count": len(keywords),
        "keywords": [
            {
                "keyword": k.keyword,
                "count": k.mention_count,
                "weight": k.weight,
                "sentiment_score": k.sentiment_score,
                "positive_count": k.positive_count,
                "negative_count": k.negative_count
            }
            for k in keywords
        ],
        # Format cho WordCloud
        "wordcloud_data": [
            {"text": k.keyword, "value": k.mention_count, "sentiment": k.sentiment_score}
            for k in keywords
        ]
    }


@router.get("/stats/websites")
async def get_website_stats(
    period_type: str = "weekly",
    topic_id: int = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """🌐 THỐNG KÊ WEBSITE HOẠT ĐỘNG"""
    from app.models.model_statistics import WebsiteActivityStats
    from sqlalchemy import desc
    
    query = db.query(WebsiteActivityStats).filter(
        WebsiteActivityStats.period_type == period_type
    )
    
    if topic_id:
        query = query.filter(WebsiteActivityStats.topic_id == topic_id)
    
    websites = query.order_by(desc(WebsiteActivityStats.article_count)).limit(limit).all()
    
    return {
        "period_type": period_type,
        "count": len(websites),
        "websites": [
            {
                "rank": w.rank_overall,
                "domain": w.domain,
                "topic_name": w.topic_name,
                "article_count": w.article_count,
                "sentiment_score": w.avg_sentiment_score,
                "dominant_emotion": w.dominant_emotion,
                "positive_count": w.positive_count,
                "negative_count": w.negative_count
            }
            for w in websites
        ]
    }


@router.get("/stats/social")
async def get_social_stats(
    period_type: str = "weekly",
    platform: str = None,
    topic_id: int = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """📱 THỐNG KÊ MẠNG XÃ HỘI"""
    from app.models.model_statistics import SocialActivityStats
    from sqlalchemy import desc
    
    query = db.query(SocialActivityStats).filter(
        SocialActivityStats.period_type == period_type
    )
    
    if platform:
        query = query.filter(SocialActivityStats.platform == platform)
    if topic_id:
        query = query.filter(SocialActivityStats.topic_id == topic_id)
    
    accounts = query.order_by(desc(SocialActivityStats.post_count)).limit(limit).all()
    
    return {
        "period_type": period_type,
        "count": len(accounts),
        "platforms": list(set(a.platform for a in accounts)),
        "accounts": [
            {
                "platform": a.platform,
                "account_name": a.account_name,
                "topic_name": a.topic_name,
                "post_count": a.post_count,
                "rank_in_platform": a.rank_in_platform,
                "sentiment_score": a.avg_sentiment_score,
                "dominant_emotion": a.dominant_emotion
            }
            for a in accounts
        ]
    }


# ============================================
# TREND ANALYSIS ENDPOINTS
# ============================================

@router.get("/trends/alerts")
async def get_trend_alerts(
    alert_type: str = None,
    alert_level: str = None,
    status: str = "active",
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """🚨 CẢNH BÁO XU HƯỚNG ĐỘT BIẾN / KHỦNG HOẢNG"""
    from app.models.model_trends import TrendAlert
    from sqlalchemy import desc
    
    query = db.query(TrendAlert)
    
    if status:
        query = query.filter(TrendAlert.alert_status == status)
    if alert_type:
        query = query.filter(TrendAlert.alert_type == alert_type)
    if alert_level:
        query = query.filter(TrendAlert.alert_level == alert_level)
    
    alerts = query.order_by(desc(TrendAlert.detected_at)).limit(limit).all()
    
    return {
        "count": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "type": a.alert_type,
                "level": a.alert_level,
                "status": a.alert_status,
                "title": a.title,
                "topic_name": a.topic_name,
                "current_count": a.current_count,
                "previous_count": a.previous_count,
                "change_percent": a.change_percent,
                "negative_ratio": a.negative_ratio,
                "detected_at": str(a.detected_at) if a.detected_at else None
            }
            for a in alerts
        ]
    }


@router.get("/trends/hashtags")
async def get_hashtag_stats(
    period_type: str = "daily",
    trending_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """#️⃣ THỐNG KÊ HASHTAG"""
    from app.models.model_trends import HashtagStats
    from sqlalchemy import desc
    
    query = db.query(HashtagStats).filter(
        HashtagStats.period_type == period_type
    )
    
    if trending_only:
        query = query.filter(HashtagStats.is_trending == True)
    
    hashtags = query.order_by(desc(HashtagStats.mention_count)).limit(limit).all()
    
    return {
        "period_type": period_type,
        "count": len(hashtags),
        "hashtags": [
            {
                "rank": h.rank,
                "hashtag": h.hashtag,
                "count": h.mention_count,
                "change_percent": h.change_percent,
                "is_trending": h.is_trending,
                "is_new": h.is_new,
                "sentiment_score": h.sentiment_score,
                "related_topics": h.related_topics[:3] if h.related_topics else []
            }
            for h in hashtags
        ],
        # Format cho WordCloud
        "wordcloud_data": [
            {"text": h.hashtag, "value": h.mention_count}
            for h in hashtags
        ]
    }


@router.get("/trends/viral")
async def get_viral_content(
    period_type: str = "daily",
    hot_only: bool = False,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """🔥 NỘI DUNG VIRAL / HOT"""
    from app.models.model_trends import ViralContent
    from sqlalchemy import desc
    
    query = db.query(ViralContent).filter(
        ViralContent.period_type == period_type
    )
    
    if hot_only:
        query = query.filter(ViralContent.is_hot == True)
    
    contents = query.order_by(desc(ViralContent.viral_score)).limit(limit).all()
    
    return {
        "period_type": period_type,
        "count": len(contents),
        "viral_contents": [
            {
                "rank": c.rank,
                "title": c.title,
                "url": c.url,
                "source_domain": c.source_domain,
                "category": c.category,
                "category_vi": c.category_vi,
                "topic_name": c.topic_name,
                "emotion": c.emotion,
                "emotion_vi": c.emotion_vi,
                "viral_score": c.viral_score,
                "is_hot": c.is_hot
            }
            for c in contents
        ]
    }


@router.get("/trends/categories")
async def get_category_trends(
    period_type: str = "daily",
    db: Session = Depends(get_db)
):
    """📊 XU HƯỚNG THEO DANH MỤC (Giáo dục, Y tế, Giao thông...)"""
    from app.models.model_trends import CategoryTrendStats
    from sqlalchemy import desc
    
    categories = db.query(CategoryTrendStats).filter(
        CategoryTrendStats.period_type == period_type
    ).order_by(desc(CategoryTrendStats.total_mentions)).all()
    
    return {
        "period_type": period_type,
        "count": len(categories),
        "categories": [
            {
                "category": c.category,
                "category_vi": c.category_vi,
                "icon": c.category_icon,
                "total_mentions": c.total_mentions,
                "positive_count": c.positive_count,
                "negative_count": c.negative_count,
                "neutral_count": c.neutral_count,
                "sentiment_score": c.sentiment_score,
                "change_percent": c.change_percent,
                "is_trending_up": c.is_trending_up,
                "is_trending_down": c.is_trending_down,
                "has_crisis": c.has_crisis,
                "dominant_emotion": c.dominant_emotion,
                "top_topics": c.top_topics[:5] if c.top_topics else [],
                "rank_by_mention": c.rank_by_mention
            }
            for c in categories
        ]
    }


@router.get("/categories")
async def get_available_categories():
    """📋 DANH SÁCH CÁC DANH MỤC CHỦ ĐỀ"""
    from app.services.classification import CATEGORIES
    
    return {
        "count": len(CATEGORIES),
        "categories": [
            {
                "id": cat_id,
                "name_vi": info["vi"],
                "icon": info["icon"],
                "keyword_count": len(info["keywords"])
            }
            for cat_id, info in CATEGORIES.items()
        ]
    }
