"""
TopicGPT Enhancement Service - Tận dụng hết khả năng TopicGPT
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.topic.topicgpt_service import get_topicgpt_service

logger = logging.getLogger(__name__)


class TopicGPTEnhancer:
    """Service tận dụng đầy đủ khả năng TopicGPT"""
    
    def __init__(self, db: Session):
        self.db = db
        self.topicgpt = get_topicgpt_service()
    
    def enhance_custom_topics(self) -> Dict:
        """
        Enhance 12 custom topics với TopicGPT:
        - Generate descriptions
        - Suggest better names
        - Extract additional keywords
        """
        logger.info("🎨 Enhancing custom topics with TopicGPT...")
        
        if not self.topicgpt.is_available():
            logger.warning("TopicGPT not available (no API key)")
            return {
                "status": "skipped",
                "message": "OPENAI_API_KEY not configured"
            }
        
        try:
            # Get all custom topics
            query = text("""
                SELECT id, name, description, keywords
                FROM custom_topics
                ORDER BY id
            """)
            topics = self.db.execute(query).fetchall()
            
            enhanced_count = 0
            for topic in topics:
                topic_id, name, description, keywords = topic
                
                # Generate better description if empty or too short
                if not description or len(description) < 50:
                    logger.info(f"   Generating description for: {name}")
                    
                    # Get sample articles for this topic
                    sample_query = text("""
                        SELECT a.title, a.content
                        FROM articles a
                        JOIN article_custom_topics act ON a.id = act.article_id
                        WHERE act.custom_topic_id = :topic_id
                        LIMIT 3
                    """)
                    samples = self.db.execute(sample_query, {"topic_id": topic_id}).fetchall()
                    sample_docs = [f"{s[0]}\n{s[1][:200]}" for s in samples]
                    
                    new_description = self.topicgpt.generate_topic_description(
                        topic_label=name,
                        keywords=keywords or [],
                        representative_docs=sample_docs if sample_docs else None
                    )
                    
                    if new_description:
                        update_query = text("""
                            UPDATE custom_topics
                            SET description = :description,
                                updated_at = NOW()
                            WHERE id = :topic_id
                        """)
                        self.db.execute(update_query, {
                            "description": new_description,
                            "topic_id": topic_id
                        })
                        enhanced_count += 1
                        logger.info(f"   ✅ Enhanced: {name}")
            
            self.db.commit()
            
            return {
                "status": "success",
                "enhanced": enhanced_count,
                "total": len(topics)
            }
            
        except Exception as e:
            logger.error(f"Failed to enhance custom topics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def refine_discovered_topics(
        self,
        session_id: Optional[str] = None,
        merge_similar: bool = True
    ) -> Dict:
        """
        Refine discovered topics với TopicGPT:
        - Suggest merging similar topics
        - Generate better labels
        - Categorize topics
        """
        logger.info("🔧 Refining discovered topics with TopicGPT...")
        
        if not self.topicgpt.is_available():
            return {
                "status": "skipped",
                "message": "TopicGPT not available"
            }
        
        try:
            # Get topics from latest session if not specified
            if session_id:
                query = text("""
                    SELECT id, topic_id, topic_label, keywords, document_count
                    FROM bertopic_discovered_topics
                    WHERE training_session_id = :session_id
                    AND topic_id != -1
                    ORDER BY document_count DESC
                """)
                topics_data = self.db.execute(query, {"session_id": session_id}).fetchall()
            else:
                query = text("""
                    SELECT bdt.id, bdt.topic_id, bdt.topic_label, bdt.keywords, bdt.document_count
                    FROM bertopic_discovered_topics bdt
                    JOIN (
                        SELECT training_session_id, MAX(created_at) as max_created
                        FROM bertopic_discovered_topics
                        GROUP BY training_session_id
                        ORDER BY max_created DESC
                        LIMIT 1
                    ) latest ON bdt.training_session_id = latest.training_session_id
                    WHERE bdt.topic_id != -1
                    ORDER BY bdt.document_count DESC
                """)
                topics_data = self.db.execute(query).fetchall()
            
            if not topics_data:
                return {
                    "status": "skipped",
                    "message": "No topics found"
                }
            
            # Format topics for analysis
            topics_list = []
            for row in topics_data[:30]:  # Top 30 topics
                db_id, topic_id, label, keywords, count = row
                topics_list.append({
                    "db_id": db_id,
                    "topic_id": topic_id,
                    "label": label or f"Topic {topic_id}",
                    "keywords": keywords,
                    "count": count
                })
            
            results = {
                "status": "success",
                "analyzed": len(topics_list),
                "merge_suggestions": []
            }
            
            # Suggest merges if enabled
            if merge_similar and len(topics_list) > 1:
                logger.info(f"   Analyzing {len(topics_list)} topics for merges...")
                merge_result = self.topicgpt.refine_topics(
                    topics=topics_list,
                    merge_threshold=0.85
                )
                
                if merge_result.get("merges"):
                    results["merge_suggestions"] = merge_result["merges"]
                    logger.info(f"   ✅ Found {len(merge_result['merges'])} merge suggestions")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to refine topics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def categorize_articles(
        self,
        limit: int = 100,
        uncategorized_only: bool = True
    ) -> Dict:
        """
        Categorize articles using TopicGPT
        """
        logger.info("📑 Categorizing articles with TopicGPT...")
        
        if not self.topicgpt.is_available():
            return {
                "status": "skipped",
                "message": "TopicGPT not available"
            }
        
        try:
            # Get articles
            if uncategorized_only:
                query = text("""
                    SELECT id, title, content
                    FROM articles
                    WHERE category IS NULL
                    AND content IS NOT NULL
                    LIMIT :limit
                """)
            else:
                query = text("""
                    SELECT id, title, content
                    FROM articles
                    WHERE content IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
            
            articles = self.db.execute(query, {"limit": limit}).fetchall()
            
            if not articles:
                return {
                    "status": "skipped",
                    "message": "No articles to categorize"
                }
            
            categorized_count = 0
            for article_id, title, content in articles:
                text_to_analyze = f"{title}\n{content[:500]}"
                
                result = self.topicgpt.categorize_content(text_to_analyze)
                
                if result and result.get("category") != "Unknown":
                    # Save category
                    update_query = text("""
                        UPDATE articles
                        SET category = :category,
                            updated_at = NOW()
                        WHERE id = :article_id
                    """)
                    self.db.execute(update_query, {
                        "category": result["category"],
                        "article_id": article_id
                    })
                    categorized_count += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "categorized": categorized_count,
                "total": len(articles)
            }
            
        except Exception as e:
            logger.error(f"Failed to categorize articles: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def generate_summaries(
        self,
        limit: int = 50,
        unsummarized_only: bool = True
    ) -> Dict:
        """
        Generate summaries for articles using TopicGPT
        """
        logger.info("📝 Generating summaries with TopicGPT...")
        
        if not self.topicgpt.is_available():
            return {
                "status": "skipped",
                "message": "TopicGPT not available"
            }
        
        try:
            # Get articles
            if unsummarized_only:
                query = text("""
                    SELECT id, title, content
                    FROM articles
                    WHERE summary IS NULL
                    AND content IS NOT NULL
                    AND LENGTH(content) > 200
                    LIMIT :limit
                """)
            else:
                query = text("""
                    SELECT id, title, content
                    FROM articles
                    WHERE content IS NOT NULL
                    AND LENGTH(content) > 200
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
            
            articles = self.db.execute(query, {"limit": limit}).fetchall()
            
            if not articles:
                return {
                    "status": "skipped",
                    "message": "No articles to summarize"
                }
            
            summarized_count = 0
            for article_id, title, content in articles:
                summary = self.topicgpt.summarize_content(
                    text=f"{title}\n\n{content}",
                    max_length=100
                )
                
                if summary:
                    update_query = text("""
                        UPDATE articles
                        SET summary = :summary,
                            updated_at = NOW()
                        WHERE id = :article_id
                    """)
                    self.db.execute(update_query, {
                        "summary": summary,
                        "article_id": article_id
                    })
                    summarized_count += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "summarized": summarized_count,
                "total": len(articles)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate summaries: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


def get_enhancer(db: Session) -> TopicGPTEnhancer:
    """Get enhancer instance"""
    return TopicGPTEnhancer(db)
