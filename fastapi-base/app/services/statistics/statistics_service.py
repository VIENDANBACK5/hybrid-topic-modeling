"""
Statistics Service - Tính toán và cập nhật các bảng thống kê
Chạy định kỳ hoặc khi có data mới để cập nhật thống kê cho Superset
"""
import logging
import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from collections import Counter
from sqlalchemy import func, and_, or_, desc, extract, Integer
from sqlalchemy.orm import Session

from app.models.model_article import Article
from app.models.model_sentiment import SentimentAnalysis
from app.models.model_statistics import (
    TrendReport, HotTopic, KeywordStats, 
    TopicMentionStats, WebsiteActivityStats, 
    SocialActivityStats, DailySnapshot
)
from app.services.statistics.keyphrase_extractor_v2 import get_keyphrase_extractor_v2
import openai
import os
import json

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_community.callbacks import get_openai_callback

logger = logging.getLogger(__name__)


# Social platforms detection
SOCIAL_PLATFORMS = {
    'facebook.com': 'facebook',
    'fb.com': 'facebook',
    'youtube.com': 'youtube',
    'youtu.be': 'youtube',
    'tiktok.com': 'tiktok',
    'twitter.com': 'twitter',
    'x.com': 'twitter',
    'instagram.com': 'instagram',
    'threads.net': 'threads',
    'zalo.me': 'zalo',
    'linkedin.com': 'linkedin',
}

# Vietnamese stopwords for keyword extraction
VIETNAMESE_STOPWORDS = {
    'và', 'của', 'là', 'có', 'được', 'cho', 'với', 'trong', 'này', 'đã',
    'các', 'những', 'một', 'không', 'người', 'để', 'theo', 'về', 'từ',
    'đến', 'như', 'tại', 'khi', 'sau', 'trên', 'ra', 'còn', 'nhiều',
    'cũng', 'nhưng', 'hay', 'hoặc', 'nếu', 'thì', 'mà', 'vì', 'nên',
    'rằng', 'bị', 'do', 'sẽ', 'đang', 'vào', 'lại', 'năm', 'ngày',
    'việc', 'làm', 'nào', 'hơn', 'rất', 'quá', 'đây', 'đó', 'ai',
    'gì', 'sao', 'thế', 'bao', 'mấy', 'đâu', 'lúc', 'giờ', 'chỉ'
}


