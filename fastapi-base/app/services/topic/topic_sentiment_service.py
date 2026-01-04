"""
Topic Sentiment Service
Link sentiment analysis với custom topics để tổng hợp cảm xúc theo chủ đề
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.model_article import Article
from app.models.model_sentiment import SentimentAnalysis
from app.models.model_custom_topic import CustomTopic, ArticleCustomTopic
from app.models.model_statistics import TopicMentionStats
from app.services.sentiment import get_sentiment_analyzer

logger = logging.getLogger(__name__)


class TopicSentimentService:
    def __init__(self, db: Session):
        self.db = db
        self.sentiment_analyzer = get_sentiment_analyzer()
    
    def analyze_and_link_article(self, article_id: int) -> Optional[SentimentAnalysis]:
        """
        Phân tích sentiment cho article và link với topics của nó
        """
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if not article:
            logger.warning(f"Article {article_id} not found")
            return None
        
        # Get topics cho article này
        article_topics = self.db.query(ArticleCustomTopic).filter(
            ArticleCustomTopic.article_id == article_id,
            ArticleCustomTopic.is_manual == False  # Only auto-classified
        ).all()
        
        # Analyze sentiment
        text = f"{article.title or ''} {article.content or ''}"
        sentiment_result = self.sentiment_analyzer.analyze(text)
        
        # Create sentiment record
        sentiment = SentimentAnalysis(
            article_id=article.id,
            source_url=article.url,
            source_domain=article.domain,
            title=article.title,
            emotion=sentiment_result.emotion,
            emotion_vi=sentiment_result.emotion_vi,
            emotion_icon=sentiment_result.icon,
            sentiment_group=sentiment_result.group,
            sentiment_group_vi=sentiment_result.group_vi,
            confidence=sentiment_result.confidence,
            emotion_scores=sentiment_result.all_scores,
            category=article.category,
            # Link to primary topic (highest confidence)
            topic_id=article_topics[0].topic_id if article_topics else None,
            topic_name=self._get_topic_name(article_topics[0].topic_id) if article_topics else None,
            published_date=datetime.fromtimestamp(article.published_date) if article.published_date else None,
            content_snippet=(article.content or '')[:200] if article.content else None
        )
        
        self.db.add(sentiment)
        self.db.commit()
        self.db.refresh(sentiment)
        
        logger.info(f"Sentiment analyzed for article {article_id}: {sentiment.emotion} (topic: {sentiment.topic_name})")
        return sentiment
    
    def analyze_articles_bulk(self, article_ids: List[int]) -> int:
        """
        Phân tích sentiment cho nhiều articles
        Returns: Số lượng đã phân tích
        """
        count = 0
        for article_id in article_ids:
            try:
                result = self.analyze_and_link_article(article_id)
                if result:
                    count += 1
            except Exception as e:
                logger.error(f"Failed to analyze article {article_id}: {e}")
                continue
        
        logger.info(f"Analyzed sentiment for {count}/{len(article_ids)} articles")
        return count
    
    def update_topic_sentiment_stats(
        self,
        topic_id: int,
        period_type: str = "all_time"
    ) -> Optional[TopicMentionStats]:
        """
        Tổng hợp sentiment theo topic
        Populate bảng topic_mention_stats
        """
        topic = self.db.query(CustomTopic).filter(CustomTopic.id == topic_id).first()
        if not topic:
            return None
        
        # Get all sentiments for this topic
        sentiments = self.db.query(SentimentAnalysis).filter(
            SentimentAnalysis.topic_id == topic_id
        ).all()
        
        if not sentiments:
            logger.info(f"No sentiments found for topic {topic_id}")
            return None
        
        # Count by sentiment group
        positive_count = sum(1 for s in sentiments if s.sentiment_group == 'positive')
        negative_count = sum(1 for s in sentiments if s.sentiment_group == 'negative')
        neutral_count = len(sentiments) - positive_count - negative_count
        
        # Emotion breakdown
        from collections import Counter
        emotion_counts = Counter(s.emotion for s in sentiments)
        emotion_breakdown = dict(emotion_counts)
        
        # Unique sources
        unique_sources = len(set(s.source_domain for s in sentiments if s.source_domain))
        
        # Sentiment score
        sentiment_score = (positive_count - negative_count) / len(sentiments) if sentiments else 0.0
        
        # Check if stats exists
        existing = self.db.query(TopicMentionStats).filter(
            TopicMentionStats.topic_id == topic_id,
            TopicMentionStats.period_type == period_type
        ).first()
        
        if existing:
            # Update
            existing.total_mentions = len(sentiments)
            existing.unique_sources = unique_sources
            existing.positive_mentions = positive_count
            existing.negative_mentions = negative_count
            existing.neutral_mentions = neutral_count
            existing.emotion_breakdown = emotion_breakdown
            existing.sentiment_score = round(sentiment_score, 4)
            stats = existing
        else:
            # Create new
            stats = TopicMentionStats(
                period_type=period_type,
                period_start=date.today(),
                period_end=date.today(),
                topic_id=topic_id,
                topic_name=topic.name,
                category=topic.parent.name if topic.parent else None,
                total_mentions=len(sentiments),
                unique_sources=unique_sources,
                positive_mentions=positive_count,
                negative_mentions=negative_count,
                neutral_mentions=neutral_count,
                emotion_breakdown=emotion_breakdown,
                sentiment_score=round(sentiment_score, 4)
            )
            self.db.add(stats)
        
        self.db.commit()
        logger.info(f"Updated sentiment stats for topic {topic.name}: {len(sentiments)} mentions, score: {sentiment_score:.2f}")
        return stats
    
    def update_all_topics_stats(self, period_type: str = "all_time") -> int:
        """
        Update sentiment stats cho tất cả topics
        """
        topics = self.db.query(CustomTopic).filter(CustomTopic.is_active == True).all()
        count = 0
        
        for topic in topics:
            try:
                result = self.update_topic_sentiment_stats(topic.id, period_type)
                if result:
                    count += 1
            except Exception as e:
                logger.error(f"Failed to update stats for topic {topic.name}: {e}")
                continue
        
        logger.info(f"Updated sentiment stats for {count}/{len(topics)} topics")
        return count
    
    def get_topic_sentiment_summary(self, topic_id: int) -> Dict:
        """
        Lấy summary cảm xúc cho 1 topic
        """
        sentiments = self.db.query(SentimentAnalysis).filter(
            SentimentAnalysis.topic_id == topic_id
        ).all()
        
        if not sentiments:
            return {
                "topic_id": topic_id,
                "total": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "sentiment_score": 0.0,
                "emotions": {}
            }
        
        positive = sum(1 for s in sentiments if s.sentiment_group == 'positive')
        negative = sum(1 for s in sentiments if s.sentiment_group == 'negative')
        neutral = len(sentiments) - positive - negative
        
        from collections import Counter
        emotion_counts = Counter(s.emotion for s in sentiments)
        
        return {
            "topic_id": topic_id,
            "total": len(sentiments),
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "positive_ratio": round(positive / len(sentiments), 3) if sentiments else 0.0,
            "negative_ratio": round(negative / len(sentiments), 3) if sentiments else 0.0,
            "sentiment_score": round((positive - negative) / len(sentiments), 3) if sentiments else 0.0,
            "emotions": dict(emotion_counts.most_common(10))
        }
    
    def _get_topic_name(self, topic_id: int) -> Optional[str]:
        topic = self.db.query(CustomTopic).filter(CustomTopic.id == topic_id).first()
        return topic.name if topic else None


def get_topic_sentiment_service(db: Session) -> TopicSentimentService:
    return TopicSentimentService(db)
