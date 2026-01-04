"""
Cost Optimizer - Smart decisions on when to use expensive LLM operations
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class CostOptimizer:
    """
    Cost Optimizer - Intelligent decisions on LLM usage
    
    Features:
    - Decide when to use LLM vs traditional methods
    - Track API costs
    - Budget management
    - Usage analytics
    - Smart sampling strategies
    """
    
    def __init__(
        self,
        daily_budget: float = 10.0,  # USD
        cost_per_call: Dict[str, float] = None,
        cache_dir: str = "data/cache/cost_optimizer"
    ):
        """
        Initialize Cost Optimizer
        
        Args:
            daily_budget: Maximum daily spend in USD
            cost_per_call: Cost estimates per operation type
            cache_dir: Directory for cost tracking
        """
        self.daily_budget = daily_budget
        
        # Default cost estimates (USD per operation)
        self.cost_per_call = cost_per_call or {
            "categorize": 0.003,
            "summarize": 0.01,
            "extract_keywords": 0.005,
            "generate_label": 0.01,
            "generate_description": 0.02,
            "semantic_similarity": 0.005,
            "topic_refinement": 0.05
        }
        
        # Tracking
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.usage_today = self._load_usage()
        self.total_calls = 0
        self.total_cost = 0.0
        
        logger.info(f"Cost Optimizer initialized (budget: ${daily_budget}/day)")
    
    def _load_usage(self) -> Dict:
        """Load today's usage from cache"""
        today = datetime.now().strftime("%Y-%m-%d")
        usage_file = self.cache_dir / f"usage_{today}.json"
        
        if usage_file.exists():
            try:
                with open(usage_file, 'r') as f:
                    usage = json.load(f)
                logger.info(f"Loaded usage: ${usage.get('total_cost', 0):.4f} spent today")
                return usage
            except Exception as e:
                logger.warning(f"Could not load usage: {e}")
        
        return {
            "date": today,
            "total_calls": 0,
            "total_cost": 0.0,
            "operations": {}
        }
    
    def _save_usage(self):
        """Save usage to cache"""
        today = datetime.now().strftime("%Y-%m-%d")
        usage_file = self.cache_dir / f"usage_{today}.json"
        
        try:
            with open(usage_file, 'w') as f:
                json.dump(self.usage_today, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save usage: {e}")
    
    def record_usage(self, operation: str, count: int = 1):
        """
        Record LLM usage
        
        Args:
            operation: Operation type
            count: Number of calls
        """
        cost = self.cost_per_call.get(operation, 0.01) * count
        
        self.usage_today["total_calls"] += count
        self.usage_today["total_cost"] += cost
        
        if operation not in self.usage_today["operations"]:
            self.usage_today["operations"][operation] = {"calls": 0, "cost": 0.0}
        
        self.usage_today["operations"][operation]["calls"] += count
        self.usage_today["operations"][operation]["cost"] += cost
        
        self.total_calls += count
        self.total_cost += cost
        
        self._save_usage()
        
        logger.info(f"Recorded: {operation} x{count} = ${cost:.4f} "
                   f"(total today: ${self.usage_today['total_cost']:.4f})")
    
    def can_afford(self, operation: str, count: int = 1) -> bool:
        """
        Check if we can afford this operation
        
        Args:
            operation: Operation type
            count: Number of calls
        
        Returns:
            True if within budget
        """
        cost = self.cost_per_call.get(operation, 0.01) * count
        remaining = self.daily_budget - self.usage_today["total_cost"]
        
        if cost > remaining:
            logger.warning(f"Budget exceeded: need ${cost:.4f}, have ${remaining:.4f}")
            return False
        
        return True
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget for today"""
        return max(0, self.daily_budget - self.usage_today["total_cost"])
    
    def should_use_llm_for_doc(
        self,
        document: Dict,
        operation: str,
        priority: str = "normal"
    ) -> bool:
        """
        Decide if should use LLM for this specific document
        
        Args:
            document: Document to process
            operation: Operation type
            priority: Priority level ('high', 'normal', 'low')
        
        Returns:
            True if should use LLM
        """
        # Check budget first
        if not self.can_afford(operation):
            return False
        
        # High priority: always use LLM if budget allows
        if priority == "high":
            return True
        
        # Evaluate document value
        doc_value = self._assess_document_value(document)
        
        # Decision thresholds based on priority
        thresholds = {
            "high": 0.3,
            "normal": 0.6,
            "low": 0.8
        }
        
        threshold = thresholds.get(priority, 0.6)
        
        decision = doc_value >= threshold
        
        if not decision:
            logger.debug(f"Skipping LLM for low-value doc (value: {doc_value:.2f})")
        
        return decision
    
    def _assess_document_value(self, document: Dict) -> float:
        """
        Assess document value (0.0-1.0)
        High value = worth spending on LLM
        
        Factors:
        - Content length
        - Domain reputation
        - Freshness
        - Media richness
        - Engagement signals
        """
        value = 0.5  # Base value
        
        content = document.get('content') or document.get('cleaned_content', '')
        metadata = document.get('metadata', {})
        
        # Length factor (longer = more valuable)
        length = len(content)
        if length > 2000:
            value += 0.15
        elif length > 1000:
            value += 0.1
        elif length < 300:
            value -= 0.2
        
        # Domain reputation
        url = metadata.get('url', '')
        trusted_domains = [
            'vnexpress.net', 'dantri.com.vn', 'thanhnien.vn',
            'tuoitre.vn', 'baohungyen.vn', 'bbc.com', 'cnn.com'
        ]
        if any(domain in url for domain in trusted_domains):
            value += 0.15
        
        # Has media (images/videos)
        if metadata.get('has_images'):
            value += 0.05
        if metadata.get('has_videos'):
            value += 0.1
        
        # Freshness (recent = more valuable)
        published = metadata.get('published_at')
        if published:
            try:
                pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                age_days = (datetime.now() - pub_date).days
                if age_days <= 1:
                    value += 0.15
                elif age_days <= 7:
                    value += 0.1
                elif age_days > 30:
                    value -= 0.1
            except:
                pass
        
        # Has proper structure
        if len(content.split('\n\n')) >= 3:
            value += 0.05
        
        return min(1.0, max(0.0, value))
    
    def get_smart_sample_size(
        self,
        total_docs: int,
        operation: str,
        min_sample: int = 10,
        max_sample: int = 100
    ) -> int:
        """
        Calculate smart sample size based on budget and operation cost
        
        Args:
            total_docs: Total number of documents
            operation: Operation type
            min_sample: Minimum sample size
            max_sample: Maximum sample size
        
        Returns:
            Optimal sample size
        """
        remaining_budget = self.get_remaining_budget()
        cost_per_doc = self.cost_per_call.get(operation, 0.01)
        
        # Calculate max we can afford
        max_affordable = int(remaining_budget / cost_per_doc)
        
        # Apply constraints
        sample_size = min(max_affordable, max_sample)
        sample_size = max(sample_size, min_sample)
        sample_size = min(sample_size, total_docs)
        
        logger.info(f"Smart sample: {sample_size}/{total_docs} docs "
                   f"(budget: ${remaining_budget:.2f})")
        
        return sample_size
    
    def should_enable_feature(
        self,
        feature: str,
        batch_size: int = 1
    ) -> Dict:
        """
        Decide if feature should be enabled
        
        Args:
            feature: Feature name
            batch_size: Number of operations
        
        Returns:
            Dict with decision and reasoning
        """
        # Map features to operations
        feature_operations = {
            "categorization": "categorize",
            "summarization": "summarize",
            "keyword_extraction": "extract_keywords",
            "topic_labeling": "generate_label",
            "semantic_deduplication": "semantic_similarity"
        }
        
        operation = feature_operations.get(feature, feature)
        
        # Check if can afford
        if not self.can_afford(operation, batch_size):
            return {
                "enabled": False,
                "reason": "budget_exceeded",
                "remaining_budget": self.get_remaining_budget()
            }
        
        # Calculate cost
        cost = self.cost_per_call.get(operation, 0.01) * batch_size
        
        # Enable if cost is reasonable (< 50% of remaining budget)
        remaining = self.get_remaining_budget()
        if cost > remaining * 0.5:
            return {
                "enabled": False,
                "reason": "cost_too_high",
                "cost": cost,
                "remaining_budget": remaining
            }
        
        return {
            "enabled": True,
            "reason": "within_budget",
            "cost": cost,
            "remaining_budget": remaining
        }
    
    def get_usage_report(self) -> Dict:
        """Get detailed usage report"""
        remaining = self.get_remaining_budget()
        
        return {
            "date": self.usage_today.get("date"),
            "daily_budget": self.daily_budget,
            "total_spent": self.usage_today.get("total_cost", 0.0),
            "remaining_budget": remaining,
            "budget_used_percent": (self.usage_today.get("total_cost", 0.0) / self.daily_budget * 100),
            "total_calls": self.usage_today.get("total_calls", 0),
            "operations": self.usage_today.get("operations", {}),
            "status": "healthy" if remaining > self.daily_budget * 0.2 else "low_budget"
        }
    
    def estimate_cost(
        self,
        operation: str,
        count: int
    ) -> Dict:
        """
        Estimate cost for operation
        
        Args:
            operation: Operation type
            count: Number of operations
        
        Returns:
            Cost estimation dict
        """
        unit_cost = self.cost_per_call.get(operation, 0.01)
        total_cost = unit_cost * count
        
        return {
            "operation": operation,
            "count": count,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "affordable": self.can_afford(operation, count)
        }
    
    def reset_daily_usage(self):
        """Reset usage for new day"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.usage_today = {
            "date": today,
            "total_calls": 0,
            "total_cost": 0.0,
            "operations": {}
        }
        self._save_usage()
        logger.info("Daily usage reset")


# Global instance
_cost_optimizer = None

def get_cost_optimizer() -> CostOptimizer:
    """Get or create global cost optimizer"""
    global _cost_optimizer
    if _cost_optimizer is None:
        _cost_optimizer = CostOptimizer()
    return _cost_optimizer
