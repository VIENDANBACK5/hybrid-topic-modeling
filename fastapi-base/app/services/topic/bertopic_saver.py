"""
Service để lưu BERTopic discovered topics vào database
"""

import uuid
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.model_bertopic_discovered import (
    BertopicDiscoveredTopic,
    ArticleBertopicTopic,
    TopicTrainingSession
)
from app.models.model_article import Article

logger = logging.getLogger(__name__)


class BertopicTopicSaver:
    
    @staticmethod
    def save_training_session(
        db: Session,
        session_id: str,
        model_type: str = 'bertopic',
        min_topic_size: int = None,
        embedding_model: str = None,
        use_vietnamese_tokenizer: bool = False,
        use_topicgpt: bool = False,
        num_documents: int = 0,
        training_duration_seconds: float = None,
        started_at: datetime = None,
        notes: str = None,
        created_by: str = None
    ) -> TopicTrainingSession:

        session = TopicTrainingSession(
            session_id=session_id,
            model_type=model_type,
            min_topic_size=min_topic_size,
            embedding_model=embedding_model,
            use_vietnamese_tokenizer=use_vietnamese_tokenizer,
            use_topicgpt=use_topicgpt,
            num_documents=num_documents,
            training_duration_seconds=training_duration_seconds,
            started_at=started_at or datetime.now(),
            status='running',
            notes=notes,
            created_by=created_by
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"Saved training session: {session_id}")
        return session
    
    @staticmethod
    def update_training_session(
        db: Session,
        session_id: str,
        status: str = 'completed',
        num_topics_found: int = None,
        num_outliers: int = None,
        model_saved_path: str = None,
        error_message: str = None,
        avg_coherence_score: float = None,
        avg_diversity_score: float = None
    ):
        session = db.query(TopicTrainingSession).filter(
            TopicTrainingSession.session_id == session_id
        ).first()
        
        if not session:
            logger.error(f"Training session not found: {session_id}")
            return
        
        session.status = status
        session.completed_at = datetime.now()
        session.num_topics_found = num_topics_found
        session.num_outliers = num_outliers
        session.model_saved_path = model_saved_path
        session.error_message = error_message
        session.avg_coherence_score = avg_coherence_score
        session.avg_diversity_score = avg_diversity_score
        
        db.commit()
        logger.info(f"Updated session: {session_id} - {status}")
    
    @staticmethod
    def save_discovered_topics(
        db: Session,
        session_id: str,
        topic_info: Dict[str, Any],
        model_version: str = None
    ) -> List[BertopicDiscoveredTopic]:
        saved_topics = []
        
        for topic_data in topic_info.get('topics', []):
            topic_id = topic_data['topic_id']
            keywords_data = [
                {'word': w['word'], 'score': w['score']}
                for w in topic_data.get('words', [])
            ]
            
            existing = db.query(BertopicDiscoveredTopic).filter(
                BertopicDiscoveredTopic.training_session_id == session_id,
                BertopicDiscoveredTopic.topic_id == topic_id
            ).first()
            
            if existing:
                existing.keywords = keywords_data
                existing.representative_docs = topic_data.get('representative_docs', [])
                existing.document_count = topic_data.get('count', 0)
                existing.topic_label = topic_data.get('natural_label')
                existing.natural_description = topic_data.get('description')
                existing.updated_at = datetime.now()
                saved_topic = existing
            else:
                new_topic = BertopicDiscoveredTopic(
                    training_session_id=session_id,
                    model_version=model_version,
                    topic_id=topic_id,
                    topic_label=topic_data.get('natural_label'),
                    keywords=keywords_data,
                    representative_docs=topic_data.get('representative_docs', []),
                    document_count=topic_data.get('count', 0),
                    natural_description=topic_data.get('description'),
                    is_outlier=(topic_id == -1)
                )
                db.add(new_topic)
                saved_topic = new_topic
            
            saved_topics.append(saved_topic)
        
        db.commit()
        for topic in saved_topics:
            db.refresh(topic)
        
        logger.info(f"Saved {len(saved_topics)} topics for session {session_id}")
        return saved_topics
    
    @staticmethod
    def save_article_topic_mappings(
        db: Session,
        session_id: str,
        document_topics: List[Dict[str, Any]],
        discovered_topics: List[BertopicDiscoveredTopic]
    ):
        topic_id_to_db_id = {topic.topic_id: topic.id for topic in discovered_topics}
        
        saved_count = 0
        skipped_count = 0
        
        for doc_topic in document_topics:
            doc_id = doc_topic['doc_id']
            topic_id = doc_topic['topic_id']
            probability = doc_topic['probability']
            
            if topic_id == -1:
                skipped_count += 1
                continue
            
            # Get article_id (assuming doc_id is article.id or we have mapping)
            # This depends on how you structure your data
            # For now, assume doc_id maps to article.id
            
            bertopic_topic_id = topic_id_to_db_id.get(topic_id)
            if not bertopic_topic_id:
                logger.warning(f"Topic {topic_id} not found in discovered topics")
                skipped_count += 1
                continue
            
            # Check if mapping exists
            existing = db.query(ArticleBertopicTopic).filter(
                ArticleBertopicTopic.article_id == doc_id,
                ArticleBertopicTopic.training_session_id == session_id
            ).first()
            
            if existing:
                # Update
                existing.bertopic_topic_id = bertopic_topic_id
                existing.probability = probability
            else:
                # Create new
                mapping = ArticleBertopicTopic(
                    article_id=doc_id,
                    bertopic_topic_id=bertopic_topic_id,
                    probability=probability,
                    training_session_id=session_id
                )
                db.add(mapping)
            
            saved_count += 1
        
        db.commit()
        logger.info(f"Saved {saved_count} mappings (skipped: {skipped_count})")
    
    @staticmethod
    def save_full_training_result(
        db: Session,
        topic_model_result: Dict[str, Any],
        training_params: Dict[str, Any],
        document_topics: List[Dict[str, Any]],
        model_saved_path: str = None,
        notes: str = None
    ) -> str:
        session_id = str(uuid.uuid4())
        started_at = datetime.now()
        
        BertopicTopicSaver.save_training_session(
            db=db,
            session_id=session_id,
            model_type=training_params.get('model_type', 'bertopic'),
            min_topic_size=training_params.get('min_topic_size'),
            embedding_model=training_params.get('embedding_model'),
            use_vietnamese_tokenizer=training_params.get('use_vietnamese_tokenizer', False),
            use_topicgpt=training_params.get('use_topicgpt', False),
            num_documents=training_params.get('num_documents', 0),
            training_duration_seconds=training_params.get('training_duration_seconds'),
            started_at=started_at,
            notes=notes
        )
        
        discovered_topics = BertopicTopicSaver.save_discovered_topics(
            db=db,
            session_id=session_id,
            topic_info=topic_model_result,
            model_version=training_params.get('model_version')
        )
        
        if document_topics:
            BertopicTopicSaver.save_article_topic_mappings(
                db=db,
                session_id=session_id,
                document_topics=document_topics,
                discovered_topics=discovered_topics
            )
        
        num_topics = len([t for t in discovered_topics if t.topic_id != -1])
        num_outliers = sum(1 for t in discovered_topics if t.topic_id == -1)
        
        BertopicTopicSaver.update_training_session(
            db=db,
            session_id=session_id,
            status='completed',
            num_topics_found=num_topics,
            num_outliers=num_outliers,
            model_saved_path=model_saved_path
        )
        
        logger.info(f"Saved session {session_id}: {num_topics} topics, {num_outliers} outliers, {len(document_topics) if document_topics else 0} docs")
        return session_id


_saver_instance: Optional[BertopicTopicSaver] = None


def get_bertopic_saver() -> BertopicTopicSaver:
    global _saver_instance
    if _saver_instance is None:
        _saver_instance = BertopicTopicSaver()
    return _saver_instance
