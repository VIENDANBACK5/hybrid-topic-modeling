"""
Topic Training API - Endpoint riêng cho BERTopic training
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.topic.bertopic_trainer import get_trainer
from pydantic import BaseModel
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/topics", tags=["🧠 Topic Training"])


class TrainingConfig(BaseModel):
    """Configuration for BERTopic training"""
    limit: Optional[int] = None
    min_topic_size: int = 10
    use_vietnamese_tokenizer: bool = True
    enable_topicgpt: bool = True  # Enable by default


@router.post("/train")
def train_bertopic(
    config: TrainingConfig = TrainingConfig(),
    db: Session = Depends(get_db)
) -> Dict:
    """
    🧠 Train BERTopic để discover topics mới từ articles
    
    **Process:**
    1. Load articles từ database
    2. Train BERTopic với Vietnamese support
    3. Save discovered topics vào `bertopic_discovered_topics`
    4. Link articles với topics trong `article_bertopic_topics`
    
    **Args:**
    - `limit`: Số articles tối đa để train (None = all, recommended: 500-1000)
    - `min_topic_size`: Kích thước tối thiểu của topic (default: 10)
    - `use_vietnamese_tokenizer`: Dùng Underthesea tokenizer (default: True)
    - `enable_topicgpt`: Dùng GPT generate topic labels & descriptions (default: True, requires OPENAI_API_KEY)
    
    **Returns:**
    - Training session info
    - Số topics discovered
    - Top 10 topics với keywords
    
    **Example:**
    ```bash
    # Train với 500 articles
    curl -X POST http://localhost:7777/api/topics/train \\
      -H "Content-Type: application/json" \\
      -d '{
        "limit": 500,
        "min_topic_size": 10,
        "use_vietnamese_tokenizer": true,
        "enable_topicgpt": false
      }'
    
    # Train với GPT enhancement
    curl -X POST http://localhost:7777/api/topics/train \\
      -H "Content-Type: application/json" \\
      -d '{
        "limit": 1000,
        "enable_topicgpt": true
      }'
    ```
    
    **Note:** Training có thể mất 5-30 phút tùy số lượng articles.
    """
    try:
        logger.info(f"Starting BERTopic training with config: {config.dict()}")
        
        trainer = get_trainer(db)
        result = trainer.train_from_articles(
            limit=config.limit,
            min_topic_size=config.min_topic_size,
            use_vietnamese_tokenizer=config.use_vietnamese_tokenizer,
            enable_topicgpt=config.enable_topicgpt
        )
        
        if result.get("status") == "completed":
            return {
                "status": "success",
                "message": f"Discovered {result['training']['num_topics']} topics",
                "result": result
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Training failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovered")
def get_discovered_topics(
    session_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
) -> Dict:
    """
    📋 Lấy danh sách topics đã discovered
    
    **Args:**
    - `session_id`: Filter theo training session (None = latest session)
    - `limit`: Số topics tối đa trả về (default: 50)
    
    **Example:**
    ```bash
    curl http://localhost:7777/api/topics/discovered?limit=20
    ```
    """
    try:
        from sqlalchemy import text
        
        if session_id:
            query = text("""
                SELECT 
                    id, topic_id, topic_label, keywords, 
                    document_count, training_session_id
                FROM bertopic_discovered_topics
                WHERE training_session_id = :session_id
                ORDER BY document_count DESC
                LIMIT :limit
            """)
            rows = db.execute(query, {"session_id": session_id, "limit": limit}).fetchall()
        else:
            # Get latest session
            query = text("""
                SELECT 
                    bdt.id, bdt.topic_id, bdt.topic_label, bdt.keywords,
                    bdt.document_count, bdt.training_session_id
                FROM bertopic_discovered_topics bdt
                JOIN (
                    SELECT training_session_id, MAX(created_at) as max_created
                    FROM bertopic_discovered_topics
                    GROUP BY training_session_id
                    ORDER BY max_created DESC
                    LIMIT 1
                ) latest ON bdt.training_session_id = latest.training_session_id
                ORDER BY bdt.document_count DESC
                LIMIT :limit
            """)
            rows = db.execute(query, {"limit": limit}).fetchall()
        
        topics = []
        for row in rows:
            topics.append({
                "id": row[0],
                "topic_id": row[1],
                "label": row[2],
                "keywords": row[3][:10] if row[3] else [],  # Top 10 keywords
                "document_count": row[4],
                "session_id": row[5]
            })
        
        return {
            "status": "success",
            "total": len(topics),
            "topics": topics
        }
        
    except Exception as e:
        logger.error(f"Failed to get discovered topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
def get_training_sessions(
    limit: int = 10,
    db: Session = Depends(get_db)
) -> Dict:
    """
    📊 Lấy lịch sử training sessions
    
    **Example:**
    ```bash
    curl http://localhost:7777/api/topics/sessions
    ```
    """
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                session_id, model_type, status, num_documents,
                num_topics_found, training_duration_seconds,
                started_at, completed_at
            FROM topic_training_sessions
            ORDER BY started_at DESC
            LIMIT :limit
        """)
        rows = db.execute(query, {"limit": limit}).fetchall()
        
        sessions = []
        for row in rows:
            sessions.append({
                "session_id": row[0],
                "model_type": row[1],
                "status": row[2],
                "num_documents": row[3],
                "num_topics": row[4],
                "duration_seconds": float(row[5]) if row[5] else None,
                "started_at": row[6].isoformat() if row[6] else None,
                "completed_at": row[7].isoformat() if row[7] else None
            })
        
        return {
            "status": "success",
            "total": len(sessions),
            "sessions": sessions
        }
        
    except Exception as e:
        logger.error(f"Failed to get training sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
