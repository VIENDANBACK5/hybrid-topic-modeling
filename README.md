# Pipeline MXH - AI-Powered News & Social Media Analysis System

**Hệ thống phân tích tin tức và mạng xã hội tự động với AI**: Crawl → ETL → Topic Modeling → RAG Search

🚀 **Production-ready** với TopicGPT Integration, Smart Crawling, và Vietnamese BERTopic

---

## 📋 Tổng quan

Hệ thống backend hoàn chỉnh để:
- **Thu thập dữ liệu** từ web, RSS, file, API với smart crawling
- **Xử lý ETL** tự động với dedupe thông minh (hash + semantic)
- **Phân tích chủ đề** bằng BERTopic Vietnamese với GPU support
- **Tìm kiếm semantic** với RAG (FAISS + Vietnamese embeddings)
- **Làm giàu nội dung** bằng LLM (keywords, categories, entities)
- **Quản lý chi phí** và budget tracking cho LLM operations

---

## 🏗️ Kiến trúc hệ thống

```
pipeline_mxh/
├── fastapi-base/                    # Main Application
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── api/routers/            
│   │   │   ├── crawl.py             # 🕷️ Crawling endpoints (8 endpoints)
│   │   │   ├── topics.py            # 🏷️ Topic modeling endpoints (7 endpoints)
│   │   │   ├── dashboard.py         # 📊 Analytics & visualization
│   │   │   ├── sources.py           # 📰 Source management
│   │   │   └── rag.py               # 🔍 RAG search endpoints
│   │   ├── services/
│   │   │   ├── crawler/             # 🕷️ Crawler Services
│   │   │   │   ├── async_crawler.py         # Async multi-URL crawler
│   │   │   │   ├── smart_pipeline.py        # 5-stage intelligent pipeline
│   │   │   │   ├── llm_content_enricher.py  # LLM selective enrichment
│   │   │   │   ├── cost_optimizer.py        # Budget & cost management
│   │   │   │   ├── pipeline.py              # Base crawler pipeline
│   │   │   │   ├── fetchers.py              # Web/RSS fetchers
│   │   │   │   └── content_extractor.py     # Content extraction
│   │   │   ├── etl/                 # 🧹 ETL Services
│   │   │   │   ├── hybrid_dedupe.py         # 2-stage deduplication
│   │   │   │   ├── dedupe_enhanced.py       # Enhanced dedupe logic
│   │   │   │   ├── text_cleaner.py          # Text cleaning
│   │   │   │   └── vietnamese_tokenizer.py  # Vietnamese tokenizer
│   │   │   ├── topic/               # 🏷️ Topic Modeling Services
│   │   │   │   ├── model.py                 # BERTopic model wrapper
│   │   │   │   ├── manager.py               # Topic manager
│   │   │   │   ├── indexer.py               # FAISS indexer
│   │   │   │   └── topicgpt_service.py      # LLM integration
│   │   │   ├── storage/             # 💾 Storage Services
│   │   │   │   ├── db.py                    # Database operations
│   │   │   │   └── object_store.py          # File storage
│   │   │   └── rag_service.py       # 🔍 RAG Service
│   │   ├── models/                  # 🗄️ Database Models
│   │   │   ├── model_article.py             # Article model
│   │   │   ├── model_source.py              # Source model
│   │   │   ├── model_crawl_history.py       # Crawl tracking
│   │   │   └── model_user.py                # User model
│   │   ├── schemas/                 # 📝 Pydantic Schemas
│   │   │   ├── sche_pipeline.py             # Pipeline schemas
│   │   │   └── sche_response.py             # Response schemas
│   │   ├── core/                    # ⚙️ Core Modules
│   │   │   ├── database.py                  # DB connection
│   │   │   ├── models.py                    # Global model manager
│   │   │   ├── config.py                    # Configuration
│   │   │   └── constants.py                 # Constants
│   │   └── static/
│   │       ├── index.html                   # Main dashboard
│   │       └── test_dashboard.html          # Test interface
│   ├── config/
│   │   └── topicgpt_config.yaml     # TopicGPT configuration
│   ├── data/                        # Application data
│   │   ├── db/                      # SQLite database
│   │   ├── models/                  # Saved BERTopic models
│   │   ├── indexes/                 # FAISS indexes
│   │   ├── cache/                   # LLM cache
│   │   └── results/                 # Analysis results
│   ├── alembic/                     # Database migrations
│   ├── requirements.txt
│   └── docker-compose.yml
└── data/                            # Shared data
    ├── raw/                         # Raw crawled data
    ├── processed/                   # Processed data
    └── results/                     # Final results
```

