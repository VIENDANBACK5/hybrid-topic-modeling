# LLM Auto-Fill System Architecture

## 🏗️ System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FastAPI Server                             │
│                      (http://localhost:7777)                        │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  API Layer    │         │  Extraction   │         │   Database    │
│               │         │    Services   │         │               │
├───────────────┤         ├───────────────┤         ├───────────────┤
│ api_llm_      │────────▶│ extract_      │────────▶│ digital_      │
│ extraction.py │         │ digital_      │         │ economy_      │
│               │         │ economy.py    │         │ detail        │
│               │         │               │         │               │
│ 8 Endpoints:  │         │ extract_      │────────▶│ fdi_detail    │
│ • async       │         │ fdi.py        │         │               │
│ • sync        │         │               │         │               │
│               │         │ extract_      │────────▶│ digital_      │
│ 4 Services:   │         │ digital_      │         │ transformation│
│ • DE          │         │ trans...py    │         │ _detail       │
│ • FDI         │         │               │         │               │
│ • DX          │         │ extract_      │────────▶│ pii_detail    │
│ • PII         │         │ pii.py        │         │               │
└───────────────┘         └───────────────┘         └───────────────┘
                                   │
                                   │
                          ┌────────▼────────┐
                          │   LLM Service   │
                          │  (OpenRouter)   │
                          │                 │
                          │  GPT-4o-mini    │
                          └─────────────────┘
```

## 📊 Data Flow

```
┌──────────────────┐
│ important_posts  │  ◀──  Source table (all news posts)
└────────┬─────────┘
         │
         │ Filter by keywords
         ▼
┌──────────────────┐
│  Filtered Posts  │
│                  │
│ • Kinh tế số     │
│ • FDI            │
│ • Chuyển đổi số  │
│ • Công nghiệp    │
└────────┬─────────┘
         │
         │ Batch Processing (50 posts/batch)
         ▼
┌──────────────────┐
│  LLM Extraction  │  ◀──  Prompt Engineering
│                  │       JSON Response Parsing
│ Model: GPT-4o-   │       Data Validation
│        mini       │
└────────┬─────────┘
         │
         │ Transform & Validate
         ▼
┌──────────────────────────────────────────────┐
│           Target Tables (4 tables)           │
│                                              │
│  ┌──────────────────┐  ┌─────────────────┐  │
│  │ digital_economy_ │  │   fdi_detail    │  │
│  │     detail       │  │                 │  │
│  │                  │  │ • Vốn đăng ký   │  │
│  │ • GDP KT số      │  │ • Giải ngân     │  │
│  │ • TMĐT revenue   │  │ • Dự án         │  │
│  │ • Thanh toán ĐT  │  │ • Phân theo     │  │
│  │ • Startup        │  │   ngành/quốc gia│  │
│  └──────────────────┘  └─────────────────┘  │
│                                              │
│  ┌──────────────────┐  ┌─────────────────┐  │
│  │ digital_trans    │  │   pii_detail    │  │
│  │ formation_detail │  │                 │  │
│  │                  │  │ • Chỉ số IIP    │  │
│  │ • Chỉ số CĐS     │  │ • Giá trị SX    │  │
│  │ • E-gov          │  │ • Các ngành CN  │  │
│  │ • Dịch vụ công   │  │ • Năng suất     │  │
│  │ • Cloud, AI, IoT │  │ • Sản lượng     │  │
│  └──────────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────┘
```

## 🔄 Extraction Process Flow

```
Step 1: Trigger Extraction
    │
    ├─ Option A: API Call (async)
    │   POST /llm-extraction/extract-{service}
    │   → Returns 202 Accepted
    │   → Runs in background
    │
    ├─ Option B: API Call (sync)
    │   POST /llm-extraction/extract-{service}/sync
    │   → Returns 200 OK with results
    │   → Blocks until complete
    │
    └─ Option C: Direct Script
        python call_llm/extract_{service}.py

Step 2: Query Database
    │
    ├─ SELECT posts FROM important_posts
    ├─ WHERE content ILIKE '%keywords%'
    └─ LIMIT batch_size

Step 3: For each post
    │
    ├─ Build LLM prompt with:
    │   • Field definitions
    │   • Extraction rules
    │   • Post content
    │
    ├─ Call LLM API
    │   • URL: openrouter.ai/api/v1/chat/completions
    │   • Model: gpt-4o-mini
    │   • Temperature: 0.1
    │
    ├─ Parse JSON response
    │   • Extract fields
    │   • Validate data types
    │   • Transform values
    │
    └─ Save to database
        INSERT INTO {target_table} (...)

Step 4: Return Results
    │
    ├─ Success count
    ├─ Total processed
    └─ Timestamp
```

## 🎯 Service Comparison Matrix

| Feature | Digital Economy | FDI | Digital Transformation | PII |
|---------|----------------|-----|----------------------|-----|
| **Target Table** | digital_economy_detail | fdi_detail | digital_transformation_detail | pii_detail |
| **Main Focus** | Tech economy | Foreign investment | Digital govt/business | Industrial production |
| **Key Metrics** | 30+ fields | 40+ fields | 35+ fields | 45+ fields |
| **Complexity** | Medium | High | High | Very High |
| **Typical Match Rate** | ~10-20% | ~5-15% | ~15-25% | ~20-30% |
| **LLM Tokens/Post** | ~2000 | ~2500 | ~2500 | ~3000 |

## 📈 Performance Metrics

### Expected Performance (per batch of 50 posts):

| Metric | Digital Economy | FDI | Digital Transformation | PII |
|--------|----------------|-----|----------------------|-----|
| **Posts matched** | 5-10 | 3-8 | 8-12 | 10-15 |
| **Extraction rate** | 60-80% | 50-70% | 70-85% | 75-90% |
| **Time per post** | 2-3 sec | 2-3 sec | 2-3 sec | 2-4 sec |
| **Total batch time** | 2-3 min | 2-3 min | 2-3 min | 3-4 min |
| **API cost/batch** | ~$0.10 | ~$0.12 | ~$0.12 | ~$0.15 |

## 🔧 Configuration Parameters

```python
# LLM Configuration
LLM_MODEL = "openai/gpt-4o-mini"
TEMPERATURE = 0.1              # Low = more deterministic
MAX_TOKENS = 3000              # Response length limit

# Processing Configuration
BATCH_SIZE = 50                # Posts per run
DELAY_BETWEEN_CALLS = 1        # Seconds (rate limiting)
MAX_RETRIES = 3                # LLM call retries
TIMEOUT = 60                   # Seconds per LLM call

# Content Processing
CONTENT_LENGTH = 4000          # Characters sent to LLM
```

## 📊 API Endpoint Routes

```
/llm-extraction/
│
├── /extract-digital-economy
│   ├── POST (async)    → 202 Accepted
│   └── /sync
│       └── POST        → 200 OK
│
├── /extract-fdi
│   ├── POST (async)    → 202 Accepted
│   └── /sync
│       └── POST        → 200 OK
│
├── /extract-digital-transformation
│   ├── POST (async)    → 202 Accepted
│   └── /sync
│       └── POST        → 200 OK
│
└── /extract-pii
    ├── POST (async)    → 202 Accepted
    └── /sync
        └── POST        → 200 OK
```

## 🔍 Monitoring & Logs

### Log Files Structure:
```
call_llm/
├── digital_economy_extraction.log
│   ├── INFO: Start time
│   ├── INFO: Posts fetched
│   ├── INFO: Processing post X/Y
│   ├── INFO: Saved to table
│   └── INFO: Summary stats
│
├── fdi_extraction.log
├── digital_transformation_extraction.log
└── pii_extraction.log
```

### Key Log Events:
- `🤖 BẮT ĐẦU` - Extraction started
- `✅ Lấy được` - Posts fetched from DB
- `🔍 Post ID` - Processing specific post
- `✅ Saved` - Successfully saved to table
- `❌ Lỗi` - Error occurred
- `📊 Progress` - X/Y posts processed
- `✅ Đã xử lý` - Batch complete

## 💾 Database Schema Highlights

All target tables share common fields:

```sql
-- Common fields in all 4 tables
id              SERIAL PRIMARY KEY
province        VARCHAR     -- Địa phương
source_post_id  INTEGER     -- Link to important_posts
source_url      TEXT        -- Original article URL
period          VARCHAR     -- "Năm 2024, Quý 1"
year            INTEGER
quarter         INTEGER     -- 1-4
month           INTEGER     -- 1-12
data_source     VARCHAR     -- "LLM Extraction"
extraction_metadata JSONB   -- LLM model, timestamp
notes           TEXT        -- Additional info
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

## 🎓 Best Practices

### 1. LLM Prompts
- Clear field definitions
- Flexible extraction rules
- Example formats
- Validation guidelines

### 2. Error Handling
- Retry on API failures
- Validate JSON responses
- Log all errors
- Graceful degradation

### 3. Performance
- Batch processing
- Rate limiting
- Connection pooling
- Background tasks

### 4. Data Quality
- Validate extracted values
- Check data types
- Handle null values
- Preserve metadata

## 🚀 Deployment Checklist

- [ ] Set environment variables (API keys)
- [ ] Test database connections
- [ ] Verify table schemas exist
- [ ] Run test extraction (small batch)
- [ ] Monitor logs
- [ ] Verify data in tables
- [ ] Set up scheduled runs (optional)
- [ ] Monitor API costs
- [ ] Review extraction accuracy
- [ ] Tune prompts if needed

---

**System Version**: 1.0  
**Last Updated**: 2026-01-22  
**Status**: ✅ Ready for Production
