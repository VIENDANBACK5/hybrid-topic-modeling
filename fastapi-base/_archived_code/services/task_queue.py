"""
Background Task Queue - Async task processing using Redis
Handles long-running tasks like crawling, training, indexing
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task definition"""
    id: str
    name: str
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    progress: int = 0
    params: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class TaskQueue:
    """
    Simple in-memory task queue with optional Redis backend
    
    Features:
    - Async task execution
    - Task status tracking
    - Progress updates
    - Result storage
    """
    
    def __init__(self, use_redis: bool = True, redis_url: str = "redis://localhost:6379"):
        """
        Initialize task queue
        
        Args:
            use_redis: Use Redis for persistence (optional)
            redis_url: Redis connection URL
        """
        self.use_redis = use_redis
        self.redis_url = redis_url
        self.redis_client = None
        
        # In-memory storage (fallback)
        self._tasks: Dict[str, Task] = {}
        self._handlers: Dict[str, Callable] = {}
        
        # Thread pool for running tasks
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        # Try Redis connection
        if use_redis:
            self._init_redis()
        
        logger.info(f"TaskQueue initialized (redis={self.redis_client is not None})")
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.warning(f"Redis not available: {e}, using in-memory storage")
            self.redis_client = None
    
    def register_handler(self, task_name: str, handler: Callable):
        """
        Register a task handler function
        
        Args:
            task_name: Name of the task
            handler: Async function to handle the task
        """
        self._handlers[task_name] = handler
        logger.info(f"Registered handler for task: {task_name}")
    
    async def submit(
        self,
        task_name: str,
        params: Optional[Dict] = None,
        task_id: Optional[str] = None
    ) -> str:
        """
        Submit a task for execution
        
        Args:
            task_name: Name of the task (must have registered handler)
            params: Parameters to pass to the handler
            task_id: Optional custom task ID
            
        Returns:
            Task ID
        """
        if task_name not in self._handlers:
            raise ValueError(f"No handler registered for task: {task_name}")
        
        # Create task
        task_id = task_id or str(uuid.uuid4())[:8]
        task = Task(
            id=task_id,
            name=task_name,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            params=params
        )
        
        # Store task
        self._store_task(task)
        
        # Execute in background
        asyncio.create_task(self._execute_task(task))
        
        logger.info(f"Task submitted: {task_id} ({task_name})")
        return task_id
    
    async def _execute_task(self, task: Task):
        """Execute a task in background"""
        try:
            # Update status to running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            self._store_task(task)
            
            # Get handler
            handler = self._handlers[task.name]
            
            # Create progress callback
            def update_progress(progress: int, message: str = None):
                task.progress = progress
                if message:
                    task.result = task.result or {}
                    task.result['progress_message'] = message
                self._store_task(task)
            
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task.params, update_progress)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._executor,
                    lambda: handler(task.params, update_progress)
                )
            
            # Update status to completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.progress = 100
            task.result = result
            self._store_task(task)
            
            logger.info(f"Task completed: {task.id}")
            
        except Exception as e:
            # Update status to failed
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now().isoformat()
            task.error = str(e)
            self._store_task(task)
            
            logger.error(f"Task failed: {task.id} - {e}")
    
    def _store_task(self, task: Task):
        """Store task in storage backend"""
        task_dict = task.to_dict()
        
        if self.redis_client:
            try:
                key = f"task:{task.id}"
                self.redis_client.hset(key, mapping={
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) if v is not None else ""
                    for k, v in task_dict.items()
                })
                self.redis_client.expire(key, 86400)  # 24h TTL
            except Exception as e:
                logger.warning(f"Redis store error: {e}")
                self._tasks[task.id] = task
        else:
            self._tasks[task.id] = task
    
    def _load_task(self, task_id: str) -> Optional[Task]:
        """Load task from storage backend"""
        if self.redis_client:
            try:
                key = f"task:{task_id}"
                data = self.redis_client.hgetall(key)
                if data:
                    # Parse JSON fields
                    for field in ['result', 'params']:
                        if data.get(field):
                            try:
                                data[field] = json.loads(data[field])
                            except:
                                pass
                    data['progress'] = int(data.get('progress', 0))
                    return Task(**data)
            except Exception as e:
                logger.warning(f"Redis load error: {e}")
        
        return self._tasks.get(task_id)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task status and result"""
        task = self._load_task(task_id)
        if task:
            return task.to_dict()
        return None
    
    def get_all_tasks(self, limit: int = 100) -> List[Dict]:
        """Get all recent tasks"""
        tasks = []
        
        if self.redis_client:
            try:
                keys = self.redis_client.keys("task:*")[:limit]
                for key in keys:
                    task_id = key.replace("task:", "")
                    task = self._load_task(task_id)
                    if task:
                        tasks.append(task.to_dict())
            except Exception as e:
                logger.warning(f"Redis list error: {e}")
        
        # Add in-memory tasks
        for task in list(self._tasks.values())[-limit:]:
            if task.to_dict() not in tasks:
                tasks.append(task.to_dict())
        
        # Sort by created_at
        tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return tasks[:limit]
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        task = self._load_task(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now().isoformat()
            self._store_task(task)
            
            # Cancel running coroutine if exists
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                del self._running_tasks[task_id]
            
            return True
        return False


# Global task queue instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get global task queue instance"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(use_redis=True)
    return _task_queue


# ============================================
# Pre-defined task handlers
# ============================================

async def handle_full_pipeline(params: Dict, progress_callback: Callable):
    """
    Full pipeline handler: Crawl → ETL → Topic → Index
    """
    from app.services.crawler.pipeline import CrawlerPipeline
    from app.services.topic.model import TopicModel
    from app.services.etl.ner_extractor import get_ner_extractor
    
    url = params.get('url')
    mode = params.get('mode', 'max')
    train_topics = params.get('train_topics', True)
    extract_ner = params.get('extract_ner', True)
    
    result = {
        'url': url,
        'stages': {}
    }
    
    # Stage 1: Crawl
    progress_callback(10, "Crawling website...")
    crawler = CrawlerPipeline()
    
    crawl_params = {
        'quick': {'max_pages': 50, 'max_depth': 2},
        'max': {'max_pages': 5000, 'max_depth': 5},
        'full': {'max_pages': 10000, 'max_depth': 10},
    }.get(mode, {'max_pages': 100, 'max_depth': 3})
    
    crawl_result = await crawler.run(
        source_type='web',
        source=url,
        clean=True,
        dedupe=True,
        follow_links=True,
        **crawl_params
    )
    
    documents = crawl_result.get('documents', [])
    result['stages']['crawl'] = {
        'status': 'completed',
        'documents': len(documents)
    }
    
    if not documents:
        progress_callback(100, "No documents found")
        result['status'] = 'no_data'
        return result
    
    progress_callback(30, f"Crawled {len(documents)} documents")
    
    # Stage 2: NER Extraction
    if extract_ner:
        progress_callback(40, "Extracting named entities...")
        ner = get_ner_extractor()
        
        all_entities = {
            'PERSON': [],
            'ORG': [],
            'LOCATION': [],
            'DATE': []
        }
        
        for doc in documents:
            text = doc.get('content', '') or doc.get('cleaned_content', '')
            entities = ner.extract(text)
            
            for ent_type, ents in entities.items():
                if ent_type in all_entities:
                    all_entities[ent_type].extend([e['text'] for e in ents])
            
            # Store entities in document
            doc['entities'] = entities
        
        # Get unique top entities
        entity_summary = {}
        for ent_type, ents in all_entities.items():
            from collections import Counter
            counts = Counter(ents).most_common(20)
            entity_summary[ent_type] = [{'text': t, 'count': c} for t, c in counts]
        
        result['stages']['ner'] = {
            'status': 'completed',
            'entities': entity_summary
        }
        
        progress_callback(50, "NER extraction completed")
    
    # Stage 3: Topic Modeling
    if train_topics and len(documents) >= 10:
        progress_callback(60, "Training topic model...")
        
        # Extract texts
        texts = []
        for doc in documents:
            content = doc.get('content', '') or doc.get('cleaned_content', '')
            title = doc.get('metadata', {}).get('title', '') or doc.get('title', '')
            text = f"{title} {content}".strip()
            if text and len(text) > 50:
                texts.append(text[:3000])
        
        if len(texts) >= 10:
            try:
                topic_model = TopicModel()
                topics, probs = topic_model.fit(texts)
                
                topic_info = topic_model.get_topic_info()
                num_topics = len(topic_info.get('topics', []))
                
                # Save model
                from datetime import datetime
                from urllib.parse import urlparse
                host = urlparse(url).netloc.replace(':', '_').replace('/', '_')
                model_name = f"pipeline_{host}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                model_path = topic_model.save(model_name)
                
                result['stages']['topics'] = {
                    'status': 'completed',
                    'num_topics': num_topics,
                    'model_path': model_path
                }
                
                progress_callback(80, f"Found {num_topics} topics")
                
            except Exception as e:
                result['stages']['topics'] = {
                    'status': 'error',
                    'error': str(e)
                }
                logger.error(f"Topic modeling error: {e}")
        else:
            result['stages']['topics'] = {
                'status': 'skipped',
                'reason': f'Insufficient documents ({len(texts)} < 10)'
            }
    
    # Stage 4: Save to database
    progress_callback(90, "Saving to database...")
    try:
        from app.core.database import SessionLocal
        from app.models.model_article import Article
        from app.models.model_source import Source
        from urllib.parse import urlparse
        
        db = SessionLocal()
        try:
            # Get or create source
            domain = urlparse(url).netloc
            source = db.query(Source).filter(Source.domain == domain).first()
            if not source:
                source = Source(name=domain, domain=domain, url=url)
                db.add(source)
                db.commit()
            
            # Save articles
            saved = 0
            for doc in documents:
                doc_url = doc.get('url', '')
                if not doc_url:
                    continue
                
                # Check duplicate
                existing = db.query(Article).filter(Article.url == doc_url).first()
                if existing:
                    continue
                
                article = Article(
                    title=doc.get('metadata', {}).get('title', '') or doc.get('title', 'Untitled'),
                    content=doc.get('content', '') or doc.get('cleaned_content', ''),
                    url=doc_url,
                    source_id=source.id
                )
                db.add(article)
                saved += 1
            
            db.commit()
            result['stages']['database'] = {
                'status': 'completed',
                'saved': saved
            }
        finally:
            db.close()
            
    except Exception as e:
        result['stages']['database'] = {
            'status': 'error',
            'error': str(e)
        }
        logger.error(f"Database save error: {e}")
    
    progress_callback(100, "Pipeline completed")
    result['status'] = 'completed'
    
    return result


# Register handlers on module load
def init_task_handlers():
    """Initialize pre-defined task handlers"""
    queue = get_task_queue()
    queue.register_handler('full_pipeline', handle_full_pipeline)
    logger.info("Task handlers initialized")
