# 📊 PIPELINE TỔNG QUAN - Hybrid Topic Modeling System

> FastAPI Service tại `http://localhost:7777` · PostgreSQL · BERTopic · OpenAI/OpenRouter LLM

---

## 1. 🌐 NGUỒN DATA ĐẦU VÀO

### 1.1 External API Chính (Social Media Crawler)

| Tham số | Giá trị |
|---------|---------|
| Base URL | `EXTERNAL_API_BASE_URL` (env, ví dụ `http://192.168.30.28:8548`) |
| Endpoint | `GET /api/v1/posts/by-type/{data_type}` |
| Phân trang | `?page=1&page_size=500&sort_by=id&order=desc` |

**Các `data_type` hỗ trợ:**

| data_type | Mô tả |
|-----------|-------|
| `facebook` | Bài viết Facebook |
| `threads` | Bài viết Threads |
| `tiktok` | Video/caption TikTok |
| `newspaper` | Bài báo điện tử |

Filter báo theo chủ đề:
```
GET /api/v1/posts/by-type-newspaper/{type}
type: economy | education | medical | politics | security | society | transportation
```

Response format:
```json
{
  "success": true,
  "data": [...],
  "metadata": { "total": 5000, "page": 1, "page_size": 500 }
}
```

---

### 1.2 AQICN API (Chất lượng không khí)

| Tham số | Giá trị |
|---------|---------|
| URL | `https://api.waqi.info` |
| File | `app/services/aqi_service.py` |
| Env | `AQICN_API_KEY` |
| Lưu vào | `air_quality_detail` |

---

### 1.3 Web Scraping - Thống kê Kinh tế

| Tham số | Giá trị |
|---------|---------|
| Source | `https://thongkehungyen.nso.gov.vn` |
| File | `app/services/universal_economic_extractor.py` |
| Lưu vào | `iip_detail`, `agri_production_detail`, `cpi_detail`, `retail_services_detail`, `investment_detail`, `budget_revenue_detail` |

---

### 1.4 World Bank API (Kinh tế vĩ mô - Free)

| Tham số | Giá trị |
|---------|---------|
| URL | `https://api.worldbank.org/v2/` |
| Auth | Không cần API key |
| Phạm vi | Cấp quốc gia (VN), yearly |

| Indicator | World Bank Code | Bảng đích |
|-----------|----------------|-----------|
| GDP Growth | `NY.GDP.MKTP.KD.ZG` | `grdp_detail` |
| CPI | `FP.CPI.TOTL.ZG` | `cpi_detail` |
| Exports | `NE.EXP.GNFS.ZS` | `export_detail` |
| FDI | `BX.KLT.DINV.CD.WD` | `investment_detail` |
| Industry | `NV.IND.TOTL.KD` | `iip_detail` |

---

### 1.5 Tài liệu nội bộ (Documents)

- `POST /api/fetch/document/internal` — Tài liệu nội bộ
- `POST /api/fetch/document/external` — Tài liệu bên ngoài
- File: `app/api/data_fetch_document.py`

---

## 2. 💾 LƯU TRỮ DATA

### 2.1 File System (Bước trung gian)

```
data/
├── raw/
│   ├── facebook/facebook_TIMESTAMP.json
│   ├── threads/threads_TIMESTAMP.json
│   ├── tiktok/tiktok_TIMESTAMP.json
│   └── newspaper/newspaper_TIMESTAMP.json
├── processed/
│   └── processed_{type}_TIMESTAMP.json
├── results/
├── cache/topicgpt/cache.json
└── models/session_abc123_TIMESTAMP/   ← BERTopic model
```

Cấu trúc file raw:
```json
{
  "data_type": "facebook",
  "source": "social",
  "fetched_at": "2026-06-03T14:30:22",
  "total_records": 1500,
  "unique_urls": 1498,
  "pages_processed": 3,
  "records": [...]
}
```

### 2.2 PostgreSQL Database

Kết nối: `postgresql://postgres:postgres@db:5432/postgres`

**Core tables:**
```
articles                      ← Tất cả bài viết (social + báo)
important_posts               ← Bài viết đặc biệt quan trọng
```

**Topic modeling tables:**
```
custom_topics                 ← Chủ đề tùy chỉnh (user-defined)
article_custom_topics         ← Mapping bài viết ↔ chủ đề
bertopic_discovered_topics    ← Topic tự động từ BERTopic
article_bertopic_topics       ← Mapping bài viết ↔ BERTopic topic
bertopic_training_sessions    ← Lịch sử train model
keyword_stats                 ← Thống kê từ khóa
```

