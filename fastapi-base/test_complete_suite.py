"""
🧪 TEST SUITE - Pipeline MXH System
Comprehensive test cases for BA & Tester validation
"""

import pytest
import requests
from datetime import datetime
from app.core.database import SessionLocal
from app.models import Article, SentimentAnalysis


# ============================================
# CONFIGURATION
# ============================================

BASE_URL = "http://localhost:7777"
API_PREFIX = "/api/v1"


# ============================================
# UNIT TESTS
# ============================================

class TestSyncService:
    """Test sync service core functionality"""
    
    def test_pagination_bug_fixed(self):
        """
        BUG #1: Verify pagination processes ALL documents
        Expected: synced_count == fetched_count
        """
        response = requests.post(f"{BASE_URL}{API_PREFIX}/sync/trigger", json={
            "limit": 50,
            "batch_size": 50
        })
        
        status = response.json()
        assert status["total_fetched"] == status["total_saved"], \
            f"Expected {status['total_fetched']} saved, got {status['total_saved']}"
    
    def test_duplicate_prevention(self):
        """
        Test: Không tạo duplicate articles
        """
        # Sync same data twice
        requests.post(f"{BASE_URL}{API_PREFIX}/sync/trigger", json={"limit": 10})
        initial_count = self._get_article_count()
        
        requests.post(f"{BASE_URL}{API_PREFIX}/sync/trigger", json={"limit": 10})
        final_count = self._get_article_count()
        
        assert final_count == initial_count, "Duplicates were created!"
    
    def test_sentiment_analysis_coverage(self):
        """
        Test: Tất cả articles đều có sentiment analysis
        """
        requests.post(f"{BASE_URL}{API_PREFIX}/sync/trigger", json={
            "limit": 20,
            "analyze_sentiment": True
        })
        
        db = SessionLocal()
        articles = db.query(Article).count()
        sentiments = db.query(SentimentAnalysis).count()
        db.close()
        
        assert articles == sentiments, \
            f"Missing sentiment: {articles} articles but {sentiments} sentiments"
    
    def test_category_classification(self):
        """
        Test: Tất cả sentiments đều có category
        """
        db = SessionLocal()
        sentiments = db.query(SentimentAnalysis).all()
        
        no_category = sum(1 for s in sentiments if not s.category)
        assert no_category == 0, f"{no_category} sentiments missing category"
        
        db.close()
    
    def _get_article_count(self):
        db = SessionLocal()
        count = db.query(Article).count()
        db.close()
        return count


class TestSentimentAnalysis:
    """Test sentiment analysis accuracy"""
    
    def test_positive_sentiment(self):
        """Test phát hiện cảm xúc tích cực"""
        from app.services.sentiment.sentiment_service import get_sentiment_analyzer
        
        analyzer = get_sentiment_analyzer()
        result = analyzer.analyze("Tôi rất vui và hạnh phúc!")
        
        assert result["sentiment_group"] == "positive"
        assert result["emotion"] in ["happy", "joy"]
    
    def test_negative_sentiment(self):
        """Test phát hiện cảm xúc tiêu cực"""
        from app.services.sentiment.sentiment_service import get_sentiment_analyzer
        
        analyzer = get_sentiment_analyzer()
        result = analyzer.analyze("Tôi rất buồn và thất vọng")
        
        assert result["sentiment_group"] == "negative"
        assert result["emotion"] in ["sad", "disappointed"]
    
    def test_neutral_sentiment(self):
        """Test phát hiện cảm xúc trung lập"""
        from app.services.sentiment.sentiment_service import get_sentiment_analyzer
        
        analyzer = get_sentiment_analyzer()
        result = analyzer.analyze("Đây là một thông tin bình thường")
        
        assert result["sentiment_group"] == "neutral"