---

## 🚀 Quick Start

### 1. Cài đặt

```bash
cd /home/ai_team/lab/pipeline_mxh/fastapi-base

# Cài đặt dependencies
pip install -r requirements.txt

# Hoặc sử dụng bertopic_env có sẵn
./start_with_bertopic_env.sh

# Cài đặt TopicGPT (optional)
pip install openai google-generativeai
```

### 2. Cấu hình

```bash
# Set API keys (nếu dùng LLM features)
export OPENAI_API_KEY=sk-your-key-here
export GEMINI_API_KEY=your-gemini-key

# Hoặc edit config file
nano config/topicgpt_config.yaml
```

### 3. Khởi động

```bash
# Development
uvicorn app.main:app --reload --port 8548

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8548 --workers 4
```

### 4. Truy cập

- **API Docs**: http://localhost:8548/docs
- **Dashboard**: http://localhost:8548/dashboard
- **Test Interface**: http://localhost:8548/static/test_dashboard.html

---

## 📡 API Endpoints

### 🕷️ Crawl API (`/api/crawl`)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/` | **Simple crawl** - Chỉ cần URL và mode |
| `POST` | `/smart` | **Smart crawl** với LLM enrichment |
| `POST` | `/preview` | Preview domain trước khi crawl |
| `POST` | `/preview-full` | Preview chi tiết toàn domain |
| `POST` | `/by-category` | Crawl theo category |
| `POST` | `/incremental` | Incremental crawl (chỉ crawl mới) |
| `GET` | `/stats/{domain}` | Thống kê crawl history |
| `GET` | `/status` | Status và capabilities |
| `GET` | `/cost/report` | Báo cáo chi phí LLM |
| `POST` | `/cost/set-budget` | Đặt budget hàng ngày |
| `POST` | `/cost/estimate` | Ước tính chi phí |

### 🏷️ Topics API (`/api/topics`)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/` | Train/update topic model |
| `POST` | `/fit` | Fit model với documents |
| `POST` | `/transform` | Transform docs → topics |
| `POST` | `/search` | Semantic search với FAISS |
| `GET` | `/` | List all topics |
| `GET` | `/topics/{id}` | Chi tiết topic |
| `GET` | `/distribution` | Topic distribution |

### 📊 Dashboard API (`/api/dashboard`)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/stats` | Thống kê tổng quan |
| `GET` | `/articles` | List articles |
| `GET` | `/sources` | List sources |
| `GET` | `/topics/trending` | Trending topics |

### 🔍 RAG API (`/api/rag`)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/search` | Semantic search |
| `POST` | `/ask` | Q&A with context |
| `GET` | `/status` | RAG system status |

---

## 💡 Ví dụ sử dụng

### 1. Simple Crawl (Khuyến nghị)

```bash
# Crawl nhanh
curl -X POST http://localhost:8548/api/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://vnexpress.net", "mode": "quick"}'

# Crawl max (5000 pages, depth 5)
curl -X POST http://localhost:8548/api/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://baohungyen.vn", "mode": "max"}'

# Preview trước khi crawl
curl -X POST http://localhost:8548/api/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "mode": "preview"}'
```

### 2. Smart Crawl với LLM

```bash
# Balanced mode (khuyến nghị - 30% docs được enrich)
curl -X POST http://localhost:8548/api/crawl/smart \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://vnexpress.net",
    "max_pages": 100,
    "llm_options": {
      "extract_keywords": true,
      "categorize": true,
      "extract_entities": true
    },
    "priority_mode": "balanced"
  }'

# Low cost mode (10% enrich - tiết kiệm)
curl -X POST http://localhost:8548/api/crawl/smart \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "priority_mode": "low"
  }'

# High quality mode (80% enrich - chất lượng cao)
curl -X POST http://localhost:8548/api/crawl/smart \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://important-source.com",
    "priority_mode": "high"
  }'
```

