from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.model_article import Article
import logging
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import re
import json

logger = logging.getLogger(__name__)
router = APIRouter()

class DashboardStatsResponse(BaseModel):
    total_documents: int
    total_topics: int
    avg_doc_length: float
    top_topics: List[Dict]
    topic_distribution: Dict[str, int]


class TopicAnalyticsResponse(BaseModel):
    topics: List[Dict]
    topic_counts: Dict[int, int]
    top_keywords: List[Dict]


# Base directories
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"
RESULTS_DIR = DATA_DIR / "results"


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in MB"""
    try:
        return file_path.stat().st_size / (1024 * 1024)
    except:
        return 0


# Cache directory size (expensive operation)
_dir_size_cache = {}
_dir_size_cache_time = {}
DIR_SIZE_CACHE_TTL = 300  # 5 minutes

def get_dir_size_mb(dir_path: Path) -> float:
    """Get total directory size in MB (cached)"""
    try:
        import time
        cache_key = str(dir_path)
        now = time.time()
        
        # Check cache
        if cache_key in _dir_size_cache:
            if now - _dir_size_cache_time.get(cache_key, 0) < DIR_SIZE_CACHE_TTL:
                return _dir_size_cache[cache_key]
        
        # Calculate size
        total = 0
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                total += file_path.stat().st_size
        result = total / (1024 * 1024)
        
        # Update cache
        _dir_size_cache[cache_key] = result
        _dir_size_cache_time[cache_key] = now
        
        return result
    except:
        return 0


def load_all_documents() -> List[Dict]:
    """Load all documents from processed directory"""
    documents = []
    
    if not PROCESSED_DIR.exists():
        return documents
    
    for file_path in PROCESSED_DIR.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    documents.extend(data)
                else:
                    documents.append(data)
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")
    
    return documents


def get_topic_count() -> int:
    """Get number of topics from model"""
    try:
        from app.core.models import topic_model
        
        if topic_model and topic_model.topic_model:
            topic_info = topic_model.get_topic_info()
            return len(topic_info.get('topics', []))
        
        return 0
    except Exception as e:
        logger.warning(f"Failed to get topic count: {e}")
        return 0


def get_recent_activity(limit: Optional[int] = None) -> List[Dict]:
    """Get recent crawl and analysis activities"""
    activities = []
    
    # Get recent crawl sessions
    if PROCESSED_DIR.exists():
        # Limit file scan to speed up
        max_files_to_scan = limit * 2 if limit else 50
        files = list(PROCESSED_DIR.glob("*.json"))
        files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:max_files_to_scan]
        
        for file_path in files[:limit] if limit else files:
            try:
                stat = file_path.stat()
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    doc_count = len(data) if isinstance(data, list) else 1
                
                activities.append({
                    "type": "crawl",
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "file": file_path.name,
                    "documents": doc_count,
                    "size_mb": round(get_file_size_mb(file_path), 2)
                })
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")
    
    # Get recent model training
    if MODELS_DIR.exists():
        model_dirs = sorted([d for d in MODELS_DIR.iterdir() if d.is_dir()], 
                          key=lambda x: x.stat().st_mtime, reverse=True)
        
        for model_dir in model_dirs[:3]:
            try:
                stat = model_dir.stat()
                activities.append({
                    "type": "training",
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "model": model_dir.name,
                    "size_mb": round(get_dir_size_mb(model_dir), 2)
                })
            except Exception as e:
                logger.warning(f"Failed to process {model_dir}: {e}")
    
    # Sort by timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return activities[:limit] if limit else activities


@router.get("")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    GỘP TẤT CẢ - Dashboard tổng hợp: stats + topics + charts + activity
    Trả về tất cả thông tin trong 1 lần gọi
    """
    try:
        # Get total count (fast query)
        from sqlalchemy import func
        total_docs = db.query(func.count(Article.id)).scalar()
        
        # Get topic count
        topic_count = get_topic_count()
        
        # Calculate avg length from sample (much faster than all)
        sample_articles = db.query(Article).limit(100).all()
        doc_lengths = [len(a.content or a.raw_content or '') for a in sample_articles if a.content or a.raw_content]
        avg_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0
        
        # Get topic distribution
        topic_distribution = {}
        top_topics = []
        
        if topic_count > 0:
            try:
                from app.core.models import topic_model
                if topic_model and topic_model.topic_model:
                    topic_info = topic_model.get_topic_info()
                    topics_list = topic_info.get('topics', [])
                    
                    # Sort by count
                    topics_list.sort(key=lambda x: x.get('count', 0), reverse=True)
                    
                    # Top 5 topics
                    for topic in topics_list[:5]:
                        name = topic.get('name', '')
                        words = topic.get('words', [])
                        
                        # Generate meaningful name from keywords
                        if not name and words:
                            keywords_list = [w.get('word', '') for w in words[:10]]
                            
                            # Smart name generation based on keywords
                            if any(k in keywords_list for k in ['học', 'giáo', 'sinh', 'trường', 'giáo dục']):
                                name = 'Giáo dục & Đào tạo'
                            elif any(k in keywords_list for k in ['đường', 'giao thông', 'cầu', 'vận tải']):
                                name = 'Giao thông & Hạ tầng'
                            elif any(k in keywords_list for k in ['dự án', 'công trình', 'xây dựng', 'đầu tư']):
                                name = 'Dự án & Đầu tư'
                            elif any(k in keywords_list for k in ['y tế', 'bệnh', 'sức khỏe', 'bệnh viện']):
                                name = 'Y tế & Sức khỏe'
                            elif any(k in keywords_list for k in ['kinh tế', 'doanh nghiệp', 'sản xuất', 'công nghiệp']):
                                name = 'Kinh tế & Doanh nghiệp'
                            elif any(k in keywords_list for k in ['văn hóa', 'du lịch', 'lễ hội', 'di sản']):
                                name = 'Văn hóa & Du lịch'
                            elif any(k in keywords_list for k in ['nông', 'nông nghiệp', 'nông thôn', 'nông dân']):
                                name = 'Nông nghiệp & Nông thôn'
                            elif any(k in keywords_list for k in ['an ninh', 'công an', 'trật tự', 'phòng']):
                                name = 'An ninh & Trật tự'
                            elif any(k in keywords_list for k in ['môi trường', 'xanh', 'rác', 'ô nhiễm']):
                                name = 'Môi trường'
                            elif any(k in keywords_list for k in ['thể thao', 'bóng', 'giải', 'vô địch']):
                                name = 'Thể thao'
                            else:
                                # Fallback: use top 3 keywords
                                name = ' - '.join(keywords_list[:3])
                        
                        top_topics.append({
                            "topic_id": topic.get('topic_id'),
                            "name": name if name else f"Chủ đề {topic.get('topic_id')}",
                            "count": topic.get('count', 0),
                            "keywords": [w.get('word', '') for w in words[:5]]
                        })
                    
                    # Distribution
                    for topic in topics_list:
                        topic_id = topic.get('topic_id')
                        count = topic.get('count', 0)
                        topic_distribution[str(topic_id)] = count
            except Exception as e:
                logger.warning(f"Failed to get topics: {e}")
        
        # Get recent activity
        recent_activity = get_recent_activity(limit=10)
        
        # Get sources count
        from app.models.model_source import Source
        total_sources = db.query(func.count(Source.id)).scalar()
        
        return {
            "total_documents": total_docs,
            "total_sources": total_sources,
            "total_topics": topic_count,
            "avg_doc_length": round(avg_length, 2),
            "stats": {
                "total_documents": total_docs,
                "total_topics": topic_count,
                "avg_doc_length": round(avg_length, 2),
                "data_size_mb": round(get_dir_size_mb(PROCESSED_DIR), 2),
                "models_size_mb": round(get_dir_size_mb(MODELS_DIR), 2)
            },
            "top_topics": top_topics,
            "topic_distribution": topic_distribution,
            "recent_activity": recent_activity,
            "sources": total_sources,
            "charts": {
                "timeline_available": total_docs > 0,
                "topics_available": topic_count > 0
            }
        }
    except Exception as e:
        logger.error(f"Dashboard overview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get comprehensive dashboard statistics (deprecated - use GET / instead)"""
    try:
        # Optimize: Use count() instead of loading all articles
        total_docs = db.query(Article).count()
        articles = db.query(Article).limit(1000).all()  # Sample for stats
        
        doc_lengths = [len(a.content or a.raw_content or '') for a in articles if a.content or a.raw_content]
        avg_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0
        
        topic_count = get_topic_count()
        
        return {
            "total_documents": total_docs,
            "total_topics": topic_count,
            "avg_doc_length": round(avg_length, 2),
            "data_size_mb": round(get_dir_size_mb(PROCESSED_DIR), 2)
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def get_topic_breakdown():
    """Get topic distribution breakdown"""
    try:
        from app.core.models import topic_model
        
        if not topic_model or not topic_model.topic_model:
            return {
                "total_topics": 0,
                "topics": [],
                "message": "No topic model available"
            }
        
        topic_info = topic_model.get_topic_info()
        topics_list = topic_info.get('topics', [])
        
        # Format topics with name replacement
        formatted_topics = []
        for topic in topics_list:
            name = topic.get('name', '')
            formatted_topics.append({
                "topic_id": topic.get('topic_id'),
                "name": name.replace('_', ' ') if name else name,  # FORMAT: bỏ dấu _
                "count": topic.get('count', 0),
                "words": topic.get('words', [])[:5]
            })
        
        return {
            "total": len(formatted_topics),
            "total_topics": len(formatted_topics),
            "topics": formatted_topics
        }
    except Exception as e:
        logger.error(f"Topic breakdown error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity")
async def get_recent_activity_endpoint():
    """Get recent crawl and analysis activities"""
    try:
        activities = get_recent_activity(limit=20)
        return {
            "activities": activities,
            "total": len(activities)
        }
    except Exception as e:
        logger.error(f"Activity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== CHART APIs ==========

@router.get("/charts/timeline")
async def get_timeline_chart(db: Session = Depends(get_db)):
    """Get timeline data for documents and crawl sessions"""
    try:
        # Optimize: Order by date and limit
        articles = (db.query(Article)
                   .order_by(Article.created_at.desc())
                   .limit(2000)
                   .all())
        
        if not articles:
            return {
                "dates": [],
                "document_counts": [],
                "cumulative_counts": []
            }
        
        # Group by date
        date_counts = {}
        for article in articles:
            if article.created_at:
                try:
                    if isinstance(article.created_at, str):
                        date_str = article.created_at[:10]
                    elif isinstance(article.created_at, (int, float)):
                        from datetime import datetime
                        date_str = datetime.fromtimestamp(article.created_at).date().isoformat()
                    else:
                        date_str = article.created_at.date().isoformat()
                    date_counts[date_str] = date_counts.get(date_str, 0) + 1
                except:
                    pass
        
        # Sort by date
        sorted_dates = sorted(date_counts.keys())
        counts = [date_counts[date] for date in sorted_dates]
        
        # Calculate cumulative
        cumulative = []
        total = 0
        for count in counts:
            total += count
            cumulative.append(total)
        
        return {
            "dates": sorted_dates,
            "document_counts": counts,
            "cumulative_counts": cumulative,
            "data": [
                {
                    "date": date,
                    "count": count,
                    "cumulative": cum
                }
                for date, count, cum in zip(sorted_dates, counts, cumulative)
            ]
        }
    except Exception as e:
        logger.error(f"Timeline chart error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/media-stats")
async def get_media_stats_chart(db: Session = Depends(get_db)):
    """Get media statistics (images, videos) from documents"""
    try:
        # Optimize: Sample recent articles
        articles = (db.query(Article)
                   .order_by(Article.created_at.desc())
                   .limit(2000)
                   .all())
        
        total_images = 0
        total_videos = 0
        docs_with_images = 0
        docs_with_videos = 0
        
        for article in articles:
            images = article.images or 0 if hasattr(article, 'images') else 0
            videos = article.videos or 0 if hasattr(article, 'videos') else 0
            
            if isinstance(images, (int, float)):
                total_images += images
                if images > 0:
                    docs_with_images += 1
            
            if isinstance(videos, (int, float)):
                total_videos += videos
                if videos > 0:
                    docs_with_videos += 1
        
        return {
            "total_images": total_images,
            "total_videos": total_videos,
            "docs_with_images": docs_with_images,
            "docs_with_videos": docs_with_videos,
            "docs_without_media": len(articles) - docs_with_images - docs_with_videos,
            "chart_data": {
                "labels": ["With Images", "With Videos", "Without Media"],
                "values": [docs_with_images, docs_with_videos, len(articles) - docs_with_images - docs_with_videos]
            }
        }
    except Exception as e:
        logger.error(f"Media stats chart error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/page-types")
async def get_page_types_chart(db: Session = Depends(get_db)):
    """Get page types distribution"""
    try:
        # Optimize: Sample recent articles
        articles = (db.query(Article)
                   .order_by(Article.created_at.desc())
                   .limit(2000)
                   .all())
        
        type_counts = {}
        for article in articles:
            page_type = article.page_type if hasattr(article, 'page_type') else 'article'
            page_type = page_type or 'unknown'
            type_counts[page_type] = type_counts.get(page_type, 0) + 1
        
        return {
            "labels": list(type_counts.keys()),
            "values": list(type_counts.values()),
            "data": [
                {"type": k, "count": v, "percentage": round(v / len(articles) * 100, 2)}
                for k, v in type_counts.items()
            ]
        }
    except Exception as e:
        logger.error(f"Page types chart error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/document-lengths")
async def get_document_lengths_chart(db: Session = Depends(get_db)):
    """Get document length distribution"""
    try:
        # Optimize: Sample recent articles with content
        articles = (db.query(Article)
                   .filter(Article.content.isnot(None))
                   .order_by(Article.created_at.desc())
                   .limit(1000)
                   .all())
        
        lengths = []
        for article in articles:
            content = article.content or article.raw_content or ''
            lengths.append(len(content))
        
        if not lengths:
            return {
                "labels": [],
                "values": [],
                "buckets": [],
                "stats": {}
            }
        
        # Create buckets
        buckets = {
            "0-500": 0,
            "500-1000": 0,
            "1000-2000": 0,
            "2000-5000": 0,
            "5000+": 0
        }
        
        for length in lengths:
            if length < 500:
                buckets["0-500"] += 1
            elif length < 1000:
                buckets["500-1000"] += 1
            elif length < 2000:
                buckets["1000-2000"] += 1
            elif length < 5000:
                buckets["2000-5000"] += 1
            else:
                buckets["5000+"] += 1
        
        sorted_lengths = sorted(lengths)
        median = sorted_lengths[len(sorted_lengths) // 2] if sorted_lengths else 0
        
        bins_array = [
            {"range": k, "count": v, "percentage": round(v / len(lengths) * 100, 2)}
            for k, v in buckets.items()
        ]
        
        return {
            "labels": list(buckets.keys()),
            "values": list(buckets.values()),
            "bins": bins_array,
            "buckets": bins_array,
            "stats": {
                "min": min(lengths),
                "max": max(lengths),
                "avg": round(sum(lengths) / len(lengths), 2),
                "median": median
            }
        }
    except Exception as e:
        logger.error(f"Document lengths chart error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/topic-probabilities")
async def get_topic_probabilities_chart():
    """Get topic probability distribution (requires topic model)"""
    try:
        from app.core.models import topic_model
        
        if not topic_model or not topic_model.topic_model:
            raise HTTPException(status_code=404, detail="No topic model available")
        
        topic_info = topic_model.get_topic_info()
        topics_list = topic_info.get('topics', [])
        
        if not topics_list:
            return {
                "labels": [],
                "probabilities": [],
                "data": []
            }
        
        # Calculate probabilities
        topic_counts = [t.get('count', 0) for t in topics_list]
        total_docs = sum(topic_counts)
        
        probabilities = [
            round(count / total_docs * 100, 2) if total_docs > 0 else 0
            for count in topic_counts
        ]
        
        labels = [t.get('name', f"Topic {t.get('topic_id')}")[:30] for t in topics_list]
        
        return {
            "labels": labels,
            "probabilities": probabilities,
            "data": [
                {
                    "topic_id": t.get('topic_id'),
                    "name": t.get('name', ''),
                    "probability": prob,
                    "count": count
                }
                for t, prob, count in zip(topics_list, probabilities, topic_counts)
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Topic probabilities chart error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/crawl-sessions")
async def get_crawl_sessions_chart():
    """Get crawl sessions statistics over time"""
    try:
        if not PROCESSED_DIR.exists():
            return {
                "labels": [],
                "sessions": [],
                "documents": [],
                "data": []
            }
        
        sessions_data = {}
        
        for file_path in PROCESSED_DIR.glob("*.json"):
            try:
                stat = file_path.stat()
                date_str = datetime.fromtimestamp(stat.st_mtime).date().isoformat()
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    doc_count = len(data) if isinstance(data, list) else 1
                
                if date_str not in sessions_data:
                    sessions_data[date_str] = {"sessions": 0, "documents": 0}
                
                sessions_data[date_str]["sessions"] += 1
                sessions_data[date_str]["documents"] += doc_count
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")
        
        sorted_dates = sorted(sessions_data.keys())
        
        return {
            "labels": sorted_dates,
            "sessions": [sessions_data[date]["sessions"] for date in sorted_dates],
            "documents": [sessions_data[date]["documents"] for date in sorted_dates],
            "data": [
                {
                    "date": date,
                    "sessions": sessions_data[date]["sessions"],
                    "documents": sessions_data[date]["documents"]
                }
                for date in sorted_dates
            ]
        }
    except Exception as e:
        logger.error(f"Crawl sessions chart error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== CONTENT & TOPIC ANALYSIS APIs ==========

def format_keywords_for_display(keywords: List[str]) -> List[str]:
    """Format keywords: replace _ with space"""
    return [k.replace('_', ' ') for k in keywords]


def extract_keywords_from_text(text: str, min_length: int = 3, extract_phrases: bool = True) -> List[str]:
    """Extract keywords from text using Vietnamese NLP"""
    if not text:
        return []
    
    try:
        from app.services.etl.vietnamese_tokenizer import get_vietnamese_tokenizer
        tokenizer = get_vietnamese_tokenizer()
        
        if tokenizer and extract_phrases:
            keywords = tokenizer(text)
            keywords = [k for k in keywords if len(k) >= min_length]
            return keywords
        else:
            from app.services.etl.text_cleaner import TextCleaner
            cleaner = TextCleaner()
            text = cleaner.clean(text, deep_clean=True, tokenize=False)
            
            words = text.split()
            keywords = [w for w in words if len(w) >= min_length and not w.isdigit()]
            return keywords
            
    except Exception as e:
        logger.warning(f"Keyword extraction error: {e}, using fallback")
        text = re.sub(r'[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', ' ', text.lower())
        words = text.split()
        keywords = [w for w in words if len(w) >= min_length and not w.isdigit()]
        return keywords


@router.get("/keywords")
async def get_keywords_analysis(db: Session = Depends(get_db)):
    """Get top keywords from all documents"""
    try:
        # Optimize: Only load recent articles with content
        articles = (db.query(Article)
                   .filter(Article.content.isnot(None))
                   .order_by(Article.created_at.desc())
                   .limit(500)
                   .all())
        
        if not articles:
            return {
                "total_keywords": 0,
                "top_keywords": [],
                "wordcloud_data": []
            }
        
        # Extract keywords
        all_keywords = []
        for article in articles:
            content = article.content or article.raw_content or ''
            title = article.title or ''
            
            text = f"{title} {content}".strip()
            keywords = extract_keywords_from_text(text)
            all_keywords.extend(keywords)
        
        # Count keywords
        keyword_counts = Counter(all_keywords)
        
        # Top keywords
        top_keywords = keyword_counts.most_common(100)
        
        # Wordcloud data
        wordcloud_data = [
            {"word": word.replace('_', ' '), "count": count, "weight": count}
            for word, count in top_keywords[:50]
        ]
        
        return {
            "total_keywords": len(keyword_counts),
            "total_occurrences": sum(keyword_counts.values()),
            "top_keywords": [
                {
                    "word": word.replace('_', ' '),
                    "count": count,
                    "percentage": round(count / len(all_keywords) * 100, 2) if all_keywords else 0
                }
                for word, count in top_keywords[:30]
            ],
            "wordcloud_data": wordcloud_data
        }
    except Exception as e:
        logger.error(f"Keywords analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics/insights")
async def get_topics_insights():
    """Get detailed insights about topics"""
    try:
        from app.core.models import topic_model
        
        if not topic_model or not topic_model.topic_model:
            try:
                topic_model._auto_load_model()
            except:
                raise HTTPException(status_code=404, detail="No topic model available")
        
        topic_info = topic_model.get_topic_info()
        topics_list = topic_info.get('topics', [])
        
        if not topics_list:
            return {"topics": [], "summary": {}}
        
        # Calculate statistics
        topic_counts = [t.get('count', 0) for t in topics_list]
        total_docs = sum(topic_counts)
        
        # Build insights
        topics_insights = []
        for topic in topics_list:
            topic_id = topic.get('topic_id')
            words = topic.get('words', [])
            top_words = [w.get('word', '') for w in words[:10]]
            
            topic_description = ", ".join(top_words[:5])
            
            topics_insights.append({
                "topic_id": topic_id,
                "name": topic.get('name', ''),
                "description": topic_description,
                "count": topic.get('count', 0),
                "percentage": round(topic.get('count', 0) / total_docs * 100, 2) if total_docs > 0 else 0,
                "keywords": top_words,
                "keyword_scores": [{"word": w.get('word', ''), "score": w.get('score', 0)} for w in words[:10]],
                "main_themes": top_words[:3]
            })
        
        topics_insights.sort(key=lambda x: x['count'], reverse=True)
        
        summary = {
            "total_topics": len(topics_insights),
            "total_documents": total_docs,
            "avg_docs_per_topic": round(total_docs / len(topics_insights), 2) if topics_insights else 0,
            "top_3_topics": [
                {
                    "topic_id": t['topic_id'],
                    "name": t['name'],
                    "count": t['count'],
                    "main_themes": t['main_themes']
                }
                for t in topics_insights[:3]
            ]
        }
        
        return {
            "topics": topics_insights,
            "summary": summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Topics insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics/keywords")
async def get_topics_keywords():
    """Get keywords for each topic"""
    try:
        from app.core.models import topic_model
        
        if not topic_model or not topic_model.topic_model:
            try:
                topic_model._auto_load_model()
            except:
                raise HTTPException(status_code=404, detail="No topic model available")
        
        topic_info = topic_model.get_topic_info()
        topics_list = topic_info.get('topics', [])
        
        if not topics_list:
            return {"topics": [], "total_topics": 0}
        
        # Extract keywords per topic
        topics_keywords = []
        for topic in topics_list:
            topic_id = topic.get('topic_id')
            words = topic.get('words', [])
            
            keywords = [
                {
                    "word": w.get('word', ''),
                    "score": w.get('score', 0),
                    "rank": i + 1
                }
                for i, w in enumerate(words[:20])
            ]
            
            topics_keywords.append({
                "topic_id": topic_id,
                "name": topic.get('name', ''),
                "count": topic.get('count', 0),
                "keywords": keywords,
                "top_keywords": [w.get('word', '') for w in words[:5]]
            })
        
        return {
            "topic_keywords": topics_keywords,
            "topics": topics_keywords,
            "total_topics": len(topics_keywords)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Topics keywords error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/analysis")
async def get_content_analysis(db: Session = Depends(get_db)):
    """Get content analysis - what the documents are about"""
    try:
        # Optimize: Sample recent articles with content
        articles = (db.query(Article)
                   .filter(Article.content.isnot(None))
                   .order_by(Article.created_at.desc())
                   .limit(500)
                   .all())
        
        if not articles:
            return {
                "total_documents": 0,
                "content_summary": {},
                "main_themes": []
            }
        
        # Extract all keywords
        all_keywords = []
        for article in articles:
            content = article.content or article.raw_content or ''
            title = article.title or ''
            text = f"{title} {content}".strip()
            keywords = extract_keywords_from_text(text)
            all_keywords.extend(keywords)
        
        # Get top keywords as main themes
        keyword_counts = Counter(all_keywords)
        top_keywords = keyword_counts.most_common(30)
        
        # Group by categories (basic clustering)
        main_themes = []
        for word, count in top_keywords[:10]:
            main_themes.append({
                "theme": word.replace('_', ' '),
                "frequency": count,
                "percentage": round(count / len(all_keywords) * 100, 2) if all_keywords else 0
            })
        
        # Calculate statistics
        lengths = [len(a.content or a.raw_content or '') for a in articles]
        avg_length = round(sum(lengths) / len(lengths), 2) if lengths else 0
        
        # Estimate sentences (rough approximation)
        total_sentences = sum(len((a.content or a.raw_content or '').split('.')) for a in articles)
        
        return {
            "total_documents": len(articles),
            "avg_length": avg_length,
            "total_sentences": total_sentences,
            "total_keywords": len(keyword_counts),
            "content_summary": {
                "most_common": main_themes[:5],
                "emerging": main_themes[5:10] if len(main_themes) > 5 else []
            },
            "main_themes": main_themes
        }
    except Exception as e:
        logger.error(f"Content analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics/summary")
async def get_topics_summary():
    """Get summary of what topics are about"""
    try:
        from app.core.models import topic_model
        
        if not topic_model or not topic_model.topic_model:
            try:
                topic_model._auto_load_model()
            except:
                raise HTTPException(status_code=404, detail="No topic model available")
        
        topic_info = topic_model.get_topic_info()
        topics_list = topic_info.get('topics', [])
        
        if not topics_list:
            return {
                "total_topics": 0,
                "summary": [],
                "main_themes": []
            }
        
        # Build summary
        summary = []
        for topic in topics_list[:20]:
            words = topic.get('words', [])
            top_words = [w.get('word', '') for w in words[:5]]
            
            summary.append({
                "topic_id": topic.get('topic_id'),
                "name": topic.get('name', ''),
                "count": topic.get('count', 0),
                "main_keywords": ", ".join(top_words),
                "description": f"Topic about {', '.join(top_words[:3])}"
            })
        
        # Extract main themes
        all_words = []
        for topic in topics_list:
            words = topic.get('words', [])
            for w in words[:3]:
                all_words.append(w.get('word', ''))
        
        word_counts = Counter(all_words)
        main_themes = [
            {"theme": word, "frequency": count}
            for word, count in word_counts.most_common(10)
        ]
        
        return {
            "total_topics": len(topics_list),
            "summary": summary,
            "main_themes": main_themes
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Topics summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== TRENDS & IMPACT ANALYSIS APIs ==========

def extract_date_from_doc(doc: Dict) -> Optional[str]:
    """Extract date from document"""
    # Try created_at
    if 'created_at' in doc and doc['created_at']:
        try:
            if isinstance(doc['created_at'], str):
                return doc['created_at'][:10]
            return doc['created_at'].date().isoformat()
        except:
            pass
    
    # Try metadata
    if 'metadata' in doc:
        metadata = doc['metadata']
        if isinstance(metadata, dict):
            if 'publish_date' in metadata:
                return metadata['publish_date'][:10]
            if 'date' in metadata:
                return metadata['date'][:10]
    
    return None


@router.get("/trends/topics")
async def get_topics_trends(db: Session = Depends(get_db)):
    """Get topics trends over time"""
    try:
        # Optimize: Get articles with topics (exclude outlier -1)
        articles = (db.query(Article)
                   .filter(Article.topic_id.isnot(None),
                          Article.topic_id != -1)
                   .order_by(Article.created_at.desc())
                   .limit(2000)
                   .all())
        
        if not articles:
            return {
                "time_periods": [],
                "trends": []
            }
        
        # Group by date and topic
        date_topic_counts = {}
        
        for article in articles:
            if article.created_at:
                try:
                    if isinstance(article.created_at, str):
                        date_str = article.created_at[:10]
                    elif isinstance(article.created_at, (int, float)):
                        from datetime import datetime
                        date_str = datetime.fromtimestamp(article.created_at).date().isoformat()
                    else:
                        date_str = article.created_at.date().isoformat()
                except:
                    continue
                topic_id = article.topic_id
                
                if date_str not in date_topic_counts:
                    date_topic_counts[date_str] = {}
                
                date_topic_counts[date_str][topic_id] = date_topic_counts[date_str].get(topic_id, 0) + 1
        
        sorted_dates = sorted(date_topic_counts.keys())
        
        # Get top topics (already filtered, no need to check again)
        all_topic_counts = {}
        for article in articles:
            all_topic_counts[article.topic_id] = all_topic_counts.get(article.topic_id, 0) + 1
        
        top_topics = sorted(all_topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Build trends with smart names
        trends_data = []
        for topic_id, _ in top_topics:
            values = [date_topic_counts.get(date, {}).get(topic_id, 0) for date in sorted_dates]
            
            # Get topic name with smart generation
            topic_name = f"Chủ đề {topic_id}"
            keywords = []
            
            try:
                from app.core.models import topic_model
                if topic_model and topic_model.topic_model:
                    topic_info = topic_model.get_topic_info()
                    for t in topic_info.get('topics', []):
                        if t.get('topic_id') == topic_id:
                            topic_name = t.get('name', '')
                            words = t.get('words', [])
                            keywords = [w.get('word', '') for w in words[:5]]
                            
                            # Generate meaningful name if empty
                            if not topic_name and words:
                                keywords_list = [w.get('word', '') for w in words[:10]]
                                
                                if any(k in keywords_list for k in ['học', 'giáo', 'sinh', 'trường', 'giáo dục']):
                                    topic_name = 'Giáo dục & Đào tạo'
                                elif any(k in keywords_list for k in ['đường', 'giao thông', 'cầu', 'vận tải']):
                                    topic_name = 'Giao thông & Hạ tầng'
                                elif any(k in keywords_list for k in ['dự án', 'công trình', 'xây dựng', 'đầu tư']):
                                    topic_name = 'Dự án & Đầu tư'
                                elif any(k in keywords_list for k in ['y tế', 'bệnh', 'sức khỏe', 'bệnh viện']):
                                    topic_name = 'Y tế & Sức khỏe'
                                elif any(k in keywords_list for k in ['kinh tế', 'doanh nghiệp', 'sản xuất', 'công nghiệp']):
                                    topic_name = 'Kinh tế & Doanh nghiệp'
                                elif any(k in keywords_list for k in ['văn hóa', 'du lịch', 'lễ hội', 'di sản']):
                                    topic_name = 'Văn hóa & Du lịch'
                                elif any(k in keywords_list for k in ['nông', 'nông nghiệp', 'nông thôn', 'nông dân']):
                                    topic_name = 'Nông nghiệp & Nông thôn'
                                elif any(k in keywords_list for k in ['an ninh', 'công an', 'trật tự', 'phòng']):
                                    topic_name = 'An ninh & Trật tự'
                                else:
                                    topic_name = ' - '.join(keywords_list[:3])
                            break
            except:
                pass
            
            trends_data.append({
                "topic_id": topic_id,
                "topic_name": topic_name if topic_name else f"Chủ đề {topic_id}",
                "keywords": keywords,
                "values": values,
                "total_count": sum(values)
            })
        
        return {
            "time_periods": sorted_dates,
            "trends": trends_data
        }
    except Exception as e:
        logger.error(f"Topics trends error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/documents")
async def get_documents_trends(db: Session = Depends(get_db)):
    """Get documents trends over time"""
    try:
        # Optimize: Order by date and limit
        articles = (db.query(Article)
                   .order_by(Article.created_at.desc())
                   .limit(2000)
                   .all())
        
        if not articles:
            return {
                "time_periods": [],
                "document_counts": [],
                "cumulative_counts": []
            }
        
        # Group by date
        date_counts = {}
        for article in articles:
            if article.created_at:
                try:
                    if isinstance(article.created_at, str):
                        date_str = article.created_at[:10]
                    elif isinstance(article.created_at, (int, float)):
                        from datetime import datetime
                        date_str = datetime.fromtimestamp(article.created_at).date().isoformat()
                    else:
                        date_str = article.created_at.date().isoformat()
                    date_counts[date_str] = date_counts.get(date_str, 0) + 1
                except:
                    pass
        
        sorted_dates = sorted(date_counts.keys())
        counts = [date_counts[date] for date in sorted_dates]
        
        # Calculate cumulative
        cumulative = []
        total = 0
        for count in counts:
            total += count
            cumulative.append(total)
        
        return {
            "time_periods": sorted_dates,
            "document_counts": counts,
            "cumulative_counts": cumulative
        }
    except Exception as e:
        logger.error(f"Documents trends error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/keywords")
async def get_keywords_trends(db: Session = Depends(get_db)):
    """Get keywords trends over time"""
    try:
        # Optimize: Only load recent articles with content
        articles = (db.query(Article)
                   .filter(Article.content.isnot(None))
                   .order_by(Article.created_at.desc())
                   .limit(500)
                   .all())
        
        if not articles:
            return {
                "time_periods": [],
                "trends": []
            }
        
        # Group by date
        date_keywords = {}
        
        for article in articles:
            if article.created_at:
                try:
                    if isinstance(article.created_at, str):
                        date_str = article.created_at[:10]
                    elif isinstance(article.created_at, (int, float)):
                        # Convert timestamp to date
                        from datetime import datetime
                        date_str = datetime.fromtimestamp(article.created_at).date().isoformat()
                    else:
                        date_str = article.created_at.date().isoformat()
                except:
                    continue
                content = article.content or article.raw_content or ''
                title = article.title or ''
                text = f"{title} {content}".strip()
                keywords = extract_keywords_from_text(text)
                
                if date_str not in date_keywords:
                    date_keywords[date_str] = []
                date_keywords[date_str].extend(keywords)
        
        sorted_dates = sorted(date_keywords.keys())
        
        # Count keywords per date
        all_keywords_over_time = {}
        for date, keywords in date_keywords.items():
            keyword_counts = Counter(keywords)
            for word, count in keyword_counts.items():
                if word not in all_keywords_over_time:
                    all_keywords_over_time[word] = {}
                all_keywords_over_time[word][date] = count
        
        # Get top keywords overall
        all_keywords = []
        for keywords in date_keywords.values():
            all_keywords.extend(keywords)
        
        top_keywords = Counter(all_keywords).most_common(15)
        
        # Build trends
        trends_data = []
        for word, _ in top_keywords:
            values = [all_keywords_over_time.get(word, {}).get(date, 0) for date in sorted_dates]
            
            # Calculate growth
            growth_rate = 0
            if len(values) >= 2:
                recent = sum(values[-7:]) if len(values) >= 7 else sum(values)
                previous = sum(values[-14:-7]) if len(values) >= 14 else sum(values[:-7]) if len(values) > 7 else 0
                if previous > 0:
                    growth_rate = round((recent - previous) / previous * 100, 2)
            
            trends_data.append({
                "keyword": word.replace('_', ' '),
                "values": values,
                "growth_rate": growth_rate,
                "total_count": sum(values)
            })
        
        return {
            "time_periods": sorted_dates,
            "trends": trends_data
        }
    except Exception as e:
        logger.error(f"Keywords trends error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/impact-analysis")
async def get_impact_analysis():
    """Đánh giá mức độ ảnh hưởng của topics và keywords"""
    try:
        from app.core.models import topic_model
        
        if not topic_model or not topic_model.topic_model:
            raise HTTPException(status_code=404, detail="No topic model available")
        
        topic_info = topic_model.get_topic_info()
        topics_list = topic_info.get('topics', [])
        
        if not topics_list:
            return {
                "high_impact_topics": [],
                "emerging_topics": [],
                "declining_topics": []
            }
        
        # Sort by count
        topics_list.sort(key=lambda x: x.get('count', 0), reverse=True)
        
        # High impact topics (top 10%)
        high_impact_count = max(1, len(topics_list) // 10)
        high_impact = topics_list[:high_impact_count]
        
        # Emerging topics (growing)
        emerging = []
        for topic in topics_list[high_impact_count:]:
            if topic.get('count', 0) > 5:
                emerging.append(topic)
        
        # Format results
        high_impact_topics = [
            {
                "topic_id": t.get('topic_id'),
                "name": t.get('name', ''),
                "count": t.get('count', 0),
                "impact_score": round(t.get('count', 0) / topics_list[0].get('count', 1) * 100, 2),
                "keywords": [w.get('word', '') for w in t.get('words', [])[:5]]
            }
            for t in high_impact
        ]
        
        emerging_topics = [
            {
                "topic_id": t.get('topic_id'),
                "name": t.get('name', ''),
                "count": t.get('count', 0),
                "keywords": [w.get('word', '') for w in t.get('words', [])[:5]]
            }
            for t in emerging[:10]
        ]
        
        return {
            "high_impact_topics": high_impact_topics,
            "emerging_topics": emerging_topics,
            "total_topics_analyzed": len(topics_list)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Impact analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending/hot-topics")
async def get_hot_topics(timeframe: str = "24h", limit: int = 10, db: Session = Depends(get_db)):
    """Top chủ đề nóng trong 24h / 7 ngày / 30 ngày"""
    try:
        # Parse timeframe
        if timeframe == "24h":
            delta = timedelta(hours=24)
        elif timeframe == "7d":
            delta = timedelta(days=7)
        elif timeframe == "30d":
            delta = timedelta(days=30)
        else:
            delta = timedelta(hours=24)
        
        cutoff_time = datetime.now() - delta
        cutoff_timestamp = cutoff_time.timestamp()
        
        # Get recent articles with topics (optimize with limit)
        recent_articles = (db.query(Article)
                          .filter(Article.created_at >= cutoff_timestamp,
                                 Article.topic_id.isnot(None))
                          .order_by(Article.created_at.desc())
                          .limit(2000)
                          .all())
        
        if not recent_articles:
            return {
                "timeframe": timeframe,
                "hot_topics": [],
                "total": 0
            }
        
        # Count topics (exclude outlier topic -1)
        topic_counts = {}
        for article in recent_articles:
            # Skip outlier topic -1
            if article.topic_id != -1:
                topic_counts[article.topic_id] = topic_counts.get(article.topic_id, 0) + 1
        
        # Sort by count
        hot_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # Get topic names with smart generation
        hot_topics_data = []
        for topic_id, count in hot_topics:
            topic_name = f"Chủ đề {topic_id}"
            keywords = []
            
            try:
                from app.core.models import topic_model
                if topic_model and topic_model.topic_model:
                    topic_info = topic_model.get_topic_info()
                    for t in topic_info.get('topics', []):
                        if t.get('topic_id') == topic_id:
                            topic_name = t.get('name', '')
                            words = t.get('words', [])
                            keywords = [w.get('word', '') for w in words[:5]]
                            
                            # Generate meaningful name if empty
                            if not topic_name and words:
                                keywords_list = [w.get('word', '') for w in words[:10]]
                                
                                if any(k in keywords_list for k in ['học', 'giáo', 'sinh', 'trường', 'giáo dục']):
                                    topic_name = 'Giáo dục & Đào tạo'
                                elif any(k in keywords_list for k in ['đường', 'giao thông', 'cầu', 'vận tải']):
                                    topic_name = 'Giao thông & Hạ tầng'
                                elif any(k in keywords_list for k in ['dự án', 'công trình', 'xây dựng', 'đầu tư']):
                                    topic_name = 'Dự án & Đầu tư'
                                elif any(k in keywords_list for k in ['y tế', 'bệnh', 'sức khỏe', 'bệnh viện']):
                                    topic_name = 'Y tế & Sức khỏe'
                                elif any(k in keywords_list for k in ['kinh tế', 'doanh nghiệp', 'sản xuất', 'công nghiệp']):
                                    topic_name = 'Kinh tế & Doanh nghiệp'
                                elif any(k in keywords_list for k in ['văn hóa', 'du lịch', 'lễ hội', 'di sản']):
                                    topic_name = 'Văn hóa & Du lịch'
                                elif any(k in keywords_list for k in ['nông', 'nông nghiệp', 'nông thôn', 'nông dân']):
                                    topic_name = 'Nông nghiệp & Nông thôn'
                                elif any(k in keywords_list for k in ['an ninh', 'công an', 'trật tự', 'phòng']):
                                    topic_name = 'An ninh & Trật tự'
                                else:
                                    topic_name = ' - '.join(keywords_list[:3])
                            break
            except:
                pass
            
            hot_topics_data.append({
                "topic_id": topic_id,
                "name": topic_name if topic_name else f"Chủ đề {topic_id}",
                "count": count,
                "percentage": round(count / len(recent_articles) * 100, 2),
                "keywords": keywords
            })
        
        return {
            "timeframe": timeframe,
            "hot_topics": hot_topics_data,
            "total": len(recent_articles)
        }
    except Exception as e:
        logger.error(f"Hot topics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending/new-topics")
async def get_new_topics(days: int = 7, db: Session = Depends(get_db)):
    """Chủ đề mới xuất hiện trong N ngày gần đây"""
    try:
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # Get recent articles
        recent_articles = db.query(Article).filter(
            Article.created_at >= cutoff_time
        ).all()
        
        # Get older articles
        older_articles = db.query(Article).filter(
            Article.created_at < cutoff_time
        ).all()
        
        # Get topic IDs
        recent_topic_ids = set(a.topic_id for a in recent_articles if a.topic_id is not None)
        older_topic_ids = set(a.topic_id for a in older_articles if a.topic_id is not None)
        
        # New topics = recent - older
        new_topic_ids = recent_topic_ids - older_topic_ids
        
        # Count occurrences
        new_topics_data = []
        for topic_id in new_topic_ids:
            count = sum(1 for a in recent_articles if a.topic_id == topic_id)
            
            topic_name = f"Topic {topic_id}"
            try:
                from app.core.models import topic_model
                if topic_model and topic_model.topic_model:
                    topic_info = topic_model.get_topic_info()
                    for t in topic_info.get('topics', []):
                        if t.get('topic_id') == topic_id:
                            topic_name = t.get('name', topic_name)
                            break
            except:
                pass
            
            new_topics_data.append({
                "topic_id": topic_id,
                "name": topic_name.replace('_', ' '),
                "count": count,
                "first_seen": "Recently"
            })
        
        # Sort by count
        new_topics_data.sort(key=lambda x: x['count'], reverse=True)
        
        return {
            "days": days,
            "new_topics": new_topics_data,
            "total_new": len(new_topics_data)
        }
    except Exception as e:
        logger.error(f"New topics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending/keywords-spike")
async def get_keywords_spike(threshold: float = 2.0, timeframe: str = "7d", limit: int = 20, db: Session = Depends(get_db)):
    """Từ khóa tăng trưởng bất thường"""
    try:
        # Parse timeframe
        if timeframe == "7d":
            delta = timedelta(days=7)
        elif timeframe == "30d":
            delta = timedelta(days=30)
        else:
            delta = timedelta(days=7)
        
        cutoff_time = datetime.now() - delta
        cutoff_timestamp = cutoff_time.timestamp()
        
        # Get recent and older articles (optimize with limits)
        recent_articles = (db.query(Article)
                          .filter(Article.created_at >= cutoff_timestamp,
                                 Article.content.isnot(None))
                          .order_by(Article.created_at.desc())
                          .limit(500)
                          .all())
        
        older_articles = (db.query(Article)
                         .filter(Article.created_at < cutoff_timestamp,
                                Article.content.isnot(None))
                         .order_by(Article.created_at.desc())
                         .limit(500)
                         .all())
        
        # Extract keywords
        recent_keywords = []
        for article in recent_articles:
            content = article.content or article.raw_content or ''
            title = article.title or ''
            text = f"{title} {content}".strip()
            keywords = extract_keywords_from_text(text)
            recent_keywords.extend(keywords)
        
        older_keywords = []
        for article in older_articles:
            content = article.content or article.raw_content or ''
            title = article.title or ''
            text = f"{title} {content}".strip()
            keywords = extract_keywords_from_text(text)
            older_keywords.extend(keywords)
        
        # Count keywords
        recent_counts = Counter(recent_keywords)
        older_counts = Counter(older_keywords)
        
        # Find spike keywords
        spike_keywords = []
        for keyword, recent_count in recent_counts.most_common(100):
            older_count = older_counts.get(keyword, 0)
            
            if older_count > 0:
                growth_rate = recent_count / older_count
                if growth_rate >= threshold:
                    spike_keywords.append({
                        "keyword": keyword.replace('_', ' '),
                        "recent_count": recent_count,
                        "older_count": older_count,
                        "growth_rate": round(growth_rate, 2),
                        "increase": recent_count - older_count
                    })
            elif recent_count >= 5:
                spike_keywords.append({
                    "keyword": keyword.replace('_', ' '),
                    "recent_count": recent_count,
                    "older_count": 0,
                    "growth_rate": 999.99,  # Use a large number instead of inf
                    "increase": recent_count
                })
        
        # Sort by growth rate
        spike_keywords.sort(key=lambda x: x['growth_rate'], reverse=True)
        
        return {
            "timeframe": timeframe,
            "threshold": threshold,
            "spike_keywords": spike_keywords[:limit],
            "total_found": len(spike_keywords)
        }
    except Exception as e:
        logger.error(f"Keywords spike error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/overview")
async def get_summary_overview(period: str = "day", db: Session = Depends(get_db)):
    """Tổng quan số lượng bài viết theo ngày/tuần/tháng"""
    try:
        # Optimize: Order by date and limit to recent data
        articles = (db.query(Article)
                   .order_by(Article.created_at.desc())
                   .limit(2000)
                   .all())
        
        if not articles:
            return {
                "period": period,
                "summary": [],
                "total": 0
            }
        
        # Group by period
        period_counts = {}
        
        for article in articles:
            if article.created_at:
                try:
                    if isinstance(article.created_at, str):
                        date_str = article.created_at[:10]
                        if period == "day":
                            key = date_str
                        elif period == "week":
                            from datetime import datetime
                            dt = datetime.fromisoformat(date_str)
                            key = f"{dt.year}-W{dt.isocalendar()[1]}"
                        elif period == "month":
                            key = date_str[:7]
                        else:
                            key = date_str
                    elif isinstance(article.created_at, (int, float)):
                        from datetime import datetime
                        dt = datetime.fromtimestamp(article.created_at)
                        if period == "day":
                            key = dt.date().isoformat()
                        elif period == "week":
                            key = f"{dt.year}-W{dt.isocalendar()[1]}"
                        elif period == "month":
                            key = f"{dt.year}-{dt.month:02d}"
                        else:
                            key = dt.date().isoformat()
                    else:
                        if period == "day":
                            key = article.created_at.date().isoformat()
                        elif period == "week":
                            key = f"{article.created_at.year}-W{article.created_at.isocalendar()[1]}"
                        elif period == "month":
                            key = f"{article.created_at.year}-{article.created_at.month:02d}"
                        else:
                            key = article.created_at.date().isoformat()
                except:
                    continue
                
                period_counts[key] = period_counts.get(key, 0) + 1
        
        # Sort
        sorted_periods = sorted(period_counts.items())
        
        summary = [
            {"period": k, "count": v}
            for k, v in sorted_periods
        ]
        
        return {
            "period": period,
            "summary": summary,
            "total": len(articles)
        }
    except Exception as e:
        logger.error(f"Summary overview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/top-influential")
async def get_top_influential(limit: int = 10, db: Session = Depends(get_db)):
    """Top bài viết có ảnh hưởng lớn"""
    try:
        # Optimize: Order by date and sample recent articles
        articles = (db.query(Article)
                   .order_by(Article.created_at.desc())
                   .limit(1000)
                   .all())
        
        if not articles:
            return {
                "top_influential": [],
                "total": 0
            }
        
        # Calculate influence score
        influential_articles = []
        
        for article in articles:
            content = article.content or article.raw_content or ''
            word_count = len(content.split())
            
            # Simple influence score
            score = word_count
            
            # Boost if has topic
            if article.topic_id is not None:
                score *= 1.5
            
            # Boost if has images/videos
            if hasattr(article, 'images') and article.images:
                score *= 1.2
            
            influential_articles.append({
                "id": article.id,
                "title": article.title,
                "url": article.url,
                "word_count": word_count,
                "topic_id": article.topic_id,
                "influence_score": round(score, 2),
                "created_at": str(article.created_at) if article.created_at else None
            })
        
        # Sort by score
        influential_articles.sort(key=lambda x: x['influence_score'], reverse=True)
        
        return {
            "top_influential": influential_articles[:limit],
            "total": len(articles)
        }
    except Exception as e:
        logger.error(f"Top influential error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SHORTCUT ROUTES - For frontend compatibility (without /dashboard prefix)
# ============================================================================

@router.get("/hot-topics")
async def get_hot_topics_shortcut(timeframe: str = "24h", limit: int = 10, db: Session = Depends(get_db)):
    """Shortcut for trending/hot-topics"""
    return await get_hot_topics(timeframe, limit, db)


@router.get("/keywords-spike")
async def get_keywords_spike_shortcut(threshold: float = 2.0, timeframe: str = "7d", limit: int = 20, db: Session = Depends(get_db)):
    """Shortcut for trending/keywords-spike"""
    return await get_keywords_spike(threshold, timeframe, limit, db)


@router.get("/overview")
async def get_summary_overview_shortcut(period: str = "day", db: Session = Depends(get_db)):
    """Shortcut for summary/overview"""
    return await get_summary_overview(period, db)


@router.get("/top-influential")
async def get_top_influential_shortcut(limit: int = 10, db: Session = Depends(get_db)):
    """Shortcut for summary/top-influential"""
    return await get_top_influential(limit, db)
