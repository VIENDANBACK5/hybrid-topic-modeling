"""
Superset Sync API - Update all tables for Superset dashboards
"""
import logging
from datetime import datetime, timedelta
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text

from app.core.database import get_db
from app.models.model_article import Article
from app.models.model_statistics import HotTopic
from app.models.model_trends import ViralContent
from app.models.model_bertopic_discovered import ArticleBertopicTopic, BertopicDiscoveredTopic
from app.services.trends.trend_service import TrendAnalysisService
from app.services.statistics.statistics_service import StatisticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/superset", tags=["Superset Sync"])


@router.post("/update-all")
async def update_all_superset_tables(
    period_days: int = 7,
    all_time: bool = False,
    db: Session = Depends(get_db)
) -> Dict:
    """
     Update ALL tables for Superset dashboards with 1 click
    
    Updates:
    - hot_topics (50 records)
    - viral_contents (100 records)
    - hashtag_stats
    - category_trend_stats
    - trend_reports
    - keyword_stats
    - daily_snapshots
    - field_summaries
    - topics_over_time
    - social_activity_stats
    
    Args:
        period_days: Number of days to analyze (default: 7, ignored if all_time=true)
        all_time: If true, analyze ALL data without time filter (default: false)
    
    Returns:
        Dict with update results for each table
    
    Examples:
        # Last 7 days
        curl -X POST "http://localhost:7777/superset/update-all"
        
        # Last 30 days
        curl -X POST "http://localhost:7777/superset/update-all?period_days=30"
        
        # ALL TIME
        curl -X POST "http://localhost:7777/superset/update-all?all_time=true"
    """
    results = {}
    errors = []
    
    try:
        if all_time:
            logger.info(f" Starting Superset table updates (ALL TIME)...")
            # Use very old date for all-time query
            period_start = datetime(2000, 1, 1)
            period_start_ts = 0  # Unix epoch start
        else:
            logger.info(f" Starting Superset table updates (period: {period_days} days)...")
            period_start = datetime.now() - timedelta(days=period_days)
            period_start_ts = period_start.timestamp()
        
        now = datetime.now()
        
        # 1. HOT TOPICS
        try:
            logger.info("1⃣ Updating hot_topics...")
            
            # Delete old records
            db.query(HotTopic).filter(
                HotTopic.period_start >= (now - timedelta(days=30)).date()
            ).delete()
            
            # Get top topics by count
            hot_data = db.query(
                BertopicDiscoveredTopic.topic_id,
                BertopicDiscoveredTopic.topic_label,
                BertopicDiscoveredTopic.keywords,
                func.count(ArticleBertopicTopic.article_id).label('cnt')
            ).join(ArticleBertopicTopic).join(Article).filter(
                Article.created_at >= period_start_ts,
                BertopicDiscoveredTopic.is_outlier == False
            ).group_by(
                BertopicDiscoveredTopic.id
            ).order_by(desc('cnt')).limit(50).all()
            
            for tid, label, keywords, cnt in hot_data:
                # Extract keywords from JSON
                keyword_list = []
                if keywords:
                    try:
                        keyword_list = [kw['word'] for kw in keywords[:5]] if isinstance(keywords, list) else []
                    except:
                        pass
                
                db.add(HotTopic(
                    period_type='weekly',
                    period_start=period_start.date(),
                    period_end=now.date(),
                    topic_id=tid,
                    topic_name=label or f"Topic {tid}",
                    topic_keywords=keyword_list,
                    mention_count=cnt,
                    hot_score=float(cnt),
                    is_hot=True
                ))
            
            db.commit()
            results['hot_topics'] = len(hot_data)
            logger.info(f"    Created {len(hot_data)} hot topics")
            
        except Exception as e:
            errors.append(f"hot_topics: {str(e)}")
            db.rollback()
            logger.error(f"    hot_topics failed: {e}")
        
        # 2. VIRAL CONTENT
        try:
            logger.info("2⃣ Updating viral_contents...")
            
            # Delete old records
            db.query(ViralContent).filter(
                ViralContent.period_start >= (now - timedelta(days=30)).date()
            ).delete()
            
            # Get recent articles with most content/engagement
            articles = db.query(Article).filter(
                Article.created_at >= period_start_ts,
                Article.content != None
            ).order_by(desc(Article.created_at)).limit(100).all()
            
            v_cnt = 0
            for art in articles:
                if not art.content or len(art.content) < 50:
                    continue
                    
                # Calculate viral score based on content length (simplified)
                viral_score = min(100.0, len(art.content) / 100.0)
                
                db.add(ViralContent(
                    article_id=art.id,
                    period_type='daily',
                    period_start=now.date(),
                    title=art.title,
                    url=art.url,
                    source_domain=art.domain,
                    content_snippet=(art.content[:500] if art.content else ''),
                    topic_name=art.topic_name,
                    viral_score=viral_score
                ))
                v_cnt += 1
            
            db.commit()
            results['viral_contents'] = v_cnt
            logger.info(f"    Created {v_cnt} viral contents")
            
        except Exception as e:
            errors.append(f"viral_contents: {str(e)}")
            db.rollback()
            logger.error(f"    viral_contents failed: {e}")
        
        # 3. TREND SERVICES
        try:
            logger.info("3⃣ Updating trend statistics...")
            trend_service = TrendAnalysisService(db)
            
            # Hashtag stats
            trend_service.calculate_hashtag_stats("daily")
            db.commit()
            results['hashtag_stats'] = 'updated'
            
            # Category trends
            trend_service.calculate_category_trends("daily")
            db.commit()
            results['category_trend_stats'] = 'updated'
            
            # Trend alerts
            alerts = trend_service.detect_trend_alerts(hours_back=period_days * 24)
            db.commit()
            results['trend_alerts'] = len(alerts) if alerts else 0
            
            logger.info(f"    Trend statistics updated")
            
        except Exception as e:
            errors.append(f"trend_services: {str(e)}")
            db.rollback()
            logger.error(f"    trend_services failed: {e}")
        
        # 4. STATISTICS SERVICES
        try:
            logger.info("4⃣ Updating statistics services...")
            stats_service = StatisticsService(db)
            
            # Trend report
            stats_service.calculate_trend_report("weekly")
            db.commit()
            results['trend_reports'] = 'updated'
            
            # Keyword stats
            stats_service.calculate_keyword_stats("weekly")
            db.commit()
            results['keyword_stats'] = 'updated'
            
            # Daily snapshot
            stats_service.create_daily_snapshot()
            db.commit()
            results['daily_snapshots'] = 'updated'
            
            logger.info(f"    Statistics services updated")
            
        except Exception as e:
            errors.append(f"stats_services: {str(e)}")
            db.rollback()
            logger.error(f"    stats_services failed: {e}")
        
        # 5. FIELD SUMMARIES - SKIPPED (use /update-field-summaries endpoint instead)
        try:
            logger.info("5⃣ Skipping field_summaries (use dedicated endpoint)...")
            results['field_summaries'] = 'skipped_use_dedicated_endpoint'
            
        except Exception as e:
            errors.append(f"field_summaries: {str(e)}")
            db.rollback()
            logger.error(f"    field_summaries failed: {e}")
        
        # 6. TOPICS OVER TIME
        try:
            logger.info("6⃣ Updating topics_over_time...")
            
            # Delete old records
            db.execute(text("DELETE FROM topics_over_time"))
            
            # Rebuild from article_bertopic_topics + articles
            # Use published_datetime instead of created_at for better time range
            query = text("""
                INSERT INTO topics_over_time 
                    (topic_id, time_bin, frequency, topic_keywords, topic_final, topic_final_vi, period_type)
                SELECT 
                    bt.topic_id,
                    DATE_TRUNC('day', a.published_datetime) as time_bin,
                    COUNT(*) as frequency,
                    bt.keywords::text as topic_keywords,
                    bt.topic_label as topic_final,
                    bt.topic_label as topic_final_vi,
                    'daily' as period_type
                FROM article_bertopic_topics abt
                JOIN bertopic_discovered_topics bt ON abt.bertopic_topic_id = bt.id
                JOIN articles a ON abt.article_id = a.id
                WHERE bt.is_outlier = false
                AND a.published_datetime IS NOT NULL
                AND a.published_datetime >= :since_date
                GROUP BY bt.topic_id, DATE_TRUNC('day', a.published_datetime), 
                         bt.keywords, bt.topic_label
                ORDER BY time_bin, bt.topic_id
            """)
            
            # Calculate since_date properly
            if all_time:
                since_date = datetime(2000, 1, 1)
            else:
                since_date = period_start
            
            result = db.execute(query, {"since_date": since_date})
            db.commit()
            
            # Count results
            count = db.execute(text("SELECT COUNT(*) FROM topics_over_time")).scalar()
            results['topics_over_time'] = count
            logger.info(f"    Created {count} topics_over_time records")
            
        except Exception as e:
            errors.append(f"topics_over_time: {str(e)}")
            db.rollback()
            logger.error(f"    topics_over_time failed: {e}")
        
        logger.info(f" Superset table updates completed!")
        
        return {
            "status": "success" if not errors else "partial_success",
            "timestamp": now.isoformat(),
            "period": "all_time" if all_time else f"{period_days}_days",
            "period_start": period_start.date().isoformat(),
            "period_end": now.date().isoformat(),
            "results": results,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        logger.error(f" Superset update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_superset_table_status(db: Session = Depends(get_db)) -> Dict:
    """
     Check status of all Superset tables
    
    Returns record counts and last update times
    """
    try:
        status = {}
        
        # Count records in key tables
        from app.models.model_sentiment import SentimentAnalysis
        from app.models.model_statistics import (
            KeywordStats, TrendReport, DailySnapshot
        )
        from app.models.model_trends import (
            HashtagStats, CategoryTrendStats, TrendAlert
        )
        from app.models.model_field_summary import FieldSummary
        
        tables = [
            ('articles', Article),
            ('bertopic_discovered_topics', BertopicDiscoveredTopic),
            ('article_bertopic_topics', ArticleBertopicTopic),
            ('sentiment_analysis', SentimentAnalysis),
            ('hot_topics', HotTopic),
            ('viral_contents', ViralContent),
            ('keyword_stats', KeywordStats),
            ('hashtag_stats', HashtagStats),
            ('category_trend_stats', CategoryTrendStats),
            ('trend_reports', TrendReport),
            ('trend_alerts', TrendAlert),
            ('daily_snapshots', DailySnapshot),
            ('field_summaries', FieldSummary),
        ]
        
        for table_name, model in tables:
            try:
                count = db.query(model).count()
                status[table_name] = {
                    'records': count,
                    'has_data': count > 0
                }
            except Exception as e:
                status[table_name] = {
                    'records': 0,
                    'error': str(e)
                }
        
        # Summary
        total_tables = len(tables)
        tables_with_data = sum(1 for t in status.values() if t.get('has_data', False))
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tables": total_tables,
                "tables_with_data": tables_with_data,
                "coverage_percent": round(tables_with_data / total_tables * 100, 1)
            },
            "tables": status
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-field-summaries")
async def update_field_summaries_only(
    db: Session = Depends(get_db)
) -> Dict:
    """
     Update ONLY field_summaries with LLM-generated summaries (using OpenRouter)
    
    Creates monthly summaries for January 2026
    Uses OpenRouter API with gpt-4o-mini (cheap & good quality)
    
    Returns:
        Dict with field_summaries update results
    
    Example:
        curl -X POST "http://localhost:7777/superset/update-field-summaries"
    """
    try:
        logger.info(" Starting field_summaries update with OpenRouter...")
        
        from app.services.classification.summary_service import FieldSummaryService
        
        summary_service = FieldSummaryService(db)
        
        # Check if LLM is available
        if not summary_service.is_llm_available():
            return {
                "status": "skipped",
                "message": "OPENAI_API_KEY not configured",
                "field_summaries": 0
            }
        
        logger.info(f" Using provider: {summary_service.provider}")
        
        # Create monthly summary for January 2026 (current data)
        all_summaries = []
        target_date = datetime(2026, 1, 15).date()  # Jan 2026
        
        logger.info(f"   Creating summaries for {target_date.strftime('%B %Y')}...")
        try:
            summaries = summary_service.create_summaries_for_all_fields(
                period='monthly',
                target_date=target_date,
                model="openai/gpt-4o-mini"  # OpenRouter model
            )
            if summaries:
                all_summaries.extend(summaries)
                logger.info(f"    Created {len(summaries)} summaries for {target_date.strftime('%B %Y')}")
            db.commit()
        except Exception as e:
            logger.error(f"    Failed for {target_date}: {e}")
            db.rollback()
        
        logger.info(f" Field summaries updated: {len(all_summaries)} records total")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "provider_used": summary_service.provider,
            "field_summaries": len(all_summaries),
            "month_processed": target_date.strftime('%B %Y')
        }
        
    except Exception as e:
        logger.error(f" Field summaries update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-field-sentiments")
