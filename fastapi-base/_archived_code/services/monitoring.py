"""
Monitoring & Metrics Service
Provides system metrics, task stats, and health monitoring
"""
import logging
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: str
    value: float
    labels: Optional[Dict] = None


class MetricsCollector:
    """
    Metrics collection and monitoring
    
    Features:
    - System metrics (CPU, memory, disk)
    - Application metrics (requests, errors, latency)
    - Pipeline metrics (crawls, topics, documents)
    - Time-series storage (in-memory with rolling window)
    """
    
    def __init__(self, retention_hours: int = 24):
        """
        Initialize metrics collector
        
        Args:
            retention_hours: How long to keep metrics
        """
        self.retention_hours = retention_hours
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = defaultdict(float)
        
        # Request tracking
        self._request_times: List[float] = []
        self._error_count = 0
        
        # Pipeline stats
        self._pipeline_stats = {
            'crawls_total': 0,
            'crawls_success': 0,
            'crawls_failed': 0,
            'documents_crawled': 0,
            'topics_trained': 0,
            'ner_extractions': 0,
        }
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        logger.info("MetricsCollector initialized")
    
    def record_metric(self, name: str, value: float, labels: Dict = None):
        """
        Record a metric value
        
        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels/tags
        """
        with self._lock:
            point = MetricPoint(
                timestamp=datetime.now().isoformat(),
                value=value,
                labels=labels
            )
            self._metrics[name].append(point)
            
            # Cleanup old data
            self._cleanup_old_data(name)
    
    def _cleanup_old_data(self, name: str):
        """Remove data older than retention period"""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        cutoff_str = cutoff.isoformat()
        
        self._metrics[name] = [
            p for p in self._metrics[name]
            if p.timestamp > cutoff_str
        ]
    
    def increment(self, name: str, value: int = 1, labels: Dict = None):
        """Increment a counter"""
        with self._lock:
            key = name if not labels else f"{name}:{str(labels)}"
            self._counters[key] += value
    
    def set_gauge(self, name: str, value: float):
        """Set a gauge value"""
        with self._lock:
            self._gauges[name] = value
    
    def record_request(self, duration_ms: float, endpoint: str, status_code: int):
        """Record an API request"""
        with self._lock:
            self._request_times.append(duration_ms)
            
            # Keep only last 1000 requests for percentile calculation
            if len(self._request_times) > 1000:
                self._request_times = self._request_times[-1000:]
            
            if status_code >= 400:
                self._error_count += 1
            
            self.increment('requests_total', labels={'endpoint': endpoint})
            self.record_metric('request_duration_ms', duration_ms, {'endpoint': endpoint})
    
    def record_pipeline_event(self, event: str, count: int = 1, success: bool = True):
        """Record pipeline events"""
        with self._lock:
            if event == 'crawl':
                self._pipeline_stats['crawls_total'] += count
                if success:
                    self._pipeline_stats['crawls_success'] += count
                else:
                    self._pipeline_stats['crawls_failed'] += count
            elif event == 'documents':
                self._pipeline_stats['documents_crawled'] += count
            elif event == 'topics':
                self._pipeline_stats['topics_trained'] += count
            elif event == 'ner':
                self._pipeline_stats['ner_extractions'] += count
    
    def get_system_metrics(self) -> Dict:
        """Get current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_percent': memory.percent,
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_percent': round(disk.percent, 1),
            }
        except Exception as e:
            logger.warning(f"Error getting system metrics: {e}")
            return {}
    
    def get_request_stats(self) -> Dict:
        """Get request statistics"""
        with self._lock:
            if not self._request_times:
                return {
                    'total_requests': 0,
                    'error_count': self._error_count,
                    'avg_latency_ms': 0,
                    'p50_latency_ms': 0,
                    'p95_latency_ms': 0,
                    'p99_latency_ms': 0,
                }
            
            sorted_times = sorted(self._request_times)
            n = len(sorted_times)
            
            return {
                'total_requests': sum(self._counters.get(k, 0) for k in self._counters if k.startswith('requests_total')),
                'error_count': self._error_count,
                'avg_latency_ms': round(sum(sorted_times) / n, 2),
                'p50_latency_ms': round(sorted_times[int(n * 0.5)], 2),
                'p95_latency_ms': round(sorted_times[int(n * 0.95)], 2),
                'p99_latency_ms': round(sorted_times[min(int(n * 0.99), n-1)], 2),
            }
    
    def get_pipeline_stats(self) -> Dict:
        """Get pipeline statistics"""
        with self._lock:
            return dict(self._pipeline_stats)
    
    def get_all_metrics(self) -> Dict:
        """Get all metrics summary"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system': self.get_system_metrics(),
            'requests': self.get_request_stats(),
            'pipeline': self.get_pipeline_stats(),
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
        }
    
    def get_metric_history(self, name: str, hours: int = 1) -> List[Dict]:
        """Get metric history for time-series display"""
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()
        
        with self._lock:
            points = [
                asdict(p) for p in self._metrics.get(name, [])
                if p.timestamp > cutoff_str
            ]
        
        return points


# Health check functions
class HealthChecker:
    """System health checker"""
    
    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics
        self._checks: Dict[str, callable] = {}
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks"""
        self._checks['database'] = self._check_database
        self._checks['redis'] = self._check_redis
        self._checks['disk_space'] = self._check_disk_space
        self._checks['memory'] = self._check_memory
    
    def _check_database(self) -> Dict:
        """Check database connectivity"""
        try:
            from app.core.database import SessionLocal
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            return {'status': 'healthy', 'message': 'Database connected'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': str(e)}
    
    def _check_redis(self) -> Dict:
        """Check Redis connectivity"""
        try:
            import redis
            client = redis.from_url("redis://localhost:6379")
            client.ping()
            return {'status': 'healthy', 'message': 'Redis connected'}
        except Exception as e:
            return {'status': 'degraded', 'message': f'Redis unavailable: {e}'}
    
    def _check_disk_space(self) -> Dict:
        """Check disk space"""
        try:
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                return {'status': 'unhealthy', 'message': f'Disk usage: {disk.percent}%'}
            elif disk.percent > 80:
                return {'status': 'degraded', 'message': f'Disk usage: {disk.percent}%'}
            return {'status': 'healthy', 'message': f'Disk usage: {disk.percent}%'}
        except Exception as e:
            return {'status': 'unknown', 'message': str(e)}
    
    def _check_memory(self) -> Dict:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                return {'status': 'unhealthy', 'message': f'Memory usage: {memory.percent}%'}
            elif memory.percent > 80:
                return {'status': 'degraded', 'message': f'Memory usage: {memory.percent}%'}
            return {'status': 'healthy', 'message': f'Memory usage: {memory.percent}%'}
        except Exception as e:
            return {'status': 'unknown', 'message': str(e)}
    
    def check_all(self) -> Dict:
        """Run all health checks"""
        results = {}
        overall_status = 'healthy'
        
        for name, check in self._checks.items():
            try:
                result = check()
                results[name] = result
                
                if result['status'] == 'unhealthy':
                    overall_status = 'unhealthy'
                elif result['status'] == 'degraded' and overall_status == 'healthy':
                    overall_status = 'degraded'
            except Exception as e:
                results[name] = {'status': 'error', 'message': str(e)}
                overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'checks': results
        }


# Global instances
_metrics_collector: Optional[MetricsCollector] = None
_health_checker: Optional[HealthChecker] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_health_checker() -> HealthChecker:
    """Get global health checker"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker(get_metrics_collector())
    return _health_checker
