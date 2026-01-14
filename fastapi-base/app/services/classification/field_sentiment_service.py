"""
Service phân tích sentiment theo lĩnh vực
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
from app.models.model_field_sentiment import FieldSentiment

logger = logging.getLogger(__name__)


class FieldSentimentService:
    """Service phân tích sentiment theo lĩnh vực"""
    
    def __init__(self, db: Session):
        self.db = db
        self.client = None
        self.provider = "openrouter"
        self._init_api_client()
    
    def _init_api_client(self):
        """Initialize OpenRouter client"""
        try:
            from openai import OpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key and api_key.startswith("sk-or-"):
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1"
                )
                self.provider = "openrouter"
                logger.info(" OpenRouter client initialized for sentiment analysis")
                return
            
            if api_key:
                self.client = OpenAI(api_key=api_key)
                self.provider = "openai"
                logger.info(" OpenAI client initialized for sentiment analysis")
                return
                    
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
        
        logger.warning(" No LLM provider available - sentiment analysis disabled")
    
    def is_llm_available(self) -> bool:
        """Kiểm tra LLM có sẵn sàng không"""
        return self.client is not None
    
    def get_articles_in_period(
        self,
        field_id: int,
        start_time: float,
        end_time: float,
        limit: int = 200
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
    
    def analyze_sentiment_with_llm(
        self,
        field_name: str,
        articles: List[Article],
        model: str = "openai/gpt-4o-mini"
    ) -> Optional[Dict]:
        """Phân tích sentiment bằng LLM"""
        if not self.is_llm_available() or not articles:
            return None
        
        # Lấy 100 bài để phân tích
        sample_articles = articles[:100]
        article_titles = []
        for i, article in enumerate(sample_articles, 1):
            article_titles.append(f"{i}. {article.title}")
        
        articles_text = "\n".join(article_titles)
        
        prompt = f"""Phân tích sentiment (cảm xúc) của các bài viết về Hưng Yên thuộc lĩnh vực "{field_name}".

DANH SÁCH {len(sample_articles)} BÀI VIẾT GẦN NHẤT:
{articles_text}

YÊU CẦU:
1. Phân loại sentiment tổng quan:
   - Positive (tích cực): Tin tốt, thành tựu, phát triển
   - Negative (tiêu cực): Vấn đề, sự cố, khó khăn  
   - Neutral (trung lập): Thông tin, báo cáo thông thường

2. Ước tính tỷ lệ % cho mỗi loại (tổng = 100%)

3. Tính sentiment score trung bình (-1 đến 1):
   - Positive: 0.3 đến 1.0
   - Neutral: -0.2 đến 0.3
   - Negative: -1.0 đến -0.2

4. Liệt kê 5-7 từ khóa tích cực phổ biến nhất
5. Liệt kê 5-7 từ khóa tiêu cực phổ biến nhất (nếu có)

6. Nhận xét xu hướng sentiment:
   - improving: Xu hướng tích cực, nhiều tin tốt
   - declining: Xu hướng tiêu cực, nhiều vấn đề
   - stable: Ổn định, cân bằng

7. Mô tả ngắn gọn (2-3 câu) về tổng quan sentiment

Trả về JSON:
{{
    "sentiment_positive": 0.65,  // % positive (0-1)
    "sentiment_negative": 0.15,  // % negative (0-1)
    "sentiment_neutral": 0.20,   // % neutral (0-1)
    "avg_sentiment_score": 0.5,  // Score trung bình (-1 to 1)
    "positive_keywords": ["phát triển", "thành công", ...],
    "negative_keywords": ["khó khăn", "sự cố", ...],
    "sentiment_trend": "improving",  // improving/declining/stable
    "trend_description": "Mô tả xu hướng..."
}}