**Classification tables:**
```
fields                        ← Danh sách lĩnh vực
article_field_classification  ← Phân loại bài viết → lĩnh vực
field_statistics              ← Thống kê theo lĩnh vực
sentiment_analysis            ← Kết quả sentiment
```

**Economic detail tables:**
```
grdp_detail                   ← GRDP (GDP tỉnh)
cpi_detail                    ← Chỉ số giá tiêu dùng
iip_detail / pii_detail       ← Sản xuất công nghiệp
fdi_detail                    ← Thu hút FDI
digital_economy_detail        ← Kinh tế số
digital_transformation_detail ← Chuyển đổi số
investment_detail             ← Đầu tư
budget_revenue_detail         ← Thu ngân sách
agri_production_detail        ← Nông nghiệp
retail_services_detail        ← Bán lẻ, dịch vụ
air_quality_detail            ← Chất lượng không khí
```

**Social indicator tables (9 lĩnh vực):**
```
health_statistics             ← Y tế
highschool_graduation         ← Giáo dục
tvet_employment               ← Đào tạo nghề
cadre_statistics              ← Cán bộ, công chức
culture_lifestyle             ← Văn hóa - Đời sống
security                      ← An ninh - Trật tự
par_index                     ← Cải cách hành chính
sipas                         ← Chỉ số SIPAS
economic_statistics           ← Thống kê kinh tế
political_statistics          ← Thống kê chính trị
```

---

## 3. ⚙️ QUY TRÌNH XỬ LÝ ETL

### Luồng tổng quát

```
[External API]
     │ GET /api/v1/posts/by-type/{type}
     ▼
[STEP 1: FETCH]
  POST /api/fetch/social/{data_type}
  Script: fetch_facebook_data.py | fetch_all_social_data.py
  Save → data/raw/{type}/{type}_TIMESTAMP.json
     │
     ▼
[STEP 2: PROCESS]
  POST /api/process/social/{data_type}
  Service: app/services/etl/data_pipeline.py
  - Auto-detect data_type từ records
  - Chạy processor tương ứng (facebook/tiktok/threads/newspaper)
  - TextCleaner: xóa HTML, ký tự đặc biệt
  - Deduplicate theo URL (3 levels: exact → fuzzy hash → semantic)
  Save → data/processed/processed_{type}_TIMESTAMP.json
     │
     ▼
[STEP 3: LOAD TO DB]
  POST /api/process/social/load-to-db
  Service: DataPipelineService.load_processed_data_to_db()
  - Check duplicate theo URL
  - INSERT mới / UPDATE nếu đã tồn tại
  - Lưu vào bảng articles
     │
     ▼
[STEP 4+: CLASSIFY & ANALYZE]
  POST /api/orchestrator/run-pipeline
```

### ETL Processors

File: `app/services/etl/processors/`

| Processor | Data Type | Đặc điểm |
|-----------|-----------|----------|
| `FacebookProcessor` | facebook | reactions, account_info, post_id |
| `TikTokProcessor` | tiktok | views, video metadata |
| `ThreadsProcessor` | threads | thread structure |
| `NewspaperProcessor` | newspaper | category, published_date, domain |

Tất cả output cùng schema → load vào `articles`.

---

## 4. 🤖 API PHÂN LOẠI TOPIC

### 4.1 Orchestrator

```
POST /api/orchestrator/run-pipeline
Body: {
  "mode": "full" | "quick" | "custom",
  "sync_data": true,
  "classify_topics": true,
  "analyze_sentiment": true,
  "calculate_statistics": true,
  "regenerate_keywords": true,
  "train_bertopic": true,
  "limit": null,
  "background": false
}
```

| mode | Mô tả |
|------|-------|
| `full` | Sync + classify + sentiment + stats + train BERTopic |
| `quick` | Chỉ classify + sentiment + keywords |
| `custom` | Tự chọn từng bước |

### 4.2 Topic Service (BERTopic + TopicGPT)

Prefix: `/topic-service/`

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/topic-service/ingest` | POST | Nạp articles vào model |
| `/topic-service/train` | POST | Train BERTopic standard |
| `/topic-service/hybrid-train` | POST | Train BERTopic + GPT labels |
| `/topic-service/topics` | GET | Danh sách topics đã discover |
| `/topic-service/categories` | GET | Danh sách categories |
| `/topic-service/status` | GET | Trạng thái model |

**BERTopic Training Flow** (`app/services/topic/bertopic_trainer.py`):
```
1. Load articles từ DB (WHERE LENGTH(content) > 100, ORDER BY created_at DESC)
2. Combine: doc = title + "\n" + content
3. Khởi tạo model:
   - embedding_model: paraphrase-multilingual-MiniLM-L12-v2
   - tokenizer: Underthesea (Vietnamese NLP)
   - min_topic_size: 10 (configurable)
