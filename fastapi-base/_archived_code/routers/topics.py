from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.model_article import Article
from app.services.topic.model import TopicModel
from app.services.topic.indexer import FAISSIndexer
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy initialization - create proxy objects that load on first use
class LazyTopicModel:
    def __init__(self):
        self._instance = None
    
    def _ensure_loaded(self):
        if self._instance is None:
            self._instance = TopicModel()
        return self._instance
    
    def __getattr__(self, name):
        return getattr(self._ensure_loaded(), name)

class LazyIndexer:
    def __init__(self):
        self._instance = None
    
    def _ensure_loaded(self):
        if self._instance is None:
            self._instance = FAISSIndexer()
        return self._instance
    
    def __getattr__(self, name):
        return getattr(self._ensure_loaded(), name)

topic_model = LazyTopicModel()
indexer = LazyIndexer()


class FitRequest(BaseModel):
    documents: List[str]
    min_topic_size: int = 10
    save_model: bool = True
    model_name: Optional[str] = "default_model"


class TransformRequest(BaseModel):
    documents: List[str]
    model_name: str


class SearchRequest(BaseModel):
    query: str
    k: int = 10


class TopicRequest(BaseModel):
    """GỘP fit + transform + search vào 1 request"""
    action: str  # "train", "assign", "search", "overview"
    
    # For train
    documents: Optional[List[str]] = None
    min_topic_size: int = 10
    save_model: bool = True
    model_name: Optional[str] = "default_model"
    
    # For search
    query: Optional[str] = None
    k: int = 10


