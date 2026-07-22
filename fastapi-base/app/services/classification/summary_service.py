"""
Service để tạo tóm tắt thông tin theo lĩnh vực sử dụng LLM
"""
import os
import json
import logging
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.models.model_article import Article
from app.models.model_field_classification import Field, ArticleFieldClassification
from app.models.model_field_summary import FieldSummary

logger = logging.getLogger(__name__)


class FieldSummaryService:
    """Service để tạo tóm tắt theo lĩnh vực sử dụng OpenRouter"""
    
    def __init__(self, db: Session):
        """
        Initialize summary service with OpenRouter
        
        Args:
            db: Database session
        """
        self.db = db
        self.client = None
        self.provider = "openrouter"
        
        self._init_api_client()
    
    def _init_api_client(self):
        """Initialize OpenRouter client"""
        try:
            from openai import OpenAI
            
            # Try OpenRouter first (preferred)
            api_key = os.getenv("OPENAI_API_KEY")  # Using OpenRouter key
            if api_key and api_key.startswith("sk-or-"):
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1"
                )
                self.provider = "openrouter"
                logger.info(" OpenRouter client initialized for summary generation")
                return
            
            # Fallback to direct OpenAI
            if api_key:
                self.client = OpenAI(api_key=api_key)
                self.provider = "openai"
                logger.info(" OpenAI client initialized for summary generation")
                return
                    
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
        
        logger.warning(" No LLM provider available - summary generation disabled")
    
    def is_llm_available(self) -> bool:
        """Kiểm tra LLM có sẵn sàng không"""
        return self.client is not None
    
    def get_articles_in_period(
        self,
        field_id: int,
        start_time: float,
        end_time: float,
        limit: int = 100
    ) -> List[Article]:
        """Lấy danh sách bài viết trong khoảng thời gian"""
        article_ids = self.db.query(ArticleFieldClassification.article_id).filter(
            ArticleFieldClassification.field_id == field_id
        ).all()
        article_ids = [aid[0] for aid in article_ids]
        
        if not article_ids:
            return []
        
        articles = self.db.query(Article).filter(
            and_(
                Article.id.in_(article_ids),
                Article.created_at >= start_time,
                Article.created_at <= end_time
            )
        ).order_by(desc(Article.created_at)).limit(limit).all()
        
        return articles
    
    def calculate_statistics(self, articles: List[Article]) -> Dict:
        """Tính toán thống kê từ danh sách bài viết"""
        if not articles:
            return {
                "total": 0,
                "avg_engagement": 0,
                "top_sources": {},
                "sentiment": {"positive": 0, "negative": 0, "neutral": 0}
            }
        
        # Tính engagement
        total_engagement = 0
        source_count = {}
        sentiment_count = {"positive": 0, "negative": 0, "neutral": 0}
        
        for article in articles:
            engagement = (
                (article.likes_count or 0) +
                (article.shares_count or 0) +
                (article.comments_count or 0)
            )
            total_engagement += engagement
            
            # Count sources
            if article.source:
                source_count[article.source] = source_count.get(article.source, 0) + 1
        
        # Sort sources by count
        top_sources = dict(sorted(source_count.items(), key=lambda x: x[1], reverse=True)[:5])
        
        return {
            "total": len(articles),
            "avg_engagement": total_engagement / len(articles) if articles else 0,
            "top_sources": top_sources,
            "sentiment": sentiment_count
        }
    
    def get_top_articles(self, articles: List[Article], limit: int = 10) -> List[Dict]:
        """Lấy top bài viết nổi bật nhất"""
        # Sort by engagement
        sorted_articles = sorted(
            articles,
            key=lambda a: (a.likes_count or 0) + (a.shares_count or 0) + (a.comments_count or 0),
            reverse=True
        )
        
        top = []
        for article in sorted_articles[:limit]:
            engagement = (article.likes_count or 0) + (article.shares_count or 0) + (article.comments_count or 0)
            top.append({
                "id": article.id,
                "title": article.title,
                "engagement": engagement,
                "source": article.source,
                "published_date": article.published_date
            })
        
        return top
    
    def generate_summary_with_llm(
        self,
        field_name: str,
        articles: List[Article],
        statistics: Dict,
        model: str = None
    ) -> Optional[Dict]:
        """Tạo tóm tắt bằng LLM với multi-provider support"""
        if not self.is_llm_available() or not articles:
            return None
        
        # Chuẩn bị dữ liệu bài viết (chỉ lấy title để tiết kiệm token)
        article_titles = []
        for i, article in enumerate(articles[:50], 1):  # Giới hạn 50 bài
            article_titles.append(f"{i}. {article.title}")
        
        articles_text = "\n".join(article_titles)
        
        # Tạo prompt - FOCUS VÀO HƯNG YÊN với độ dài chi tiết
        prompt = f"""Phân tích và tóm tắt các bài viết gần đây về TỈNH HƯNG YÊN thuộc lĩnh vực "{field_name}".

 QUAN TRỌNG: CHỈ TÓM TẮT VỀ HƯNG YÊN, KHÔNG ĐỀ CẬP CÁC TỈNH KHÁC HAY CẢ NƯỚC.

THỐNG KÊ:
- Tổng số bài: {statistics['total']}
- Engagement trung bình: {statistics['avg_engagement']:.1f}
- Nguồn chính: {', '.join([f"{k}({v})" for k, v in list(statistics['top_sources'].items())[:3]])}

DANH SÁCH BÀI VIẾT VỀ HƯNG YÊN (50 bài gần nhất):
{articles_text}

YÊU CẦU:
1. Tóm tắt CHI TIẾT (8-10 câu) về các xu hướng, sự kiện chính tại HƯNG YÊN trong lĩnh vực này
   - Nêu rõ địa điểm, thời gian, nhân vật/cơ quan cụ thể
   - Đề cập các con số, số liệu quan trọng
   - Mô tả tác động, ý nghĩa của các sự kiện
2. Liệt kê 7-10 chủ đề chính về HƯNG YÊN được đề cập nhiều nhất
3. Liệt kê 10-15 từ khóa liên quan đến HƯNG YÊN
4. Đánh giá tổng quan chi tiết (3-4 câu) về tình hình lĩnh vực này tại HƯNG YÊN

LƯU Ý: 
- CHỈ nói về Hưng Yên, KHÔNG đề cập các tỉnh khác hoặc cả nước
- Tập trung vào địa danh, cơ quan, dự án CỤ THỂ tại Hưng Yên
- Viết CHI TIẾT, cụ thể, có chiều sâu
- Ví dụ: "tại Hưng Yên", "thành phố Hưng Yên", "các huyện trong tỉnh", "UBND tỉnh Hưng Yên", v.v.

Trả về JSON với format:
{{
    "summary": "Tóm tắt chi tiết 8-10 câu về Hưng Yên...",
    "key_topics": ["Chủ đề 1 về Hưng Yên", "Chủ đề 2 về Hưng Yên", ...],
    "trending_keywords": ["keyword1", "keyword2", ...],
    "overall_assessment": "Đánh giá chi tiết 3-4 câu về tình hình tại Hưng Yên..."
}}

Chỉ trả về JSON, không giải thích thêm."""

        try:
            result_text = None
            
            # OpenAI/OpenRouter compatible API
            model_name = model or "openai/gpt-4o-mini"
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia phân tích tin tức về TỈNH HƯNG YÊN. Bạn chỉ tóm tắt và phân tích thông tin liên quan đến Hưng Yên, không đề cập các địa phương khác. Viết chi tiết, cụ thể với đầy đủ thông tin."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1200,
                response_format={"type": "json_object"}
            )
            result_text = response.choices[0].message.content
            
            if not result_text:
                logger.error("No response from LLM")
                return None
            
            # Parse JSON response
            # Clean markdown code blocks if present
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            logger.info(f" Generated summary for field '{field_name}' using {self.provider}")
            return result
            
        except Exception as e:
            logger.error(f" Failed to generate summary with {self.provider}: {e}")
            return None
    
    def create_summary(
        self,
        field_id: int,
        period: str = "daily",  # daily, weekly, monthly
        target_date: Optional[date] = None,
        model: str = "openai/gpt-4o-mini"
    ) -> Optional[FieldSummary]:
        """
        Tạo tóm tắt cho một lĩnh vực trong khoảng thời gian
        
        Args:
            field_id: ID lĩnh vực
            period: Kỳ tóm tắt (daily, weekly, monthly)
            target_date: Ngày tạo summary (default: hôm nay)
            model: Model name (default: openai/gpt-4o-mini for OpenRouter)
            
        Returns:
            FieldSummary hoặc None
        """
        # Get field
        field = self.db.query(Field).filter(Field.id == field_id).first()
        if not field:
            logger.error(f"Field {field_id} not found")
            return None
        
        # Determine time range
        if target_date is None:
            target_date = date.today()
        
        target_datetime = datetime.combine(target_date, datetime.min.time())
        
        if period == "daily":
            start_time = target_datetime.timestamp()
            end_time = (target_datetime + timedelta(days=1)).timestamp()
        elif period == "weekly":
            # Start from Monday
            start_date = target_datetime - timedelta(days=target_datetime.weekday())
            start_time = start_date.timestamp()
            end_time = (start_date + timedelta(days=7)).timestamp()
        elif period == "monthly":
            start_date = target_datetime.replace(day=1)
            if target_datetime.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1)
            start_time = start_date.timestamp()
            end_time = end_date.timestamp()
        else:
            logger.error(f"Invalid period: {period}")
            return None
        
        # Get articles
        articles = self.get_articles_in_period(field_id, start_time, end_time)
        
        if not articles:
            logger.warning(f"No articles found for field {field_id} in period {period}")
            return None
        
        # Calculate statistics
        stats = self.calculate_statistics(articles)
        top_articles = self.get_top_articles(articles)
        
        # Generate summary with LLM
        llm_result = self.generate_summary_with_llm(
            field_name=field.name,
            articles=articles,
            statistics=stats,
            model=model
        )
        
        if not llm_result:
            logger.error("Failed to generate LLM summary")
            return None
        
        # Create or update summary
        existing = self.db.query(FieldSummary).filter(
            and_(
                FieldSummary.field_id == field_id,
                FieldSummary.summary_period == period,
                FieldSummary.summary_date == target_date
            )
        ).first()
        
        if existing:
            # Update
            existing.field_name = field.name
            existing.period_start = start_time
            existing.period_end = end_time
            existing.total_articles = stats['total']
            existing.avg_engagement = stats['avg_engagement']
            existing.top_sources = stats['top_sources']
            existing.key_topics = llm_result.get('key_topics', [])
            existing.summary_text = llm_result.get('summary', '')
            existing.sentiment_overview = stats['sentiment']
            existing.top_articles = top_articles
            existing.trending_keywords = llm_result.get('trending_keywords', [])
            existing.generation_method = 'llm'
            existing.model_used = f"{self.provider}:{model or 'default'}"
            existing.updated_at = time.time()
            
            self.db.commit()
            logger.info(f" Updated summary for field {field_id}")
            return existing
        else:
            # Create new
            summary = FieldSummary(
                field_id=field_id,
                field_name=field.name,
                summary_period=period,
                period_start=start_time,
                period_end=end_time,
                summary_date=target_date,
                total_articles=stats['total'],
                avg_engagement=stats['avg_engagement'],
                top_sources=stats['top_sources'],
                key_topics=llm_result.get('key_topics', []),
                summary_text=llm_result.get('summary', ''),
                sentiment_overview=stats['sentiment'],
                top_articles=top_articles,
                trending_keywords=llm_result.get('trending_keywords', []),
                generation_method='llm',
                model_used=f"{self.provider}:{model or 'default'}",
                created_at=time.time(),
                updated_at=time.time()
            )
            
            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)
            
            logger.info(f" Created summary for field {field_id}")
            return summary
    
    def create_summaries_for_all_fields(
        self,
        period: str = "daily",
        target_date: Optional[date] = None,
        model: str = "openai/gpt-4o-mini"
    ) -> List[FieldSummary]:
        """Tạo tóm tắt cho tất cả lĩnh vực"""
        fields = self.db.query(Field).all()
        summaries = []
        
        for field in fields:
            try:
                summary = self.create_summary(
                    field_id=field.id,
                    period=period,
                    target_date=target_date,
                    model=model
                )
                if summary:
                    summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to create summary for field {field.id}: {e}")
        
        return summaries
    
    def get_latest_summaries(
        self,
        period: str = "daily",
        limit: int = 10
    ) -> List[FieldSummary]:
        """Lấy các tóm tắt mới nhất"""
        return self.db.query(FieldSummary).filter(
            FieldSummary.summary_period == period
        ).order_by(desc(FieldSummary.summary_date)).limit(limit).all()
    
    def get_field_summaries(
        self,
        field_id: int,
        period: Optional[str] = None,
        limit: int = 10
    ) -> List[FieldSummary]:
        """Lấy tóm tắt của một lĩnh vực"""
        query = self.db.query(FieldSummary).filter(
            FieldSummary.field_id == field_id
        )
        
        if period:
            query = query.filter(FieldSummary.summary_period == period)
        
        return query.order_by(desc(FieldSummary.summary_date)).limit(limit).all()
