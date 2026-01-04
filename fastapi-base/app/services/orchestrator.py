"""
Pipeline Orchestrator - Điều phối toàn bộ luồng xử lý data
Workflow: Sync → Classify → Sentiment → Statistics → Keywords
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.statistics.statistics_service import StatisticsService
from app.services.topic.custom_classifier import CustomTopicClassifier
from app.services.topic.topic_sentiment_service import TopicSentimentService

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrator cho toàn bộ pipeline xử lý data"""
    
    def __init__(self, db: Session):
        self.db = db
        self.stats_service = StatisticsService(db)
        self.classifier = CustomTopicClassifier(db)
        self.sentiment_service = TopicSentimentService(db)
    
    def run_full_pipeline(
        self,
        sync_data: bool = True,
        classify_topics: bool = True,
        analyze_sentiment: bool = True,
        calculate_statistics: bool = True,
        regenerate_keywords: bool = True,
        train_bertopic: bool = False,
        limit: Optional[int] = None
    ) -> Dict:
        """
        Chạy toàn bộ pipeline từ đầu đến cuối
        
        Args:
            sync_data: Sync data từ external API
            classify_topics: Classify topics cho articles chưa classify
            analyze_sentiment: Phân tích sentiment và link với topics
            calculate_statistics: Tính toán các bảng statistics
            regenerate_keywords: Regenerate keywords với GPT
            train_bertopic: Train BERTopic model (expensive, optional)
            limit: Giới hạn số articles xử lý (None = all)
        
        Returns:
            Dict với kết quả từng bước
        """
        start_time = datetime.now()
        results = {
            "started_at": start_time.isoformat(),
            "steps": {},
            "errors": []
        }
        
        logger.info("=" * 60)
        logger.info("🚀 STARTING FULL PIPELINE")
        logger.info("=" * 60)
        
        try:
            # Step 1: Sync data từ external API
            if sync_data:
                logger.info("\n📥 Step 1/6: Syncing data from external API...")
                try:
                    from sqlalchemy import text
                    # Check current count
                    count_result = self.db.execute(text("SELECT COUNT(*) FROM articles")).scalar()
                    
                    # TODO: Call sync service API
                    # For now, just report current count
                    results["steps"]["sync"] = {
                        "status": "skipped",
                        "message": "Call POST /api/v1/sync/all to sync data",
                        "current_articles": count_result
                    }
                    logger.info(f"   Current articles in DB: {count_result}")
                except Exception as e:
                    logger.error(f"   ❌ Sync failed: {e}")
                    results["errors"].append(f"Sync: {str(e)}")
                    results["steps"]["sync"] = {"status": "error", "error": str(e)}
            
            # Step 2: Classify topics
            if classify_topics:
                logger.info("\n🏷️  Step 2/6: Classifying topics...")
                try:
                    from sqlalchemy import text
                    
                    # Get unclassified articles
                    unclassified = self.db.execute(text("""
                        SELECT COUNT(DISTINCT a.id)
                        FROM articles a
                        LEFT JOIN article_custom_topics act ON a.id = act.article_id
                        WHERE act.article_id IS NULL
                        LIMIT :limit
                    """), {"limit": limit or 999999}).scalar()
                    
                    if unclassified > 0:
                        logger.info(f"   Found {unclassified} unclassified articles")
                        
                        # Get articles to classify
                        articles_to_classify = self.db.execute(text("""
                            SELECT a.id, a.title, a.content
                            FROM articles a
                            LEFT JOIN article_custom_topics act ON a.id = act.article_id
                            WHERE act.article_id IS NULL
                            LIMIT :limit
                        """), {"limit": limit or 1000}).fetchall()
                        
                        classified_count = 0
                        for article in articles_to_classify:
                            try:
                                result = self.classifier.classify_article(
                                    article_id=article[0],
                                    title=article[1],
                                    content=article[2]
                                )
                                if result and result.get('topics'):
                                    classified_count += 1
                            except Exception as e:
                                logger.debug(f"   Failed to classify article {article[0]}: {e}")
                        
                        results["steps"]["classify"] = {
                            "status": "success",
                            "processed": len(articles_to_classify),
                            "classified": classified_count
                        }
                        logger.info(f"   ✅ Classified {classified_count}/{len(articles_to_classify)} articles")
                    else:
                        results["steps"]["classify"] = {
                            "status": "skipped",
                            "message": "No unclassified articles"
                        }
                        logger.info("   ⏭️  No unclassified articles found")
                        
                except Exception as e:
                    logger.error(f"   ❌ Classification failed: {e}")
                    results["errors"].append(f"Classify: {str(e)}")
                    results["steps"]["classify"] = {"status": "error", "error": str(e)}
            
            # Step 3: Analyze sentiment & link to topics
            if analyze_sentiment:
                logger.info("\n😊 Step 3/6: Analyzing sentiment...")
                try:
                    from sqlalchemy import text
                    
                    # Get articles with topics but no sentiment
                    articles_need_sentiment = self.db.execute(text("""
                        SELECT DISTINCT act.article_id
                        FROM article_custom_topics act
                        LEFT JOIN sentiment_analysis sa ON act.article_id = sa.article_id
                        WHERE sa.article_id IS NULL
                        LIMIT :limit
                    """), {"limit": limit or 500}).fetchall()
                    
                    if articles_need_sentiment:
                        logger.info(f"   Found {len(articles_need_sentiment)} articles needing sentiment analysis")
                        
                        analyzed_count = 0
                        for row in articles_need_sentiment:
                            try:
                                self.sentiment_service.analyze_and_link_article(row[0])
                                analyzed_count += 1
                            except Exception as e:
                                logger.debug(f"   Failed sentiment for article {row[0]}: {e}")
                        
                        # Update topic sentiment stats
                        from sqlalchemy import text
                        topics = self.db.execute(text("SELECT id FROM custom_topics")).fetchall()
                        for topic_row in topics:
                            try:
                                self.sentiment_service.update_topic_sentiment_stats(
                                    topic_id=topic_row[0],
                                    period_type='all'
                                )
                            except Exception as e:
                                logger.debug(f"   Failed to update stats for topic {topic_row[0]}: {e}")
                        
                        results["steps"]["sentiment"] = {
                            "status": "success",
                            "analyzed": analyzed_count,
                            "topics_updated": len(topics)
                        }
                        logger.info(f"   ✅ Analyzed {analyzed_count} articles, updated {len(topics)} topics")
                    else:
                        results["steps"]["sentiment"] = {
                            "status": "skipped",
                            "message": "No articles need sentiment analysis"
                        }
                        logger.info("   ⏭️  No articles need sentiment analysis")
                        
                except Exception as e:
                    logger.error(f"   ❌ Sentiment analysis failed: {e}")
                    results["errors"].append(f"Sentiment: {str(e)}")
                    results["steps"]["sentiment"] = {"status": "error", "error": str(e)}
            
            # Step 4: Calculate statistics
            if calculate_statistics:
                logger.info("\n📊 Step 4/6: Calculating statistics...")
                try:
                    # Update trend reports
                    trend_report = self.stats_service.calculate_trend_report(period_type='weekly')
                    if trend_report:
                        self.db.add(trend_report)
                    
                    # Update hot topics
                    hot_topics = self.stats_service.calculate_hot_topics(period_days=7, top_n=10)
                    
                    # Update daily snapshot
                    snapshot = self.stats_service.create_daily_snapshot()
                    if snapshot:
                        self.db.add(snapshot)
                    
                    self.db.commit()
                    
                    results["steps"]["statistics"] = {
                        "status": "success",
                        "trend_report": bool(trend_report),
                        "hot_topics": len(hot_topics) if hot_topics else 0,
                        "snapshot": bool(snapshot)
                    }
                    logger.info(f"   ✅ Statistics updated: {len(hot_topics or [])} hot topics")
                    
                except Exception as e:
                    logger.error(f"   ❌ Statistics calculation failed: {e}")
                    results["errors"].append(f"Statistics: {str(e)}")
                    results["steps"]["statistics"] = {"status": "error", "error": str(e)}
            
            # Step 5: Regenerate keywords
            if regenerate_keywords:
                logger.info("\n🔑 Step 5/6: Regenerating keywords...")
                try:
                    keyword_result = self.stats_service.regenerate_keywords_with_gpt(
                        limit=limit or 200
                    )
                    results["steps"]["keywords"] = {
                        "status": "success",
                        "total": keyword_result.get("total", 0),
                        "method": keyword_result.get("method", "unknown")
                    }
                    logger.info(f"   ✅ Generated {keyword_result.get('total', 0)} keywords")
                    
                except Exception as e:
                    logger.error(f"   ❌ Keyword generation failed: {e}")
                    results["errors"].append(f"Keywords: {str(e)}")
                    results["steps"]["keywords"] = {"status": "error", "error": str(e)}
            
            # Step 6: Train BERTopic (optional, expensive)
            if train_bertopic:
                logger.info("\n🤖 Step 6/6: Training BERTopic...")
                try:
                    from app.services.topic.bertopic_trainer import get_trainer
                    
                    trainer = get_trainer(self.db)
                    training_result = trainer.train_from_articles(
                        limit=limit,
                        min_topic_size=10,
                        use_vietnamese_tokenizer=True,
                        enable_topicgpt=True  # Enable GPT for natural topic labels
                    )
                    
                    if training_result.get("status") == "completed":
                        results["steps"]["bertopic"] = {
                            "status": "success",
                            "session_id": training_result.get("session_id"),
                            "num_topics": training_result.get("training", {}).get("num_topics", 0),
                            "num_documents": training_result.get("training", {}).get("num_documents", 0),
                            "duration": training_result.get("training", {}).get("duration_seconds", 0)
                        }
                        logger.info(f"   ✅ Discovered {training_result['training']['num_topics']} topics")
                    else:
                        results["steps"]["bertopic"] = {
                            "status": "error",
                            "error": training_result.get("error", "Unknown error")
                        }
                        logger.error(f"   ❌ Training failed: {training_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"   ❌ BERTopic training failed: {e}", exc_info=True)
                    results["errors"].append(f"BERTopic: {str(e)}")
                    results["steps"]["bertopic"] = {"status": "error", "error": str(e)}
            
            # Final summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            results["completed_at"] = end_time.isoformat()
            results["duration_seconds"] = duration
            
            success_count = sum(1 for step in results["steps"].values() if step.get("status") == "success")
            total_steps = len(results["steps"])
            
            logger.info("\n" + "=" * 60)
            logger.info(f"✅ PIPELINE COMPLETED: {success_count}/{total_steps} steps successful")
            logger.info(f"⏱️  Duration: {duration:.2f} seconds")
            if results["errors"]:
                logger.warning(f"⚠️  Errors: {len(results['errors'])}")
            logger.info("=" * 60)
            
            return results
            
        except Exception as e:
            logger.error(f"💥 Pipeline failed: {e}", exc_info=True)
            results["errors"].append(f"Pipeline: {str(e)}")
            results["status"] = "failed"
            return results


def get_orchestrator(db: Session) -> PipelineOrchestrator:
    """Get orchestrator instance"""
    return PipelineOrchestrator(db)
