"""
Hybrid Topic Training - Combine full training & incremental updates

Strategy:
- Full train: Monthly or when concept drift detected
- Transform: Daily for new articles
- Drift detection: Monitor topic distribution changes
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np

from app.services.topic.model import TopicModel
from app.services.topic.bertopic_trainer import BertopicTrainer

logger = logging.getLogger(__name__)


class HybridTopicTrainer:
    """Hybrid approach: Full training + incremental transform"""
    
    def __init__(self, db: Session):
        self.db = db
        self.full_trainer = BertopicTrainer(db)
        self.drift_threshold = 0.3  # 30% topic distribution change triggers retrain
    
    def should_retrain(self) -> Tuple[bool, str]:
        """
        Check if full retrain is needed
        
        Returns:
            (should_retrain, reason)
        """
        # Check last training time
        last_train = self._get_last_training_time()
        
        if not last_train:
            return True, "No previous training found"
        
        days_since_train = (datetime.now() - last_train).days
        
        # Force retrain after 30 days
        if days_since_train >= 30:
            return True, f"Monthly retrain due ({days_since_train} days since last)"
        
        # Check concept drift
        drift_score = self._detect_concept_drift()
        if drift_score > self.drift_threshold:
            return True, f"Concept drift detected (score: {drift_score:.2f})"
        
        # Check new data volume
        new_articles = self._count_new_articles_since(last_train)
        total_articles = self._count_total_articles()
        
        if total_articles > 0:
            new_ratio = new_articles / total_articles
            if new_ratio > 0.2:  # 20% new data
                return True, f"Significant new data ({new_ratio:.1%})"
        
        return False, "Model still fresh"
    
    def train_or_transform(
        self,
        force_full_train: bool = False,
        min_topic_size: int = 10,
        use_vietnamese_tokenizer: bool = True,
        enable_topicgpt: bool = False
    ) -> Dict:
        """
        Smart training: Full train or transform based on conditions
        
        Args:
            force_full_train: Force full training regardless of conditions
            min_topic_size: Minimum topic size for training
            use_vietnamese_tokenizer: Use Vietnamese tokenizer
            enable_topicgpt: Enable TopicGPT for natural labels
        
        Returns:
            Dict with results and method used
        """
        logger.info(" HYBRID TRAINER - Analyzing training needs...")
        
        # Rollback any pending transaction
        try:
            self.db.rollback()
        except:
            pass
        
        # Check if retrain needed
        should_retrain, reason = self.should_retrain()
        
        if force_full_train:
            should_retrain = True
            reason = "Forced full training"
        
        logger.info(f"   Decision: {'FULL TRAIN' if should_retrain else 'TRANSFORM'}")
        logger.info(f"   Reason: {reason}")
        
        if should_retrain:
            # Full training
            logger.info(" Executing FULL TRAINING...")
            result = self.full_trainer.train_from_articles(
                limit=None,  # All articles
                min_topic_size=min_topic_size,
                use_vietnamese_tokenizer=use_vietnamese_tokenizer,
                enable_topicgpt=enable_topicgpt
            )
            result['method'] = 'full_train'
            result['reason'] = reason
            return result
        else:
            # Transform new articles only
            logger.info(" Executing INCREMENTAL TRANSFORM...")
            result = self._transform_new_articles()
            result['method'] = 'transform'
            result['reason'] = reason
            return result
    
    def _transform_new_articles(self) -> Dict:
        """
        Transform new articles using existing model
        """
        from app.models import BertopicDiscoveredTopic, ArticleTopicMapping
        
        # Get last training time
        last_train = self._get_last_training_time()
        
        if not last_train:
            return {
                "status": "error",
                "message": "No existing model found. Please run full training first."
            }
        
        # Load latest model
        logger.info(" Loading existing model...")
        model = self._load_latest_model()
        
        if not model:
            return {
                "status": "error",
                "message": "Failed to load existing model"
            }
        
        # Get new articles
        query = text("""
            SELECT id, title, content, created_at
            FROM articles
            WHERE created_at > :since
            AND content IS NOT NULL
            AND LENGTH(content) > 100
            AND id NOT IN (SELECT article_id FROM article_topic_mappings)
            ORDER BY created_at DESC
        """)
        
        rows = self.db.execute(query, {"since": last_train}).fetchall()
        
        if not rows:
            logger.info(" No new articles to process")
            return {
                "status": "success",
                "message": "No new articles found",
                "processed": 0,
                "method": "transform"
            }
        
        logger.info(f"   Found {len(rows)} new articles")
        
        # Prepare documents
        article_ids = [row[0] for row in rows]
        documents = [f"{row[1] or ''}\n{row[2] or ''}" for row in rows]
        
        # Transform
        logger.info(" Transforming new articles...")
        topics, probs = model.transform(documents)
        
        # Save mappings
        logger.info(" Saving topic mappings...")
        saved = 0
        for article_id, topic_id, prob in zip(article_ids, topics, probs):
            if topic_id == -1:  # Skip outliers
                continue
            
            # Get topic from DB
            topic = self.db.query(BertopicDiscoveredTopic).filter(
                BertopicDiscoveredTopic.topic_id == topic_id
            ).first()
            
            if topic:
                mapping = ArticleTopicMapping(
                    article_id=article_id,
                    bertopic_topic_id=topic.id,
                    relevance_score=float(np.max(prob)),
                    detected_at=datetime.now()
                )
                self.db.add(mapping)
                saved += 1
        
        self.db.commit()
        
        logger.info(f" Transform completed: {saved}/{len(documents)} mapped")
        
        return {
            "status": "success",
            "message": f"Transformed {len(documents)} new articles",
            "processed": len(documents),
            "mapped": saved,
            "outliers": len([t for t in topics if t == -1]),
            "method": "transform"
        }
    
    def _detect_concept_drift(self) -> float:
        """
        Detect concept drift by comparing recent vs historical topic distribution
        
        Returns:
            Drift score (0-1, higher = more drift)
        """
        try:
            # Get topic distribution from last 7 days
            recent_query = text("""
                SELECT btm.topic_id, COUNT(*) as count
                FROM article_topic_mappings atm
                JOIN bertopic_discovered_topics btm ON atm.bertopic_topic_id = btm.id
                JOIN articles a ON atm.article_id = a.id
                WHERE a.created_at >= NOW() - INTERVAL '7 days'
                GROUP BY btm.topic_id
            """)
            
            recent_dist = {}
            for row in self.db.execute(recent_query):
                recent_dist[row[0]] = row[1]
            
            # Get historical distribution (30-7 days ago)
            historical_query = text("""
                SELECT btm.topic_id, COUNT(*) as count
                FROM article_topic_mappings atm
                JOIN bertopic_discovered_topics btm ON atm.bertopic_topic_id = btm.id
                JOIN articles a ON atm.article_id = a.id
                WHERE a.created_at >= NOW() - INTERVAL '30 days'
                AND a.created_at < NOW() - INTERVAL '7 days'
                GROUP BY btm.topic_id
            """)
            
            historical_dist = {}
            for row in self.db.execute(historical_query):
                historical_dist[row[0]] = row[1]
            
            if not recent_dist or not historical_dist:
                return 0.0
            
            # Normalize distributions
            recent_total = sum(recent_dist.values())
            historical_total = sum(historical_dist.values())
            
            recent_norm = {k: v/recent_total for k, v in recent_dist.items()}
            historical_norm = {k: v/historical_total for k, v in historical_dist.items()}
            
            # Calculate Jensen-Shannon divergence
            all_topics = set(recent_norm.keys()) | set(historical_norm.keys())
            
            drift = 0.0
            for topic in all_topics:
                r = recent_norm.get(topic, 0)
                h = historical_norm.get(topic, 0)
                if r > 0 or h > 0:
                    drift += abs(r - h)
            
            drift_score = drift / 2  # Normalize to 0-1
            
            logger.info(f"   Drift score: {drift_score:.3f}")
            return drift_score
            
        except Exception as e:
            logger.warning(f"Could not detect concept drift: {e}")
            return 0.0
    
    def _get_last_training_time(self) -> Optional[datetime]:
        """Get timestamp of last successful training"""
        try:
            query = text("""
                SELECT started_at
                FROM topic_training_sessions
                WHERE status = 'completed'
                ORDER BY started_at DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query).fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.debug(f"Could not get last training time (table may not exist): {e}")
            return None
    
    def _count_new_articles_since(self, since: datetime) -> int:
        """Count articles created after given time"""
        try:
            query = text("""
                SELECT COUNT(*)
                FROM articles
                WHERE created_at > :since
                AND content IS NOT NULL
            """)
            
            result = self.db.execute(query, {"since": since}).fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.debug(f"Could not count new articles: {e}")
            self.db.rollback()
            return 0
    
    def _count_total_articles(self) -> int:
        """Count total articles"""
        try:
            query = text("SELECT COUNT(*) FROM articles WHERE content IS NOT NULL")
            result = self.db.execute(query).fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.debug(f"Could not count total articles: {e}")
            self.db.rollback()
            return 0
    
    def _load_latest_model(self) -> Optional[TopicModel]:
        """Load latest trained model"""
        try:
            # Get latest training session
            query = text("""
                SELECT session_id, min_topic_size, use_vietnamese_tokenizer
                FROM topic_training_sessions
                WHERE status = 'completed'
                ORDER BY started_at DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query).fetchone()
            if not result:
                return None
            
            session_id, min_topic_size, use_viet = result
            
            # Load model
            from pathlib import Path
            model_path = Path(f"data/models/{session_id}")
            
            if not model_path.exists():
                logger.warning(f"Model path not found: {model_path}")
                return None
            
            model = TopicModel(
                min_topic_size=min_topic_size,
                use_vietnamese_tokenizer=use_viet
            )
            
            # Load BERTopic model
            from bertopic import BERTopic
            model.topic_model = BERTopic.load(str(model_path / "bertopic_model"))
            
            logger.info(f" Loaded model from {session_id}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return None


def get_hybrid_trainer(db: Session) -> HybridTopicTrainer:
    """Factory function"""
    return HybridTopicTrainer(db)
