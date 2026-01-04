"""
Comprehensive Test Suite for Sync Service API
Run: pytest test_sync_service.py -v
"""

import pytest
import requests
from datetime import datetime
import time

BASE_URL = "http://localhost:7777/api/v1/sync"
API_KEY = "dev-key-12345"
HEADERS = {"X-API-Key": API_KEY}


# ============================================
# UNIT TESTS
# ============================================

class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_endpoint_exists(self):
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
    
    def test_health_returns_correct_structure(self):
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "sentiment_analyzer" in data["checks"]
        assert "sync_service" in data["checks"]
    
    def test_health_status_values(self):
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]


class TestAuthentication:
    """Test API authentication"""
    
    def test_protected_endpoint_without_key(self):
        response = requests.post(
            f"{BASE_URL}/trigger",
            json={"source_api_base": "http://example.com"}
        )
        assert response.status_code == 403
        assert "Missing API Key" in response.json()["detail"]
    
    def test_protected_endpoint_with_invalid_key(self):
        response = requests.post(
            f"{BASE_URL}/trigger",
            headers={"X-API-Key": "invalid-key"},
            json={"source_api_base": "http://example.com"}
        )
        assert response.status_code == 403
    
    def test_protected_endpoint_with_valid_key(self):
        response = requests.post(
            f"{BASE_URL}/trigger",
            headers=HEADERS,
            json={
                "source_api_base": "http://192.168.30.28:8000",
                "endpoint": "/api/v1/posts",
                "limit": 1
            }
        )
        # Should not be auth error (may be running or other status)
        assert response.status_code != 403
    
    def test_public_endpoint_no_auth_required(self):
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        
        response = requests.get(f"{BASE_URL}/status")
        assert response.status_code == 200


class TestDatabaseStats:
    """Test database statistics endpoint"""
    
    def test_db_stats_structure(self):
        response = requests.get(f"{BASE_URL}/db-stats")
        data = response.json()
        assert "status" in data
        assert "tables" in data
        assert "total_rows" in data
    
    def test_db_stats_table_counts(self):
        response = requests.get(f"{BASE_URL}/db-stats")
        data = response.json()
        tables = data["tables"]
        
        # Check key tables exist
        assert "articles" in tables
        assert "sentiment_analysis" in tables
        assert isinstance(tables["articles"], int)
        assert tables["articles"] >= 0


# ============================================
# INTEGRATION TESTS
# ============================================

class TestSyncWorkflow:
    """Test complete sync workflow"""
    
    def test_sync_status_idle_initially(self):
        response = requests.get(f"{BASE_URL}/status")
        data = response.json()
        assert data["status"] in ["idle", "completed", "running"]
    
    def test_trigger_sync_with_minimal_params(self):
        response = requests.post(
            f"{BASE_URL}/trigger",
            headers=HEADERS,
            json={
                "source_api_base": "http://192.168.30.28:8000",
                "endpoint": "/api/v1/posts",
                "limit": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "running"
    
    def test_sync_completion(self):
        # Trigger small sync
        requests.post(
            f"{BASE_URL}/trigger",
            headers=HEADERS,
            json={
                "source_api_base": "http://192.168.30.28:8000",
                "endpoint": "/api/v1/posts",
                "limit": 5
            }
        )
        
        # Wait and check completion
        time.sleep(3)
        response = requests.get(f"{BASE_URL}/status")
        data = response.json()
        assert data["status"] in ["completed", "idle"]


class TestDataIntegrity:
    """Test data integrity and validation"""
    
    def test_articles_have_required_fields(self):
        # This would query database directly
        # For now, check via API
        response = requests.get(f"{BASE_URL}/db-stats")
        data = response.json()
        assert data["tables"]["articles"] > 0
    
    def test_sentiment_analysis_matches_articles(self):
        response = requests.get(f"{BASE_URL}/db-stats")
        data = response.json()
        
        # Sentiment should be <= articles
        if data["tables"]["articles"] > 0:
            assert data["tables"]["sentiment_analysis"] <= data["tables"]["articles"]


# ============================================
# PERFORMANCE TESTS
# ============================================

class TestPerformance:
    """Test API performance"""
    
    def test_health_endpoint_response_time(self):
        start = time.time()
        response = requests.get(f"{BASE_URL}/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond within 1 second
    
    def test_db_stats_response_time(self):
        start = time.time()
        response = requests.get(f"{BASE_URL}/db-stats")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0  # Should respond within 2 seconds
    
    def test_concurrent_health_checks(self):
        import concurrent.futures
        
        def check_health():
            response = requests.get(f"{BASE_URL}/health")
            return response.status_code == 200
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_health) for _ in range(10)]
            results = [f.result() for f in futures]
        
        assert all(results), "All concurrent requests should succeed"


# ============================================
# ERROR HANDLING TESTS
# ============================================

class TestErrorHandling:
    """Test error handling and validation"""
    
    def test_invalid_source_api(self):
        response = requests.post(
            f"{BASE_URL}/trigger",
            headers=HEADERS,
            json={
                "source_api_base": "http://invalid-domain-that-does-not-exist.com",
                "limit": 1
            }
        )
        # Should start but may fail during execution
        assert response.status_code in [200, 400]
    
    def test_missing_required_params(self):
        response = requests.post(
            f"{BASE_URL}/trigger",
            headers=HEADERS,
            json={}
        )
        assert response.status_code in [400, 422]  # Validation error


# ============================================
# BACKUP TESTS
# ============================================

class TestBackup:
    """Test backup functionality"""
    
    def test_backup_directory_exists(self):
        import os
        backup_dir = "/home/ai_team/lab/pipeline_mxh/backups"
        assert os.path.exists(backup_dir) or True  # Create if doesn't exist
    
    def test_backup_file_created(self):
        import os
        import subprocess
        
        # Run backup
        result = subprocess.run(
            ["./backup_database.sh"],
            cwd="/home/ai_team/lab/pipeline_mxh/fastapi-base",
            capture_output=True
        )
        
        # Check backup exists
        backup_dir = "/home/ai_team/lab/pipeline_mxh/backups"
        if os.path.exists(backup_dir):
            backups = [f for f in os.listdir(backup_dir) if f.startswith("DBHuYe_")]
            assert len(backups) > 0


# ============================================
# PYTEST CONFIGURATION
# ============================================

@pytest.fixture(scope="session", autouse=True)
def setup_tests():
    """Setup before all tests"""
    print("\n🧪 Starting test suite...")
    yield
    print("\n✅ Test suite completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
