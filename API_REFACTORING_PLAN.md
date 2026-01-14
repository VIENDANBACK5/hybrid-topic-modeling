# Kế hoạch tối ưu API Endpoints (71 → ~30 endpoints)

## 📊 Hiện trạng
- **71 endpoints** - quá nhiều, khó quản lý
- Nhiều endpoints làm việc tương tự nhau
- Phân tán ở nhiều prefix khác nhau

---

## 🎯 Đề xuất gộp endpoints

### 1. **FETCH APIs (7→3 endpoints)** ⭐ Ưu tiên cao

#### Hiện tại:
```
POST /api/fetch/facebook
POST /api/fetch/newspaper  
POST /api/fetch/threads
POST /api/fetch/tiktok
POST /api/fetch/all
GET  /api/fetch/status
GET  /api/fetch/files/{data_type}
```

#### ✅ Sau khi gộp:
```python
# GỘP THÀNH 1 ENDPOINT DUY NHẤT
POST /api/fetch
Body: {
    "sources": ["facebook", "newspaper", "threads", "tiktok"],  # hoặc ["all"]
    "params": {...}  # params riêng cho từng source
}
Response: {
    "status": "success",
    "results": {
        "facebook": {...},
        "newspaper": {...}
    }
}

GET /api/fetch/status?source=facebook  # Optional filter
GET /api/fetch/files/{data_type}  # Giữ nguyên
```

**Lợi ích:** 
- Giảm từ 7→3 endpoints
- Linh hoạt fetch 1 hoặc nhiều source cùng lúc
- Code dễ maintain hơn

---

### 2. **PROCESS APIs (8→3 endpoints)** ⭐ Ưu tiên cao

#### Hiện tại:
```
POST /api/process/facebook
POST /api/process/newspaper
POST /api/process/threads
POST /api/process/tiktok
POST /api/process/all
POST /api/process/load-to-db
GET  /api/process/status
GET  /api/process/files/{data_type}
```

#### ✅ Sau khi gộp:
```python
# GỘP THÀNH 1 ENDPOINT
POST /api/process
Body: {
    "sources": ["facebook", "newspaper"],  # hoặc ["all"]
    "action": "process",  # hoặc "load-to-db" hoặc "process-and-load"
    "params": {...}
}

GET /api/process/status?source=facebook
GET /api/process/files/{data_type}  # Giữ nguyên
```

**Lợi ích:**
- Giảm từ 8→3 endpoints  
- Xử lý pipeline linh hoạt hơn
- Dễ extend thêm source mới

---

### 3. **SUPERSET APIs (4→2 endpoints)** 

#### Hiện tại:
```
GET  /superset/status
POST /superset/update-all
POST /superset/update-field-sentiments
POST /superset/update-field-summaries
```

#### ✅ Sau khi gộp:
```python
GET  /superset/status  # Giữ nguyên

POST /superset/sync
Body: {
    "targets": ["field-sentiments", "field-summaries"],  # hoặc ["all"]
    "force": false
}
```

**Lợi ích:**
- Giảm từ 4→2 endpoints
- Đồng bộ linh hoạt

---

### 4. **TOPIC SERVICE (7→4 endpoints)**

#### Hiện tại:
```
POST /topic-service/ingest
POST /topic-service/train
POST /topic-service/hybrid-train
GET  /topic-service/topics
GET  /topic-service/categories
GET  /topic-service/status
GET  /topic-service/training-recommendation
```

#### ✅ Sau khi gộp:
```python
# GỘP train endpoints
POST /topic-service/train
Body: {
    "mode": "standard" | "hybrid",  # gộp train và hybrid-train
    "params": {...}
}

POST /topic-service/ingest  # Giữ nguyên
GET  /topic-service/metadata  # GỘP topics, categories, training-recommendation
GET  /topic-service/status  # Giữ nguyên
```

**Lợi ích:**
- Giảm từ 7→4 endpoints
- Logic train gọn hơn

---

### 5. **ECONOMIC INDICATORS (10→6 endpoints)**

#### Hiện tại:
```
GET  /api/v1/economic-indicators/
POST /api/v1/economic-indicators/batch/import
POST /api/v1/economic-indicators/batch/fill-missing
POST /api/v1/economic-indicators/{id}/fill-missing
POST /api/v1/economic-indicators/generate-summaries
POST /api/v1/economic-indicators/generate-analyses
...
```

