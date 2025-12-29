"""
Database connection pool and batch operations
"""
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabasePool:
    """Database connection pool manager"""
    
    def __init__(
        self,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600
    ):
        """
        Args:
            pool_size: Number of connections to maintain
            max_overflow: Max connections beyond pool_size
            pool_timeout: Seconds to wait for connection
            pool_recycle: Recycle connections after N seconds
        """
        self.engine = create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Verify connections before using
            echo=settings.DEBUG
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(
            f"Database pool initialized: size={pool_size}, "
            f"max_overflow={max_overflow}"
        )
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session with context manager"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get database session (synchronous)"""
        return self.SessionLocal()
    
    def execute_batch(
        self,
        query: str,
        data: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        Execute batch insert/update
        
        Args:
            query: SQL query with named parameters
            data: List of parameter dicts
            batch_size: Number of records per batch
        
        Returns:
            Total number of records processed
        """
        total = 0
        session = self.get_session_sync()
        
        try:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                session.execute(text(query), batch)
                total += len(batch)
                
                if i % (batch_size * 10) == 0:
                    logger.info(f"Processed {total}/{len(data)} records")
            
            session.commit()
            logger.info(f"Batch operation completed: {total} records")
            return total
            
        except Exception as e:
            session.rollback()
            logger.error(f"Batch operation failed: {e}")
            raise
        finally:
            session.close()
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pool = self.engine.pool
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'total_connections': pool.size() + pool.overflow()
        }
    
    def close_all(self):
        """Close all connections"""
        self.engine.dispose()
        logger.info("All database connections closed")


# Global database pool instance
db_pool: Optional[DatabasePool] = None


def get_db_pool() -> DatabasePool:
    """Get or create database pool"""
    global db_pool
    if db_pool is None:
        db_pool = DatabasePool()
    return db_pool


def init_db_pool(
    pool_size: int = 10,
    max_overflow: int = 20
) -> DatabasePool:
    """Initialize database pool with custom settings"""
    global db_pool
    db_pool = DatabasePool(pool_size=pool_size, max_overflow=max_overflow)
    return db_pool
