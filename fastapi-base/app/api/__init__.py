from fastapi import APIRouter
from .routers import crawl, topics, dashboard, pipeline, sources, rag, orchestrator, hitl

api_router = APIRouter()

# ===== 8 API CHÍNH - FULL PIPELINE =====

# 1. CRAWL - Ném link vào, tự động crawl + lưu DB
api_router.include_router(crawl.router, prefix="/crawl", tags=["1️⃣ Crawl"])

# 2. TOPICS - Train model, gán topics, search
api_router.include_router(topics.router, prefix="/topics", tags=["2️⃣ Topics"])

# 3. DASHBOARD - Xem tổng quan tất cả
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["3️⃣ Dashboard"])

# 4. SOURCES - Quản lý nguồn thu thập (báo, mạng xã hội, diễn đàn...)
api_router.include_router(sources.router, prefix="/sources", tags=["4️⃣ Sources"])

# 5. RAG - Search & QA trên tài liệu (Hỏi đáp thông minh)
api_router.include_router(rag.router, prefix="/rag", tags=["5️⃣ RAG (Q&A)"])

# 6. ORCHESTRATOR - Full pipeline tự động: Crawl → ETL → NER → Topic → Index
api_router.include_router(orchestrator.router, prefix="/orchestrator", tags=["6️⃣ Orchestrator"])

# 7. HITL - Human-in-the-Loop: Review & approve labels
api_router.include_router(hitl.router, prefix="/hitl", tags=["7️⃣ HITL (Review)"])

# ===== LEGACY APIs (Ẩn trong docs) =====
# Các API cũ vẫn hoạt động nhưng không hiển thị trong docs chính
api_router.include_router(
    pipeline.router, 
    prefix="/pipeline", 
    tags=["[Legacy] Pipeline"],
    include_in_schema=False  # Ẩn khỏi docs
)