class StatisticsService:
    """Service tính toán và cập nhật các bảng thống kê"""
    
    def __init__(self, db: Session):
        self.db = db
        self.keyphrase_extractor = get_keyphrase_extractor_v2()
        
        # Initialize LangChain LLM for GPT cleaning
        self.llm = None
        try:
            if os.getenv('OPENAI_API_KEY'):
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.3,
                    max_tokens=4000,
                    max_retries=2
                )
                logger.info(" LangChain LLM initialized for statistics")
        except Exception as e:
            logger.warning(f"Could not init LLM: {e}")
    
    # ========== HELPER METHODS ==========
    
    def _get_period_range(self, period_type: str, reference_date: date = None) -> Tuple[date, date, str]:
        """Tính khoảng thời gian cho period_type"""
        ref = reference_date or date.today()
        
        if period_type == "daily":
            start = end = ref
            label = ref.strftime("%d/%m/%Y")
        elif period_type == "weekly":
            start = ref - timedelta(days=ref.weekday())
            end = start + timedelta(days=6)
            week_num = ref.isocalendar()[1]
            label = f"Tuần {week_num}/{ref.year}"
        elif period_type == "monthly":
            start = ref.replace(day=1)
            next_month = start.replace(day=28) + timedelta(days=4)
            end = next_month - timedelta(days=next_month.day)
            label = f"Tháng {ref.month}/{ref.year}"
        elif period_type == "latest_import":
            start = end = ref
            label = "Đợt nhập mới nhất"
        else:  # all_time
            start = date(2020, 1, 1)
            end = ref
            label = "Tất cả"
        
        return start, end, label
    
    def _detect_platform(self, domain: str) -> Optional[str]:
        """Detect social media platform từ domain"""
        if not domain:
            return None
        domain_lower = domain.lower()
        for pattern, platform in SOCIAL_PLATFORMS.items():
            if pattern in domain_lower:
                return platform
        return None
    
    def _extract_keywords(self, text: str, top_n: int = 50) -> List[Dict]:
        """
        Extract keyphrases (cụm từ có nghĩa) thay vì từ đơn
        Dùng TF-IDF để lấy n-grams (1-3 words)
        """
        if not text:
            return []
        
        try:
            # Extract keyphrases using TF-IDF (1-3 word phrases)
            keyphrases = self.keyphrase_extractor.extract_keyphrases_tfidf(
                texts=[text],
                top_n=top_n,
                ngram_range=(1, 3),  # 1-3 word phrases
                min_df=1
            )
            
            # Convert to old format for compatibility
            return [{"word": kp["phrase"], "count": int(kp["score"] * 100)} for kp in keyphrases]
            
        except Exception as e:
            logger.error(f"Keyphrase extraction failed, falling back to simple words: {e}")
            # Fallback to single words
            words = re.findall(r'\b[a-zA-Zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]{2,}\b', 
                              text.lower())
            word_counts = Counter(w for w in words if w not in VIETNAMESE_STOPWORDS and len(w) > 2)
            return [{"word": w, "count": c} for w, c in word_counts.most_common(top_n)]
    
    def _calculate_sentiment_score(self, pos: int, neg: int, neu: int) -> float:
        """Tính sentiment score: -1 (rất tiêu cực) đến +1 (rất tích cực)"""
        total = pos + neg + neu
        if total == 0:
            return 0.0
        return round((pos - neg) / total, 4)
    
    def regenerate_keywords_with_gpt(self, limit: int = 200) -> Dict:
        """
        Regenerate keywords với GPT cleaning và entity preservation
        """
        from sklearn.feature_extraction.text import CountVectorizer
        from sqlalchemy import text
        
        logger.info(f"Regenerating keywords from {limit} articles...")
        
        # 1. Load articles
        result = self.db.execute(
            text("SELECT content FROM articles WHERE content IS NOT NULL LIMIT :limit"),
            {"limit": limit}
        )
        texts = [row[0] for row in result.fetchall()]
        logger.info(f"Loaded {len(texts)} articles")
        
        # 2. Clean text
        cleaned = []
        for text in texts:
            text = re.sub(r'Created by.*?with.*?Truyền hình Hưng Yên', '', text, flags=re.IGNORECASE)
            text = re.sub(r'#\w+', '', text)
            text = re.sub(r'http\S+', '', text)
            text = re.sub(r'translate\s+\w+', '', text, flags=re.IGNORECASE)
            cleaned.append(text)
        
        # 3. Extract n-grams
        vectorizer = CountVectorizer(
            ngram_range=(2, 3),
            min_df=2,
            max_df=0.8,
            lowercase=True,
            max_features=200
        )
        X = vectorizer.fit_transform(cleaned)
        feature_names = vectorizer.get_feature_names_out()
        
        # Count mentions
        phrase_counts = {}
        for phrase in feature_names:
            count = sum(1 for text in cleaned if phrase in text.lower())
            phrase_counts[phrase] = count
        
        sorted_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)[:80]
        logger.info(f"Extracted {len(sorted_phrases)} raw phrases")
        
        # 4. GPT clean với entity preservation using LangChain
        if not self.llm:
            logger.warning("No LLM available, using raw keywords")
            return {"keywords": [p for p, c in sorted_phrases[:30]], "method": "raw"}
        
        phrases_list = [p for p, c in sorted_phrases[:50]]
        
        template = """Bạn là chuyên gia xử lý từ khóa tiếng Việt.

Danh sách cụm từ từ tin tức Hưng Yên:
{phrases}

**YÊU CẦU:**
1.  GIỮ địa danh HOÀN CHỈNH: "hưng yên", "phố hiến", "hà nội"
2.  LOẠI BỎ: "hình hưng", "truyền hình hưng" (metadata), "có ai", "yên có" (không hoàn chỉnh)
3.  GIỮ: "giải phóng mặt bằng", "dự án", "phát triển kinh tế", "doanh nghiệp"

Output JSON:
{{
  "kept": [
    {{"phrase": "hưng yên", "category": "địa danh"}},
    {{"phrase": "giải phóng mặt bằng", "category": "hành chính"}}
  ],
  "removed": ["hình hưng", "có ai"]
}}

Giữ 25-35 cụm có nghĩa.
"""
        
        prompt = PromptTemplate(
            input_variables=["phrases"],
            template=template
        )
        
        try:
            with get_openai_callback() as cb:
                chain = prompt | self.llm
                response = chain.invoke({"phrases": json.dumps(phrases_list, ensure_ascii=False)})
                result = json.loads(response.content)
                kept = result.get('kept', [])
                logger.info(f"GPT kept {len(kept)} clean phrases (tokens: {cb.total_tokens}, cost: ${cb.total_cost:.4f})")
        except Exception as e:
            logger.error(f"GPT cleaning failed: {e}")
            return {"keywords": [p for p, c in sorted_phrases[:30]], "method": "raw"}
        
        # 5. Match counts
        phrase_to_count = dict(sorted_phrases)
        final = []
        for item in kept:
            phrase = item['phrase'].lower()
            count = phrase_to_count.get(phrase, 0)
            if count == 0:
                for orig, orig_count in sorted_phrases:
                    if phrase in orig or orig in phrase:
                        count = orig_count
                        break
            if count > 0:
                final.append({
                    "phrase": phrase,
                    "count": count,
                    "category": item.get('category', 'khác')
                })
        
        final.sort(key=lambda x: x['count'], reverse=True)
        
        # 6. Save to database
        self.db.execute(text("DELETE FROM keyword_stats"))
        for kw in final:
            self.db.execute(
                text("""
                    INSERT INTO keyword_stats (keyword, mention_count, weight, period_type)
                    VALUES (:keyword, :count, :weight, 'all')
                """),
                {
                    "keyword": kw['phrase'],
                    "count": kw['count'],
                    "weight": kw['count'] / len(texts)
                }
            )
        self.db.commit()
        
        logger.info(f"Saved {len(final)} keywords to database")
        return {
            "total": len(final),
            "max_mentions": final[0]['count'] if final else 0,
            "keywords": final[:30],
            "method": "gpt_cleaned"
        }
    
    # ========== TREND REPORT ==========
    
    def calculate_trend_report(self, period_type: str = "weekly", reference_date: date = None) -> TrendReport:
        """Tính báo cáo xu hướng cho period_type"""
        start, end, label = self._get_period_range(period_type, reference_date)
        
        # Query sentiment data trong kỳ
        sentiments = self.db.query(SentimentAnalysis).filter(
            and_(
                func.date(SentimentAnalysis.published_date) >= start,
                func.date(SentimentAnalysis.published_date) <= end
            )
        ).all()
        
        if not sentiments:
            logger.info(f"No data for {period_type} {label}")
            return None
        
        # Tính toán
        total = len(sentiments)
        pos_count = sum(1 for s in sentiments if s.sentiment_group == 'positive')
        neg_count = sum(1 for s in sentiments if s.sentiment_group == 'negative')
        neu_count = total - pos_count - neg_count
        
        # Emotion distribution
        emotion_dist = Counter(s.emotion for s in sentiments)
        
        # Unique sources
        unique_sources = len(set(s.source_domain for s in sentiments if s.source_domain))
        
        # Unique topics
        unique_topics = len(set(s.topic_id for s in sentiments if s.topic_id))
        
        # Extract keywords từ tất cả content
        all_text = " ".join(s.content_snippet or "" for s in sentiments)
        top_keywords = self._extract_keywords(all_text, 20)
        
        # Top sources
        source_counts = Counter(s.source_domain for s in sentiments if s.source_domain)
        top_sources = [{"domain": d, "count": c} for d, c in source_counts.most_common(10)]
        
        # So sánh với kỳ trước
        prev_start = start - (end - start + timedelta(days=1))
        prev_end = start - timedelta(days=1)
        prev_count = self.db.query(func.count(SentimentAnalysis.id)).filter(
            and_(
                func.date(SentimentAnalysis.published_date) >= prev_start,
                func.date(SentimentAnalysis.published_date) <= prev_end
            )
        ).scalar() or 0
        
        mention_change = ((total - prev_count) / prev_count * 100) if prev_count > 0 else 0
        
        # Create/update report
        existing = self.db.query(TrendReport).filter(
            and_(
                TrendReport.period_type == period_type,
                TrendReport.period_start == start
            )
        ).first()
        
        if existing:
            report = existing
        else:
            report = TrendReport()
        
        report.period_type = period_type
        report.period_start = start
        report.period_end = end
        report.period_label = label
        report.total_mentions = total
        report.total_sources = unique_sources
        report.total_topics = unique_topics
        report.positive_count = pos_count
        report.negative_count = neg_count
        report.neutral_count = neu_count
        report.positive_ratio = round(pos_count / total * 100, 2) if total > 0 else 0
        report.negative_ratio = round(neg_count / total * 100, 2) if total > 0 else 0
        report.emotion_distribution = dict(emotion_dist)
        report.mention_change = round(mention_change, 2)
        report.top_keywords = top_keywords
        report.top_sources = top_sources
        
        if not existing:
            self.db.add(report)
        
        return report
    
    # ========== HOT TOPICS ==========
    
    def calculate_hot_topics(self, period_type: str = "weekly", reference_date: date = None, top_n: int = 20) -> List[HotTopic]:
        """Tính chủ đề hot / khủng hoảng"""
        start, end, label = self._get_period_range(period_type, reference_date)
        
        # Query sentiment grouped by topic
        topic_stats = self.db.query(
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            func.count(SentimentAnalysis.id).label('mention_count'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'positive', Integer)).label('pos'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'negative', Integer)).label('neg'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'neutral', Integer)).label('neu'),
        ).filter(
            and_(
                func.date(SentimentAnalysis.published_date) >= start,
                func.date(SentimentAnalysis.published_date) <= end,
                SentimentAnalysis.topic_id.isnot(None)
            )
        ).group_by(
            SentimentAnalysis.topic_id, 
            SentimentAnalysis.topic_name
        ).order_by(desc('mention_count')).limit(top_n * 2).all()
        
        # Tính velocity (so với kỳ trước)
        period_days = (end - start).days + 1
        prev_start = start - timedelta(days=period_days)
        prev_end = start - timedelta(days=1)
        
        results = []
        for rank, stat in enumerate(topic_stats[:top_n], 1):
            topic_id, topic_name, count, pos, neg, neu = stat
            pos = pos or 0
            neg = neg or 0
            neu = neu or 0
            
            # Previous period count
            prev_count = self.db.query(func.count(SentimentAnalysis.id)).filter(
                and_(
                    SentimentAnalysis.topic_id == topic_id,
                    func.date(SentimentAnalysis.published_date) >= prev_start,
                    func.date(SentimentAnalysis.published_date) <= prev_end
                )
            ).scalar() or 0
            
            velocity = ((count - prev_count) / prev_count) if prev_count > 0 else (1 if count > 0 else 0)
            
            # Hot score = mention * (1 + velocity)
            hot_score = count * (1 + max(0, velocity))
            
            # Crisis score = negative_ratio * velocity (nếu velocity > 0)
            neg_ratio = neg / count if count > 0 else 0
            crisis_score = neg_ratio * max(0, velocity) if velocity > 0 else neg_ratio
            
            # Emotion distribution for this topic
            emotions = self.db.query(
                SentimentAnalysis.emotion,
                func.count(SentimentAnalysis.id)
            ).filter(
                and_(
                    SentimentAnalysis.topic_id == topic_id,
                    func.date(SentimentAnalysis.published_date) >= start,
                    func.date(SentimentAnalysis.published_date) <= end
                )
            ).group_by(SentimentAnalysis.emotion).all()
            emotion_dist = {e: c for e, c in emotions}
            dominant_emotion = max(emotion_dist, key=emotion_dist.get) if emotion_dist else None
            
            # Sample titles
            samples = self.db.query(SentimentAnalysis.title).filter(
                and_(
                    SentimentAnalysis.topic_id == topic_id,
                    func.date(SentimentAnalysis.published_date) >= start,
                    func.date(SentimentAnalysis.published_date) <= end,
                    SentimentAnalysis.title.isnot(None)
                )
            ).limit(5).all()
            sample_titles = [s[0] for s in samples if s[0]]
            
            # Check existing
            existing = self.db.query(HotTopic).filter(
                and_(
                    HotTopic.period_type == period_type,
                    HotTopic.period_start == start,
                    HotTopic.topic_id == topic_id
                )
            ).first()
            
            hot_topic = existing or HotTopic()
            hot_topic.period_type = period_type
            hot_topic.period_start = start
            hot_topic.period_end = end
            hot_topic.topic_id = topic_id
            hot_topic.topic_name = topic_name
            hot_topic.mention_count = count
            hot_topic.mention_velocity = round(velocity, 4)
            hot_topic.hot_score = round(hot_score, 2)
            hot_topic.is_hot = hot_score > count * 1.5  # Hot nếu score cao hơn 50%
            hot_topic.is_crisis = crisis_score > 0.3  # Crisis nếu score > 0.3
            hot_topic.is_trending_up = velocity > 0.2
            hot_topic.is_trending_down = velocity < -0.2
            hot_topic.positive_count = pos
            hot_topic.negative_count = neg
            hot_topic.neutral_count = neu
            hot_topic.crisis_score = round(crisis_score, 4)
            hot_topic.dominant_emotion = dominant_emotion
            hot_topic.emotion_distribution = emotion_dist
            hot_topic.sample_titles = sample_titles
            hot_topic.rank = rank
            
            if not existing:
                self.db.add(hot_topic)
            results.append(hot_topic)
        
        return results
    
    # ========== KEYWORD STATS ==========
    
    def calculate_keyword_stats(self, period_type: str = "weekly", reference_date: date = None, top_n: int = 100) -> List[KeywordStats]:
        """Tính thống kê từ khóa cho WordCloud - ƯU TIÊN TÊN RIÊNG VÀ SỰ KIỆN HOT"""
        start, end, label = self._get_period_range(period_type, reference_date)
        
        if period_type == "latest_import":
            # Lấy thời gian tạo mới nhất trong bảng articles
            max_created = self.db.query(func.max(Article.created_at)).scalar()
            if not max_created:
                return []
            
            # Lấy tất cả các bài thuộc đợt import này (trong vòng 1 giờ từ mốc max)
            articles = self.db.query(
                SentimentAnalysis.content_snippet,
                SentimentAnalysis.title,
                SentimentAnalysis.sentiment_group,
                SentimentAnalysis.topic_id,
                SentimentAnalysis.topic_name,
                SentimentAnalysis.source_domain
            ).join(
                Article, SentimentAnalysis.article_id == Article.id
            ).filter(
                Article.created_at >= max_created - 3600
            ).all()
        else:
            # Lấy tất cả content trong kỳ
            articles = self.db.query(
                SentimentAnalysis.content_snippet,
                SentimentAnalysis.title,
                SentimentAnalysis.sentiment_group,
                SentimentAnalysis.topic_id,
                SentimentAnalysis.topic_name,
                SentimentAnalysis.source_domain
            ).filter(
                and_(
                    func.date(SentimentAnalysis.published_date) >= start,
                    func.date(SentimentAnalysis.published_date) <= end
                )
            ).all()
        
        if not articles:
            return []
        
        # COMPREHENSIVE Vietnamese stopwords - TẤT CẢ từ đơn vô nghĩa
        STOPWORDS = {
            # Common stopwords
            'và', 'của', 'là', 'có', 'được', 'cho', 'với', 'trong', 'này', 'đã',
            'các', 'những', 'một', 'không', 'người', 'để', 'theo', 'về', 'từ',
            'đến', 'như', 'tại', 'khi', 'sau', 'trên', 'ra', 'còn', 'nhiều',
            'cũng', 'nhưng', 'hay', 'hoặc', 'nếu', 'thì', 'mà', 'vì', 'nên',
            'rằng', 'bị', 'do', 'sẽ', 'đang', 'vào', 'lại', 'năm', 'ngày',
            'việc', 'làm', 'nào', 'hơn', 'rất', 'quá', 'đây', 'đó', 'ai',
            'gì', 'sao', 'thế', 'bao', 'mấy', 'đâu', 'lúc', 'giờ', 'chỉ',
            'mình', 'bạn', 'anh', 'chị', 'em', 'ông', 'bà', 'cô', 'chú',
            'con', 'cái', 'nhà', 'rồi', 'nữa', 'luôn', 'xong', 'xin', 'ạ',
            'nhé', 'nha', 'nhỉ', 'ơi', 'hả', 'vậy', 'thôi', 'lắm', 'ghê',
            'cần', 'muốn', 'phải', 'biết', 'thấy', 'nói', 'xem', 'đi', 'lên',
            'xuống', 'qua', 'lại', 'mới', 'vừa', 'hết', 'xong', 'liền',
            # Single meaningless words - EXPANDED
            'tỉnh', 'xã', 'huyện', 'phường', 'quận', 'thôn', 'xóm', 'ấp',
            'nhạc', 'nền', 'tiền', 'đất', 'nay', 'nhất', 'chơi', 'nước',
            'gần', 'xa', 'cùng', 'số', 'hai', 'ba', 'bốn', 'năm', 'sáu',
            'bảy', 'tám', 'chín', 'mười', 'trăm', 'nghìn', 'triệu', 'tỷ',
            'xe', 'nhận', 'vẫn', 'tháng', 'tuần', 'ngày', 'giờ', 'phút',
            'cả', 'toàn', 'mọi', 'tất', 'riêng', 'chung', 'khác', 'như',
            'tết', 'lễ', 'hội', 'đêm', 'đầu', 'cuối', 'giữa', 'trước',
            'sang', 'bên', 'quán', 'ngay', 'gặp', 'khu', 'thứ', 'yêu',
            'thi', 'quanh', 'nhau', 'tốt', 'bằng', 'tới', 'tin', 'chiều',
            'câu', 'đẹp', 'mua', 'mất', 'đường', 'lương', 'chỗ', 'chứ',
            'tiếng', 'lần', 'giá', 'bài', 'trước', 'hưng', 'yên', 'hình',
            'truyền', 'ocean', 'concert', 'show', 'live', 'clip', 'post',
            'bộ', 'nơi', 'mỹ', 'nga', 'hiện', 'no1', 'cuộc', 'lần', 'đầu_tiên',
            # Social media garbage & TikTok tags
            'translate', 'with', 'created', 'http', 'https', 'www', 'com',
            'tiktoknews', 'truyenhinhhungyen', 'facebook', 'tiktok', 'threads',
            'video', 'photo', 'image', 'link', 'share', 'like', 'comment',
            'by', 'the', 'and', 'for', 'you', 'this', 'that', 'are', 'was',
            'music', 'songs', 'song', 'lyrics', 'lyric', 'lyricsvideo', 'fyp', 
            'foryou', 'foryoupage', 'viral', 'trending', 'xyzbca', 'fypシviral', 
            'targetaudience', 'prodshushy', 'malcolmtodd', 'repost', 'dance', 
            'singing', 'nmusic', 'applemusic', 'remix', 'nightcore', 'banger', 
            'edit', 'relatable', 'slow', 'slowed', 'cover', 'vibe',
            # English common stopwords (non-overlapping with Vietnamese)
            'to', 'in', 'on', 'at', 'of', 'is', 'am', 'be', 'been', 'being', 
            'have', 'has', 'had', 'do', 'does', 'did', 'but', 'if', 'then', 
            'else', 'from', 'up', 'out', 'now', 'about', 'all', 'any', 'both', 
            'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 
            'not', 'only', 'own', 'same', 'too', 'very', 'will', 'just',
            # Garbage patterns
            'yêns', 'hưngs', 'việts', 'nams'
        }
        
        GARBAGE_PATTERNS = [
            'translate', 'http', 'www', 'tiktoknews', 'titkoknews', 'truyenhinhhungyen',
            'created', 'by truyền', 'hưng yêns', '.com', '.vn', 'facebook.com',
            'maduro', 'venezuela', 'khiến', 'khoảng', 'titkok',
            'hôm nay', 'tối qua', 'thật sự', 'thời gian',
            'lyrics', 'music', 'songs', 'song', 'blowthisup', 'xyzbca', 'of the',
            'foryou', 'fyp', 'viral', 'trending', 'repost', 'applemusic', 'nightcore',
            'banger', 'edit', 'vibe', 'slow', 'sound', 'audio', 'melaniemartinez',
            'prodshushy', 'malcolmtodd'
        ]
        
        HOT_EVENT_PATTERNS = [
            'tai nạn', 'cháy', 'vụ án', 'bắt giữ', 'triệt phá', 'phá án',
            'sập', 'đổ', 'lũ lụt', 'bão', 'động đất', 'dịch bệnh',
            'biểu tình', 'đình công', 'tham nhũng', 'kỷ luật', 'bổ nhiệm',
            'bầu cử', 'họp quốc hội', 'nghị quyết', 'chỉ thị',
            'tăng giá', 'giảm giá', 'lạm phát', 'tỷ giá', 'chứng khoán',
            'bất động sản', 'đấu giá', 'phá sản', 'nợ xấu',
            'ma túy', 'cờ bạc', 'lừa đảo', 'trộm cắp', 'cướp',
            'buôn lậu', 'đường dây', 'ổ nhóm', 'băng nhóm',
            'kẹt xe', 'ùn tắc', 'tai nạn giao thông', 'csgt', 'phạt nguội',
            'scandal', 'ly hôn', 'kết hôn', 'qua đời', 'nhập viện'
        ]
        
        # 1. Prepare raw texts and document info for stats calculation
        # Run Underthesea tokenizer on each text first for clean word boundaries
        from underthesea import word_tokenize
        texts = []
        tokenized_texts = []
        doc_info = []
        for content, title, sentiment_group, topic_id, topic_name, domain in articles:
            text = f"{title or ''} {content or ''}"
            texts.append(text)
            try:
                # format="text" replaces spaces inside compound words with underscores
                tok = word_tokenize(text.lower(), format="text")
            except:
                tok = text.lower()
            tokenized_texts.append(tok)
            doc_info.append({
                'sentiment': sentiment_group,
                'topic_id': topic_id,
                'topic_name': topic_name,
                'domain': domain
            })
            
        # 2. Clean stop words from the tokenized texts
        cleaned_texts = []
        for tok in tokenized_texts:
            words = []
            for w in tok.split():
                clean_w = re.sub(r'[^\w\s_àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', '', w)
                if clean_w and clean_w not in STOPWORDS and not clean_w.isdigit() and len(clean_w.replace('_', '')) >= 2:
                    words.append(clean_w)
            cleaned_texts.append(' '.join(words))
            
        # 3. Extract keyphrase candidates using Scikit-Learn TF-IDF N-grams (1-2 words)
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1 if len(articles) < 5 else 2,
            max_df=0.9,
            max_features=500
        )
        
        try:
            vectorizer.fit(cleaned_texts)
            feature_names = vectorizer.get_feature_names_out()
        except Exception as e:
            logger.warning(f"TF-IDF Vectorizer fit failed: {e}")
            feature_names = []
            
        # 4. Filter candidates
        candidates = []
        for phrase in feature_names:
            display_phrase = phrase.replace('_', ' ')
            words_in_phrase = display_phrase.split()
            
            # Must not contain stopwords
            if any(w in STOPWORDS for w in words_in_phrase):
                continue
            # Must not match garbage patterns
            if any(any(p in w for p in GARBAGE_PATTERNS) for w in words_in_phrase):
                continue
            # Must satisfy length constraints (at least 2 words / syllables)
            if len(words_in_phrase) < 2:
                continue
                
            candidates.append((phrase, display_phrase))
            
        # 5. Extract exact count, docs, sentiment, topics, and sources
        keyword_data = {}
        entity_set = getattr(self.keyphrase_extractor, 'entity_set', set())
        
        for phrase, display_phrase in candidates[:top_n * 2]:
            boost = 1.0
            if any(p in display_phrase for p in HOT_EVENT_PATTERNS):
                boost *= 2.0
            # Boost multi-word phrases (more than 1 word)
            if len(display_phrase.split()) >= 2:
                boost *= 1.5
            if any(e in display_phrase for e in entity_set):
                boost *= 2.5
                
            keyword_data[display_phrase] = {
                'count': 0, 'docs': 0, 'pos': 0, 'neg': 0, 'neu': 0,
                'topics': Counter(), 'sources': Counter(),
                'boost': boost
            }
            
            # Count exact occurrences with word boundaries (\b) in space-separated text
            pattern = re.compile(r'\b' + re.escape(display_phrase).replace(r'\ ', r'\s+') + r'\b')
            for idx, tok in enumerate(tokenized_texts):
                text_lower = tok.replace('_', ' ').lower()
                matches = pattern.findall(text_lower)
                if matches:
                    count = len(matches)
                    info = doc_info[idx]
                    keyword_data[display_phrase]['count'] += count
                    keyword_data[display_phrase]['docs'] += 1
                    
                    if info['sentiment'] == 'positive':
                        keyword_data[display_phrase]['pos'] += 1
                    elif info['sentiment'] == 'negative':
                        keyword_data[display_phrase]['neg'] += 1
                    else:
                        keyword_data[display_phrase]['neu'] += 1
                        
                    if info['topic_id']:
                        keyword_data[display_phrase]['topics'][(info['topic_id'], info['topic_name'])] += 1
                    if info['domain']:
                        keyword_data[display_phrase]['sources'][info['domain']] += 1
                        
        # Filter out candidates with 0 count
        keyword_data = {k: v for k, v in keyword_data.items() if v['count'] > 0}
        
        # Calculate weighted score = count * boost
        for key in keyword_data:
            keyword_data[key]['weighted_score'] = keyword_data[key]['count'] * keyword_data[key].get('boost', 1.0)
            
        # Sort by weighted_score
        sorted_keywords = sorted(keyword_data.items(), key=lambda x: x[1]['weighted_score'], reverse=True)[:top_n]
        
        # Normalize weight for WordCloud
        max_score = sorted_keywords[0][1]['weighted_score'] if sorted_keywords else 1
        
        results = []
        for keyword, data in sorted_keywords:
            # Check existing
            existing = self.db.query(KeywordStats).filter(
                and_(
                    KeywordStats.period_type == period_type,
                    KeywordStats.period_start == start,
                    KeywordStats.keyword == keyword
                )
            ).first()
            
            stat = existing or KeywordStats()
            stat.period_type = period_type
            stat.period_start = start
            stat.period_end = end
            stat.keyword = keyword
            stat.keyword_normalized = keyword.lower()
            stat.mention_count = data['count']
            stat.document_count = data['docs']
            stat.positive_count = data['pos']
            stat.negative_count = data['neg']
            stat.neutral_count = data['neu']
            stat.sentiment_score = self._calculate_sentiment_score(data['pos'], data['neg'], data['neu'])
            stat.related_topics = [
                {"topic_id": tid, "topic_name": tname, "count": cnt}
                for (tid, tname), cnt in data['topics'].most_common(5)
            ]
            stat.top_sources = [
                {"domain": d, "count": c}
                for d, c in data['sources'].most_common(5)
            ]
            # Weight uses logarithmic scaling to look nice
            import math
            stat.weight = round(math.log1p(data['weighted_score']) / math.log1p(max_score), 4)
            
            if not existing:
                self.db.add(stat)
            results.append(stat)
            
        logger.info(f"Calculated {len(results)} keyword stats using TF-IDF N-grams for {period_type}")
        return results
    
    # ========== TOPIC MENTION STATS ==========
    
    def calculate_topic_mention_stats(self, period_type: str = "weekly", reference_date: date = None) -> List[TopicMentionStats]:
        """Thống kê đề cập theo chủ đề"""
        start, end, label = self._get_period_range(period_type, reference_date)
        
        # Query grouped by topic
        from sqlalchemy import Integer
        topic_data = self.db.query(
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            SentimentAnalysis.category,
            func.count(SentimentAnalysis.id).label('total'),
            func.count(func.distinct(SentimentAnalysis.source_domain)).label('sources'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'positive', Integer)).label('pos'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'negative', Integer)).label('neg'),
        ).filter(
            and_(
                func.date(SentimentAnalysis.published_date) >= start,
                func.date(SentimentAnalysis.published_date) <= end,
                SentimentAnalysis.topic_id.isnot(None)
            )
        ).group_by(
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            SentimentAnalysis.category
        ).order_by(desc('total')).all()
        
        results = []
        for rank, data in enumerate(topic_data, 1):
            topic_id, topic_name, category, total, sources, pos, neg = data
            pos = pos or 0
            neg = neg or 0
            neu = total - pos - neg
            
            # Emotion breakdown
            emotions = self.db.query(
                SentimentAnalysis.emotion,
                func.count(SentimentAnalysis.id)
            ).filter(
                and_(
                    SentimentAnalysis.topic_id == topic_id,
                    func.date(SentimentAnalysis.published_date) >= start,
                    func.date(SentimentAnalysis.published_date) <= end
                )
            ).group_by(SentimentAnalysis.emotion).all()
            emotion_breakdown = {e: c for e, c in emotions}
            
            # Previous period comparison
            period_days = (end - start).days + 1
            prev_start = start - timedelta(days=period_days)
            prev_count = self.db.query(func.count(SentimentAnalysis.id)).filter(
                and_(
                    SentimentAnalysis.topic_id == topic_id,
                    func.date(SentimentAnalysis.published_date) >= prev_start,
                    func.date(SentimentAnalysis.published_date) < start
                )
            ).scalar() or 0
            
            change_pct = ((total - prev_count) / prev_count * 100) if prev_count > 0 else 0
            
            # Check existing
            existing = self.db.query(TopicMentionStats).filter(
                and_(
                    TopicMentionStats.period_type == period_type,
                    TopicMentionStats.period_start == start,
                    TopicMentionStats.topic_id == topic_id
                )
            ).first()
            
            stat = existing or TopicMentionStats()
            stat.period_type = period_type
            stat.period_start = start
            stat.period_end = end
            stat.topic_id = topic_id
            stat.topic_name = topic_name
            stat.category = category
            stat.total_mentions = total
            stat.unique_sources = sources
            stat.positive_mentions = pos
            stat.negative_mentions = neg
            stat.neutral_mentions = neu
            stat.emotion_breakdown = emotion_breakdown
            stat.sentiment_score = self._calculate_sentiment_score(pos, neg, neu)
            stat.mention_change_pct = round(change_pct, 2)
            stat.rank_by_mention = rank
            
            if not existing:
                self.db.add(stat)
            results.append(stat)
        
        # Rank by negative
        results.sort(key=lambda x: x.negative_mentions, reverse=True)
        for rank, stat in enumerate(results, 1):
            stat.rank_by_negative = rank
        
        return results
    
    # ========== WEBSITE ACTIVITY STATS ==========
    
    def calculate_website_stats(self, period_type: str = "weekly", reference_date: date = None) -> List[WebsiteActivityStats]:
        """Thống kê website hoạt động theo chủ đề"""
        start, end, label = self._get_period_range(period_type, reference_date)
        
        from sqlalchemy import Integer
        # Query grouped by domain and topic
        data = self.db.query(
            SentimentAnalysis.source_domain,
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            SentimentAnalysis.category,
            func.count(SentimentAnalysis.id).label('count'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'positive', Integer)).label('pos'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'negative', Integer)).label('neg'),
        ).filter(
            and_(
                func.date(SentimentAnalysis.published_date) >= start,
                func.date(SentimentAnalysis.published_date) <= end,
                SentimentAnalysis.source_domain.isnot(None)
            )
        ).group_by(
            SentimentAnalysis.source_domain,
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            SentimentAnalysis.category
        ).all()
        
        # Filter out social platforms (handled separately)
        results = []
        overall_ranks = {}  # domain -> total count
        
        for domain, topic_id, topic_name, category, count, pos, neg in data:
            if self._detect_platform(domain):
                continue  # Skip social platforms
            
            pos = pos or 0
            neg = neg or 0
            neu = count - pos - neg
            
            # Accumulate for overall ranking
            overall_ranks[domain] = overall_ranks.get(domain, 0) + count
            
            # Emotion distribution
            emotions = self.db.query(
                SentimentAnalysis.emotion,
                func.count(SentimentAnalysis.id)
            ).filter(
                and_(
                    SentimentAnalysis.source_domain == domain,
                    SentimentAnalysis.topic_id == topic_id if topic_id else True,
                    func.date(SentimentAnalysis.published_date) >= start,
                    func.date(SentimentAnalysis.published_date) <= end
                )
            ).group_by(SentimentAnalysis.emotion).all()
            emotion_dist = {e: c for e, c in emotions}
            dominant = max(emotion_dist, key=emotion_dist.get) if emotion_dist else None
            
            # Check existing
            existing = self.db.query(WebsiteActivityStats).filter(
                and_(
                    WebsiteActivityStats.period_type == period_type,
                    WebsiteActivityStats.period_start == start,
                    WebsiteActivityStats.domain == domain,
                    WebsiteActivityStats.topic_id == topic_id if topic_id else WebsiteActivityStats.topic_id.is_(None)
                )
            ).first()
            
            stat = existing or WebsiteActivityStats()
            stat.period_type = period_type
            stat.period_start = start
            stat.period_end = end
            stat.domain = domain
            stat.website_type = 'news'  # Default, có thể classify sau
            stat.topic_id = topic_id
            stat.topic_name = topic_name
            stat.category = category
            stat.article_count = count
            stat.total_mentions = count
            stat.positive_count = pos
            stat.negative_count = neg
            stat.neutral_count = neu
            stat.avg_sentiment_score = self._calculate_sentiment_score(pos, neg, neu)
            stat.emotion_distribution = emotion_dist
            stat.dominant_emotion = dominant
            
            if not existing:
                self.db.add(stat)
            results.append(stat)
        
        # Set overall ranks
        sorted_domains = sorted(overall_ranks.items(), key=lambda x: x[1], reverse=True)
        domain_ranks = {d: r for r, (d, _) in enumerate(sorted_domains, 1)}
        for stat in results:
            stat.rank_overall = domain_ranks.get(stat.domain, 999)
        
        return results
    
    # ========== SOCIAL ACTIVITY STATS ==========
    
    def calculate_social_stats(self, period_type: str = "weekly", reference_date: date = None) -> List[SocialActivityStats]:
        """Thống kê mạng xã hội theo chủ đề"""
        start, end, label = self._get_period_range(period_type, reference_date)
        
        from sqlalchemy import Integer
        # Query grouped by domain and topic
        data = self.db.query(
            SentimentAnalysis.source_domain,
            SentimentAnalysis.source_url,
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            SentimentAnalysis.category,
            func.count(SentimentAnalysis.id).label('count'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'positive', Integer)).label('pos'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'negative', Integer)).label('neg'),
        ).filter(
            and_(
                func.date(SentimentAnalysis.published_date) >= start,
                func.date(SentimentAnalysis.published_date) <= end,
                SentimentAnalysis.source_domain.isnot(None)
            )
        ).group_by(
            SentimentAnalysis.source_domain,
            SentimentAnalysis.source_url,
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            SentimentAnalysis.category
        ).all()
        
        results = []
        platform_ranks = {}  # platform -> {account -> count}
        
        for domain, url, topic_id, topic_name, category, count, pos, neg in data:
            platform = self._detect_platform(domain)
            if not platform:
                continue  # Skip non-social
            
            pos = pos or 0
            neg = neg or 0
            neu = count - pos - neg
            
            # Track for ranking
            if platform not in platform_ranks:
                platform_ranks[platform] = {}
            platform_ranks[platform][domain] = platform_ranks[platform].get(domain, 0) + count
            
            # Emotion distribution
            emotions = self.db.query(
                SentimentAnalysis.emotion,
                func.count(SentimentAnalysis.id)
            ).filter(
                and_(
                    SentimentAnalysis.source_domain == domain,
                    SentimentAnalysis.topic_id == topic_id if topic_id else True,
                    func.date(SentimentAnalysis.published_date) >= start,
                    func.date(SentimentAnalysis.published_date) <= end
                )
            ).group_by(SentimentAnalysis.emotion).all()
            emotion_dist = {e: c for e, c in emotions}
            dominant = max(emotion_dist, key=emotion_dist.get) if emotion_dist else None
            
            # Check existing
            existing = self.db.query(SocialActivityStats).filter(
                and_(
                    SocialActivityStats.period_type == period_type,
                    SocialActivityStats.period_start == start,
                    SocialActivityStats.platform == platform,
                    SocialActivityStats.account_name == domain,
                    SocialActivityStats.topic_id == topic_id if topic_id else SocialActivityStats.topic_id.is_(None)
                )
            ).first()
            
            stat = existing or SocialActivityStats()
            stat.period_type = period_type
            stat.period_start = start
            stat.period_end = end
            stat.platform = platform
            stat.account_name = domain
            stat.account_url = url
            stat.topic_id = topic_id
            stat.topic_name = topic_name
            stat.category = category
            stat.post_count = count
            stat.total_mentions = count
            stat.positive_count = pos
            stat.negative_count = neg
            stat.neutral_count = neu
            stat.avg_sentiment_score = self._calculate_sentiment_score(pos, neg, neu)
            stat.emotion_distribution = emotion_dist
            stat.dominant_emotion = dominant
            
            if not existing:
                self.db.add(stat)
            results.append(stat)
        
        # Set platform ranks
        for stat in results:
            if stat.platform in platform_ranks:
                sorted_accounts = sorted(platform_ranks[stat.platform].items(), key=lambda x: x[1], reverse=True)
                account_ranks = {a: r for r, (a, _) in enumerate(sorted_accounts, 1)}
                stat.rank_in_platform = account_ranks.get(stat.account_name, 999)
        
        return results
    
    # ========== DAILY SNAPSHOT ==========
    
    def create_daily_snapshot(self, snapshot_date: date = None) -> DailySnapshot:
        """Tạo snapshot cho một ngày"""
        target_date = snapshot_date or date.today()
        
        from sqlalchemy import Integer
        # Query data for the day
        day_data = self.db.query(SentimentAnalysis).filter(
            func.date(SentimentAnalysis.published_date) == target_date
        ).all()
        
        if not day_data:
            return None
        
        total = len(day_data)
        pos = sum(1 for d in day_data if d.sentiment_group == 'positive')
        neg = sum(1 for d in day_data if d.sentiment_group == 'negative')
        
        # Emotion counts
        emotion_counts = Counter(d.emotion for d in day_data)
        
        # Unique sources
        sources = len(set(d.source_domain for d in day_data if d.source_domain))
        
        # Top topics
        topic_counts = Counter((d.topic_id, d.topic_name) for d in day_data if d.topic_id)
        top_topics = [
            {"topic_id": tid, "name": tname, "count": cnt}
            for (tid, tname), cnt in topic_counts.most_common(10)
        ]
        
        # Top keywords
        all_text = " ".join(f"{d.title or ''} {d.content_snippet or ''}" for d in day_data)
        top_keywords = self._extract_keywords(all_text, 20)
        
        # Top sources
        source_counts = Counter(d.source_domain for d in day_data if d.source_domain)
        top_sources = [{"domain": d, "count": c} for d, c in source_counts.most_common(10)]
        
        # Check existing
        existing = self.db.query(DailySnapshot).filter(
            DailySnapshot.snapshot_date == target_date
        ).first()
        
        snapshot = existing or DailySnapshot()
        snapshot.snapshot_date = target_date
        snapshot.total_articles = total
        snapshot.total_sources = sources
        snapshot.positive_count = pos
        snapshot.negative_count = neg
        snapshot.neutral_count = total - pos - neg
        snapshot.emotion_counts = dict(emotion_counts)
        snapshot.top_topics = top_topics
        snapshot.top_keywords = top_keywords
        snapshot.top_sources = top_sources
        
        if not existing:
            self.db.add(snapshot)
        
        return snapshot
    
    # ========== BATCH UPDATE ALL ==========
    
    def update_all_statistics(self, reference_date: date = None):
        """Cập nhật tất cả thống kê"""
        ref = reference_date or date.today()
        logger.info(f"Updating all statistics for reference date: {ref}")
        
        try:
            # Daily snapshot
            self.create_daily_snapshot(ref)
            
            # Weekly reports
            self.calculate_trend_report("weekly", ref)
            self.calculate_hot_topics("weekly", ref)
            self.calculate_keyword_stats("weekly", ref)
            self.calculate_topic_mention_stats("weekly", ref)
            self.calculate_website_stats("weekly", ref)
            self.calculate_social_stats("weekly", ref)
            
            # Monthly reports (chỉ chạy đầu tháng hoặc cuối tháng)
            if ref.day <= 7 or ref.day >= 25:
                self.calculate_trend_report("monthly", ref)
                self.calculate_hot_topics("monthly", ref)
                self.calculate_keyword_stats("monthly", ref)
                self.calculate_topic_mention_stats("monthly", ref)
            
            self.db.commit()
            logger.info("All statistics updated successfully")
            
            return {"status": "success", "reference_date": str(ref)}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating statistics: {e}", exc_info=True)
            raise


def get_statistics_service(db: Session) -> StatisticsService:
    """Factory function để lấy StatisticsService"""
    return StatisticsService(db)
