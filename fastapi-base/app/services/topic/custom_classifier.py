"""
Custom Topic Classification Service
Hỗ trợ 3 phương pháp: Keyword, Embedding, Hybrid
"""

import time
import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import numpy as np

from app.models.model_custom_topic import CustomTopic, ArticleCustomTopic, TopicClassificationLog
from app.models.model_article import Article
from app.schemas.schema_custom_topic import (
    ClassificationMethod, 
    ClassificationScores,
    TopicClassificationResult,
    ArticleClassificationResult
)

logger = logging.getLogger(__name__)


class CustomTopicClassifier:
    def __init__(self):
        self.embedding_model = None
        self.topic_embeddings_cache: Dict[int, np.ndarray] = {}
        self._init_embedding_model()
    
    def _init_embedding_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(
                'paraphrase-multilingual-MiniLM-L12-v2',
                device='cpu'
            )
            logger.info("Embedding model loaded")
        except Exception as e:
            logger.warning(f"Could not load embedding model: {e}")
            self.embedding_model = None
    
    def classify_article(
        self,
        article: Article,
        topics: List[CustomTopic],
        method: ClassificationMethod = ClassificationMethod.HYBRID,
        min_confidence_override: Optional[float] = None
    ) -> List[TopicClassificationResult]:
        text = f"{article.title} {article.content or ''}".lower().strip()
        if not text:
            return []
        
        results = []
        
        for topic in topics:
            if not topic.is_active:
                continue
            
            start_time = time.time()
            classification_method = method if method != ClassificationMethod.MANUAL else topic.classification_method
            if classification_method == ClassificationMethod.KEYWORD:
                keyword_score = self._classify_keyword(text, topic)
                embedding_score = None
                final_score = keyword_score
                
            elif classification_method == ClassificationMethod.EMBEDDING:
                keyword_score = None
                embedding_score = self._classify_embedding(text, topic)
                final_score = embedding_score
                
            elif classification_method == ClassificationMethod.HYBRID:
                keyword_score = self._classify_keyword(text, topic)
                if keyword_score < 0.05:
                    embedding_score = 0.0
                    final_score = 0.0
                else:
                    embedding_score = self._classify_embedding(text, topic)
                    final_score = (
                        topic.keywords_weight * keyword_score +
                        topic.example_weight * embedding_score
                    ) / (topic.keywords_weight + topic.example_weight)
            
            else:
                logger.warning(f"Unknown classification method: {classification_method}")
                continue
            
            if topic.negative_keywords:
                has_negative = any(neg_kw.lower() in text for neg_kw in topic.negative_keywords)
                if has_negative:
                    final_score *= 0.3
            
            min_conf = min_confidence_override if min_confidence_override is not None else topic.min_confidence
            is_accepted = final_score >= min_conf
            processing_time = int((time.time() - start_time) * 1000)
            result = TopicClassificationResult(
                topic_id=topic.id,
                topic_name=topic.name,
                confidence=round(final_score, 4),
                method=classification_method,
                is_accepted=is_accepted,
                scores=ClassificationScores(
                    keyword_score=round(keyword_score, 4) if keyword_score is not None else 0.0,
                    embedding_score=round(embedding_score, 4) if embedding_score is not None else None,
                    llm_score=None,
                    final_score=round(final_score, 4)
                )
            )
            
            results.append(result)
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
    
    def classify_articles_bulk(
        self,
        articles: List[Article],
        topics: List[CustomTopic],
        method: ClassificationMethod = ClassificationMethod.HYBRID,
        min_confidence_override: Optional[float] = None
    ) -> List[ArticleClassificationResult]:
        results = []
        
        for article in articles:
            start_time = time.time()
            
            topic_results = self.classify_article(
                article=article,
                topics=topics,
                method=method,
                min_confidence_override=min_confidence_override
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            result = ArticleClassificationResult(
                article_id=article.id,
                article_title=article.title,
                topics=topic_results,
                processing_time_ms=processing_time
            )
            
            results.append(result)
        
        return results
    
    def save_classification_results(
        self,
        db: Session,
        results: List[ArticleClassificationResult],
        save_logs: bool = True
    ) -> Dict[str, int]:
        """
        Lưu kết quả phân loại vào database
        
        Returns:
            Summary dict: {"saved": 100, "skipped": 20, "errors": 5}
        """
        summary = {"saved": 0, "skipped": 0, "errors": 0}
        
        for article_result in results:
            article_id = article_result.article_id
            
            for topic_result in article_result.topics:
                # Only save accepted results
                if not topic_result.is_accepted:
                    summary["skipped"] += 1
                    continue
                
                try:
                    # Check if mapping exists
                    existing = db.query(ArticleCustomTopic).filter(
                        ArticleCustomTopic.article_id == article_id,
                        ArticleCustomTopic.topic_id == topic_result.topic_id
                    ).first()
                    
                    if existing:
                        # Update existing
                        existing.confidence = topic_result.confidence
                        existing.method = topic_result.method.value
                        existing.keyword_score = topic_result.scores.keyword_score if topic_result.scores else None
                        existing.embedding_score = topic_result.scores.embedding_score if topic_result.scores else None
                    else:
                        # Create new mapping
                        mapping = ArticleCustomTopic(
                            article_id=article_id,
                            topic_id=topic_result.topic_id,
                            confidence=topic_result.confidence,
                            method=topic_result.method.value,
                            keyword_score=topic_result.scores.keyword_score if topic_result.scores else None,
                            embedding_score=topic_result.scores.embedding_score if topic_result.scores else None,
                            is_manual=False
                        )
                        db.add(mapping)
                    
                    # Save log
                    if save_logs:
                        log = TopicClassificationLog(
                            article_id=article_id,
                            topic_id=topic_result.topic_id,
                            confidence=topic_result.confidence,
                            method=topic_result.method.value,
                            accepted=True,
                            scores_detail=topic_result.scores.dict() if topic_result.scores else {},
                            processing_time_ms=article_result.processing_time_ms
                        )
                        db.add(log)
                    
                    summary["saved"] += 1
                    
                except Exception as e:
                    logger.error(f"Error saving classification for article {article_id}, topic {topic_result.topic_id}: {e}")
                    summary["errors"] += 1
                    db.rollback()
                    continue
        
        # Commit all changes
        try:
            db.commit()
            
            # Update topic article counts
            self._update_topic_counts(db, results)
            
        except Exception as e:
            logger.error(f"Error committing classification results: {e}")
            db.rollback()
            summary["errors"] += summary["saved"]
            summary["saved"] = 0
        
        return summary
    
    def _update_topic_counts(self, db: Session, results: List[ArticleClassificationResult]):
        try:
            from sqlalchemy import func
            counts = db.query(
                ArticleCustomTopic.topic_id,
                func.count(ArticleCustomTopic.article_id).label('count')
            ).group_by(ArticleCustomTopic.topic_id).all()
            
            for topic_id, count in counts:
                db.query(CustomTopic).filter(CustomTopic.id == topic_id).update({
                    'article_count': count,
                    'last_classified_at': func.now()
                })
            db.commit()
            logger.info(f"Updated counts for {len(counts)} topics")
            
        except Exception as e:
            logger.error(f"Error updating topic counts: {e}")
            db.rollback()
    
    def _classify_keyword(self, text: str, topic: CustomTopic) -> float:
        if not topic.keywords:
            return 0.0
        
        text_lower = text.lower()
        matched_count = sum(1 for kw in topic.keywords if kw.lower() in text_lower)
        return matched_count / len(topic.keywords)
    
    def _classify_embedding(self, text: str, topic: CustomTopic) -> float:
        if not self.embedding_model:
            logger.warning("Embedding model unavailable")
            return self._classify_keyword(text, topic)
        
        try:
            if topic.id not in self.topic_embeddings_cache:
                topic_texts = []
                if topic.keywords:
                    topic_texts.extend(topic.keywords)
                
                # Add example docs
                if topic.example_docs:
                    topic_texts.extend(topic.example_docs)
                
                if not topic_texts:
                    return 0.0
                
                # Compute average embedding
                topic_embeddings = self.embedding_model.encode(topic_texts)
                topic_embedding_avg = np.mean(topic_embeddings, axis=0)
                
                # Cache it
                self.topic_embeddings_cache[topic.id] = topic_embedding_avg
            
            # Get article embedding
            article_embedding = self.embedding_model.encode([text[:1000]])[0]  # Truncate for speed
            
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity(
                [article_embedding],
                [self.topic_embeddings_cache[topic.id]]
            )[0][0]
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Embedding classification error: {e}")
            return 0.0
    
    def clear_cache(self):
        self.topic_embeddings_cache.clear()
        logger.info("Cache cleared")


# Singleton instance
_classifier_instance: Optional[CustomTopicClassifier] = None


def get_classifier() -> CustomTopicClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = CustomTopicClassifier()
    return _classifier_instance


def reset_classifier():
    global _classifier_instance
    if _classifier_instance:
        _classifier_instance.clear_cache()
    _classifier_instance = None