### 3. Topic Modeling

```bash
# Train model từ database
curl -X POST http://localhost:8548/api/topics/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "train",
    "model_name": "my_model_v1",
    "n_topics": 20,
    "min_topic_size": 10
  }'

# Transform new documents
curl -X POST http://localhost:8548/api/topics/transform \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      "Bài viết về công nghệ AI",
      "Tin tức kinh tế Việt Nam"
    ]
  }'

# Search similar documents
curl -X POST http://localhost:8548/api/topics/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "công nghệ trí tuệ nhân tạo",
    "k": 10
  }'
```

### 4. Quản lý chi phí

```bash
# Xem báo cáo chi phí
curl http://localhost:8548/api/crawl/cost/report

# Đặt budget
curl -X POST http://localhost:8548/api/crawl/cost/set-budget \
  -H "Content-Type: application/json" \
  -d '{"budget": 20.0}'

# Ước tính chi phí
curl -X POST http://localhost:8548/api/crawl/cost/estimate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://vnexpress.net", "max_pages": 100}'
```

---

## 🎯 Tính năng chính

### 🕷️ Smart Crawling

- **Multi-mode crawling**: preview, quick, max, full
- **Smart selection**: Chỉ enrich docs có giá trị cao
- **Incremental crawling**: Chỉ crawl URLs mới
- **Cost optimization**: Budget tracking & smart decisions
- **Content extraction**: Advanced HTML parsing
- **Quality filtering**: Auto filter low-quality content

### 🧹 ETL Pipeline

- **Two-stage deduplication**:
  - Stage 1: Hash-based (MD5 + SimHash) - nhanh
  - Stage 2: Semantic similarity - chính xác
- **Text cleaning**: Vietnamese-optimized
- **Tokenization**: Vietnamese word segmentation
- **Normalization**: Unicode, whitespace, special chars

### 🏷️ Topic Modeling

- **Vietnamese BERTopic**: Optimized for Vietnamese
- **Embedding models**:
  - `keepitreal/vietnamese-sbert` (default)
  - `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **GPU acceleration**: cuML UMAP + HDBSCAN
- **BM25 weighting**: Better topic quality
- **Representation**: KeyBERT + MMR
- **Incremental learning**: Update models with new data
- **Model persistence**: Save/load trained models

### 🤖 LLM Integration (TopicGPT)

- **Multi-API support**: OpenAI, Gemini, Azure OpenAI
- **Smart features**:
  - Keyword extraction (5-10 keywords)
  - Categorization (12 categories)
  - Entity extraction (people, places, orgs)
  - Summarization
  - Topic labeling & description
- **Cost optimization**:
  - Selective enrichment (only high-value docs)
  - Response caching
  - Budget management
  - Usage tracking

### 🔍 RAG Search

- **FAISS indexing**: Fast similarity search
- **Vietnamese embeddings**: Optimized vectors
- **Hybrid search**: Combine semantic + keyword
- **Context retrieval**: Get relevant documents
- **Q&A**: Answer questions with sources

### 📊 Analytics & Dashboard

- **Real-time stats**: Articles, sources, topics
- **Trending topics**: Track hot topics
- **Source monitoring**: Track crawl performance
- **Cost reports**: LLM usage & spending
- **Interactive UI**: Web dashboard

---

## 💰 Chi phí & Budget

### Priority Modes

| Mode | Enrich % | Chi phí/100 docs | Khi nào dùng |
|------|----------|------------------|--------------|
| **Low** | 10% | $0.08 | Crawl số lượng lớn, không quan trọng |
| **Balanced** ⭐ | 30% | $0.60 | Daily crawl (khuyến nghị) |
| **High** | 80% | $2.00 | Nguồn quan trọng, phân tích sâu |

### Budget Management

- **Default budget**: $10/ngày (~1,600 docs ở balanced mode)
- **Auto tracking**: Theo dõi chi phí real-time
- **Budget alerts**: Cảnh báo khi gần hết budget
- **Cost estimation**: Ước tính trước khi crawl

---

## 🛠️ Configuration

### TopicGPT Config (`config/topicgpt_config.yaml`)

```yaml
llm:
  provider: openai  # openai, gemini, azure
  model: gpt-4o-mini
  api_key: ${OPENAI_API_KEY}
  max_tokens: 500
  temperature: 0.3

