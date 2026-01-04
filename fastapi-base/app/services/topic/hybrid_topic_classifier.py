"""
Hybrid Topic Classifier:
- Long content (>200 chars): Use BERTopic clustering
- Short content (<200 chars): Use GPT to classify/generate topics
"""
import logging
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class HybridTopicClassifier:
    """Combines BERTopic for long content and GPT for short content"""
    
    def __init__(self, db: Session, topicgpt_service=None):
        self.db = db
        self.topicgpt_service = topicgpt_service
        self.short_content_threshold = 200
        
    def classify_short_content(
        self, 
        content: str, 
        existing_topics: List[Dict]
    ) -> Tuple[int, str, float]:
        """
        Classify short content using GPT
        
        Args:
            content: Short text to classify
            existing_topics: List of existing topics with labels and keywords
            
        Returns:
            (topic_id, topic_label, confidence)
        """
        if not self.topicgpt_service:
            return -1, "Uncategorized", 0.0
            
        try:
            # Build prompt with existing topics
            topics_desc = "\n".join([
                f"{t['topic_id']}. {t['label']} - Keywords: {', '.join([w['word'] for w in t['keywords'][:5]])}"
                for t in existing_topics
            ])
            
            prompt = f"""Given the following topics:
{topics_desc}

Classify this short text into one of the above topics, or suggest a new topic if it doesn't fit:

Text: "{content}"

Respond in format:
topic_id: <number or "new">
topic_label: <label>
confidence: <0.0-1.0>
"""
            
            # Call GPT
            response = self.topicgpt_service.llm_client.generate(prompt)
            
            # Parse response
            lines = response.strip().split('\n')
            result = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    result[key.strip()] = value.strip()
            
            topic_id = result.get('topic_id', '-1')
            if topic_id == 'new':
                topic_id = max([t['topic_id'] for t in existing_topics]) + 1
            else:
                topic_id = int(topic_id)
                
            topic_label = result.get('topic_label', 'Uncategorized')
            confidence = float(result.get('confidence', '0.5'))
            
            logger.info(f"✅ GPT classified short content: Topic {topic_id} ({topic_label})")
            return topic_id, topic_label, confidence
            
        except Exception as e:
            logger.error(f"GPT classification failed: {e}")
            return -1, "Uncategorized", 0.0
    
    def process_short_content_batch(
        self, 
        articles: List[Dict],
        existing_topics: List[Dict]
    ) -> List[Dict]:
        """
        Process a batch of short articles
        
        Returns:
            List of {article_id, topic_id, topic_label, confidence}
        """
        results = []
        
        for article in articles:
            content = article.get('content', '')
            
            topic_id, label, confidence = self.classify_short_content(
                content, 
                existing_topics
            )
            
            results.append({
                'article_id': article['id'],
                'topic_id': topic_id,
                'topic_label': label,
                'confidence': confidence,
                'content_length': len(content)
            })
            
        return results
    
    def get_short_articles(self, limit: int = None) -> List[Dict]:
        """Get articles with short content"""
        query = text(f"""
            SELECT id, title, content, LENGTH(content) as content_length
            FROM articles
            WHERE content IS NOT NULL
            AND LENGTH(content) < :threshold
            ORDER BY created_at DESC
            {f"LIMIT {limit}" if limit else ""}
        """)
        
        rows = self.db.execute(
            query, 
            {"threshold": self.short_content_threshold}
        ).fetchall()
        
        return [
            {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'content_length': row[3]
            }
            for row in rows
        ]
    
    def save_classifications(self, classifications: List[Dict]):
        """Save GPT classifications to document_topics table"""
        for item in classifications:
            # Check if mapping exists
            check_query = text("""
                SELECT id FROM document_topics
                WHERE article_id = :article_id
            """)
            exists = self.db.execute(
                check_query,
                {"article_id": item['article_id']}
            ).fetchone()
            
            if exists:
                # Update
                update_query = text("""
                    UPDATE document_topics
                    SET topic_id = :topic_id,
                        probability = :confidence
                    WHERE article_id = :article_id
                """)
                self.db.execute(update_query, {
                    'article_id': item['article_id'],
                    'topic_id': item['topic_id'],
                    'confidence': item['confidence']
                })
            else:
                # Insert
                insert_query = text("""
                    INSERT INTO document_topics (article_id, topic_id, probability)
                    VALUES (:article_id, :topic_id, :confidence)
                """)
                self.db.execute(insert_query, {
                    'article_id': item['article_id'],
                    'topic_id': item['topic_id'],
                    'confidence': item['confidence']
                })
        
        self.db.commit()
        logger.info(f"✅ Saved {len(classifications)} GPT classifications")