4. Train BERTopic → auto-discover topics
5. Save → bertopic_discovered_topics + article_bertopic_topics
6. (Optional) TopicGPT: generate natural language labels
7. (Optional) GPT classify short docs (<200 chars) vào discovered topics
```

**TopicGPT Service** (`app/services/topic/topicgpt_service.py`):

| Method | Mô tả |
|--------|-------|
| `generate_topic_label()` | Tạo tên topic từ keywords (LLM) |
| `generate_topic_description()` | Mô tả chi tiết topic |
| `refine_topics()` | Gợi ý gộp topic tương tự |
| `categorize_content()` | Phân loại content vào 13 categories |
| `extract_keywords_and_tags()` | Trích xuất từ khóa + hashtag |
| `summarize_content()` | Tóm tắt nội dung |

LLM config TopicGPT:
```
api   = TOPICGPT_API   (env, default: "openai")
model = TOPICGPT_MODEL (env, default: "gpt-4o-mini")
cache = data/cache/topicgpt/cache.json  (tiết kiệm cost)
```

### 4.3 Custom Topics

Prefix: `/api/v1/custom-topics/`

| Endpoint | Mô tả |
|----------|-------|
| `GET /` | Danh sách custom topics |
| `POST /` | Tạo topic mới với keywords |
| `PUT /{id}` | Sửa topic |
| `DELETE /{id}` | Xóa topic |
| `POST /{id}/classify` | Phân loại articles theo topic |
| `POST /classify-all` | Phân loại tất cả articles |

### 4.4 Field Classification (Phân loại Lĩnh vực)

Prefix: `/api/v1/field-classification/`

File: `app/services/classification/field_classifier.py`

**2 phương pháp auto-cascade:**

```
Bài viết
   │
   ├─ [1] Keyword Matching
   │       - Tìm từ khóa trong title + content + summary
   │       - Score = số từ khóa match được
   │       - confidence = min(1.0, score / 5.0)
   │
   └─ [2] LLM Fallback (nếu keyword không match)
           - Model: gpt-3.5-turbo (OpenAI)
           - Prompt: danh sách lĩnh vực + nội dung bài (max 2000 chars)
           - Response: {"field_id": N, "confidence": 0.9, "reason": "..."}
```

---

## 5. 🔬 API EXTRACT LLM - TRÍCH XUẤT CHỈ SỐ

### 5.1 LLM Extraction Flow

```
POST /api/llm/extract-{domain}
         │
         ▼
SELECT * FROM important_posts
WHERE content ILIKE '%keyword%'
LIMIT 50
         │
         ▼
For each post:
  Build prompt (field definitions + extraction rules + content max 4000 chars)
         │
         ▼
Call OpenRouter API:
  URL:   https://openrouter.ai/api/v1/chat/completions
  Model: openai/gpt-4o-mini
  Temp:  0.1
  Tokens: 3000
  Retry: 3 lần | Delay: 1s | Timeout: 60s
         │
         ▼
Parse JSON response → Validate → Transform
         │
         ▼
INSERT INTO {target_table}
(province, source_post_id, source_url, period, year, quarter, month,
 data_source, extraction_metadata, notes, ...)
