"""
Topic Service API - Core endpoints for topic modeling and sentiment analysis
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, field_validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.core.database import get_db
from app.models.model_article import Article
from app.models.model_sentiment import SentimentAnalysis
from app.services.topic.model import TopicModel
from app.services.sentiment.sentiment_service import get_sentiment_analyzer
from app.services.classification import get_category_classifier
from app.utils.domain_utils import ensure_domain
import logging
import threading

logger = logging.getLogger(__name__)
router = APIRouter()

_training_lock = threading.Lock()
_training_status = {"is_training": False, "started_at": None}


class DocumentInput(BaseModel):
    source: str = "web"
    source_id: str
    content: str
    raw_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v or len(v.strip()) < 20:
            raise ValueError('Content must have at least 20 characters')
        return v.strip()


class IngestRequest(BaseModel):
    documents: List[DocumentInput]
    skip_duplicates: bool = True
    analyze_sentiment: bool = True


class TrainRequest(BaseModel):
    min_topic_size: int = 10
    use_vietnamese_tokenizer: bool = True
    enable_topicgpt: bool = False


@router.post("/ingest")
async def ingest_documents(request: IngestRequest, db: Session = Depends(get_db)):
    """Ingest documents with sentiment analysis and auto-update statistics"""
    try:
        saved = 0
        skipped = 0
        sentiment_saved = 0
        errors = []
        
        analyzer = get_sentiment_analyzer() if request.analyze_sentiment else None
        classifier = get_category_classifier()
        
        from app.services.etl.data_normalizer import normalize_and_validate
        
        for doc in request.documents:
            try:
                doc_dict = {
                    "source": doc.source,
                    "source_id": doc.source_id,
                    "content": doc.content,
                    "metadata": doc.metadata or {}
                }
                
                normalized, is_valid, norm_errors, warnings = normalize_and_validate(doc_dict)
                
                if not is_valid:
                    errors.append({"url": doc.source_id, "errors": norm_errors})
                    skipped += 1
                    continue
                
                if request.skip_duplicates:
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
                reactions = engagement.get("reactions", {})
                likes = engagement.get("likes", 0)
                shares = engagement.get("shares", 0)
                comments = engagement.get("comments", 0)
                views = engagement.get("views", 0)
                engagement_rate = (likes + shares + comments) / views if views > 0 else None
                
                social = metadata.get("social_account", {})
                location = metadata.get("location", {})
                
                # Ensure domain is filled
                article_data = ensure_domain({
                    'url': normalized['url'],
                    'source': normalized['url'],
                    'domain': normalized['domain'],
                    'social_platform': normalized['platform'],
                    'account_name': social.get("account_name")
                })
                
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
                    reactions=reactions if reactions else None,
                    engagement_rate=engagement_rate,
                    social_platform=normalized['platform'],
                    account_id=social.get("account_id"),
                    account_name=social.get("account_name"),
                    account_url=social.get("account_url"),
                    account_type=social.get("account_type"),
                    account_followers=social.get("followers"),
                    post_id=metadata.get("post_id"),
                    post_type=metadata.get("post_type"),
                    post_language=metadata.get("language", "vi"),
                    province=location.get("province"),
                    district=location.get("district"),
                    ward=location.get("ward"),
                    location_text=metadata.get("location_text") or location.get("location_text"),
                    coordinates=location.get("coordinates"),
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
                        content_snippet=normalized['content'][:200] if normalized['content'] else None
                    )
                    db.add(sentiment_record)
                    sentiment_saved += 1
                
            except Exception as e:
                errors.append(f"{doc.source_id}: {str(e)}")
        
        db.commit()
        
        # Auto-update statistics
        stats_updated = []
        if saved > 0:
            try:
                from app.services.statistics import get_statistics_service
                from app.services.trends import get_trend_service
                
                stats_service = get_statistics_service(db)
                trend_service = get_trend_service(db)
                
                stats_service.create_daily_snapshot()
                stats_updated.append("daily_snapshot")
                
                if db.query(SentimentAnalysis).count() >= 10:
                    stats_service.calculate_trend_report("weekly")
                    stats_service.calculate_hot_topics("weekly")
                    stats_service.calculate_keyword_stats("weekly")
                    stats_updated.append("weekly_stats")
                
                trend_service.detect_trend_alerts(hours_back=24)
                trend_service.calculate_hashtag_stats("daily")
                trend_service.detect_viral_content("daily")
                trend_service.calculate_category_trends("daily")
                
                db.commit()
            except Exception as e:
                db.rollback()
                logger.warning(f"Could not auto-update stats: {e}")
        
        return {
            "status": "success",
            "saved": saved,
            "skipped": skipped,
            "sentiment_analyzed": sentiment_saved,
            "stats_updated": stats_updated,
            "errors": errors[:10] if errors else [],
            "total_in_db": db.query(Article).count()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ingest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train")
async def train_topics(request: TrainRequest, db: Session = Depends(get_db)):
    """Train BERTopic model from database articles"""
    global _training_status
    
    if not _training_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=f"Training in progress since {_training_status.get('started_at')}")
    
    try:
        _training_status = {"is_training": True, "started_at": datetime.now().isoformat()}
        
        articles = db.query(Article).filter(Article.content.isnot(None)).all()
        
        if len(articles) < 10:
            raise HTTPException(status_code=400, detail=f"Need at least 10 documents, got {len(articles)}")
        
        topic_model = TopicModel(
            min_topic_size=request.min_topic_size,
            use_vietnamese_tokenizer=request.use_vietnamese_tokenizer,
            enable_topicgpt=request.enable_topicgpt
        )
        
        documents = [a.content for a in articles]
        topics, probs = topic_model.fit(documents)
        topic_info = topic_model.get_topic_info()
        
        for i, (topic_id, article) in enumerate(zip(topics, articles)):
            article.topic_id = int(topic_id)
            article.topic_probability = float(probs[i].max()) if probs[i] is not None else 0.0
            
            topic_data = next((t for t in topic_info['topics'] if t['topic_id'] == topic_id), None)
            if topic_data:
                keywords = [w['word'] for w in topic_data.get('words', [])[:3]]
                article.topic_name = " - ".join(keywords)
            
            sentiment_record = db.query(SentimentAnalysis).filter(SentimentAnalysis.article_id == article.id).first()
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


@router.post("/hybrid-train")
async def hybrid_train(
    request: TrainRequest, 
    force_full: bool = False,
    db: Session = Depends(get_db)
):
    """
    Hybrid Training - Smart decision between full training and transform
    
    - Auto-detects if full retrain needed (monthly, drift, new data)
    - Uses transform for daily updates
    - Force full training with force_full=true
    
    Example:
    ```bash
    # Auto decision
    curl -X POST http://localhost:7777/api/topic-service/hybrid-train
    
    # Force full training
    curl -X POST "http://localhost:7777/api/topic-service/hybrid-train?force_full=true"
    ```
    """
    global _training_status
    
    if not _training_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409, 
            detail=f"Training in progress since {_training_status.get('started_at')}"
        )
    
    try:
        _training_status = {
            "is_training": True, 
            "started_at": datetime.now().isoformat(),
            "method": "hybrid"
        }
        
        from app.services.topic.hybrid_trainer import get_hybrid_trainer
        
        trainer = get_hybrid_trainer(db)
        result = trainer.train_or_transform(
            force_full_train=force_full,
            min_topic_size=request.min_topic_size,
            use_vietnamese_tokenizer=request.use_vietnamese_tokenizer,
            enable_topicgpt=request.enable_topicgpt
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Hybrid train error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _training_status = {"is_training": False, "started_at": None}
        _training_lock.release()


@router.get("/training-recommendation")
async def get_training_recommendation(db: Session = Depends(get_db)):
    """
    Get recommendation on whether to retrain or transform
    
    Returns analysis without actually training
    """
    try:
        from app.services.topic.hybrid_trainer import get_hybrid_trainer
        
        trainer = get_hybrid_trainer(db)
        should_retrain, reason = trainer.should_retrain()
        
        # Get additional stats
        last_train = trainer._get_last_training_time()
        new_articles = trainer._count_new_articles_since(last_train) if last_train else 0
        total_articles = trainer._count_total_articles()
        drift_score = trainer._detect_concept_drift()
        
        return {
            "recommendation": "full_train" if should_retrain else "transform",
            "reason": reason,
            "analysis": {
                "last_training": last_train.isoformat() if last_train else None,
                "days_since_training": (datetime.now() - last_train).days if last_train else None,
                "new_articles": new_articles,
                "total_articles": total_articles,
                "new_ratio": new_articles / total_articles if total_articles > 0 else 0,
                "concept_drift_score": round(drift_score, 3),
                "drift_threshold": trainer.drift_threshold
            }
        }
        
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status(db: Session = Depends(get_db)):
    """Get service status"""
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
    except Exception as e:
        result["status"] = "database_error"
        result["error"] = str(e)[:100]
    
    return result


@router.get("/topics")
async def get_topics(db: Session = Depends(get_db)):
    """Get list of topics"""
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


@router.get("/categories")
async def get_available_categories():
    """Get available topic categories"""
    from app.services.classification import CATEGORIES
    
    return {
        "count": len(CATEGORIES),
        "categories": [
            {"id": cat_id, "name_vi": info["vi"], "keyword_count": len(info["keywords"])}
            for cat_id, info in CATEGORIES.items()
        ]
    }


_embedding_training_lock = threading.Lock()
_embedding_training_status = {"is_training": False, "started_at": None, "current_version": None}


class EmbeddingFineTuneRequest(BaseModel):
    epochs: int = Field(
        default=2,
        ge=1,
        le=10,
        description=(
            "Số lượt huấn luyện (Epochs). [Hợp lệ: 1 -> 10]. "
            "Tăng epochs giúp mô hình học sâu hơn vào dữ liệu cụ thể, nâng cao độ chính xác biểu diễn (Cosine Similarity). "
            "Tuy nhiên, nếu > 5 sẽ dễ gây quá khớp (overfitting) - làm giảm khả năng nhận diện dữ liệu mới và tăng thời gian train."
        )
    )
    batch_size: int = Field(
        default=64,
        ge=8,
        le=256,
        description=(
            "Kích thước lô dữ liệu (Batch size). [Hợp lệ: 8 -> 256]. "
            "Tăng giúp tối ưu hóa phần cứng (GPU) và ổn định gradient (MultipleNegativesRankingLoss cần batch size lớn để so sánh chéo). "
            "Tuy nhiên, nếu quá lớn (> 128) sẽ dễ gây tràn bộ nhớ VRAM của GPU (lỗi OOM)."
        )
    )
    learning_rate: float = Field(
        default=2e-5,
        ge=1e-6,
        le=1e-3,
        description=(
            "Tốc độ học (Learning rate). [Hợp lệ: 1e-6 -> 1e-3]. "
            "Tốc độ học lớn giúp mô hình hội tụ nhanh hơn. Tuy nhiên, giá trị quá lớn (> 1e-4) có thể khiến mô hình bị mất ổn định, "
            "học hỏng mô hình (lỗi NaN hoặc bùng nổ gradient), trong khi giá trị quá nhỏ khiến mô hình học rất chậm."
        )
    )
    warmup_ratio: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Tỉ lệ khởi động (Warmup ratio). [Hợp lệ: 0.0 -> 0.5]. Tỉ lệ số bước tăng dần learning rate từ 0 lên tối đa trong giai đoạn đầu để ổn định trọng số transformer."
    )
    min_topic_size: int = Field(
        default=10,
        ge=2,
        le=100,
        description=(
            "Kích thước chủ đề tối thiểu để sinh mẫu. [Hợp lệ: 2 -> 100]. "
            "Giảm xuống giúp lấy được nhiều cụm chủ đề nhỏ hơn, tăng lượng dữ liệu huấn luyện. "
            "Nhưng nếu quá nhỏ (< 5) có thể khiến dữ liệu huấn luyện bị nhiễu do các cụm nhỏ thường chứa bài viết không đồng đều."
        )
    )
    min_avg_prob: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description=(
            "Độ tin cậy trung bình tối thiểu của chủ đề. [Hợp lệ: 0.0 -> 1.0]. "
            "Giảm xuống giúp tăng số lượng cụm chủ đề được chọn để huấn luyện, nhưng có nguy cơ kéo theo các cụm phân loại kém chất lượng."
        )
    )
    max_pairs_per_topic: int = Field(
        default=200,
        ge=10,
        le=1000,
        description="Số lượng cặp tối đa trên mỗi chủ đề. [Hợp lệ: 10 -> 1000]. Tránh bùng nổ tổ hợp mẫu và mất cân bằng dữ liệu giữa các chủ đề lớn và nhỏ."
    )
    min_doc_prob: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Độ tin cậy gán chủ đề tối thiểu của mỗi bài viết. [Hợp lệ: 0.0 -> 1.0]. "
            "Lọc bài viết chắc chắn thuộc chủ đề để sinh cặp chất lượng. Giảm xuống giúp có thêm nhiều bài viết để ghép cặp huấn luyện."
        )
    )
    val_split: float = Field(
        default=0.1,
        ge=0.05,
        le=0.5,
        description="Tỉ lệ chia dữ liệu xác thực (Validation split). [Hợp lệ: 0.05 -> 0.5]. Tỉ lệ dùng để đánh giá độc lập mô hình sau khi huấn luyện."
    )
    force_train: bool = Field(
        default=False,
        description="Bắt buộc huấn luyện. Nếu True, bỏ qua kiểm tra số lượng mẫu và tiến hành chạy huấn luyện kể cả khi không tìm thấy phiên phân cụm mới."
    )


class EmbeddingSwitchRequest(BaseModel):
    version: str


def _run_embedding_training_task(request: EmbeddingFineTuneRequest):
    global _embedding_training_status
    from app.core.database import SessionLocal
    from app.services.topic.embedding_trainer import EmbeddingTrainer
    
    db = SessionLocal()
    try:
        trainer = EmbeddingTrainer(db)
        logger.info("Starting background embedding fine-tuning task...")
        trainer.run_fine_tuning(
            epochs=request.epochs,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
            warmup_ratio=request.warmup_ratio,
            min_topic_size=request.min_topic_size,
            min_avg_prob=request.min_avg_prob,
            max_pairs_per_topic=request.max_pairs_per_topic,
            min_doc_prob=request.min_doc_prob,
            val_split=request.val_split,
            force_train=request.force_train
        )
    except Exception as e:
        logger.error(f"Error in background embedding fine-tuning: {e}", exc_info=True)
    finally:
        db.close()
        _embedding_training_status["is_training"] = False
        _embedding_training_status["started_at"] = None
        _embedding_training_lock.release()


@router.post("/embedding/fine-tune")
async def trigger_embedding_fine_tune(
    background_tasks: BackgroundTasks,
    request: Optional[EmbeddingFineTuneRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Kích hoạt tiến trình tinh chỉnh (Fine-tune) mô hình Vector Embedding (SentenceTransformer) dưới nền.
    
    ### HƯỚNG DẪN DÀNH CHO NGƯỜI VẬN HÀNH (MLOps Guide)
    
    API này cho phép bạn cấu hình và tinh chỉnh lại mô hình biểu diễn ngôn ngữ (vector embeddings) dựa trên các bài viết đã phân cụm thành công trong hệ thống.
    
    ---
    ### 🛡️ NGUYÊN TẮC AN TOÀN TRÁNH HỎNG MÔ HÌNH (Safety Bounds)
    Để tránh làm suy giảm chất lượng biểu diễn ngôn ngữ hoặc gây lỗi hệ thống, các ngưỡng giới hạn cứng đã được thiết lập:
    * **Epochs (1 -> 10):** Không nên chỉnh vượt quá **5**. Số lượng quá lớn sẽ gây hiện tượng **Quá khớp (Overfitting)**, khiến mô hình chỉ nhớ các bài viết cũ và không thể gom cụm các bài viết mới sau này.
    * **Batch Size (8 -> 256):** Khuyên dùng **64** (nếu có GPU CUDA) hoặc **16** (nếu chạy bằng CPU). Đặt quá lớn (> 128) sẽ gây tràn bộ nhớ VRAM của card đồ họa, dẫn đến lỗi **Out Of Memory (OOM)** và sập tiến trình ngầm.
    * **Learning Rate (1e-6 -> 1e-3):** **Ngưỡng cực kỳ quan trọng!** Khuyên dùng từ `2e-5` đến `3e-5`. Tránh đặt quá lớn (> 1e-4) vì sẽ làm đứt gãy trọng số của mô hình (lỗi gradient bùng nổ, loss trả về `NaN`).
    
    ---
    ### ⚙️ HƯỚNG DẪN THAM SỐ LỌC DỮ LIỆU ĐỂ ĐẠT HIỆU QUẢ CAO
    Dữ liệu huấn luyện được sinh ra tự động bằng cách kết hợp các bài viết trong cùng một cụm chủ đề chất lượng.
    * **min_topic_size:** Nên đặt **10**. Nếu đặt quá lớn (ví dụ: 50), bạn sẽ có ít chủ đề hợp lệ, dẫn đến **0 mẫu để train**. Nếu đặt quá nhỏ (ví dụ: 2), dữ liệu sẽ bị nhiễu do các cụm nhỏ chưa đủ tin cậy.
    * **min_avg_prob:** Độ chắc chắn trung bình của chủ đề. Nên đặt **0.7** hoặc **0.5**. Đặt quá cao (0.9) sẽ khiến bộ lọc loại bỏ toàn bộ chủ đề, không sinh được dữ liệu train.
    * **min_doc_prob:** Độ chắc chắn của bài viết trong cụm. Nên đặt **0.5**.
    
    ---
    ### 💡 CẤU HÌNH KHUYÊN DÙNG (Best Practices)
    * **Dành cho chạy thử nghiệm nhanh:**
      ```json
      { "epochs": 2, "min_topic_size": 10, "min_avg_prob": 0.7, "min_doc_prob": 0.5 }
      ```
    * **Dành cho huấn luyện kỹ lưỡng (Cần GPU):**
      ```json
      { "epochs": 3, "learning_rate": 3e-5, "min_topic_size": 10, "min_avg_prob": 0.6, "min_doc_prob": 0.5 }
      ```
    """
    global _embedding_training_status
    
    req = request or EmbeddingFineTuneRequest()
    
    if not _embedding_training_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409, 
            detail=f"Embedding training is already in progress since {_embedding_training_status.get('started_at')}"
        )
        
    _embedding_training_status["is_training"] = True
    _embedding_training_status["started_at"] = datetime.now().isoformat()
    _embedding_training_status["current_version"] = "generating..."
    
    background_tasks.add_task(_run_embedding_training_task, req)
    
    return {
        "status": "started",
        "message": "Embedding fine-tuning task has been scheduled in the background",
        "started_at": _embedding_training_status["started_at"]
    }


