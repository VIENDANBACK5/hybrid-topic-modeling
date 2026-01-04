"""
Statistics API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.statistics.statistics_service import StatisticsService
from typing import Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["statistics"])


@router.get("/overview")
def get_overview(
    period_type: str = "day",
    db: Session = Depends(get_db)
) -> Dict:
    """Get statistics overview"""
    service = StatisticsService(db)
    # TODO: implement get_statistics_overview
    return {"message": "Not implemented yet"}


@router.post("/keywords/regenerate")
def regenerate_keywords(
    limit: int = 200,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Regenerate keywords với GPT cleaning và entity preservation
    
    Args:
        limit: Number of articles to analyze (default 200)
    
    Returns:
        {
            "total": 27,
            "max_mentions": 100,
            "keywords": [...],
            "method": "gpt_cleaned"
        }
    """
    try:
        service = StatisticsService(db)
        result = service.regenerate_keywords_with_gpt(limit)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Keyword regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords")
def get_keywords(
    limit: int = 50,
    db: Session = Depends(get_db)
) -> Dict:
    """Get current keywords from database"""
    from sqlalchemy import text
    
    result = db.execute(
        text("""
            SELECT keyword, mention_count, weight, period_type
            FROM keyword_stats
            ORDER BY mention_count DESC
            LIMIT :limit
        """),
        {"limit": limit}
    )
    
    keywords = []
    for row in result.fetchall():
        keywords.append({
            "keyword": row[0],
            "mention_count": row[1],
            "weight": float(row[2]) if row[2] else 0.0,
            "period_type": row[3]
        })
    
    return {
        "total": len(keywords),
        "keywords": keywords
    }

@router.post("/update-all")
def update_all_statistics(
    db: Session = Depends(get_db)
) -> Dict:
    """
    Update ALL statistics tables:
    - hot_topics
    - keyword_stats
    - topic_mention_stats
    - social_activity_stats
    - website_activity_stats
    - trend_reports
    - daily_snapshots
    """
    try:
        service = StatisticsService(db)
        result = service.update_all_statistics()
        return {
            "success": True,
            "message": "All statistics updated",
            "data": result
        }
    except Exception as e:
        logger.error(f"Statistics update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-topics")
def get_hot_topics(
    period_type: str = "weekly",
    limit: int = 20,
    db: Session = Depends(get_db)
) -> Dict:
    """Get hot topics"""
    from sqlalchemy import text
    
    result = db.execute(
        text("""
            SELECT topic_id, topic_name, mention_count, engagement_score, trend_direction
            FROM hot_topics
            WHERE period_type = :period_type
            ORDER BY mention_count DESC
            LIMIT :limit
        """),
        {"period_type": period_type, "limit": limit}
    )
    
    topics = []
    for row in result.fetchall():
        topics.append({
            "topic_id": row[0],
            "topic_name": row[1],
            "mention_count": row[2],
            "engagement_score": float(row[3]) if row[3] else 0.0,
            "trend_direction": row[4]
        })
    
    return {
        "total": len(topics),
        "period_type": period_type,
        "topics": topics
    }