@router.post("")
async def topics_unified(request: TopicRequest):
    """
    GỘP TẤT CẢ - API topics đa năng
    
    Actions:
    - "train": Train topic model từ documents
    - "assign": Gán topics cho documents mới
    - "search": Tìm kiếm documents theo query
    - "overview": Xem tổng quan topics
    
    Example:
        {"action": "train", "documents": ["doc1", "doc2"]}
        {"action": "search", "query": "kinh tế"}
        {"action": "overview"}
    """
    try:
        if request.action == "train":
            if not request.documents:
                raise HTTPException(status_code=400, detail="documents required for training")
            
            logger.info(f"Training topics on {len(request.documents)} documents")
            topic_model.min_topic_size = request.min_topic_size
            topics, probs = topic_model.fit(request.documents)
            topic_info = topic_model.get_topic_info()
            
            model_path = None
            if request.save_model:
                model_path = topic_model.save(request.model_name)
            
            return {
                "status": "success",
                "action": "train",
                "total_documents": len(request.documents),
                "total_topics": len(topic_info['topics']),
                "model_saved": request.save_model,
                "model_path": model_path,
                "topics": topic_info
            }
        
        elif request.action == "assign":
            if not request.documents:
                raise HTTPException(status_code=400, detail="documents required for assignment")
            
            topic_model.load(request.model_name)
            topics, probs = topic_model.transform(request.documents)
            
            return {
                "status": "success",
                "action": "assign",
                "topics": [int(t) for t in topics],
                "probabilities": [float(p.max()) for p in probs]
            }
        
        elif request.action == "search":
            if not request.query:
                raise HTTPException(status_code=400, detail="query required for search")
            
            if not topic_model.embedding_model:
                topic_model._setup_embedding_model()
            
            query_embedding = topic_model.embedding_model.encode([request.query])[0]
            results = indexer.search(query_embedding, k=request.k)
            
            return {
                "status": "success",
                "action": "search",
                "query": request.query,
                "results": [{"doc_id": doc_id, "score": score} for doc_id, score in results]
            }
        
        elif request.action == "overview":
            topic_info = topic_model.get_topic_info()
            return {
                "status": "success",
                "action": "overview",
                **topic_info
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Topics unified error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-auto")
async def train_topics_auto(
    min_topic_size: int = 10,
    model_name: str = "vietnamese_model_v3",
    db: Session = Depends(get_db)
):
    """
    AUTO-TRAIN: Tự động load tất cả articles từ DB và train topics
    
    ✨ Features mới:
    - Auto load từ DB
    - Preprocessing nâng cao (diacritics normalization, abbreviation expansion)
    - Vietnamese tokenization (underthesea)
    - Stopwords removal
    - Better phrase extraction
    
    Example:
        POST /api/topics/train-auto?min_topic_size=15&model_name=my_model
    """
    try:
        # Load all articles from DB
        articles = db.query(Article).filter(Article.content.isnot(None)).all()
        
        if len(articles) < 10:
            raise HTTPException(status_code=400, detail=f"Need at least 10 articles, found {len(articles)}")
        
        logger.info(f"🔄 Training topics on {len(articles)} articles with improved Vietnamese NLP")
        
        # Extract documents (title + content)
        documents = []
        article_ids = []
        for art in articles:
            text = f"{art.title or ''} {art.content or ''}"
            if text.strip():
                documents.append(text)
                article_ids.append(art.id)
        
        logger.info(f"📝 Processing {len(documents)} documents with Vietnamese preprocessing...")
        
        # Train topic model (with new preprocessing pipeline)
        topic_model.min_topic_size = min_topic_size
        topics, probs = topic_model.fit(documents)
        topic_info = topic_model.get_topic_info()
        
        logger.info(f"✅ Created {len(topic_info['topics'])} topics")
        
        # Update articles with topic assignments
        updated_count = 0
        for i, (topic_id, article_id) in enumerate(zip(topics, article_ids)):
            article = db.query(Article).filter(Article.id == article_id).first()
            if article:
                article.topic_id = int(topic_id)
                # Get topic name from topic_info
                topic_row = next((t for t in topic_info['topics'] if t['topic_id'] == topic_id), None)
                if topic_row:
                    article.topic_name = topic_row['name']
                updated_count += 1
        
        db.commit()
        logger.info(f"💾 Updated {updated_count} articles with topics")
        
        # Save model
        model_path = topic_model.save(model_name)
        logger.info(f"💾 Model saved to {model_path}")
        
        return {
            "status": "success",
            "total_articles": len(articles),
            "processed_documents": len(documents),
            "topics_created": len(topic_info['topics']),
            "articles_updated": updated_count,
            "model_saved": model_path,
            "min_topic_size": min_topic_size,
            "topics": topic_info['topics'][:10],  # Top 10 topics
            "improvements": [
                "✨ Vietnamese diacritics normalization",
                "✨ Abbreviation expansion (tp.hcm → thành phố hồ chí minh)",
                "✨ Underthesea tokenization",
                "✨ Stopwords removal",
                "✨ Better phrase extraction (bigrams, trigrams)"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Training error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fit")
async def fit_topics(request: FitRequest):
    """Deprecated - use POST / with action='train' instead"""
    try:
        logger.info(f"Fitting topics on {len(request.documents)} documents")
        
        topic_model.min_topic_size = request.min_topic_size
        topics, probs = topic_model.fit(request.documents)
        
        topic_info = topic_model.get_topic_info()
        
        if request.save_model:
            model_path = topic_model.save(request.model_name)
        
        return {
            "status": "success",
            "total_documents": len(request.documents),
            "total_topics": len(topic_info['topics']),
            "model_saved": request.save_model,
            "model_path": model_path if request.save_model else None
        }
    except Exception as e:
        logger.error(f"Fit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transform")
async def transform_documents(request: TransformRequest):
    try:
        topic_model.load(request.model_name)
        
        topics, probs = topic_model.transform(request.documents)
        
        return {
            "status": "success",
            "topics": [int(t) for t in topics],
            "probabilities": [float(p.max()) for p in probs]
        }
    except Exception as e:
        logger.error(f"Transform error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_topics():
    try:
        topic_info = topic_model.get_topic_info()
        return topic_info
    except Exception as e:
        logger.error(f"Get topics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics/{topic_id}")
async def get_topic_detail(topic_id: int):
    try:
        if not topic_model.topic_model:
            raise HTTPException(status_code=400, detail="No model loaded")
        
        topic_words = topic_model.topic_model.get_topic(topic_id)
        representative_docs = topic_model.topic_model.get_representative_docs(topic_id)
        
        return {
            "topic_id": topic_id,
            "words": [{"word": w, "score": float(s)} for w, s in topic_words],
            "representative_docs": representative_docs
        }
    except Exception as e:
        logger.error(f"Get topic detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_documents(request: SearchRequest):
    try:
        if not topic_model.embedding_model:
            topic_model._setup_embedding_model()
        
        query_embedding = topic_model.embedding_model.encode([request.query])[0]
        
        results = indexer.search(query_embedding, k=request.k)
        
        return {
            "query": request.query,
            "results": [{"doc_id": doc_id, "score": score} for doc_id, score in results]
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/distribution")
async def get_topic_distribution():
    """
    tạo ra chỉ để fix 404 
    chứ chưa biết làm gì TT -vũ-
    """
    return {
        "status": "success",
        "distribution": [] 
    }
@router.get("/")
def topics_root():
    return {"topics": "ok"}