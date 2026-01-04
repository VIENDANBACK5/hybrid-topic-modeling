"""BERTopic Discovered Topics - Lưu topics tự động phát hiện"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.model_base import BareBaseModel

# Import to avoid circular dependency issues
if False:  # TYPE_CHECKING
    from app.models.model_custom_topic import CustomTopic


class BertopicDiscoveredTopic(BareBaseModel):
    __tablename__ = "bertopic_discovered_topics"
    
    # Override BareBaseModel timestamps to use DateTime instead of Float
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Training session info
    training_session_id = Column(String(100), ForeignKey('topic_training_sessions.session_id'), nullable=False, index=True)
    model_version = Column(String(50))  # Model version/name
    
    # Topic info from BERTopic
    topic_id = Column(Integer, nullable=False)  # BERTopic topic ID (-1 for outliers)
    topic_label = Column(String(512))  # Generated label (from TopicGPT if available)
    
    # Keywords and representations
    keywords = Column(JSONB, nullable=False)  # Top keywords with scores
    representative_docs = Column(JSONB)  # Representative documents
    
    # Statistics
    document_count = Column(Integer, default=0)  # Number of docs in this topic
    coherence_score = Column(Float)  # Topic coherence score
    diversity_score = Column(Float)  # Topic diversity score
    
    # Natural language description (from TopicGPT)
    natural_description = Column(Text)
    
    # Status
    is_outlier = Column(Boolean, default=False)  # True if topic_id == -1
    is_reviewed = Column(Boolean, default=False, index=True)  # Has been reviewed by human
    reviewed_by = Column(String(100))  # Who reviewed
    reviewed_at = Column(DateTime)  # When reviewed
    review_notes = Column(Text)  # Review notes
    is_converted = Column(Boolean, default=False)  # Converted to custom topic
    converted_custom_topic_id = Column(Integer, ForeignKey('custom_topics.id'), nullable=True)
    converted_at = Column(DateTime)  # When converted
    
    # Relationships
    converted_custom_topic = relationship('CustomTopic', foreign_keys=[converted_custom_topic_id], lazy='joined')
    training_session = relationship('TopicTrainingSession', foreign_keys=[training_session_id])


class ArticleBertopicTopic(BareBaseModel):
    """
    Mapping articles với BERTopic discovered topics
    """
    __tablename__ = "article_bertopic_topics"
    
    # Override to remove updated_at (not in migration)
    updated_at = None
    
    # Create created_at as DateTime
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    article_id = Column(Integer, ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, index=True)
    bertopic_topic_id = Column(Integer, ForeignKey('bertopic_discovered_topics.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Classification info
    probability = Column(Float, nullable=False)  # Probability from BERTopic
    training_session_id = Column(String(100), ForeignKey('topic_training_sessions.session_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Relationships
    article = relationship('Article', backref='bertopic_topics')
    topic = relationship('BertopicDiscoveredTopic', backref='article_mappings')
    training_session = relationship('TopicTrainingSession', foreign_keys=[training_session_id])
    
    # Constraints
    __table_args__ = (
        {'comment': 'Mapping articles to BERTopic discovered topics'}
    )


class TopicTrainingSession(BareBaseModel):
    """
    Training session metadata
    Lưu thông tin mỗi lần train BERTopic
    """
    __tablename__ = "topic_training_sessions"
    
    # Override BareBaseModel timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    session_id = Column(String(100), nullable=False, unique=True, index=True)  # UUID
    
    # Training parameters  
    model_type = Column(String(50), default='bertopic')  # bertopic, lda, nmf, etc.
    min_topic_size = Column(Integer)
    embedding_model = Column(String(255))
    use_vietnamese_tokenizer = Column(Boolean, default=False)
    use_topicgpt = Column(Boolean, default=False)
    
    # Dataset info
    num_documents = Column(Integer, nullable=False)
    num_topics_found = Column(Integer)  # Total topics discovered
    num_outliers = Column(Integer)  # Documents in outlier topic (-1)
    
    # Timing
    training_duration_seconds = Column(Float)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    
    # Quality metrics
    avg_coherence_score = Column(Float)
    avg_diversity_score = Column(Float)
    
    # Status
    status = Column(String(50), default='running')  # running, completed, failed
    error_message = Column(Text)
    
    # Model path
    model_saved_path = Column(String(512))
    
    # Metadata
    created_by = Column(String(100))
    notes = Column(Text)
    
    # Relationships
    discovered_topics = relationship('BertopicDiscoveredTopic', 
                                    primaryjoin='TopicTrainingSession.session_id == foreign(BertopicDiscoveredTopic.training_session_id)')
    article_mappings = relationship('ArticleBertopicTopic',
                                   primaryjoin='TopicTrainingSession.session_id == foreign(ArticleBertopicTopic.training_session_id)')
