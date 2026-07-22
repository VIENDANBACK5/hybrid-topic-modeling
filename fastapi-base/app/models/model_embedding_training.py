"""Embedding Training Session Model - Track fine-tuning history for SentenceTransformers"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.models.model_base import BareBaseModel


class EmbeddingTrainingSession(BareBaseModel):
    __tablename__ = "embedding_training_sessions"

    # Override timestamps to use DateTime instead of Float
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    version = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(String(50), default="running", nullable=False)  # running, completed, failed, evaluated, deployed
    
    # Dataset info
    num_documents = Column(Integer, default=0, nullable=False)
    num_pairs = Column(Integer, default=0, nullable=False)
    
    # Hyperparameters
    epochs = Column(Integer, default=2, nullable=False)
    
    # Timing
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    
    # Final loss and metrics
    loss = Column(Float, nullable=True)
    metrics = Column(JSONB, nullable=True)  # Silhouette, Similarity, Retrieval Accuracy, etc.
    
    # Paths & Errors
    model_path = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        {'comment': 'Session logs for fine-tuning SentenceTransformer models'}
    )
