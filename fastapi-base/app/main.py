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
from app.api.routers import topic_service, sync_service, custom_topics, field_classification, superset_sync, economic_indicators
from app.api import orchestrator, data_fetch_social, data_fetch_document, data_process_social, data_process_document, api_grdp_detail, api_economic_extraction, api_social_indicators, api_aqi, api_important_posts, api_statistics, api_xay_dung_dang, api_llm_extraction, api_digital_economy_detail, api_fdi_detail, api_digital_transformation_detail, api_pii_detail, api_iip, api_cpi, api_cadre_statistics, api_highschool_graduation, api_tvet_employment, api_health_statistics, api_culture_lifestyle, api_security, api_par_index, api_sipas
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
    
    # ============================================
    # ETL PIPELINE (Giai đoạn 1: Fetch → Process → Load)
    # ============================================
    
    # Data Fetch - Social Media & News (facebook, tiktok, threads, newspaper)
    application.include_router(data_fetch_social.router)
    
    # Data Fetch - Documents (internal, external)
    application.include_router(data_fetch_document.router)
    
    # Data Process - Social Media & News
    application.include_router(data_process_social.router)
    
    # Data Process - Documents (Internal/External)
    application.include_router(data_process_document.router)
    
    # ============================================
    # TOPIC MODELING
    # ============================================
    
    # Topic Service - Topic modeling API
    application.include_router(topic_service.router, prefix="/topic-service", tags=["Topic Service"])
    
    # Custom Topics - User-defined topics
    application.include_router(custom_topics.router)
    
    # ============================================
    # ECONOMIC DATA
    # ============================================
    
    # Economic Indicators
    application.include_router(economic_indicators.router)
    
    # Economic Data Extraction (Universal)
    application.include_router(api_economic_extraction.router)
    
    # GRDP Detail API
    application.include_router(api_grdp_detail.router)
    
    # Economic Indicator Detail APIs
    application.include_router(api_digital_economy_detail.router)
    application.include_router(api_fdi_detail.router)
    application.include_router(api_digital_transformation_detail.router)
    application.include_router(api_pii_detail.router)
    application.include_router(api_iip.router)
    application.include_router(api_cpi.router)
    
    # Education Detail APIs
    application.include_router(api_highschool_graduation.router)
    application.include_router(api_tvet_employment.router)
    
    # Social/Society Detail APIs  
    application.include_router(api_cadre_statistics.router)
    application.include_router(api_health_statistics.router)
    application.include_router(api_culture_lifestyle.router)
    application.include_router(api_security.router)
    
    # Public Administration APIs
    application.include_router(api_par_index.router)
    application.include_router(api_sipas.router)
    
    # ============================================
    # SOCIAL INDICATORS (9 Lĩnh vực × 3 Chỉ số = 27 bảng)
    # ============================================
    
    # Social Indicator Extraction - Extract từ articles fill vào 27 bảng detail
    application.include_router(api_social_indicators.router)
    
    # AQI Data - Air Quality Index from external API
    application.include_router(api_aqi.router)
    
    # ============================================
    # IMPORTANT POSTS (Bài viết quan trọng)
    # ============================================
    
    # Important Posts - Lưu trữ các bài viết đặc biệt quan trọng
    application.include_router(api_important_posts.router)
    
    # ============================================
    # STATISTICS (Thống kê từ bài viết quan trọng)
    # ============================================
    
    # Statistics API - Economic and Political statistics extracted from posts
    application.include_router(api_statistics.router, prefix="/api/statistics", tags=["Statistics"])
    
    # ============================================
    # LLM EXTRACTION (Pure LLM - Không dùng Regex)
    # ============================================
    
    # Unified LLM Extraction API - Tất cả lĩnh vực
    application.include_router(api_llm_extraction.router, prefix="/api/llm", tags=["LLM Extraction"])
    
    # ============================================
    # SERVICES & UTILITIES
    # ============================================
    
    # Sync Service - Data synchronization
    application.include_router(sync_service.router, prefix="/api/v1", tags=["Sync Service"])
    
    # Field Classification
    application.include_router(field_classification.router, prefix="/api/v1", tags=["Field Classification"])
    
    # Orchestrator - Workflow orchestration
    application.include_router(orchestrator.router)
    
    # Superset Sync - Dashboard data sync
    application.include_router(superset_sync.router, tags=["Superset Sync"])
    
    application.add_exception_handler(CustomException, custom_error_handler)
    application.add_exception_handler(ValidationException, validation_exception_handler)
    application.add_exception_handler(Exception, fastapi_error_handler)

    return application


app = get_application()

# Setup Prometheus metrics
setup_metrics(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=settings.DEBUG)
