# Pipeline Automation Guide

## 🎯 Tổng quan

Hệ thống có **Orchestrator tự động** điều phối toàn bộ luồng xử lý data.

## 🚀 3 Cách chạy Pipeline

### 1️⃣ API Endpoint (Recommended)

```bash
# Full pipeline (foreground - đợi kết quả)
curl -X POST http://localhost:7777/api/orchestrator/run-full-pipeline

# Background (không block)
curl -X POST "http://localhost:7777/api/orchestrator/run-full-pipeline?background=true"

# Quick update (chỉ classify + sentiment + keywords)
curl -X POST "http://localhost:7777/api/orchestrator/quick-update?limit=200"

# Check status
curl http://localhost:7777/api/orchestrator/status
```

### 2️⃣ Shell Script

```bash
# Chạy full pipeline
./scripts/run_full_pipeline.sh

# Custom limit
LIMIT=1000 ./scripts/run_full_pipeline.sh

# Background mode
BACKGROUND=true ./scripts/run_full_pipeline.sh
```

### 3️⃣ Python Code

```python
from app.services.orchestrator import PipelineOrchestrator
from app.core.database import SessionLocal

db = SessionLocal()
orchestrator = PipelineOrchestrator(db)

result = orchestrator.run_full_pipeline(
    sync_data=False,           # Skip external API sync
    classify_topics=True,      # Classify unclassified articles
    analyze_sentiment=True,    # Analyze sentiment + link topics
    calculate_statistics=True, # Update stats tables
    regenerate_keywords=True,  # Regenerate keywords with GPT
    train_bertopic=False,      # Skip BERTopic training (expensive)
    limit=500                  # Process max 500 articles
)

print(f"Success: {result['steps']}")
db.close()
```

## 📋 Pipeline Workflow

```
┌─────────────────────────────────────────────────────────┐
│                   PIPELINE WORKFLOW                      │
└─────────────────────────────────────────────────────────┘

1. 📥 Sync Data (optional)
   └─> Call external API → Load articles into DB

2. 🏷️  Classify Topics
   └─> Find unclassified articles
   └─> Run CustomTopicClassifier
   └─> Save to article_custom_topics

3. 😊 Analyze Sentiment
   └─> Get articles with topics but no sentiment
   └─> Run sentiment analysis
   └─> Link sentiment to topics
   └─> Update topic_mention_stats

4. 📊 Calculate Statistics
   └─> Update trend_reports (weekly)
   └─> Calculate hot_topics (top 10)
   └─> Create daily_snapshot

5. 🔑 Regenerate Keywords
   └─> Extract n-grams from articles
   └─> GPT-4 cleaning (entity preservation)
   └─> Save to keyword_stats

6. 🤖 Train BERTopic (optional, expensive)
   └─> Train BERTopic model on all articles
   └─> Save discovered topics
```

## ⚙️ Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sync_data` | `true` | Sync từ external API |
| `classify_topics` | `true` | Classify topics |
| `analyze_sentiment` | `true` | Phân tích sentiment |
| `calculate_statistics` | `true` | Tính statistics |
| `regenerate_keywords` | `true` | Tạo keywords mới |
| `train_bertopic` | `true` | Train BERTopic discover topics |
| `limit` | `None` | Giới hạn articles xử lý |

## 🔄 Khi nào chạy?

### Hàng ngày (Quick Update)
```bash
curl -X POST "http://localhost:7777/api/orchestrator/quick-update?limit=200"
```
- Chỉ xử lý data mới (classify + sentiment + keywords)
- Nhanh (< 1 phút)
- Không sync, không train

### Hàng tuần (Full Pipeline)
```bash
curl -X POST http://localhost:7777/api/orchestrator/run-full-pipeline
```
- Full workflow bao gồm statistics + BERTopic training
- Discover topics mới từ data
- Trung bình (10-30 phút tùy data size)

### Train Topics riêng (Khi cần discover topics mới)
```bash
curl -X POST http://localhost:7777/api/topics/train \
  -H "Content-Type: application/json" \
  -d '{"limit": 500, "min_topic_size": 10}'
```
- Chỉ train BERTopic
- Discover topics từ articles
- Save vào `bertopic_discovered_topics`
- 5-15 phút

### Khi có data lớn mới
```bash
# 1. Sync data trước
curl -X POST http://localhost:7777/api/v1/sync/all

# 2. Chạy full pipeline
LIMIT=5000 ./scripts/run_full_pipeline.sh
```

## 📊 Monitoring

### Check Status
```bash
curl http://localhost:7777/api/orchestrator/status
```

Response:
```json
{
  "status": "ok",
  "totals": {
    "articles": 200,
    "topics": 12,
    "classifications": 47,
    "sentiments": 45,
    "keywords": 27
  },
  "pending": {
    "unclassified_articles": 0,
    "articles_no_sentiment": 2
  },
  "needs_action": true
}
```

### Check Logs
```bash
tail -f logs/app.log | grep -E "PIPELINE|Step"
```

## 🎛️ API Docs

Swagger UI: http://localhost:7777/docs
- Tìm section "🎯 Orchestrator"
- Test endpoints trực tiếp

## 🔧 Troubleshooting

### Pipeline fails với DB error
```bash
# Check DB connection
export POSTGRES_PORT=5555
psql postgresql://postgres:postgres@localhost:5555/DBHuYe -c "SELECT COUNT(*) FROM articles"
```

### Không có OpenAI API key
```bash
# Set key trước khi chạy
export OPENAI_API_KEY='sk-...'
```

### Pipeline chạy quá lâu
```bash
# Giảm limit
curl -X POST "http://localhost:7777/api/orchestrator/quick-update?limit=50"
```

## 📌 Best Practices

1. **Quick updates hàng ngày** - Xử lý data mới nhanh
2. **Full pipeline hàng tuần** - Đảm bảo consistency
3. **Check status trước** - Biết có bao nhiêu pending
4. **Background mode** - Không block API cho tasks lớn
5. **Logs monitoring** - Luôn check logs để catch errors sớm
