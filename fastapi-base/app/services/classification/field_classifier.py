"""
Service để phân loại bài viết vào các lĩnh vực dựa trên từ khóa và nội dung
"""
import re
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.model_article import Article
from app.models.model_field_classification import (
    Field,
    ArticleFieldClassification,
    FieldStatistics
)
from app.services.classification.llm_classifier import LLMFieldClassifier

logger = logging.getLogger(__name__)

# Platform detection mapping
SOCIAL_PLATFORMS = {
    'facebook.com': 'Facebook',
    'fb.com': 'Facebook',
    'tiktok.com': 'TikTok',
    'threads.net': 'Threads',
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'twitter.com': 'Twitter',
    'x.com': 'Twitter',
    'instagram.com': 'Instagram',
    'zalo.me': 'Zalo',
}


class FieldClassificationService:
    """Service để phân loại bài viết theo lĩnh vực"""
    
    def __init__(self, db: Session, use_llm: bool = True):
        self.db = db
        self.use_llm = use_llm
        self.llm_classifier = LLMFieldClassifier() if use_llm else None
    
    def _normalize_text(self, text: str) -> str:
        """Chuẩn hóa text để so sánh từ khóa"""
        if not text:
            return ""
        # Chuyển về lowercase, loại bỏ dấu câu
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _detect_platform(self, source: str, url: str = None) -> str:
        """
        Phát hiện platform từ source/domain hoặc URL
        Returns: Platform name hoặc 'Newspaper' nếu không phải social media
        """
        # Thử detect từ source trước
        if source and source != 'external':
            source_lower = source.lower()
            for pattern, platform in SOCIAL_PLATFORMS.items():
                if pattern in source_lower:
                    return platform
        
        # Nếu source là "external" hoặc không có info, check URL
        if url:
            url_lower = url.lower()
            for pattern, platform in SOCIAL_PLATFORMS.items():
                if pattern in url_lower:
                    return platform
        
        # Nếu không match với social platform nào, coi như là báo chí
        return 'Newspaper'
    
    def _match_keywords(self, text: str, keywords: List[str]) -> Tuple[bool, List[str]]:
        """
        Kiểm tra xem text có chứa từ khóa nào không
        Returns: (có_match, danh_sách_keywords_matched)
        """
        if not text or not keywords:
            return False, []
        
        normalized_text = self._normalize_text(text)
        matched = []
        
        for keyword in keywords:
            normalized_keyword = self._normalize_text(keyword)
            # Tìm keyword dạng whole word
            pattern = r'\b' + re.escape(normalized_keyword) + r'\b'
            if re.search(pattern, normalized_text):
                matched.append(keyword)
        
        return len(matched) > 0, matched
    
    def classify_article(
        self, 
        article_id: int, 
        force: bool = False,
        method: str = "auto"  # auto, keyword, llm
    ) -> Optional[ArticleFieldClassification]:
        """
        Phân loại một bài viết vào lĩnh vực
        
        Args:
            article_id: ID của bài viết
            force: Có phân loại lại nếu đã được phân loại chưa
            method: Phương pháp phân loại (auto, keyword, llm)
                - auto: Dùng keyword trước, nếu không match thì dùng LLM
                - keyword: Chỉ dùng keyword matching
                - llm: Chỉ dùng LLM
            
        Returns:
            ArticleFieldClassification nếu phân loại thành công, None nếu không
        """
        # Kiểm tra xem đã phân loại chưa
        existing = self.db.query(ArticleFieldClassification).filter(
            ArticleFieldClassification.article_id == article_id
        ).first()
        
        if existing and not force:
            return existing
        
        # Lấy bài viết
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return None
        
        # Lấy tất cả các lĩnh vực
        fields = self.db.query(Field).order_by(Field.order_index).all()
        if not fields:
            return None
        
        result_field_id = None
        result_confidence = 0
        result_keywords = []
        result_method = "keyword"
        
        # Thử keyword matching trước (nếu method cho phép)
        if method in ["auto", "keyword"]:
            # Ghép title + content để tìm keyword
            text_to_search = f"{article.title or ''} {article.content or ''} {article.summary or ''}"
            
            best_match = None
            best_score = 0
            best_keywords = []
            
            # Tìm lĩnh vực match nhất
            for field in fields:
                if not field.keywords:
                    continue
                
                matched, matched_keywords = self._match_keywords(text_to_search, field.keywords)
                if matched:
                    score = len(matched_keywords)
                    if score > best_score:
                        best_score = score
                        best_match = field
                        best_keywords = matched_keywords
            
            # Nếu match được bằng keyword
            if best_match:
                result_field_id = best_match.id
                result_confidence = min(1.0, best_score / 5.0)  # Normalize score
                result_keywords = best_keywords
                result_method = "keyword"
        
        # Nếu không match được và method cho phép LLM
        if not result_field_id and method in ["auto", "llm"]:
            if self.use_llm and self.llm_classifier and self.llm_classifier.is_available():
                logger.info(f"Using LLM to classify article {article_id}")
                
                # Chuẩn bị dữ liệu lĩnh vực cho LLM
                fields_data = [
                    {
                        "id": f.id,
                        "name": f.name,
                        "description": f.description or ""
                    }
                    for f in fields
                ]
                
                # Gọi LLM
                llm_result = self.llm_classifier.classify_article(
                    title=article.title or "",
                    content=article.content or "",
                    fields=fields_data
                )
                
                if llm_result:
                    field_id, confidence, reason = llm_result
                    result_field_id = field_id
                    result_confidence = confidence
                    result_keywords = [reason]  # Lưu lý do vào matched_keywords
                    result_method = "llm"
        
        # Nếu vẫn không phân loại được
        if not result_field_id:
            return None
        
        # Tạo hoặc update phân loại
        if existing:
            existing.field_id = result_field_id
            existing.confidence_score = result_confidence
            existing.matched_keywords = result_keywords
            existing.classification_method = result_method
            existing.updated_at = time.time()
            self.db.commit()
            logger.info(f" Updated classification for article {article_id}: field={result_field_id}, method={result_method}")
            return existing
        else:
            classification = ArticleFieldClassification(
                article_id=article_id,
                field_id=result_field_id,
                confidence_score=result_confidence,
                matched_keywords=result_keywords,
                classification_method=result_method,
                created_at=time.time(),
                updated_at=time.time()
            )
            self.db.add(classification)
            self.db.commit()
            self.db.refresh(classification)
            return classification
    
    def classify_articles_batch(
        self, 
        article_ids: Optional[List[int]] = None,
        force: bool = False,
        limit: Optional[int] = None,
        method: str = "auto"  # auto, keyword, llm
    ) -> Dict[str, any]:
        """
        Phân loại nhiều bài viết cùng lúc
        
        Args:
            article_ids: Danh sách ID bài viết cần phân loại. Nếu None, phân loại tất cả
            force: Có phân loại lại không
            limit: Giới hạn số lượng bài viết xử lý
            method: Phương pháp phân loại (auto, keyword, llm)
            
        Returns:
            Dict chứa thống kê kết quả
        """
        start_time = time.time()
        
        # Lấy danh sách bài viết cần phân loại
        query = self.db.query(Article.id)
        
        if article_ids:
            query = query.filter(Article.id.in_(article_ids))
        
        if not force:
            # Chỉ lấy những bài chưa được phân loại
            classified_ids = self.db.query(ArticleFieldClassification.article_id).distinct()
            query = query.filter(~Article.id.in_(classified_ids))
        
        if limit:
            query = query.limit(limit)
        
        article_ids_to_process = [row[0] for row in query.all()]
        
        # Phân loại từng bài
        classified_count = 0
        failed_count = 0
        field_counts = {}
        method_stats = {"keyword": 0, "llm": 0}
        
        for article_id in article_ids_to_process:
            try:
                result = self.classify_article(article_id, force=force, method=method)
                if result:
                    classified_count += 1
                    field_name = self.db.query(Field.name).filter(
                        Field.id == result.field_id
                    ).scalar()
                    field_counts[field_name] = field_counts.get(field_name, 0) + 1
                    
                    # Track method used
                    if result.classification_method in method_stats:
                        method_stats[result.classification_method] += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                print(f"Error classifying article {article_id}: {e}")
        
        processing_time = time.time() - start_time
        
        return {
            "total_processed": len(article_ids_to_process),
            "classified": classified_count,
            "failed": failed_count,
            "field_distribution": field_counts,
            "method_stats": method_stats,
            "processing_time": processing_time
        }
    
    def get_field_distribution(self) -> List[Dict[str, any]]:
        """
        Lấy phân bố bài viết theo lĩnh vực
        
        Returns:
            Danh sách các lĩnh vực với số lượng bài viết
        """
        # Query để đếm số bài viết theo lĩnh vực
        results = self.db.query(
            Field.id,
            Field.name,
            func.count(ArticleFieldClassification.id).label('count')
        ).outerjoin(
            ArticleFieldClassification,
            Field.id == ArticleFieldClassification.field_id
        ).group_by(
            Field.id,
            Field.name
        ).order_by(
            Field.order_index
        ).all()
        
        total = sum(r.count for r in results)
        
        return [
            {
                "field_id": r.id,
                "field_name": r.name,
                "article_count": r.count,
                "percentage": round(r.count * 100 / total, 2) if total > 0 else 0
            }
            for r in results
        ]
    
    def update_field_statistics(self, field_id: Optional[int] = None):
        """
        Cập nhật thống kê cho một hoặc tất cả lĩnh vực
        
        Args:
            field_id: ID lĩnh vực cần update. Nếu None, update tất cả
        """
        fields_to_update = []
        
        if field_id:
            field = self.db.query(Field).filter(Field.id == field_id).first()
            if field:
                fields_to_update.append(field)
        else:
            fields_to_update = self.db.query(Field).all()
        
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day).timestamp()
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp()
        month_start = datetime(now.year, now.month, 1).timestamp()
        
        for field in fields_to_update:
            # Lấy tất cả bài viết của lĩnh vực này
            article_ids = self.db.query(ArticleFieldClassification.article_id).filter(
                ArticleFieldClassification.field_id == field.id
            ).all()
            article_ids = [aid[0] for aid in article_ids]
            
            if not article_ids:
                continue
            
            # Đếm tổng số bài
            total_articles = len(article_ids)
            
            # Đếm theo thời gian
            articles_today = self.db.query(Article).filter(
                and_(
                    Article.id.in_(article_ids),
                    Article.created_at >= today_start
                )
            ).count()
            
            articles_this_week = self.db.query(Article).filter(
                and_(
                    Article.id.in_(article_ids),
                    Article.created_at >= week_start
                )
            ).count()
            
            articles_this_month = self.db.query(Article).filter(
                and_(
                    Article.id.in_(article_ids),
                    Article.created_at >= month_start
                )
            ).count()
            
            # Tính engagement trung bình
            engagement_stats = self.db.query(
                func.avg(Article.likes_count).label('avg_likes'),
                func.avg(Article.shares_count).label('avg_shares'),
                func.avg(Article.comments_count).label('avg_comments'),
                func.sum(
                    func.coalesce(Article.likes_count, 0) +
                    func.coalesce(Article.shares_count, 0) +
                    func.coalesce(Article.comments_count, 0)
                ).label('total_engagement')
            ).filter(
                Article.id.in_(article_ids)
            ).first()
            
            # Phân bố theo nguồn
            source_dist = {}
            source_results = self.db.query(
                Article.source,
                func.count(Article.id)
            ).filter(
                Article.id.in_(article_ids)
            ).group_by(Article.source).all()
            for source, count in source_results:
                if source:
                    source_dist[source] = count
            
            # Phân bố theo platform (Facebook, TikTok, Threads, etc.)
            # Cần query từng article để lấy URL khi source = "external"
            platform_dist = {}
            articles_for_platform = self.db.query(
                Article.source, Article.url
            ).filter(
                Article.id.in_(article_ids)
            ).all()
            
            for article in articles_for_platform:
                platform = self._detect_platform(article.source, article.url)
                platform_dist[platform] = platform_dist.get(platform, 0) + 1
            
            # Phân bố theo tỉnh
            province_dist = {}
            province_results = self.db.query(
                Article.province,
                func.count(Article.id)
            ).filter(
                and_(
                    Article.id.in_(article_ids),
                    Article.province.isnot(None)
                )
            ).group_by(Article.province).all()
            for province, count in province_results:
                if province:
                    province_dist[province] = count
            
            # Tạo hoặc update statistics
            stats = self.db.query(FieldStatistics).filter(
                FieldStatistics.field_id == field.id
            ).first()
            
            if stats:
                stats.field_name = field.name
                stats.total_articles = total_articles
                stats.articles_today = articles_today
                stats.articles_this_week = articles_this_week
                stats.articles_this_month = articles_this_month
                stats.avg_likes = float(engagement_stats.avg_likes or 0)
                stats.avg_shares = float(engagement_stats.avg_shares or 0)
                stats.avg_comments = float(engagement_stats.avg_comments or 0)
                stats.total_engagement = int(engagement_stats.total_engagement or 0)
                stats.source_distribution = source_dist
                stats.platform_distribution = platform_dist
                stats.province_distribution = province_dist
                stats.stats_date = time.time()
                stats.updated_at = time.time()
            else:
                stats = FieldStatistics(
                    field_id=field.id,
                    field_name=field.name,
                    total_articles=total_articles,
                    articles_today=articles_today,
                    articles_this_week=articles_this_week,
                    articles_this_month=articles_this_month,
                    avg_likes=float(engagement_stats.avg_likes or 0),
                    avg_shares=float(engagement_stats.avg_shares or 0),
                    avg_comments=float(engagement_stats.avg_comments or 0),
                    total_engagement=int(engagement_stats.total_engagement or 0),
                    source_distribution=source_dist,
                    platform_distribution=platform_dist,
                    province_distribution=province_dist,
                    stats_date=time.time(),
                    created_at=time.time(),
                    updated_at=time.time()
                )
                self.db.add(stats)
            
            self.db.commit()
    
    def get_all_statistics(self) -> List[FieldStatistics]:
        """Lấy tất cả thống kê lĩnh vực"""
        return self.db.query(FieldStatistics).join(Field).order_by(Field.order_index).all()
