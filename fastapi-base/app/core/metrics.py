"""
Prometheus Metrics Integration for FastAPI
Exposes application metrics for monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client.core import CollectorRegistry
from fastapi import FastAPI, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time
import psutil
from typing import Callable


# Metrics Registry
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

REQUEST_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint']
)

# Application metrics
SYNC_OPERATIONS = Counter(
    'sync_operations_total',
    'Total sync operations',
    ['status']  # success, error
)

ARTICLES_PROCESSED = Counter(
    'articles_processed_total',
    'Total articles processed'
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Active database connections'
)

# System metrics
CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

MEMORY_USAGE = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes'
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        endpoint = request.url.path
        
        # Track in-progress requests
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        
        # Track request duration
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            status = 500
            raise e
        finally:
            duration = time.time() - start_time
            
            # Record metrics
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        
        return response


def update_system_metrics():
    """Update system resource metrics"""
    CPU_USAGE.set(psutil.cpu_percent())
    MEMORY_USAGE.set(psutil.virtual_memory().used)


async def metrics_endpoint(request: Request):
    """
    Expose metrics endpoint for Prometheus scraping
    GET /metrics
    """
    update_system_metrics()
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain"
    )


def setup_metrics(app: FastAPI):
    """
    Setup Prometheus metrics for FastAPI application
    
    Usage in main.py:
        from app.core.metrics import setup_metrics
        app = get_application()
        setup_metrics(app)
    """
    # Add metrics middleware
    app.add_middleware(PrometheusMiddleware)
    
    # Add metrics endpoint
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])
    
    return app


# Helper functions for custom metrics
def track_sync_success():
    """Track successful sync operation"""
    SYNC_OPERATIONS.labels(status='success').inc()


def track_sync_error():
    """Track failed sync operation"""
    SYNC_OPERATIONS.labels(status='error').inc()


def track_articles(count: int):
    """Track number of articles processed"""
    ARTICLES_PROCESSED.inc(count)


def set_db_connections(count: int):
    """Update active database connection count"""
    DATABASE_CONNECTIONS.set(count)
