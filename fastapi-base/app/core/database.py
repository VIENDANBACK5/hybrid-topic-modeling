from typing import Generator, Optional
from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine: Optional[object] = None
_SessionLocal: Optional[object] = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return _engine

def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

# For backward compatibility
engine = get_engine()
SessionLocal = get_session_local()


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