#### ✅ Sau khi gộp:
```python
GET  /api/v1/economic-indicators/  # Giữ nguyên

# GỘP batch operations
POST /api/v1/economic-indicators/batch
Body: {
    "action": "import" | "fill-missing" | "generate-summaries" | "generate-analyses",
    "data": [...]
}

# GỘP single operations  
POST /api/v1/economic-indicators/{id}/actions
Body: {
    "action": "fill-missing" | "generate-summary" | "generate-analysis"
}
```

**Lợi ích:**
- Giảm từ 10→6 endpoints
- Batch operations gọn gàng

---

### 6. **CUSTOM TOPICS & FIELDS - GIỮ NGUYÊN**
- Các endpoints này đã được thiết kế RESTful tốt
- Không nên gộp vì mỗi endpoint có logic riêng biệt

---

## 📊 Tổng kết

| Group | Trước | Sau | Giảm |
|-------|-------|-----|------|
| Fetch | 7 | 3 | -4 |
| Process | 8 | 3 | -5 |
| Superset | 4 | 2 | -2 |
| Topic Service | 7 | 4 | -3 |
| Economic | 10 | 6 | -4 |
| **Tổng cộng** | **71** | **~48** | **-23** |

**Giảm ~32% số lượng endpoints!**

---

## 🚀 Kế hoạch triển khai

### Phase 1: Quick wins (1-2 ngày)
1. ✅ Gộp FETCH APIs (7→3)
2. ✅ Gộp PROCESS APIs (8→3)  
3. ✅ Gộp SUPERSET APIs (4→2)

### Phase 2: Medium changes (2-3 ngày)
4. ✅ Gộp TOPIC SERVICE (7→4)
5. ✅ Gộp ECONOMIC INDICATORS (10→6)

### Phase 3: Backward compatibility
6. ⚠️ Giữ old endpoints với deprecation warning trong 1 tháng
7. 📝 Update documentation
8. 🔔 Thông báo breaking changes

---

## 💻 Code example - Gộp Fetch API

### File: `app/api/unified_fetch_api.py` (MỚI)

```python
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/fetch", tags=["Unified Fetch"])

class FetchRequest(BaseModel):
    sources: List[str]  # ["facebook", "newspaper", "threads", "tiktok"] hoặc ["all"]
    params: Optional[dict] = {}
    
class FetchResponse(BaseModel):
    status: str
    results: dict
    errors: Optional[dict] = {}

@router.post("/", response_model=FetchResponse)
async def unified_fetch(request: FetchRequest):
    """
    🔥 UNIFIED FETCH ENDPOINT - Thay thế 5 endpoints cũ
    
    Fetch data from multiple sources in one call:
    - facebook, newspaper, threads, tiktok
    - or use "all" to fetch from all sources
    
    Example:
    ```json
    {
        "sources": ["facebook", "newspaper"],
        "params": {
            "limit": 100
        }
    }
    ```
    """
    results = {}
    errors = {}
    
    sources = request.sources
    if "all" in sources:
        sources = ["facebook", "newspaper", "threads", "tiktok"]
    
    for source in sources:
        try:
            if source == "facebook":
                result = await fetch_facebook(request.params)
            elif source == "newspaper":
                result = await fetch_newspaper(request.params)
            elif source == "threads":
                result = await fetch_threads(request.params)
            elif source == "tiktok":
                result = await fetch_tiktok(request.params)
            else:
                errors[source] = f"Unknown source: {source}"
                continue
                
            results[source] = result
        except Exception as e:
            errors[source] = str(e)
    
    return FetchResponse(
        status="success" if results else "failed",
        results=results,
        errors=errors if errors else None
    )

@router.get("/status")
async def fetch_status(source: Optional[str] = None):
    """Get fetch status, optionally filtered by source"""
    # Implementation...
    pass
```

### Deprecate old endpoints:

```python
# File: app/api/data_fetch_api.py

@router.post("/facebook")
@deprecated(version="2.0", reason="Use POST /api/fetch with sources=['facebook']")
async def fetch_facebook_deprecated():
    """⚠️ DEPRECATED - Use unified fetch endpoint instead"""
    return await unified_fetch(FetchRequest(sources=["facebook"]))
```

---

## 🎯 Bạn muốn tôi:

1. ⚡ **Implement ngay Phase 1** (Fetch + Process APIs)?
2. 📝 **Tạo migration guide** cho frontend team?
3. 🔍 **Xem code hiện tại** để estimate effort?
4. 🚀 **Làm từng bước** và test kỹ từng endpoint?

Chọn option nào để tôi bắt đầu? 🚀