Chỉ trả về JSON."""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia phân tích sentiment tin tức về Hưng Yên. Phân tích cảm xúc chính xác và khách quan."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            
            # Clean markdown
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            logger.info(f" Analyzed sentiment for field '{field_name}' using {self.provider}")
            return result
            
        except Exception as e:
            logger.error(f" Failed to analyze sentiment: {e}")
            return None
    
    def create_sentiment_analysis(
        self,
        field_id: int,
        period: str = "monthly",
        target_date: Optional[date] = None,
        model: str = "openai/gpt-4o-mini"
    ) -> Optional[FieldSentiment]:
        """
        Tạo phân tích sentiment cho một lĩnh vực
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
        
        # Analyze sentiment with LLM
        llm_result = self.analyze_sentiment_with_llm(
            field_name=field.name,
            articles=articles,
            model=model
        )
        
        if not llm_result:
            logger.error("Failed to analyze sentiment with LLM")
            return None
        
        # Calculate counts
        total = len(articles)
        pos_ratio = llm_result.get('sentiment_positive', 0.0)
        neg_ratio = llm_result.get('sentiment_negative', 0.0)
        neu_ratio = llm_result.get('sentiment_neutral', 0.0)
        
        positive_count = int(total * pos_ratio)
        negative_count = int(total * neg_ratio)
        neutral_count = total - positive_count - negative_count
        
        # Create or update
        existing = self.db.query(FieldSentiment).filter(
            and_(
                FieldSentiment.field_id == field_id,
                FieldSentiment.period_type == period,
                FieldSentiment.period_date == target_date
            )
        ).first()
        
        if existing:
            # Update
            existing.field_name = field.name
            existing.period_start = start_time
            existing.period_end = end_time
            existing.total_articles = total
            existing.analyzed_articles = len(articles[:100])
            existing.sentiment_positive = pos_ratio
            existing.sentiment_negative = neg_ratio
            existing.sentiment_neutral = neu_ratio
            existing.positive_count = positive_count
            existing.negative_count = negative_count
            existing.neutral_count = neutral_count
            existing.avg_sentiment_score = llm_result.get('avg_sentiment_score', 0.0)
            existing.positive_keywords = llm_result.get('positive_keywords', [])
            existing.negative_keywords = llm_result.get('negative_keywords', [])
            existing.sentiment_trend = llm_result.get('sentiment_trend', 'stable')
            existing.trend_description = llm_result.get('trend_description', '')
            existing.analysis_method = 'llm'
            existing.model_used = f"{self.provider}:{model}"
            existing.updated_at = time.time()
            
            self.db.commit()
            logger.info(f" Updated sentiment for field {field_id}")
            return existing
        else:
            # Create new
            sentiment = FieldSentiment(
                field_id=field_id,
                field_name=field.name,
                period_type=period,
                period_date=target_date,
                period_start=start_time,
                period_end=end_time,
                total_articles=total,
                analyzed_articles=len(articles[:100]),
                sentiment_positive=pos_ratio,
                sentiment_negative=neg_ratio,
                sentiment_neutral=neu_ratio,
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                avg_sentiment_score=llm_result.get('avg_sentiment_score', 0.0),
                positive_keywords=llm_result.get('positive_keywords', []),
                negative_keywords=llm_result.get('negative_keywords', []),
                sentiment_trend=llm_result.get('sentiment_trend', 'stable'),
                trend_description=llm_result.get('trend_description', ''),
                analysis_method='llm',
                model_used=f"{self.provider}:{model}",
                created_at=time.time(),
                updated_at=time.time()
            )
            
            self.db.add(sentiment)
            self.db.commit()
            self.db.refresh(sentiment)
            
            logger.info(f" Created sentiment analysis for field {field_id}")
            return sentiment
    
    def create_sentiment_for_all_fields(
        self,
        period: str = "monthly",
        target_date: Optional[date] = None,
        model: str = "openai/gpt-4o-mini"
    ) -> List[FieldSentiment]:
        """Tạo phân tích sentiment cho tất cả lĩnh vực"""
        fields = self.db.query(Field).all()
        sentiments = []
        
        for field in fields:
            try:
                sentiment = self.create_sentiment_analysis(
                    field_id=field.id,
                    period=period,
                    target_date=target_date,
                    model=model
                )
                if sentiment:
                    sentiments.append(sentiment)
            except Exception as e:
                logger.error(f"Failed to analyze sentiment for field {field.id}: {e}")
        
        return sentiments