class TestStatistics:
    """Test statistics calculation"""
    
    def test_hot_topics_calculation(self):
        """Test tính hot topics đúng"""
        from fill_all_tables import SessionLocal
        from app.models.model_statistics import HotTopic
        
        db = SessionLocal()
        hot_topics = db.query(HotTopic).order_by(HotTopic.rank).all()
        
        # Should have at least 1 hot topic
        assert len(hot_topics) > 0
        
        # Rank should be sequential
        for i, topic in enumerate(hot_topics, 1):
            assert topic.rank == i
        
        # First should have highest mention_count
        if len(hot_topics) > 1:
            assert hot_topics[0].mention_count >= hot_topics[1].mention_count
        
        db.close()
    
    def test_keyword_stats(self):
        """Test keyword stats có data"""
        response = requests.get(f"{BASE_URL}{API_PREFIX}/sync/db-stats")
        stats = response.json()
        
        assert stats["tables"]["keyword_stats"] > 0, "No keyword stats"
    
    def test_category_trends(self):
        """Test category trends calculation"""
        db = SessionLocal()
        from app.models.model_trends import CategoryTrendStats
        
        trends = db.query(CategoryTrendStats).all()
        assert len(trends) > 0, "No category trends"
        
        # Each trend should have valid data
        for trend in trends:
            assert trend.category is not None
            assert trend.total_mentions > 0
            assert trend.positive_count + trend.negative_count + trend.neutral_count == trend.total_mentions
        
        db.close()
    
    def test_trend_alerts(self):
        """Test trend alerts detection"""
        db = SessionLocal()
        from app.models.model_trends import TrendAlert
        
        alerts = db.query(TrendAlert).all()
        
        # May or may not have alerts depending on data
        for alert in alerts:
            assert alert.alert_type in ["crisis", "spike", "drop", "viral"]
            assert alert.alert_level in ["low", "medium", "high", "critical"]
        
        db.close()


# ============================================
# INTEGRATION TESTS
# ============================================

