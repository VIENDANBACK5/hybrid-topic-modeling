"""
Global Model Manager - Load models 1 lần duy nhất
Các file khác chỉ cần: from app.core.models import topic_model, embedding_model
"""
import logging

logger = logging.getLogger(__name__)

# ===== SINGLETON INSTANCES - Load 1 lần, dùng mãi =====
topic_model = None
embedding_model = None
rag_service = None

def init_models():
    """Load tất cả models 1 lần khi app khởi động"""
    global topic_model, embedding_model, rag_service
    
    if topic_model is None:
        try:
            from app.services.topic.model import TopicModel
            logger.info("🔄 Loading TopicModel...")
            topic_model = TopicModel()
            
            # Auto-load pre-trained model if exists
            try:
                topic_model.load(model_name="baohungyen_all_categories/model")
                logger.info("✅ TopicModel loaded with baohungyen_all_categories")
            except Exception as e:
                logger.warning(f"Could not load model: {e}")
                logger.info("✅ TopicModel initialized (no model yet)")
        except Exception as e:
            logger.error(f"Failed to load TopicModel: {e}")
    
    if embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("🔄 Loading SentenceTransformer...")
            embedding_model = SentenceTransformer("keepitreal/vietnamese-sbert")
            embedding_model.max_seq_length = 128
            logger.info("✅ SentenceTransformer loaded")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
    
    if rag_service is None:
        try:
            from app.services.rag_service import RAGService
            logger.info("🔄 Loading RAGService...")
            rag_service = RAGService()
            if embedding_model:
                rag_service.embedding_model = embedding_model
            logger.info("✅ RAGService loaded")
        except Exception as e:
            logger.error(f"Failed to load RAGService: {e}")

# Load models ngay khi import module này
init_models()
