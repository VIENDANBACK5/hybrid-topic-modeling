"""
Trend Analysis Service - Phân tích xu hướng đột biến, khủng hoảng, viral content
"""
import logging
import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from collections import Counter
from sqlalchemy import func, and_, or_, desc, Integer
from sqlalchemy.orm import Session

from app.models.model_article import Article
from app.models.model_sentiment import SentimentAnalysis
from app.models.model_trends import TrendAlert, HashtagStats, ViralContent, CategoryTrendStats
from app.services.classification import get_category_classifier, CATEGORIES

logger = logging.getLogger(__name__)


class TrendAnalysisService:
    """Service phân tích xu hướng đột biến, khủng hoảng"""
    
    def __init__(self, db: Session):
        self.db = db
        self.classifier = get_category_classifier()
    
    # ========== HASHTAG EXTRACTION ==========
    
    def extract_hashtags(self, text: str) -> List[str]:
        """Trích xuất hashtags từ text"""
        if not text:
            return []
        # Match #hashtag (tiếng Việt và tiếng Anh)
        pattern = r'#([a-zA-Z0-9_àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]+)'
        hashtags = re.findall(pattern, text.lower())
        return list(set(hashtags))
    
    # ========== TREND ALERTS ==========
    
    def detect_trend_alerts(self, hours_back: int = 24) -> List[TrendAlert]:
        """Phát hiện xu hướng đột biến trong N giờ qua"""
        now = datetime.now()
        period_start = now - timedelta(hours=hours_back)
        prev_start = period_start - timedelta(hours=hours_back)
        
        alerts = []
        
        # 1. Phát hiện SPIKE (đột biến tăng) theo topic
        current_topics = self._get_topic_counts(period_start, now)
        prev_topics = self._get_topic_counts(prev_start, period_start)
        
        for topic_id, topic_name, current_count in current_topics:
            prev_count = next((c for tid, _, c in prev_topics if tid == topic_id), 0)
            
            if prev_count > 0:
                change_pct = ((current_count - prev_count) / prev_count) * 100
            else:
                change_pct = 100 if current_count > 5 else 0
            
            # Spike: tăng > 50% và có ít nhất 10 mentions
            if change_pct > 50 and current_count >= 10:
                alert = self._create_alert(
                    alert_type="spike",
                    alert_level=self._determine_alert_level(change_pct, current_count),
                    topic_id=topic_id,
                    topic_name=topic_name,
                    current_count=current_count,
                    previous_count=prev_count,
                    change_percent=change_pct,
                    period_start=period_start,
                    period_end=now
                )
                alerts.append(alert)
        
        # 2. Phát hiện CRISIS (khủng hoảng - nhiều tiêu cực)
        crisis_topics = self._detect_crisis_topics(period_start, now)
        for topic_id, topic_name, neg_ratio, count, emotions in crisis_topics:
            alert = self._create_alert(
                alert_type="crisis",
                alert_level="high" if neg_ratio > 0.6 else "medium",
                topic_id=topic_id,
                topic_name=topic_name,
                current_count=count,
                negative_ratio=neg_ratio,
                emotion_distribution=emotions,
                period_start=period_start,
                period_end=now
            )
            alerts.append(alert)
        
        # 3. Phát hiện DROP (đột biến giảm)
        for topic_id, topic_name, prev_count in prev_topics:
            current_count = next((c for tid, _, c in current_topics if tid == topic_id), 0)
            
            if prev_count >= 10:
                change_pct = ((current_count - prev_count) / prev_count) * 100
                
                # Drop: giảm > 50%
                if change_pct < -50:
                    alert = self._create_alert(
                        alert_type="drop",
                        alert_level="low",
                        topic_id=topic_id,
                        topic_name=topic_name,
                        current_count=current_count,
                        previous_count=prev_count,
                        change_percent=change_pct,
                        period_start=period_start,
                        period_end=now
                    )
                    alerts.append(alert)
        
        # Save alerts
        for alert in alerts:
            self.db.add(alert)
        
        return alerts
    
    def _get_topic_counts(self, start: datetime, end: datetime) -> List[Tuple]:
        """Đếm mentions theo topic trong khoảng thời gian"""
        return self.db.query(
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            func.count(SentimentAnalysis.id)
        ).filter(
            and_(
                SentimentAnalysis.analyzed_at >= start,
                SentimentAnalysis.analyzed_at <= end,
                SentimentAnalysis.topic_id.isnot(None)
            )
        ).group_by(
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name
        ).all()
    
    def _detect_crisis_topics(self, start: datetime, end: datetime) -> List[Tuple]:
        """Phát hiện topics có dấu hiệu khủng hoảng (nhiều tiêu cực)"""
        results = []
        
        topic_sentiments = self.db.query(
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            func.count(SentimentAnalysis.id).label('total'),
            func.sum(func.cast(SentimentAnalysis.sentiment_group == 'negative', Integer)).label('neg'),
        ).filter(
            and_(
                SentimentAnalysis.analyzed_at >= start,
                SentimentAnalysis.analyzed_at <= end,
                SentimentAnalysis.topic_id.isnot(None)
            )
        ).group_by(
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name
        ).having(func.count(SentimentAnalysis.id) >= 5).all()
        
        for topic_id, topic_name, total, neg in topic_sentiments:
            neg = neg or 0
            neg_ratio = neg / total if total > 0 else 0
            
            # Crisis: > 40% tiêu cực
            if neg_ratio > 0.4:
                # Get emotion distribution
                emotions = dict(self.db.query(
                    SentimentAnalysis.emotion,
                    func.count(SentimentAnalysis.id)
                ).filter(
                    and_(
                        SentimentAnalysis.topic_id == topic_id,
                        SentimentAnalysis.analyzed_at >= start,
                        SentimentAnalysis.analyzed_at <= end
                    )
                ).group_by(SentimentAnalysis.emotion).all())
                
                results.append((topic_id, topic_name, neg_ratio, total, emotions))
        
        return results
    
    def _create_alert(self, **kwargs) -> TrendAlert:
        """Tạo alert object"""
        alert = TrendAlert(
            alert_type=kwargs.get('alert_type'),
            alert_level=kwargs.get('alert_level', 'medium'),
            alert_status='active',
            topic_id=kwargs.get('topic_id'),
            topic_name=kwargs.get('topic_name'),
            current_count=kwargs.get('current_count', 0),
            previous_count=kwargs.get('previous_count', 0),
            change_percent=kwargs.get('change_percent'),
            negative_ratio=kwargs.get('negative_ratio'),
            emotion_distribution=kwargs.get('emotion_distribution'),
            period_start=kwargs.get('period_start'),
            period_end=kwargs.get('period_end'),
        )
        
        # Generate title
        if alert.alert_type == 'spike':
            alert.title = f" Đột biến: {alert.topic_name} tăng {alert.change_percent:.0f}%"
        elif alert.alert_type == 'crisis':
            alert.title = f" Khủng hoảng: {alert.topic_name} ({alert.negative_ratio*100:.0f}% tiêu cực)"
        elif alert.alert_type == 'drop':
            alert.title = f" Sụt giảm: {alert.topic_name} giảm {abs(alert.change_percent):.0f}%"
        elif alert.alert_type == 'viral':
            alert.title = f" Viral: {alert.topic_name}"
        
        return alert
    
    def _determine_alert_level(self, change_pct: float, count: int) -> str:
        """Xác định mức độ cảnh báo"""
        if change_pct > 200 and count > 50:
            return "critical"
        elif change_pct > 100 and count > 30:
            return "high"
        elif change_pct > 50 and count > 10:
            return "medium"
        return "low"
    
    # ========== HASHTAG STATS ==========
    
    def calculate_hashtag_stats(self, period_type: str = "daily") -> List[HashtagStats]:
        """Tính thống kê hashtag"""
        from app.services.statistics.statistics_service import StatisticsService
        
        # Get period range
        today = date.today()
        if period_type == "daily":
            start = today
            end = today
        elif period_type == "weekly":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        else:  # monthly
            start = today.replace(day=1)
            next_month = start.replace(day=28) + timedelta(days=4)
            end = next_month - timedelta(days=next_month.day)
        
        # Previous period for comparison
        period_days = (end - start).days + 1
        prev_start = start - timedelta(days=period_days)
        prev_end = start - timedelta(days=1)
        
        # Extract hashtags from all content
        articles = self.db.query(
            SentimentAnalysis.content_snippet,
            SentimentAnalysis.title,
            SentimentAnalysis.sentiment_group,
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name,
            SentimentAnalysis.source_domain
        ).filter(
            func.date(SentimentAnalysis.published_date).between(start, end)
        ).all()
        
        # Count hashtags
        hashtag_data = {}
        
        for content, title, sentiment, topic_id, topic_name, domain in articles:
            text = f"{title or ''} {content or ''}"
            hashtags = self.extract_hashtags(text)
            
            for tag in hashtags:
                if tag not in hashtag_data:
                    hashtag_data[tag] = {
                        'count': 0, 'sources': set(),
                        'pos': 0, 'neg': 0, 'neu': 0,
                        'topics': Counter(), 'categories': Counter()
                    }
                
                hashtag_data[tag]['count'] += 1
                if domain:
                    hashtag_data[tag]['sources'].add(domain)
                
                if sentiment == 'positive':
                    hashtag_data[tag]['pos'] += 1
                elif sentiment == 'negative':
                    hashtag_data[tag]['neg'] += 1
                else:
                    hashtag_data[tag]['neu'] += 1
                
                if topic_id:
                    hashtag_data[tag]['topics'][(topic_id, topic_name)] += 1
        
        # Sort by count
        sorted_tags = sorted(hashtag_data.items(), key=lambda x: x[1]['count'], reverse=True)[:100]
        
        results = []
        for rank, (tag, data) in enumerate(sorted_tags, 1):
            total = data['count']
            
            # Check previous period
            prev_count = self.db.query(func.count(SentimentAnalysis.id)).filter(
                and_(
                    func.date(SentimentAnalysis.published_date).between(prev_start, prev_end),
                    or_(
                        SentimentAnalysis.title.ilike(f'%#{tag}%'),
                        SentimentAnalysis.content_snippet.ilike(f'%#{tag}%')
                    )
                )
            ).scalar() or 0
            
            change_pct = ((total - prev_count) / prev_count * 100) if prev_count > 0 else 100
            
            # Check existing
            existing = self.db.query(HashtagStats).filter(
                and_(
                    HashtagStats.period_type == period_type,
                    HashtagStats.period_start == start,
                    HashtagStats.hashtag == tag
                )
            ).first()
            
            stat = existing or HashtagStats()
            stat.period_type = period_type
            stat.period_start = start
            stat.period_end = end
            stat.hashtag = f"#{tag}"
            stat.hashtag_normalized = tag.lower()
            stat.mention_count = total
            stat.unique_sources = len(data['sources'])
            stat.previous_count = prev_count
            stat.change_percent = round(change_pct, 2)
            stat.is_trending = change_pct > 30 and total >= 5
            stat.is_new = prev_count == 0 and total >= 3
            stat.positive_count = data['pos']
            stat.negative_count = data['neg']
            stat.neutral_count = data['neu']
            stat.sentiment_score = round((data['pos'] - data['neg']) / total, 4) if total > 0 else 0
            stat.related_topics = [
                {"topic_id": tid, "topic_name": tname, "count": cnt}
                for (tid, tname), cnt in data['topics'].most_common(5)
            ]
            stat.rank = rank
            
            if not existing:
                self.db.add(stat)
            results.append(stat)
        
        return results
    
    # ========== VIRAL CONTENT ==========
    
    def detect_viral_content(self, period_type: str = "daily", top_n: int = 20) -> List[ViralContent]:
        """Phát hiện nội dung viral/hot"""
        today = date.today()
        if period_type == "daily":
            start = today
            end = today
        elif period_type == "weekly":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        else:
            start = today.replace(day=1)
            end = today
        
        # Get articles with high engagement indicators
        articles = self.db.query(
            Article.id,
            Article.title,
            Article.url,
            Article.domain,
            Article.content,
            Article.topic_id,
            Article.topic_name,
            SentimentAnalysis.sentiment_group,
            SentimentAnalysis.emotion,
            SentimentAnalysis.emotion_vi
        ).join(
            SentimentAnalysis, Article.id == SentimentAnalysis.article_id
        ).filter(
            func.date(Article.created_at).between(start, end)
        ).all()
        
        # Calculate viral score
        viral_items = []
        
        for art in articles:
            # Viral score based on:
            # - Title length & quality
            # - Content sentiment
            # - Domain reputation
            
            title_score = min(len(art.title or '') / 50, 2) if art.title else 0
            
            # Negative/controversial content often goes viral
            sentiment_multiplier = 1.5 if art.sentiment_group == 'negative' else 1.0
            
            viral_score = (1 + title_score) * sentiment_multiplier
            
            # Classify category
            classification = self.classifier.classify(art.content or '', art.title)
            
            viral_items.append({
                'article_id': art.id,
                'title': art.title,
                'url': art.url,
                'domain': art.domain,
                'content': (art.content or '')[:300],
                'topic_id': art.topic_id,
                'topic_name': art.topic_name,
                'sentiment_group': art.sentiment_group,
                'emotion': art.emotion,
                'emotion_vi': art.emotion_vi,
                'category': classification.category,
                'category_vi': classification.category_vi,
                'viral_score': viral_score
            })
        
        # Sort and take top N
        viral_items.sort(key=lambda x: x['viral_score'], reverse=True)
        top_items = viral_items[:top_n]
        
        results = []
        for rank, item in enumerate(top_items, 1):
            existing = self.db.query(ViralContent).filter(
                and_(
                    ViralContent.period_type == period_type,
                    ViralContent.period_start == start,
                    ViralContent.article_id == item['article_id']
                )
            ).first()
            
            viral = existing or ViralContent()
            viral.period_type = period_type
            viral.period_start = start
            viral.article_id = item['article_id']
            viral.title = item['title']
            viral.url = item['url']
            viral.source_domain = item['domain']
            viral.content_snippet = item['content']
            viral.category = item['category']
            viral.category_vi = item['category_vi']
            viral.topic_id = item['topic_id']
            viral.topic_name = item['topic_name']
            viral.sentiment_group = item['sentiment_group']
            viral.emotion = item['emotion']
            viral.emotion_vi = item['emotion_vi']
            viral.viral_score = item['viral_score']
            viral.rank = rank
            viral.is_hot = rank <= 10
            
            if not existing:
                self.db.add(viral)
            results.append(viral)
        
        return results
    
    # ========== CATEGORY TREND STATS ==========
    
    def calculate_category_trends(self, period_type: str = "weekly") -> List[CategoryTrendStats]:
        """Tính thống kê xu hướng theo danh mục"""
        today = date.today()
        if period_type == "daily":
            start = today
            end = today
        elif period_type == "weekly":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        else:
            start = today.replace(day=1)
            next_month = start.replace(day=28) + timedelta(days=4)
            end = next_month - timedelta(days=next_month.day)
        
        # Previous period
        period_days = (end - start).days + 1
        prev_start = start - timedelta(days=period_days)
        
        # Get all articles and classify
        articles = self.db.query(
            Article.id,
            Article.title,
            Article.content,
            Article.domain,
            SentimentAnalysis.sentiment_group,
            SentimentAnalysis.emotion,
            SentimentAnalysis.topic_id,
            SentimentAnalysis.topic_name
        ).join(
            SentimentAnalysis, Article.id == SentimentAnalysis.article_id
        ).filter(
            func.date(SentimentAnalysis.published_date).between(start, end)
        ).all()
        
        # Group by category
        category_data = {}
        
        for art in articles:
            classification = self.classifier.classify(art.content or '', art.title)
            cat = classification.category
            
            if cat not in category_data:
                category_data[cat] = {
                    'vi': classification.category_vi,
                    'icon': classification.icon,
                    'count': 0, 'sources': set(), 'articles': set(),
                    'pos': 0, 'neg': 0, 'neu': 0,
                    'emotions': Counter(),
                    'keywords': Counter(),
                    'topics': Counter()
                }
            
            category_data[cat]['count'] += 1
            category_data[cat]['articles'].add(art.id)
            if art.domain:
                category_data[cat]['sources'].add(art.domain)
            
            if art.sentiment_group == 'positive':
                category_data[cat]['pos'] += 1
            elif art.sentiment_group == 'negative':
                category_data[cat]['neg'] += 1
            else:
                category_data[cat]['neu'] += 1
            
            if art.emotion:
                category_data[cat]['emotions'][art.emotion] += 1
            
            if art.topic_id:
                category_data[cat]['topics'][(art.topic_id, art.topic_name)] += 1
        
        results = []
        for cat, data in category_data.items():
            total = data['count']
            
            # Previous period count (simplified)
            prev_count = self.db.query(func.count(SentimentAnalysis.id)).filter(
                func.date(SentimentAnalysis.published_date).between(prev_start, start - timedelta(days=1))
            ).scalar() or 0
            # Note: This is simplified, real implementation would classify prev articles too
            prev_count = int(prev_count * (total / max(len(articles), 1)))
            
            change_pct = ((total - prev_count) / prev_count * 100) if prev_count > 0 else 0
            
            existing = self.db.query(CategoryTrendStats).filter(
                and_(
                    CategoryTrendStats.period_type == period_type,
                    CategoryTrendStats.period_start == start,
                    CategoryTrendStats.category == cat
                )
            ).first()
            
            stat = existing or CategoryTrendStats()
            stat.period_type = period_type
            stat.period_start = start
            stat.period_end = end
            stat.category = cat
            stat.category_vi = data['vi']
            stat.category_icon = data['icon']
            stat.total_mentions = total
            stat.unique_sources = len(data['sources'])
            stat.unique_articles = len(data['articles'])
            stat.positive_count = data['pos']
            stat.negative_count = data['neg']
            stat.neutral_count = data['neu']
            stat.sentiment_score = round((data['pos'] - data['neg']) / total, 4) if total > 0 else 0
            stat.emotion_distribution = dict(data['emotions'])
            stat.dominant_emotion = data['emotions'].most_common(1)[0][0] if data['emotions'] else None
            stat.previous_mentions = prev_count
            stat.change_percent = round(change_pct, 2)
            stat.is_trending_up = change_pct > 20
            stat.is_trending_down = change_pct < -20
            stat.top_topics = [
                {"topic_id": tid, "topic_name": tname, "count": cnt}
                for (tid, tname), cnt in data['topics'].most_common(5)
            ]
            stat.has_crisis = data['neg'] / total > 0.4 if total > 0 else False
            
            if not existing:
                self.db.add(stat)
            results.append(stat)
        
        # Set rankings
        results.sort(key=lambda x: x.total_mentions, reverse=True)
        for rank, stat in enumerate(results, 1):
            stat.rank_by_mention = rank
        
        results.sort(key=lambda x: x.change_percent or 0, reverse=True)
        for rank, stat in enumerate(results, 1):
            stat.rank_by_growth = rank
        
        return results
    
    # ========== UPDATE ALL ==========
    
    def update_all_trends(self, period_type: str = "daily"):
        """Cập nhật tất cả phân tích xu hướng"""
        logger.info(f"Updating all trend analysis for {period_type}")
        
        try:
            # Trend alerts (last 24 hours)
            alerts = self.detect_trend_alerts(hours_back=24)
            logger.info(f"Detected {len(alerts)} trend alerts")
            
            # Hashtag stats
            hashtags = self.calculate_hashtag_stats(period_type)
            logger.info(f"Calculated {len(hashtags)} hashtag stats")
            
            # Viral content
            viral = self.detect_viral_content(period_type)
            logger.info(f"Detected {len(viral)} viral contents")
            
            # Category trends
            categories = self.calculate_category_trends(period_type)
            logger.info(f"Calculated {len(categories)} category trends")
            
            return {
                "alerts": len(alerts),
                "hashtags": len(hashtags),
                "viral_content": len(viral),
                "category_trends": len(categories)
            }
            
        except Exception as e:
            logger.error(f"Error updating trends: {e}", exc_info=True)
            raise


def get_trend_service(db: Session) -> TrendAnalysisService:
    """Factory function"""
    return TrendAnalysisService(db)