async def update_field_sentiments_only(
    db: Session = Depends(get_db)
) -> Dict:
    """
     Update field_sentiments - Phân tích sentiment theo lĩnh vực
    
    Phân tích cảm xúc (tích cực/tiêu cực/trung lập) của tin tức theo từng lĩnh vực
    Sử dụng OpenRouter + LLM để phân tích sentiment
    
    Returns:
        Dict with sentiment analysis results
    
    Example:
        curl -X POST "http://localhost:7777/superset/update-field-sentiments"
    """
    try:
        logger.info(" Starting field sentiment analysis...")
        
        from app.services.classification.field_sentiment_service import FieldSentimentService
        
        sentiment_service = FieldSentimentService(db)
        
        # Check if LLM is available
        if not sentiment_service.is_llm_available():
            return {
                "status": "skipped",
                "message": "LLM not available for sentiment analysis",
                "field_sentiments": 0
            }
        
        logger.info(f" Using provider: {sentiment_service.provider}")
        
        # Create sentiment analysis for January 2026
        target_date = datetime(2026, 1, 15).date()
        
        logger.info(f"   Analyzing sentiment for {target_date.strftime('%B %Y')}...")
        try:
            sentiments = sentiment_service.create_sentiment_for_all_fields(
                period='monthly',
                target_date=target_date,
                model="openai/gpt-4o-mini"
            )
            logger.info(f"    Created {len(sentiments)} sentiment analyses")
            db.commit()
        except Exception as e:
            logger.error(f"    Failed sentiment analysis: {e}")
            db.rollback()
            raise
        
        logger.info(f" Field sentiments updated: {len(sentiments)} records")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "provider_used": sentiment_service.provider,
            "field_sentiments": len(sentiments),
            "month_processed": target_date.strftime('%B %Y')
        }
        
    except Exception as e:
        logger.error(f" Field sentiments update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
