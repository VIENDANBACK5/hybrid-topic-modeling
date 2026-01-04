"""
Orchestrator API - Endpoints để trigger pipeline
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.orchestrator import get_orchestrator, PipelineOrchestrator
from pydantic import BaseModel
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orchestrator", tags=["🎯 Orchestrator"])


class PipelineConfig(BaseModel):
    """Configuration for pipeline execution"""
    sync_data: bool = True
    classify_topics: bool = True
    analyze_sentiment: bool = True
    calculate_statistics: bool = True
    regenerate_keywords: bool = True
    train_bertopic: bool = True  # Enable by default
    limit: Optional[int] = None


@router.post("/run-full-pipeline")
def run_full_pipeline(
    config: PipelineConfig = PipelineConfig(),
    background: bool = False,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
) -> Dict:
    """
    🚀 Chạy toàn bộ pipeline xử lý data
    
    **Workflow:**
    1. 📥 Sync data từ external API
    2. 🏷️  Classify topics (custom classifier)
    3. 😊 Analyze sentiment & link to topics
    4. 📊 Calculate statistics (trends, hot topics)
    5. 🔑 Regenerate keywords với GPT
    6. 🤖 Train BERTopic (optional)
    
    **Args:**
    - `sync_data`: Sync data từ external API (default: True)
    - `classify_topics`: Classify topics chưa xử lý (default: True)
    - `analyze_sentiment`: Phân tích sentiment (default: True)
    - `calculate_statistics`: Tính statistics (default: True)
    - `regenerate_keywords`: Tạo keywords mới (default: True)
    - `train_bertopic`: Train BERTopic để discover topics mới (default: True)
    - `limit`: Giới hạn số articles xử lý (None = all)
    - `background`: Chạy background không block (default: False)
    
    **Returns:**
    - Kết quả chi tiết từng bước hoặc task_id nếu background
    
    **Example:**
    ```bash
    # Chạy full pipeline (foreground)
    curl -X POST http://localhost:7777/api/orchestrator/run-full-pipeline
    
    # Chạy background
    curl -X POST http://localhost:7777/api/orchestrator/run-full-pipeline?background=true
    
    # Custom config
    curl -X POST http://localhost:7777/api/orchestrator/run-full-pipeline \\
      -H "Content-Type: application/json" \\
      -d '{
        "classify_topics": true,
        "analyze_sentiment": true,
        "regenerate_keywords": true,
        "train_bertopic": true,
        "limit": 500
      }'
    ```
    """
    try:
        orchestrator = get_orchestrator(db)
        
        if background and background_tasks:
            # Run in background
            task_id = f"pipeline_{int(datetime.now().timestamp())}"
            background_tasks.add_task(
                orchestrator.run_full_pipeline,
                sync_data=config.sync_data,
                classify_topics=config.classify_topics,
                analyze_sentiment=config.analyze_sentiment,
                calculate_statistics=config.calculate_statistics,
                regenerate_keywords=config.regenerate_keywords,
                train_bertopic=config.train_bertopic,
                limit=config.limit
            )
            return {
                "status": "started",
                "task_id": task_id,
                "message": "Pipeline started in background. Check logs for progress."
            }
        else:
            # Run synchronously (block until done)
            result = orchestrator.run_full_pipeline(
                sync_data=config.sync_data,
                classify_topics=config.classify_topics,
                analyze_sentiment=config.analyze_sentiment,
                calculate_statistics=config.calculate_statistics,
                regenerate_keywords=config.regenerate_keywords,
                train_bertopic=config.train_bertopic,
                limit=config.limit
            )
            return {
                "status": "completed" if not result.get("errors") else "completed_with_errors",
                "result": result
            }
            
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-update")
def quick_update(
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Dict:
    """
    ⚡ Quick update - Chỉ classify + sentiment + keywords
    
    Bỏ qua sync và training, chỉ xử lý data có sẵn.
    Phù hợp cho updates nhanh hàng ngày.
    
    **Args:**
    - `limit`: Số articles tối đa xử lý (default: 100)
    
    **Example:**
    ```bash
    curl -X POST http://localhost:7777/api/orchestrator/quick-update?limit=200
    ```
    """
    try:
        orchestrator = get_orchestrator(db)
        result = orchestrator.run_full_pipeline(
            sync_data=False,
            classify_topics=True,
            analyze_sentiment=True,
            calculate_statistics=True,
            regenerate_keywords=True,
            train_bertopic=False,
            limit=limit
        )
        return {
            "status": "completed",
            "mode": "quick_update",
            "result": result
        }
    except Exception as e:
        logger.error(f"Quick update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def get_status(db: Session = Depends(get_db)) -> Dict:
    """
    📊 Kiểm tra trạng thái hệ thống
    
    Returns:
    - Số lượng articles, topics, classifications, sentiments
    - Articles chưa classify, chưa analyze sentiment
    - Keywords count
    
    **Example:**
    ```bash
    curl http://localhost:7777/api/orchestrator/status
    ```
    """
    try:
        from sqlalchemy import text
        
        # Count totals
        total_articles = db.execute(text("SELECT COUNT(*) FROM articles")).scalar()
        total_topics = db.execute(text("SELECT COUNT(*) FROM custom_topics")).scalar()
        total_classifications = db.execute(text("SELECT COUNT(*) FROM article_custom_topics")).scalar()
        total_sentiments = db.execute(text("SELECT COUNT(*) FROM sentiment_analysis")).scalar()
        total_keywords = db.execute(text("SELECT COUNT(*) FROM keyword_stats")).scalar()
        
        # Count pending
        unclassified = db.execute(text("""
            SELECT COUNT(DISTINCT a.id)
            FROM articles a
            LEFT JOIN article_custom_topics act ON a.id = act.article_id
            WHERE act.article_id IS NULL
        """)).scalar()
        
        no_sentiment = db.execute(text("""
            SELECT COUNT(DISTINCT act.article_id)
            FROM article_custom_topics act
            LEFT JOIN sentiment_analysis sa ON act.article_id = sa.article_id
            WHERE sa.article_id IS NULL
        """)).scalar()
        
        return {
            "status": "ok",
            "totals": {
                "articles": total_articles,
                "topics": total_topics,
                "classifications": total_classifications,
                "sentiments": total_sentiments,
                "keywords": total_keywords
            },
            "pending": {
                "unclassified_articles": unclassified,
                "articles_no_sentiment": no_sentiment
            },
            "needs_action": unclassified > 0 or no_sentiment > 0
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
