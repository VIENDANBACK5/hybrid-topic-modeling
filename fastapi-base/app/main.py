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
from app.api.routers import dashboard, crawl, topics, sources, rag
from app.core.database import get_engine
from app.core.config import settings
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
        Pipeline MXH - Crawl → ETL → Topic Modeling API
            - Web/RSS/File/API Crawler
            - Topic Modeling với BERTopic Vietnamese
            - Dashboard & Analytics
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
    application.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)
    
    # Primary routes - no /api prefix (for frontend compatibility)
    application.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
    application.include_router(crawl.router, prefix="/crawl", tags=["Crawl"])
    application.include_router(topics.router, prefix="/topics", tags=["Topics"])
    application.include_router(sources.router, prefix="/sources", tags=["Sources"])
    application.include_router(rag.router, prefix="/rag", tags=["RAG"])
    
    # Secondary routes with /api prefix (includes all routers above + healthcheck)
    application.include_router(api_router, prefix="/api", tags=["API"])
    
    # Healthcheck at /api/healthcheck
    application.include_router(router, prefix=settings.API_PREFIX)
    
    application.add_exception_handler(CustomException, custom_error_handler)
    application.add_exception_handler(ValidationException, validation_exception_handler)
    application.add_exception_handler(Exception, fastapi_error_handler)

    return application


app = get_application()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=settings.DEBUG)
