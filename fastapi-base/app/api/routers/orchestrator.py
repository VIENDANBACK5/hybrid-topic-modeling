"""
Full Pipeline API - Orchestrated pipeline endpoints
Provides automatic full-flow: Crawl → ETL → NER → Topic → Index → Dashboard
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import logging

from app.services.task_queue import get_task_queue, init_task_handlers, TaskStatus
from app.services.monitoring import get_metrics_collector, get_health_checker

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize task handlers
try:
    init_task_handlers()
except Exception as e:
    logger.warning(f"Task handlers init: {e}")


# ============================================
# Request/Response Models
# ============================================

class FullPipelineRequest(BaseModel):
    """Request for full pipeline execution"""
    url: str
    mode: str = "max"  # quick, max, full
    train_topics: bool = True
    extract_ner: bool = True
    save_to_db: bool = True
    async_mode: bool = True  # Run in background


class FullPipelineResponse(BaseModel):
    """Response for full pipeline"""
    status: str
    task_id: Optional[str] = None
    message: str
    result: Optional[Dict] = None


class TaskStatusResponse(BaseModel):
    """Task status response"""
    id: str
    name: str
    status: str
    progress: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


# ============================================
# Full Pipeline Endpoints
# ============================================

@router.post("/run", response_model=FullPipelineResponse)
async def run_full_pipeline(request: FullPipelineRequest):
    """
    🚀 FULL PIPELINE - Chạy toàn bộ luồng tự động
    
    Luồng: Crawl → Clean → Dedupe → NER → Topic Modeling → Save DB
    
    Args:
        url: URL website cần crawl
        mode: "quick" (50 trang), "max" (5000 trang), "full" (10000 trang)
        train_topics: Tự động train topic model
        extract_ner: Trích xuất Named Entities
        save_to_db: Lưu vào database
        async_mode: Chạy background (khuyến nghị cho crawl lớn)
    
    Returns:
        task_id: ID để theo dõi tiến độ (nếu async)
        result: Kết quả (nếu sync)
    """
    try:
        queue = get_task_queue()
        metrics = get_metrics_collector()
        
        # Record pipeline start
        metrics.record_pipeline_event('crawl', 1)
        
        params = {
            'url': request.url,
            'mode': request.mode,
            'train_topics': request.train_topics,
            'extract_ner': request.extract_ner,
            'save_to_db': request.save_to_db,
        }
        
        if request.async_mode:
            # Run in background
            task_id = await queue.submit('full_pipeline', params)
            
            return FullPipelineResponse(
                status="submitted",
                task_id=task_id,
                message=f"Pipeline đã được submit. Theo dõi tại /api/orchestrator/task/{task_id}"
            )
        else:
            # Run synchronously (for small crawls)
            from app.services.task_queue import handle_full_pipeline
            
            result = await handle_full_pipeline(params, lambda p, m: None)
            
            # Record success
            metrics.record_pipeline_event('crawl', success=True)
            if result.get('stages', {}).get('topics', {}).get('num_topics'):
                metrics.record_pipeline_event('topics', result['stages']['topics']['num_topics'])
            
            return FullPipelineResponse(
                status="completed",
                message="Pipeline hoàn thành",
                result=result
            )
    
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        metrics = get_metrics_collector()
        metrics.record_pipeline_event('crawl', success=False)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    📊 Lấy trạng thái task
    
    Args:
        task_id: ID của task cần kiểm tra
    
    Returns:
        Task status với progress và result
    """
    queue = get_task_queue()
    task = queue.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} không tồn tại")
    
    return TaskStatusResponse(**task)


@router.get("/tasks", response_model=List[TaskStatusResponse])
async def list_tasks(limit: int = 20):
    """
    📋 Liệt kê các tasks gần đây
    
    Args:
        limit: Số lượng tasks tối đa
    """
    queue = get_task_queue()
    tasks = queue.get_all_tasks(limit=limit)
    return [TaskStatusResponse(**t) for t in tasks]


@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    ❌ Hủy task đang chạy
    """
    queue = get_task_queue()
    success = await queue.cancel_task(task_id)
    
    if success:
        return {"status": "cancelled", "task_id": task_id}
    else:
        raise HTTPException(status_code=400, detail="Không thể hủy task")


# ============================================
# Monitoring Endpoints
# ============================================

@router.get("/metrics")
async def get_metrics():
    """
    📈 Lấy metrics hệ thống
    
    Returns:
        - System metrics (CPU, RAM, Disk)
        - Request stats (latency, errors)
        - Pipeline stats (crawls, topics, etc.)
    """
    metrics = get_metrics_collector()
    return metrics.get_all_metrics()


@router.get("/metrics/system")
async def get_system_metrics():
    """Get system metrics only"""
    metrics = get_metrics_collector()
    return metrics.get_system_metrics()


@router.get("/metrics/pipeline")
async def get_pipeline_metrics():
    """Get pipeline metrics only"""
    metrics = get_metrics_collector()
    return metrics.get_pipeline_stats()


@router.get("/health")
async def health_check():
    """
    🏥 Health check endpoint
    
    Checks:
        - Database connectivity
        - Redis connectivity
        - Disk space
        - Memory usage
    """
    checker = get_health_checker()
    result = checker.check_all()
    
    status_code = 200
    if result['status'] == 'unhealthy':
        status_code = 503
    elif result['status'] == 'degraded':
        status_code = 200  # Still OK but with warning
    
    return result


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.now().isoformat()}


@router.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe"""
    checker = get_health_checker()
    result = checker.check_all()
    
    if result['status'] == 'unhealthy':
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {"status": "ready", "timestamp": datetime.now().isoformat()}


# ============================================
# Quick Pipeline Shortcuts
# ============================================

@router.post("/quick-crawl")
async def quick_crawl(url: str, max_pages: int = 50):
    """
    ⚡ Quick crawl - Crawl nhanh không train topic
    """
    return await run_full_pipeline(FullPipelineRequest(
        url=url,
        mode="quick",
        train_topics=False,
        extract_ner=True,
        async_mode=False
    ))


@router.post("/full-analysis")
async def full_analysis(url: str):
    """
    🔬 Full analysis - Crawl + NER + Topics (async)
    """
    return await run_full_pipeline(FullPipelineRequest(
        url=url,
        mode="max",
        train_topics=True,
        extract_ner=True,
        async_mode=True
    ))