crawler:
  priority_mode: balanced  # low, balanced, high
  max_pages: 100
  delay_ms: 100
  
cost:
  daily_budget: 10.0
  alert_threshold: 0.8
  
deduplication:
  hash_threshold: 0.95
  semantic_threshold: 0.85
```

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./data/db/pipeline.db

# LLM APIs
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
AZURE_OPENAI_KEY=...

# App Settings
DEBUG=True
LOG_LEVEL=INFO
```

---

## 📦 Dependencies

### Core

```
fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
```

### Crawler

```
httpx>=0.25.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
feedparser>=6.0.10
```

### Topic Modeling

```
bertopic>=0.16.0
sentence-transformers>=2.2.0
umap-learn>=0.5.4
hdbscan>=0.8.33
faiss-cpu>=1.7.4
```

### LLM

```
openai>=1.0.0
google-generativeai>=0.3.0
```

### Vietnamese NLP

```
pyvi>=0.1.1
underthesea>=1.3.0
```

---

## 🧪 Testing

### Quick Test

```bash
# Test all endpoints
python test_topicgpt.py report

# Test specific feature
python test_topicgpt.py balanced https://vnexpress.net
```

### Shell Commands

```bash
# Balanced crawl
./topicgpt_commands.sh balanced https://vnexpress.net

# Cost report
./topicgpt_commands.sh report

# Set budget
./topicgpt_commands.sh budget 20.0

# Estimate cost
./topicgpt_commands.sh estimate https://example.com
```

---

## 📈 Performance

### Crawling

- **Speed**: 10-50 pages/sec (depends on delay)
- **Throughput**: 1000+ pages/minute (parallel)
- **Memory**: ~500MB base + 2MB per 1000 docs

### Topic Modeling

- **Training**: ~10-30s per 1000 docs (GPU)
- **Inference**: ~100ms per doc (GPU)
- **Memory**: ~2GB (model + embeddings)

### RAG Search

- **Index build**: ~5s per 10K docs
- **Search**: <100ms per query
- **Memory**: ~1GB per 100K docs

---

## 🔒 Security

- SQL injection protection (SQLAlchemy ORM)
- XSS protection (input sanitization)
- Rate limiting (optional via middleware)
- API key authentication (optional)
- CORS configuration

---

## 📚 Documentation

- **API Docs**: http://localhost:8548/docs
- **ReDoc**: http://localhost:8548/redoc
- **Source code**: Fully documented với docstrings

---

## 🐛 Troubleshooting

### Common Issues

1. **Database locked**
   ```bash
   rm data/db/pipeline.db
   alembic upgrade head
   ```

2. **Model not found**
   ```bash
   # Train new model
   curl -X POST http://localhost:8548/api/topics/ -d '{"action":"train"}'
   ```

3. **Out of memory**
   ```bash
   # Reduce batch size in config
   # Or use CPU instead of GPU
   ```

4. **LLM API errors**
   ```bash
   # Check API key
   echo $OPENAI_API_KEY
   
   # Check budget
   curl http://localhost:8548/api/crawl/cost/report
   ```

---

## 🚀 Deployment

### Docker

```bash
docker-compose up -d
```

### Production

```bash
# Use production ASGI server
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8548 \
  --access-logfile - \
  --error-logfile -
```

---

## 📝 License

MIT License

---

## 👥 Team

AI Team - Lab Pipeline MXH

---

## 📞 Support

- **Issues**: GitHub Issues
- **Email**: support@example.com
- **Docs**: http://localhost:8548/docs

---

**Last Updated**: December 2025
