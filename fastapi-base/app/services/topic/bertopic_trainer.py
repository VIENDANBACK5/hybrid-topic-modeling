"""
BERTopic Training Service - Train và discover topics mới từ articles
"""
import logging
import uuid
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.topic.model import TopicModel
from app.services.topic.bertopic_saver import BertopicTopicSaver

logger = logging.getLogger(__name__)


class BertopicTrainer:
    """Service để train BERTopic và discover topics mới"""
    
    def __init__(self, db: Session):
        self.db = db
        self.saver = BertopicTopicSaver()
    
    def train_from_articles(
        self,
        limit: Optional[int] = None,
        min_topic_size: int = 10,
        use_vietnamese_tokenizer: bool = True,
        enable_topicgpt: bool = False,
        from_processed_file: Optional[str] = None
    ) -> Dict:
        """
        Train BERTopic từ articles trong database hoặc processed file
        
        Args:
            limit: Số articles tối đa để train (None = all)
            min_topic_size: Minimum topic size (default: 10)
            use_vietnamese_tokenizer: Dùng Underthesea tokenizer (default: True)
            enable_topicgpt: Dùng GPT để generate topic labels (default: False)
            from_processed_file: Path to processed file (None = use database)
        
        Returns:
            Dict với training results và discovered topics
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        started_at = datetime.now()
        
        logger.info("=" * 60)
        logger.info(f" STARTING BERTOPIC TRAINING - Session: {session_id}")
        logger.info("=" * 60)
        
        try:
            # 1. Load articles from database or processed file
            logger.info("\n Step 1/4: Loading articles...")
            
            if from_processed_file:
                logger.info(f"   Loading from processed file: {from_processed_file}")
                from app.services.etl.data_pipeline import get_data_pipeline
                
                pipeline = get_data_pipeline(self.db)
                load_result = pipeline.get_processed_data_for_training(
                    processed_file=from_processed_file,
                    limit=limit
                )
                
                if load_result["status"] != "success":
                    return {
                        "status": "error",
                        "message": load_result.get("error", "Failed to load processed file"),
                        "session_id": session_id
                    }
                
                documents = load_result["documents"]
                metadata = load_result["metadata"]
                article_ids = [m.get("id") for m in metadata if m.get("id")]
                
                logger.info(f"    Loaded {len(documents)} documents from file")
                
            else:
                logger.info("   Loading from database...")
                query = text("""
                    SELECT id, title, content
                    FROM articles
                    WHERE content IS NOT NULL
                    AND LENGTH(content) > 100
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                
                rows = self.db.execute(query, {"limit": limit or 999999}).fetchall()
                
                if not rows:
                    logger.warning(" No articles found for training")
                    return {
                        "status": "error",
                        "message": "No articles found",
                        "session_id": session_id
                    }
                
                # Prepare documents
                article_ids = [row[0] for row in rows]
                documents = []
                for row in rows:
                    title = row[1] or ""
                    content = row[2] or ""
                    # Combine title + content
                    doc = f"{title}\n{content}"
                    documents.append(doc)
                
                logger.info(f"    Loaded {len(documents)} articles from database")
            
            # 2. Save training session
            logger.info("\n Step 2/4: Creating training session...")
            self.saver.save_training_session(
                db=self.db,
                session_id=session_id,
                model_type='bertopic',
                min_topic_size=min_topic_size,
                embedding_model="paraphrase-multilingual-MiniLM-L12-v2",
                use_vietnamese_tokenizer=use_vietnamese_tokenizer,
                use_topicgpt=enable_topicgpt,
                num_documents=len(documents),
                started_at=started_at,
                notes=f"Training on {len(documents)} articles",
                created_by="orchestrator"
            )
            logger.info(f"    Session created: {session_id}")
            
            # 3. Initialize and train BERTopic
            logger.info("\n Step 3/4: Training BERTopic model...")
            logger.info(f"   Configuration:")
            logger.info(f"   - Documents: {len(documents)}")
            logger.info(f"   - Min topic size: {min_topic_size}")
            logger.info(f"   - Vietnamese tokenizer: {use_vietnamese_tokenizer}")
            logger.info(f"   - TopicGPT: {enable_topicgpt}")
            
            topic_model = TopicModel(
                min_topic_size=min_topic_size,
                use_vietnamese_tokenizer=use_vietnamese_tokenizer,
                enable_topicgpt=enable_topicgpt
            )
            
            # Train và auto-save to DB
            topics, probs = topic_model.fit(
                documents=documents,
                db=self.db,
                save_to_db=True,
                article_ids=article_ids
            )
            
            # 4. Get results
            logger.info("\n Step 4/4: Analyzing results...")
            num_topics = len(set(topics)) - 1  # Exclude outlier topic (-1)
            num_outliers = sum(1 for t in topics if t == -1)
            
            # Get topic info - returns dict with topics list
            topic_info = topic_model.get_topic_info()
            
            # Update training session
            training_duration = (datetime.now() - started_at).total_seconds()
            self.saver.update_training_session(
                db=self.db,
                session_id=session_id,
                status='completed',
                num_topics_found=num_topics,
                num_outliers=num_outliers,
                model_saved_path=f"data/models/{session_id}"
            )
            
            logger.info("\n" + "=" * 60)
            logger.info(f" TRAINING COMPLETED")
            logger.info(f"   - Topics discovered: {num_topics}")
            logger.info(f"   - Outliers: {num_outliers}")
            logger.info(f"   - Duration: {training_duration:.1f}s")
            logger.info("=" * 60)
            
            # Format results - topic_info is already formatted dict
            discovered_topics = []
            for topic_result in topic_info['topics']:
                discovered_topics.append({
                    "topic_id": topic_result['topic_id'],
                    "count": topic_result['count'],
                    "keywords": [w['word'] for w in topic_result['words'][:10]],
                    "natural_label": topic_result.get('natural_label', ''),
                    "description": topic_result.get('description', '')
                })
            
            # 5. Auto-classify short content with GPT
            short_docs_classified = 0
            if enable_topicgpt:
                logger.info("\n Step 5/5: Classifying short content with GPT...")
                short_docs_classified = self._classify_short_content_with_gpt(
                    session_id=session_id,
                    discovered_topics=discovered_topics
                )
                logger.info(f" Classified {short_docs_classified} short documents")
            
            return {
                "status": "completed",
                "session_id": session_id,
                "training": {
                    "num_documents": len(documents),
                    "num_topics": num_topics,
                    "num_outliers": num_outliers,
                    "duration_seconds": training_duration,
                    "short_docs_classified": short_docs_classified
                },
                "config": {
                    "min_topic_size": min_topic_size,
                    "vietnamese_tokenizer": use_vietnamese_tokenizer,
                    "topicgpt": enable_topicgpt
                },
                "topics": discovered_topics[:10]  # Top 10 topics
            }
            
        except Exception as e:
            logger.error(f" Training failed: {e}", exc_info=True)
            
            # Update session as failed
            self.saver.update_training_session(
                db=self.db,
                session_id=session_id,
                status='failed',
                error_message=str(e)
            )
            
            return {
                "status": "failed",
                "session_id": session_id,
                "error": str(e)
            }
    
    def _classify_short_content_with_gpt(
        self,
        session_id: str,
        discovered_topics: List[Dict]
    ) -> int:
        """
        Classify short content (<200 chars) using GPT into discovered topics
        
        Args:
            session_id: Training session ID
            discovered_topics: List of discovered topics with labels and keywords
        
        Returns:
            Number of short documents classified
        """
        from app.services.topic.topicgpt_service import TopicGPTService
        
        # Get short articles that weren't used in training (LENGTH < 200)
        query = text("""
            SELECT id, content, LENGTH(content) as len
            FROM articles
            WHERE LENGTH(content) < 200 
              AND LENGTH(content) > 20
              AND content IS NOT NULL
              AND id NOT IN (
                SELECT article_id 
                FROM article_bertopic_topics 
                WHERE training_session_id = :session_id
              )
            LIMIT 500
        """)
        
        result = self.db.execute(query, {"session_id": session_id})
        short_articles = result.fetchall()
        
        if not short_articles:
            logger.info("   No short articles to classify")
            return 0
        
        logger.info(f"   Found {len(short_articles)} short articles to classify")
        
        # Prepare topic context for GPT
        topics_context = []
        for topic in discovered_topics:
            topics_context.append({
                "topic_id": topic['topic_id'],
                "label": topic['natural_label'],
                "keywords": topic['keywords'][:5]
            })
        
        # Initialize GPT service
        gpt_service = TopicGPTService()
        
        classified_count = 0
        outlier_count = 0
        error_count = 0
        batch_size = 10
        
        for i in range(0, len(short_articles), batch_size):
            batch = short_articles[i:i+batch_size]
            
            for article in batch:
                try:
                    # Ask GPT to classify
                    prompt = f"""Given these topics:
{chr(10).join([f"- Topic {t['topic_id']}: {t['label']} (keywords: {', '.join(t['keywords'])})" for t in topics_context])}

Classify this short text into ONE topic ID (just return the number):
"{article.content}"

Return format: <topic_id>
If none match well, return: -1"""
                    
                    response = gpt_service.client.chat.completions.create(
                        model=gpt_service.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=10
                    )
                    
                    predicted_topic_id = int(response.choices[0].message.content.strip())
                    
                    if predicted_topic_id == -1:
                        outlier_count += 1
                        continue  # Skip outliers
                    
                    # Get bertopic_topic_id from discovered_topics table
                    topic_query = text("""
                        SELECT id FROM bertopic_discovered_topics
                        WHERE topic_id = :topic_id AND session_id = :session_id
                        LIMIT 1
                    """)
                    topic_result = self.db.execute(topic_query, {
                        "topic_id": predicted_topic_id,
                        "session_id": session_id
                    }).first()
                    
                    if not topic_result:
                        logger.warning(f"   Topic {predicted_topic_id} not found in DB")
                        error_count += 1
                        continue  # Topic not found
                    
                    bertopic_topic_id = topic_result[0]
                    
                    # Save to database
                    insert_query = text("""
                        INSERT INTO article_bertopic_topics 
                        (article_id, bertopic_topic_id, training_session_id, probability, created_at)
                        VALUES (:article_id, :bertopic_topic_id, :training_session_id, 0.8, NOW())
                        ON CONFLICT (article_id, training_session_id) 
                        DO UPDATE SET bertopic_topic_id = :bertopic_topic_id, probability = 0.8
                    """)
                    
                    self.db.execute(insert_query, {
                        "article_id": article.id,
                        "bertopic_topic_id": bertopic_topic_id,
                        "training_session_id": session_id
                    })
                    
                    classified_count += 1
                    
                    if classified_count % 50 == 0:
                        logger.info(f"   Classified {classified_count}/{len(short_articles)}...")
                        self.db.commit()
                        
                except Exception as e:
                    logger.warning(f"   Failed to classify article {article.id}: {e}")
                    error_count += 1
                    continue
        
        self.db.commit()
        logger.info(f"   Summary: {classified_count} classified, {outlier_count} outliers, {error_count} errors")
        return classified_count



def get_trainer(db: Session) -> BertopicTrainer:
    """Get trainer instance"""
    return BertopicTrainer(db)

