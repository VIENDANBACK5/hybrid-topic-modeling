"""
Orchestrator API - Endpoints de trigger pipeline
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.orchestrator import get_orchestrator
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orchestrator", tags=["Orchestrator"])


class PipelineConfig(BaseModel):
    """Configuration for pipeline execution"""
    mode: str = "full"  # full, quick, custom
    sync_data: bool = True
    classify_topics: bool = True
    analyze_sentiment: bool = True
    calculate_statistics: bool = True
    regenerate_keywords: bool = True
    train_bertopic: bool = True
    limit: Optional[int] = None


@router.post("/run-pipeline")
def run_pipeline(
    config: PipelineConfig = PipelineConfig(),
    background: bool = False,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Chay pipeline xu ly data
    
    Modes:
    - full: Chay tat ca steps (sync, classify, sentiment, stats, keywords, bertopic)
    - quick: Chi classify + sentiment + keywords (bo sync va training)
    - custom: Tu chon cac steps
    
    Args:
    - mode: "full" | "quick" | "custom" (default: full)
    - sync_data: Sync data tu external API (default: True)
    - classify_topics: Classify topics chua xu ly (default: True)
    - analyze_sentiment: Phan tich sentiment (default: True)
    - calculate_statistics: Tinh statistics (default: True)
    - regenerate_keywords: Tao keywords moi (default: True)
    - train_bertopic: Train BERTopic de discover topics moi (default: True)
    - limit: Gioi han so articles xu ly (None = all)
    - background: Chay background khong block (default: False)
    
    Example:
    ```bash
    # Chay full pipeline
    curl -X POST http://localhost:7777/api/orchestrator/run-pipeline
    
    # Chay quick update
    curl -X POST http://localhost:7777/api/orchestrator/run-pipeline \\
      -H "Content-Type: application/json" \\
      -d '{"mode": "quick", "limit": 200}'
    
    # Custom config
    curl -X POST http://localhost:7777/api/orchestrator/run-pipeline \\
      -H "Content-Type: application/json" \\
      -d '{
        "mode": "custom",
        "classify_topics": true,
        "analyze_sentiment": true,
        "train_bertopic": false,
        "limit": 500
      }'
    ```
    """
    try:
        orchestrator = get_orchestrator(db)
        
        # Apply mode presets
        if config.mode == "quick":
            config.sync_data = False
            config.train_bertopic = False
        elif config.mode == "full":
            config.sync_data = True
            config.train_bertopic = True
        
        if background and background_tasks:
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
                "mode": config.mode,
                "message": "Pipeline started in background. Check logs for progress."
            }
        else:
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
                "mode": config.mode,
                "result": result
            }
            
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def get_status(db: Session = Depends(get_db)) -> Dict:
    """
    Kiem tra trang thai he thong
    
    Returns:
    - So luong articles, topics, classifications, sentiments
    - Articles chua classify, chua analyze sentiment
    - Keywords count
    """
    try:
        from sqlalchemy import text
        
        total_articles = db.execute(text("SELECT COUNT(*) FROM articles")).scalar()
        total_topics = db.execute(text("SELECT COUNT(*) FROM custom_topics")).scalar()
        total_classifications = db.execute(text("SELECT COUNT(*) FROM article_custom_topics")).scalar()
        total_sentiments = db.execute(text("SELECT COUNT(*) FROM sentiment_analysis")).scalar()
        total_keywords = db.execute(text("SELECT COUNT(*) FROM keyword_stats")).scalar()
        
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
