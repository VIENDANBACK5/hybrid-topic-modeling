#!/usr/bin/env python3
"""
TopicGPT Integration Demo & Testing
====================================

Test các tính năng Smart Crawl với TopicGPT integration.
"""

import requests
import json
from typing import Dict, List
from datetime import datetime
import time

BASE_URL = "http://localhost:8000/api/crawl"


class TopicGPTDemo:
    """Demo class for TopicGPT features"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def print_header(self, text: str):
        """Print formatted header"""
        print("\n" + "="*60)
        print(f"  {text}")
        print("="*60)
    
    def print_result(self, label: str, value):
        """Print formatted result"""
        print(f"✓ {label}: {value}")
    
    # ==================== SMART CRAWL TESTS ====================
    
    def test_balanced_crawl(self, url: str):
        """Test 1: Balanced mode crawl (RECOMMENDED)"""
        self.print_header("TEST 1: Smart Crawl - Balanced Mode")
        
        payload = {
            "url": url,
            "mode": "max",
            "enable_llm_enrichment": True,
            "enable_semantic_dedupe": True,
            "enable_auto_categorization": True,
            "priority": "balanced"
        }
        
        start_time = time.time()
        response = self.session.post(f"{self.base_url}/smart", json=payload)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            self.print_result("Status", "SUCCESS ✓")
            self.print_result("Articles Found", len(data.get("articles", [])))
            self.print_result("LLM Enriched", data.get("llm_enriched_count", 0))
            self.print_result("Duplicates Found", data.get("duplicates_found", 0))
            self.print_result("Categories Assigned", data.get("categories_assigned", 0))
            self.print_result("Estimated Cost", f"${data.get('estimated_cost', 0):.4f}")
            self.print_result("Actual Cost", f"${data.get('actual_cost', 0):.4f}")
            self.print_result("Processing Time", f"{data.get('processing_time', 0):.2f}s")
            self.print_result("High Value Docs", data.get("high_value_docs", 0))
            
            # Show sample article
            if data.get("articles"):
                sample = data["articles"][0]
                print("\n📄 Sample Article:")
                print(f"  Title: {sample.get('title', 'N/A')[:80]}...")
                print(f"  URL: {sample.get('url', 'N/A')[:80]}...")
                if sample.get("llm_enriched"):
                    print(f"  Keywords: {', '.join(sample.get('keywords', [])[:5])}")
                    print(f"  Category: {sample.get('category', 'N/A')}")
        else:
            print(f"✗ Error: {response.status_code} - {response.text}")
        
        return response
    
    def test_high_quality_crawl(self, url: str):
        """Test 2: High quality mode"""
        self.print_header("TEST 2: Smart Crawl - High Quality Mode")
        
        payload = {
            "url": url,
            "mode": "max",
            "force_enrich_all": True,
            "priority": "high",
            "max_cost": 5.0
        }
        
        response = self.session.post(f"{self.base_url}/smart", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.print_result("Status", "SUCCESS ✓")
            self.print_result("Total Articles", len(data.get("articles", [])))
            self.print_result("All Enriched", data.get("llm_enriched_count", 0))
            self.print_result("Total Cost", f"${data.get('actual_cost', 0):.4f}")
        else:
            print(f"✗ Error: {response.status_code}")
        
        return response
    
    def test_low_cost_crawl(self, url: str):
        """Test 3: Low cost mode"""
        self.print_header("TEST 3: Smart Crawl - Low Cost Mode")
        
        payload = {
            "url": url,
            "mode": "quick",
            "enable_llm_enrichment": False,
            "enable_semantic_dedupe": True,
            "priority": "low"
        }
        
        response = self.session.post(f"{self.base_url}/smart", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.print_result("Status", "SUCCESS ✓")
            self.print_result("Total Articles", len(data.get("articles", [])))
            self.print_result("Cost (Dedupe only)", f"${data.get('actual_cost', 0):.4f}")
            self.print_result("Savings vs High", "~95%")
        else:
            print(f"✗ Error: {response.status_code}")
        
        return response
    
    # ==================== COST MANAGEMENT TESTS ====================
    
    def test_cost_report(self):
        """Test 4: Get cost report"""
        self.print_header("TEST 4: Cost Report")
        
        response = self.session.get(f"{self.base_url}/cost/report")
        
        if response.status_code == 200:
            data = response.json()
            self.print_result("Daily Usage", f"${data.get('daily_usage', 0):.4f}")
            self.print_result("Monthly Usage", f"${data.get('monthly_usage', 0):.4f}")
            self.print_result("Daily Budget", f"${data.get('daily_budget', 0):.2f}")
            self.print_result("Budget Remaining", f"${data.get('budget_remaining', 0):.4f}")
            
            print("\n📊 Operations Count:")
            ops = data.get("operations_count", {})
            for op, count in ops.items():
                print(f"  • {op}: {count}")
            
            print("\n💰 Cost Breakdown:")
            costs = data.get("cost_by_operation", {})
            for op, cost in costs.items():
                print(f"  • {op}: ${cost:.4f}")
        else:
            print(f"✗ Error: {response.status_code}")
        
        return response
    
    def test_set_budget(self, budget: float = 20.0):
        """Test 5: Set daily budget"""
        self.print_header("TEST 5: Set Daily Budget")
        
        response = self.session.post(
            f"{self.base_url}/cost/set-budget",
            params={"daily_budget": budget}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.print_result("New Budget", f"${data.get('daily_budget', 0):.2f}")
            self.print_result("Message", data.get("message", ""))
        else:
            print(f"✗ Error: {response.status_code}")
        
        return response
    
    def test_estimate_cost(self, url: str):
        """Test 6: Estimate crawl cost"""
        self.print_header("TEST 6: Cost Estimation")
        
        payload = {
            "url": url,
            "enable_llm_enrichment": True,
            "enable_semantic_dedupe": True
        }
        
        response = self.session.post(f"{self.base_url}/cost/estimate", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.print_result("Estimated Cost", f"${data.get('estimated_cost', 0):.4f}")
            self.print_result("Estimated Docs", data.get("estimated_documents", 0))
            self.print_result("Can Afford?", "YES ✓" if data.get("can_afford") else "NO ✗")
            self.print_result("Budget Remaining", f"${data.get('budget_remaining', 0):.4f}")
            self.print_result("Recommendation", data.get("recommendation", ""))
            
            print("\n💵 Cost Breakdown:")
            breakdown = data.get("cost_breakdown", {})
            for item, cost in breakdown.items():
                print(f"  • {item}: ${cost:.4f}")
        else:
            print(f"✗ Error: {response.status_code}")
        
        return response
    
    # ==================== PIPELINE TESTS ====================
    
    def test_pipeline_stats(self):
        """Test 7: Get pipeline statistics"""
        self.print_header("TEST 7: Pipeline Statistics")
        
        response = self.session.get(f"{self.base_url}/pipeline/stats")
        
        if response.status_code == 200:
            data = response.json()
            self.print_result("Total Crawls", data.get("total_crawls", 0))
            self.print_result("Success Rate", f"{data.get('success_rate', 0)*100:.1f}%")
            self.print_result("Avg Processing Time", f"{data.get('avg_processing_time', 0):.2f}s")
            
            llm_usage = data.get("llm_usage", {})
            if llm_usage:
                print("\n🤖 LLM Usage:")
                self.print_result("  Total Operations", llm_usage.get("total_operations", 0))
                self.print_result("  Total Cost", f"${llm_usage.get('total_cost', 0):.4f}")
                self.print_result("  Cache Hit Rate", f"{llm_usage.get('cache_hit_rate', 0)*100:.1f}%")
        else:
            print(f"✗ Error: {response.status_code}")
        
        return response
    
    def test_configure_pipeline(self):
        """Test 8: Configure pipeline"""
        self.print_header("TEST 8: Configure Pipeline")
        
        payload = {
            "enable_llm_enrichment": True,
            "enable_semantic_dedupe": True,
            "similarity_threshold": 0.85,
            "priority": "balanced",
            "max_cost": 5.0
        }
        
        response = self.session.post(f"{self.base_url}/pipeline/configure", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.print_result("Status", "SUCCESS ✓")
            self.print_result("Message", data.get("message", ""))
            print("\n⚙️ New Configuration:")
            for key, value in data.get("config", {}).items():
                print(f"  • {key}: {value}")
        else:
            print(f"✗ Error: {response.status_code}")
        
        return response
    
    # ==================== DEDUPLICATION TEST ====================
    
    def test_find_duplicates(self, articles: List[Dict]):
        """Test 9: Find duplicates"""
        self.print_header("TEST 9: Semantic Deduplication")
        
        payload = {
            "articles": articles,
            "similarity_threshold": 0.85,
            "use_llm": True
        }
        
        response = self.session.post(f"{self.base_url}/dedupe/find", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.print_result("Status", "SUCCESS ✓")
            self.print_result("Total Duplicates", data.get("total_duplicates", 0))
            self.print_result("Unique Articles", data.get("unique_articles", 0))
            self.print_result("Processing Time", f"{data.get('processing_time', 0):.2f}s")
            self.print_result("Cost", f"${data.get('cost', 0):.4f}")
            
            groups = data.get("duplicate_groups", [])
            if groups:
                print(f"\n🔍 Found {len(groups)} duplicate groups:")
                for i, group in enumerate(groups[:3], 1):  # Show first 3 groups
                    print(f"  Group {i}:")
                    print(f"    Master: {group['master'].get('title', 'N/A')[:60]}...")
                    print(f"    Duplicates: {len(group.get('duplicates', []))}")
        else:
            print(f"✗ Error: {response.status_code}")
        
        return response
    
    # ==================== RUN ALL TESTS ====================
    
    def run_all_tests(self, test_url: str = "https://vnexpress.net"):
        """Run all tests"""
        print("\n" + "█"*60)
        print("  TopicGPT Integration - Full Test Suite")
        print("█"*60)
        print(f"\nTest URL: {test_url}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Cost Management Tests
            self.test_cost_report()
            self.test_set_budget(20.0)
            self.test_estimate_cost(test_url)
            
            # Pipeline Configuration
            self.test_pipeline_stats()
            self.test_configure_pipeline()
            
            # Smart Crawl Tests
            self.test_balanced_crawl(test_url)
            # self.test_high_quality_crawl(test_url)  # Skip to save cost
            # self.test_low_cost_crawl(test_url)
            
            # Final Report
            self.print_header("FINAL REPORT")
            self.test_cost_report()
            
            print("\n" + "█"*60)
            print("  ✓ All Tests Completed Successfully!")
            print("█"*60)
            
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main function"""
    import sys
    
    demo = TopicGPTDemo()
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        url = sys.argv[2] if len(sys.argv) > 2 else "https://vnexpress.net"
        
        if test_name == "balanced":
            demo.test_balanced_crawl(url)
        elif test_name == "high":
            demo.test_high_quality_crawl(url)
        elif test_name == "low":
            demo.test_low_cost_crawl(url)
        elif test_name == "report":
            demo.test_cost_report()
        elif test_name == "estimate":
            demo.test_estimate_cost(url)
        elif test_name == "stats":
            demo.test_pipeline_stats()
        elif test_name == "all":
            demo.run_all_tests(url)
        else:
            print("Available tests:")
            print("  balanced <url>  - Balanced mode crawl")
            print("  high <url>      - High quality crawl")
            print("  low <url>       - Low cost crawl")
            print("  report          - Cost report")
            print("  estimate <url>  - Cost estimation")
            print("  stats           - Pipeline stats")
            print("  all <url>       - Run all tests")
    else:
        # Run all tests
        demo.run_all_tests()


if __name__ == "__main__":
    main()