```

### 5.2 Các Endpoint Extract theo Lĩnh vực

| Endpoint (POST) | Lĩnh vực | Bảng đích |
|-----------------|----------|-----------|
| `/api/llm/extract-politics` | Xây dựng Đảng | `political_statistics` |
| `/api/llm/extract-medical` | Y tế | `health_statistics` |
| `/api/llm/extract-education` | Giáo dục | `highschool_graduation` |
| `/api/llm/extract-security` | An ninh | `security` |
| `/api/llm/extract-society` | Văn hóa - XH | `culture_lifestyle` |
| `/api/llm/extract-transportation` | Giao thông | transport table |
| `/api/llm/extract-statistics` | Kinh tế & CT | `economic_statistics`, `political_statistics` |
| `/api/llm/extract-digital-economy` | Kinh tế số | `digital_economy_detail` |
| `/api/llm/extract-fdi` | FDI | `fdi_detail` |
| `/api/llm/extract-digital-transformation` | Chuyển đổi số | `digital_transformation_detail` |
| `/api/llm/extract-pii` | SX Công nghiệp | `pii_detail` |

**Mỗi domain có 2 mode:**
- `POST /api/llm/extract-{domain}` → **async** (202, background)
- `POST /api/llm/extract-{domain}/sync` → **sync** (200, chờ kết quả)

**LLM Config:**
```python
LLM_MODEL           = "openai/gpt-4o-mini" (qua OpenRouter)
TEMPERATURE         = 0.1
MAX_TOKENS          = 3000
BATCH_SIZE          = 50 posts/run
DELAY_BETWEEN_CALLS = 1 second
MAX_RETRIES         = 3
TIMEOUT             = 60 seconds
CONTENT_LENGTH      = 4000 chars
```

**Chi phí ước tính (50 posts/batch):**

| Domain | Tokens/post | Cost/batch |
|--------|------------|-----------|
| Digital Economy | ~2000 | ~$0.10 |
| FDI | ~2500 | ~$0.12 |
| Digital Transformation | ~2500 | ~$0.12 |
| PII | ~3000 | ~$0.15 |

### 5.3 Social Indicators API

Prefix: `/api/social-indicators/`

Extract chỉ số từ `important_posts` → fill 27 bảng detail.

### 5.4 Economic Indicators API

Prefix: `/api/v1/economic-indicators/`

| Endpoint | Mô tả |
|----------|-------|
| `GET /` | Danh sách indicators |
| `POST /batch/import` | Import batch |
| `POST /batch/fill-missing` | Điền data thiếu |
| `POST /{id}/fill-missing` | Điền 1 indicator |
| `POST /generate-summaries` | Summary bằng LLM |
| `POST /generate-analyses` | Phân tích bằng LLM |

---

## 6. 📡 CÁC SERVICE KHÁC

### 6.1 Sync Service

Prefix: `/api/v1/sync/`

| Endpoint | Mô tả |
|----------|-------|
| `GET /db-stats` | Thống kê tổng quan DB |
| `POST /sync-articles` | Đồng bộ articles |
| `GET /health` | Health check |

### 6.2 Superset Sync (Dashboard)

Prefix: `/superset/`

| Endpoint | Mô tả |
|----------|-------|
| `GET /superset/status` | Trạng thái |
| `POST /superset/update-all` | Sync tất cả |
| `POST /superset/update-field-sentiments` | Sync sentiment |
| `POST /superset/update-field-summaries` | Sync summary |

### 6.3 Orchestrator Status

```
GET /api/orchestrator/status
→ {
    "totals": { articles, topics, classifications, sentiments, keywords },
    "pending": { unclassified_articles, articles_no_sentiment },
    "needs_action": true/false
  }
```

---

## 7. ⚙️ ENV CONFIG

```bash
# Database
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

# External API (crawler backend)
EXTERNAL_API_BASE_URL=http://192.168.30.28:8548
LOCAL_API_BASE_URL=http://localhost:7777

# LLM APIs
OPENAI_API_KEY=sk-...          # OpenAI (field classification, TopicGPT)
OPENROUTER_API_KEY=sk-or-...   # OpenRouter (LLM extraction)

# TopicGPT
TOPICGPT_API=openai
TOPICGPT_MODEL=gpt-4o-mini

# Air Quality
AQICN_API_KEY=...
```

---

## 8. 🐳 DEPLOYMENT

```bash
# Start
docker-compose up -d

# Verify
bash verify_installation.sh

# DB migration
alembic upgrade head
```

Services: `app` (FastAPI port 7777) · `db` (PostgreSQL 15)

---

## 9. 📈 LUỒNG TỔNG HỢP

```
[External Crawler API] ──GET /api/v1/posts/by-type/*──▶ Fetch
[AQICN API]            ──────────────────────────────▶ AQI Service
[Web Scraping]         ──────────────────────────────▶ Economic Extractor
[World Bank API]       ──────────────────────────────▶ Macro Indicators
                                    │
                          data/raw/{type}/*.json
                                    │
                       Process + Clean + Deduplicate
                                    │
                       data/processed/*.json
                                    │
                       Load ──▶ articles (PostgreSQL)
                                    │
              ┌─────────────────────┼──────────────────────┐
              ▼                     ▼                       ▼
    [Field Classify]       [BERTopic Train]        [LLM Extract]
    keyword → GPT3.5       BERTopic model          important_posts
    article_field_         bertopic_discovered     ──▶ detail tables
    classification         _topics                 (fdi, grdp, cpi...)
              │
              ▼
    [Sentiment Analysis]
              │
              ▼
    [Stats + Keywords]
              │
              ▼
    [Superset Dashboard]
```

---

*Updated: 2026-06-03 | v2.0 | FastAPI Topic Modeling Pipeline*
