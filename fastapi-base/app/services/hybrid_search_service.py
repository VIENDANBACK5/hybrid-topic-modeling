"""
Hybrid Search Service - BM25 + Vector Search + RAG
Kết hợp full-text search và semantic search để tìm articles relevant
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_, func, desc
from datetime import datetime, timedelta

from app.models.model_article import Article

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    Service tìm kiếm hybrid: BM25 (PostgreSQL full-text) + Semantic context
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def search_articles_for_grdp(
        self,
        province: str,
        year: int,
        quarter: Optional[int] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm articles về GRDP của tỉnh bằng hybrid approach
        
        Args:
            province: Tên tỉnh (VD: "Hưng Yên")
            year: Năm cần tìm
            quarter: Quý (nếu có)
            top_k: Số lượng bài viết top
        
        Returns:
            List các article dict có score
        """
        
        # 1. BUILD SEARCH QUERY - BM25 style
        search_terms = self._build_search_terms(province, year, quarter)
        
        # 2. FULL-TEXT SEARCH với PostgreSQL
        results = self._bm25_search(search_terms, year, quarter, top_k * 3)  # Lấy nhiều hơn để filter
        
        # 3. SEMANTIC FILTERING - Lọc theo context
        filtered_results = self._semantic_filter(results, province, year, quarter)
        
        # 4. RANKING - Xếp hạng theo relevance
        ranked_results = self._rank_by_relevance(filtered_results, province, year, quarter)
        
        return ranked_results[:top_k]
    
    def _build_search_terms(
        self, 
        province: str, 
        year: int, 
        quarter: Optional[int]
    ) -> List[str]:
        """
        Tạo các search terms cho BM25
        """
        terms = [
            province,
            f"năm {year}",
            "GRDP",
            "tổng sản phẩm",
            "tăng trưởng",
            "kinh tế",
            "GDP",
            "quy mô",
            "phát triển",
            "bình quân",
            "công nghiệp",
            "nông nghiệp",
            "dịch vụ",
            "xuất khẩu",
            "thu hút đầu tư",
        ]
        
        if quarter:
            terms.extend([
                f"quý {quarter}",
                f"Q{quarter}",
                f"{quarter} tháng đầu năm"
            ])
        
        return terms
    
    def _bm25_search(
        self,
        search_terms: List[str],
        year: int,
        quarter: Optional[int],
        limit: int
    ) -> List[Article]:
        """
        Full-text search sử dụng PostgreSQL ILIKE (simplified BM25)
        Trong production nên dùng tsvector + tsquery
        """
        
        try:
            # Time range: +/- 1 năm quanh năm cần tìm (nới lỏng để tìm được nhiều articles)
            start_dt = datetime(year - 1, 1, 1)
            end_dt = datetime(year + 1, 12, 31, 23, 59, 59)
            
            start_timestamp = start_dt.timestamp()
            end_timestamp = end_dt.timestamp()
            
            logger.info(f"📅 Date range: {start_dt} → {end_dt} (timestamps: {start_timestamp} → {end_timestamp})")
            
            query = self.db.query(Article)
            
            # Filter by date range - published_date là Float (UNIX timestamp)
            query = query.filter(
                and_(
                    Article.published_date >= start_timestamp,
                    Article.published_date <= end_timestamp
                )
            )
            
            # Multi-term search
            conditions = []
            for term in search_terms[:5]:  # Top 5 important terms
                conditions.append(
                    or_(
                        Article.title.ilike(f"%{term}%"),
                        Article.content.ilike(f"%{term}%")
                    )
                )
            
            if conditions:
                query = query.filter(or_(*conditions))
            
            # Order by most recent and with longer content (proxy for quality)
            query = query.order_by(
                desc(func.length(Article.content)),
                desc(Article.published_date)  # UNIX timestamp - càng lớn càng mới
            )
            
            results = query.limit(limit).all()
            
            logger.info(f"🔍 BM25 search found {len(results)} articles")
            return results
            
        except Exception as e:
            logger.error(f"BM25 search error: {str(e)}")
            self.db.rollback()
            return []
    
    def _semantic_filter(
        self,
        articles: List[Article],
        province: str,
        year: int,
        quarter: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Filter bài viết theo semantic context:
        - Có chứa tên tỉnh
        - Có chứa năm/quý
        - Có chứa chỉ số kinh tế
        """
        
        filtered = []
        
        for article in articles:
            text = f"{article.title} {article.content}".lower()
            
            # Check 1: Có chứa tên tỉnh
            if province.lower() not in text:
                continue
            
            # Check 2: Có chứa năm
            year_patterns = [
                f"năm {year}",
                f"{year}",
                f"năm {year - 1}",  # Có thể so sánh với năm trước
            ]
            has_year = any(pattern in text for pattern in year_patterns)
            if not has_year:
                continue
            
            # Check 3: Có chứa chỉ số kinh tế
            economic_keywords = [
                "grdp", "gdp", "tổng sản phẩm", "tăng trưởng", 
                "tỷ đồng", "nghìn tỷ", "triệu đồng",
                "phát triển kinh tế", "thu hút đầu tư",
                "xuất khẩu", "công nghiệp", "nông nghiệp"
            ]
            has_economic = any(kw in text for kw in economic_keywords)
            if not has_economic:
                continue
            
            # Calculate relevance score
            score = self._calculate_score(article, province, year, quarter)
            
            filtered.append({
                "article": article,
                "score": score,
                "has_numbers": self._has_numeric_data(text)
            })
        
        logger.info(f"✅ Semantic filter kept {len(filtered)}/{len(articles)} articles")
        return filtered
    
    def _calculate_score(
        self,
        article: Article,
        province: str,
        year: int,
        quarter: Optional[int]
    ) -> float:
        """
        Tính relevance score cho article
        """
        text = f"{article.title} {article.content}".lower()
        score = 0.0
        
        # Title bonus
        if province.lower() in article.title.lower():
            score += 2.0
        
        # Exact year match
        if f"năm {year}" in text:
            score += 3.0
        
        # Quarter match
        if quarter and f"quý {quarter}" in text:
            score += 2.0
        
        # Keyword density
        keywords = ["grdp", "tăng trưởng", "tỷ đồng", "phát triển"]
        for kw in keywords:
            score += text.count(kw) * 0.5
        
        # Content length (longer = more detailed)
        if len(article.content) > 2000:
            score += 1.0
        
        # Recency (newer articles might have updated data)
        if article.published_date:
            article_date = datetime.fromtimestamp(article.published_date)
            days_diff = abs((article_date - datetime(year, 6, 30)).days)
            if days_diff < 180:  # Within 6 months
                score += 1.0
        
        return score
    
    def _has_numeric_data(self, text: str) -> bool:
        """
        Kiểm tra có chứa số liệu không
        """
        numeric_patterns = [
            r'\d+[\.,]?\d*\s*tỷ',
            r'\d+[\.,]?\d*%',
            r'\d+[\.,]?\d*\s*triệu'
        ]
        import re
        return any(re.search(pattern, text) for pattern in numeric_patterns)
    
    def _rank_by_relevance(
        self,
        results: List[Dict[str, Any]],
        province: str,
        year: int,
        quarter: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Xếp hạng theo score và có số liệu
        """
        # Sort by score descending, then by has_numbers
        sorted_results = sorted(
            results,
            key=lambda x: (x["score"], x["has_numbers"]),
            reverse=True
        )
        
        logger.info(f"📊 Top article score: {sorted_results[0]['score']:.2f}" if sorted_results else "No results")
        return sorted_results
    
    def prepare_context_for_llm(
        self,
        articles: List[Dict[str, Any]],
        max_tokens: int = 6000
    ) -> str:
        """
        Chuẩn bị context từ top articles để pass vào LLM
        Giới hạn token để fit vào context window
        """
        
        context_parts = []
        current_length = 0
        max_length = max_tokens * 3  # Rough estimate: 1 token ≈ 3 chars Vietnamese
        
        for i, item in enumerate(articles[:5], 1):  # Top 5 articles
            article = item["article"]
            
            # Extract relevant snippet (first 1500 chars + last 500 chars)
            content = article.content[:1500]
            if len(article.content) > 2000:
                content += "..." + article.content[-500:]
            
            published_str = 'N/A'
            if article.published_date:
                try:
                    published_str = datetime.fromtimestamp(article.published_date).strftime('%d/%m/%Y')
                except:
                    pass
            
            snippet = f"""
[Nguồn {i}] {article.title}
URL: {article.url}
Ngày: {published_str}
Relevance Score: {item['score']:.2f}

{content}

---
"""
            
            if current_length + len(snippet) > max_length:
                break
            
            context_parts.append(snippet)
            current_length += len(snippet)
        
        context = "\n".join(context_parts)
        
        logger.info(f"📝 Prepared context: {len(context)} chars from {len(context_parts)} articles")
        return context
