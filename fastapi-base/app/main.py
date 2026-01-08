import logging
import logging.config

from fastapi.exceptions import ValidationException
import uvicorn
from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.router import router
from app.api import api_router
from app.models import Base
from app.api.routers import topic_service, sync_service, custom_topics, field_classification, superset_sync
from app.api import orchestrator, topicgpt_api, data_pipeline_api, data_fetch_api, data_process_api
from app.core.database import get_engine
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.core.metrics import setup_metrics
from app.utils.exception_handler import (
    CustomException,
    fastapi_error_handler,
    validation_exception_handler,
    custom_error_handler,
)

logging.config.fileConfig(settings.LOGGING_CONFIG_FILE, disable_existing_loggers=False)
# Lazy database initialization - only create tables when actually needed
try:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logging.warning(f"Could not initialize database: {e}. Database operations may fail.")


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        docs_url="/docs",
        redoc_url="/re-docs",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        description="""
        Topic Modeling Service
            - Nhận data từ BE khác (đã crawl & clean)
            - Topic Modeling với BERTopic Vietnamese
            - Lưu vào PostgreSQL
        """,
        debug=settings.DEBUG,
        swagger_ui_init_oauth={
            "clientId": settings.KEYCLOAK_CLIENT_ID,
            "scopes": {"openid": "OpenID Connect scope"},
        },
        swagger_ui_parameters={
            "docExpansion": "none",
        },
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Rate limiting middleware - 10 requests per minute per IP
    application.add_middleware(RateLimitMiddleware, calls=100, period=60)
    
    application.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)
    
    # Topic Service API
    application.include_router(topic_service.router, prefix="/topic-service", tags=["Topic Service"])
    
    # Sync Service API
    application.include_router(sync_service.router, prefix="/api/v1", tags=["Sync Service"])
    
    # Custom Topics
    application.include_router(custom_topics.router)
    
    # Field Classification
    application.include_router(field_classification.router, prefix="/api/v1", tags=["Field Classification"])
    
    # Superset Sync (Update all tables for Superset dashboards)
    application.include_router(superset_sync.router, tags=["Superset Sync"])
    
    # Orchestrator
    application.include_router(orchestrator.router)
    
    # TopicGPT
    application.include_router(topicgpt_api.router)
    
    # Data Pipeline
    application.include_router(data_pipeline_api.router)
    
    # Data Fetch (per data type)
    application.include_router(data_fetch_api.router)
    
    # Data Process (per data type)
    application.include_router(data_process_api.router)
    
    application.add_exception_handler(CustomException, custom_error_handler)
    application.add_exception_handler(ValidationException, validation_exception_handler)
    application.add_exception_handler(Exception, fastapi_error_handler)

    return application


app = get_application()

# Setup Prometheus metrics
setup_metrics(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=settings.DEBUG)