class TestAPIEndpoints:
    """Test all API endpoints"""
    
    def test_sync_trigger_endpoint(self):
        """Test POST /sync/trigger"""
        response = requests.post(f"{BASE_URL}{API_PREFIX}/sync/trigger", json={
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_sync_status_endpoint(self):
        """Test GET /sync/status"""
        response = requests.get(f"{BASE_URL}{API_PREFIX}/sync/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_db_stats_endpoint(self):
        """Test GET /sync/db-stats"""
        response = requests.get(f"{BASE_URL}{API_PREFIX}/sync/db-stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert "articles" in data["tables"]
    
    def test_clear_data_endpoint(self):
        """Test DELETE /sync/clear-data"""
        # Should require confirmation
        response = requests.delete(f"{BASE_URL}{API_PREFIX}/sync/clear-data", json={
            "table_name": "articles",
            "confirm": False
        })
        
        # Should fail without confirmation
        assert response.status_code in [400, 422]


# ============================================
# E2E TESTS
# ============================================

class TestEndToEndWorkflow:
    """Test complete workflow"""
    
    def test_full_sync_workflow(self):
        """
        Test toàn bộ flow: Sync → Analyze → Statistics
        """
        # Step 1: Clear existing data
        requests.delete(f"{BASE_URL}{API_PREFIX}/sync/clear-data", json={
            "table_name": "articles",
            "confirm": True
        })
        
        # Step 2: Sync data
        sync_response = requests.post(f"{BASE_URL}{API_PREFIX}/sync/trigger", json={
            "limit": 50,
            "analyze_sentiment": True
        })
        assert sync_response.status_code == 200
        
        # Step 3: Wait for completion
        import time
        time.sleep(10)
        
        # Step 4: Check data
        db = SessionLocal()
        
        articles = db.query(Article).count()
        sentiments = db.query(SentimentAnalysis).count()
        
        assert articles > 0, "No articles synced"
        assert sentiments == articles, "Sentiment analysis incomplete"
        
        db.close()
        
        # Step 5: Check statistics
        stats = requests.get(f"{BASE_URL}{API_PREFIX}/sync/db-stats").json()
        assert stats["tables"]["keyword_stats"] > 0
        assert stats["tables"]["hot_topics"] > 0


# ============================================
# PERFORMANCE TESTS
# ============================================

class TestPerformance:
    """Test system performance"""
    
    def test_sync_performance(self):
        """
        Test: Sync 100 posts nên < 30 giây
        """
        import time
        
        start = time.time()
        response = requests.post(f"{BASE_URL}{API_PREFIX}/sync/trigger", json={
            "limit": 100
        })
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 30, f"Sync took {duration}s (should be < 30s)"
    
    def test_stats_query_performance(self):
        """
        Test: DB stats query nên < 2 giây
        """
        import time
        
        start = time.time()
        response = requests.get(f"{BASE_URL}{API_PREFIX}/sync/db-stats")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0, f"Query took {duration}s (should be < 2s)"


# ============================================
# DATA QUALITY TESTS
# ============================================

class TestDataQuality:
    """Test data quality and integrity"""
    
    def test_no_duplicates(self):
        """Test: Không có duplicate URLs"""
        db = SessionLocal()
        
        articles = db.query(Article).all()
        urls = [a.url for a in articles if a.url]
        
        duplicates = len(urls) - len(set(urls))
        assert duplicates == 0, f"Found {duplicates} duplicate URLs"
        
        db.close()
    
    def test_required_fields(self):
        """Test: Tất cả articles có đủ trường bắt buộc"""
        db = SessionLocal()
        
        articles = db.query(Article).all()
        
        no_title = sum(1 for a in articles if not a.title)
        no_content = sum(1 for a in articles if not a.content)
        no_url = sum(1 for a in articles if not a.url)
        
        assert no_title == 0, f"{no_title} articles missing title"
        assert no_content == 0, f"{no_content} articles missing content"
        assert no_url == 0, f"{no_url} articles missing URL"
        
        db.close()
    
    def test_sentiment_confidence(self):
        """Test: Sentiment confidence trong khoảng [0, 1]"""
        db = SessionLocal()
        
        sentiments = db.query(SentimentAnalysis).all()
        
        for s in sentiments:
            assert 0 <= s.confidence <= 1, \
                f"Invalid confidence {s.confidence} for article {s.article_id}"
        
        db.close()


# ============================================
# SECURITY TESTS
# ============================================

class TestSecurity:
    """Test security measures"""
    
    def test_sql_injection_prevention(self):
        """Test: API không vulnerable với SQL injection"""
        # Try SQL injection in URL param
        response = requests.get(f"{BASE_URL}{API_PREFIX}/sync/status?id=1' OR '1'='1")
        
        # Should handle gracefully, not crash
        assert response.status_code in [200, 400, 422]
    
    def test_xss_prevention(self):
        """Test: Không lưu malicious scripts"""
        # This would require actually syncing malicious content
        # For now, just verify content is properly escaped
        db = SessionLocal()
        
        articles = db.query(Article).first()
        if articles and articles.content:
            # Check for common XSS patterns
            dangerous_patterns = ["<script>", "javascript:", "onerror="]
            for pattern in dangerous_patterns:
                assert pattern.lower() not in articles.content.lower()
        
        db.close()


# ============================================
# REGRESSION TESTS
# ============================================

class TestRegression:
    """Test known bugs don't reappear"""
    
    def test_pagination_bug_regression(self):
        """
        REGRESSION: BUG #1 - Pagination should process all docs
        """
        response = requests.post(f"{BASE_URL}{API_PREFIX}/sync/trigger", json={
            "limit": 20
        })
        
        data = response.json()
        # After fix, fetched should equal saved
        assert data["total_saved"] == data["total_fetched"]
    
    def test_datetime_type_regression(self):
        """
        REGRESSION: BUG #2 - created_at should be DateTime not Float
        """
        db = SessionLocal()
        article = db.query(Article).first()
        
        if article:
            # Should be able to use date functions
            from sqlalchemy import func
            result = db.query(func.date(article.created_at)).first()
            # If this doesn't crash, type is correct
        
        db.close()


# ============================================
# RUN ALL TESTS
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