@router.get("/embedding/status")
async def get_embedding_status(db: Session = Depends(get_db)):
    """Get active embedding version, status of running training and logs history"""
    from app.services.topic.embedding_manager import EmbeddingManager
    from app.models.model_embedding_training import EmbeddingTrainingSession
    from sqlalchemy import desc
    
    manager = EmbeddingManager()
    active_config = manager.get_active_config()
    all_versions = manager.get_all_versions()
    
    # Query database history
    history = []
    try:
        sessions = db.query(EmbeddingTrainingSession).order_by(desc(EmbeddingTrainingSession.started_at)).limit(10).all()
        for s in sessions:
            history.append({
                "id": s.id,
                "version": s.version,
                "status": s.status,
                "num_documents": s.num_documents,
                "num_pairs": s.num_pairs,
                "epochs": s.epochs,
                "loss": s.loss,
                "metrics": s.metrics,
                "model_path": s.model_path,
                "error_message": s.error_message,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            })
    except Exception as e:
        logger.error(f"Error querying embedding training session history: {e}")
        
    return {
        "active_model": active_config,
        "available_versions": all_versions,
        "training_state": _embedding_training_status,
        "history": history
    }


@router.post("/embedding/switch")
async def switch_embedding_version(request: EmbeddingSwitchRequest, db: Session = Depends(get_db)):
    """Manually switch active embedding version or rollback"""
    from app.services.topic.embedding_manager import EmbeddingManager
    from app.models.model_embedding_training import EmbeddingTrainingSession
    
    manager = EmbeddingManager()
    
    # Perform switch/rollback
    success = manager.rollback_to(request.version)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Version '{request.version}' could not be loaded or activated. Make sure it exists."
        )
        
    # Update state in DB if it exists
    if request.version != "default":
        try:
            session = db.query(EmbeddingTrainingSession).filter(
                EmbeddingTrainingSession.version == request.version
            ).first()
            if session:
                session.status = "deployed"
                db.commit()
        except Exception as e:
            logger.error(f"Could not update status to deployed in DB: {e}")
            
    return {
        "status": "success",
        "message": f"Successfully activated embedding version: {request.version}",
        "active_model": manager.get_active_config()
    }
