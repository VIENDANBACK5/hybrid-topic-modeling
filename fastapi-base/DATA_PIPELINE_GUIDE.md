# Data Pipeline Guide

## 📊 Data Flow Architecture

```
External API / Database
        ↓
   data/raw/          ← Raw data (JSON)
        ↓
  🔧 Processing       ← Clean, normalize, validate
        ↓
  data/processed/    ← Processed data (JSON)
        ↓
   Database          ← Structured data
        ↓
   🤖 Training       ← BERTopic, Classification
        ↓
  data/results/      ← Training results
```

## 🎯 Quy trình chuẩn

### 1️⃣ **Fetch Data từ BE khác**

```bash
# Fetch từ external API
curl -X POST http://localhost:7777/api/data/fetch-external \
  -H "Content-Type: application/json" \
  -d '{
    "api_url": "http://192.168.30.28:8000/api/articles",
    "params": {"limit": 500}
  }'

# Kết quả: data/raw/raw_20260104_120000.json
```

### 2️⃣ **Xử lý Raw Data**

```bash
# Process: clean, normalize, validate
curl -X POST http://localhost:7777/api/data/process \
  -H "Content-Type: application/json" \
  -d '{
    "raw_file": "data/raw/raw_20260104_120000.json"
  }'

# Kết quả: data/processed/processed_20260104_120000.json
```

**Processing actions:**
- ✅ Normalize data structure
- ✅ Clean HTML tags, special characters
- ✅ Extract metadata (source, category, url)
- ✅ Validate minimum content length
- ✅ Filter invalid records

### 3️⃣ **Load vào Database**

```bash
# Load processed data → database
curl -X POST http://localhost:7777/api/data/load-to-db \
  -H "Content-Type: application/json" \
  -d '{
    "processed_file": "data/processed/processed_20260104_120000.json",
    "update_existing": false
  }'
```

### 4️⃣ **Train từ Processed File**

```bash
# Train BERTopic từ processed file (không cần database)
curl -X POST http://localhost:7777/api/topics/train \
  -H "Content-Type: application/json" \
  -d '{
    "from_processed_file": "data/processed/processed_20260104_120000.json",
    "min_topic_size": 10
  }'
```

## ⚡ ONE-COMMAND ETL

```bash
# Full ETL: Fetch → Process → Load → Database
curl -X POST "http://localhost:7777/api/data/full-etl?use_database=true&limit=500"

# Hoặc từ external API
curl -X POST "http://localhost:7777/api/data/full-etl?external_api_url=http://192.168.30.28:8000/api/articles"
```

## 📁 Cấu trúc thư mục

```
data/
├── raw/                    # Raw data từ API
│   ├── raw_20260104_120000.json
│   ├── raw_20260104_130000.json
│   └── raw_from_db_20260104.json
│
├── processed/              # Data đã xử lý
│   ├── processed_20260104_120000.json
│   ├── processed_20260104_130000.json
│   └── processed_clean_500.json
│
├── results/                # Training results
│   ├── bertopic_session_abc123/
│   │   ├── model.pkl
│   │   ├── topics.json
│   │   └── visualizations/
│   └── training_logs/
│
├── models/                 # Saved models
│   └── bertopic_latest.pkl
│
└── cache/                  # Cache data
    └── topicgpt/
```

## 🔄 Workflows thường dùng

### Workflow 1: Sync từ External API hàng ngày

```bash
#!/bin/bash
# daily_sync.sh

# 1. Fetch data
curl -X POST http://localhost:7777/api/data/fetch-external \
  -d '{"api_url": "http://external-api.com/articles"}' \
  > fetch_result.json

RAW_FILE=$(jq -r '.result.raw_file' fetch_result.json)

# 2. Process
curl -X POST http://localhost:7777/api/data/process \
  -d "{\"raw_file\": \"$RAW_FILE\"}" \
  > process_result.json

PROCESSED_FILE=$(jq -r '.result.processed_file' process_result.json)

# 3. Load to DB
curl -X POST http://localhost:7777/api/data/load-to-db \
  -d "{\"processed_file\": \"$PROCESSED_FILE\"}"

# 4. Run full pipeline (classify, sentiment, etc.)
curl -X POST http://localhost:7777/api/orchestrator/quick-update?limit=500
```

### Workflow 2: Train từ Processed File

```bash
# Có sẵn processed file, không cần database
curl -X POST http://localhost:7777/api/topics/train \
  -H "Content-Type: application/json" \
  -d '{
    "from_processed_file": "data/processed/processed_clean_1000.json",
    "min_topic_size": 15,
    "enable_topicgpt": true
  }'
```

### Workflow 3: Export DB → Process → Train

```bash
# 1. Export database to raw
curl -X POST "http://localhost:7777/api/data/export-db-to-raw?limit=1000" \
  > export_result.json

RAW_FILE=$(jq -r '.result.raw_file' export_result.json)

# 2. Process
curl -X POST http://localhost:7777/api/data/process \
  -d "{\"raw_file\": \"$RAW_FILE\"}" \
  > process_result.json

PROCESSED_FILE=$(jq -r '.result.processed_file' process_result.json)

# 3. Train từ processed file
curl -X POST http://localhost:7777/api/topics/train \
  -d "{\"from_processed_file\": \"$PROCESSED_FILE\"}"
```

## 📋 Quản lý Files

### List files

```bash
# Xem raw files
curl http://localhost:7777/api/data/files/raw

# Xem processed files
curl http://localhost:7777/api/data/files/processed
```

### File naming convention

```
raw_YYYYMMDD_HHMMSS.json          # Raw data với timestamp
raw_from_db_YYYYMMDD.json         # Export từ database
processed_YYYYMMDD_HHMMSS.json    # Processed data
processed_clean_1000.json         # Custom name với size
```

## 🎯 Best Practices

### 1. Lưu trữ organized

- ✅ Raw data: Lưu nguyên từ API (traceability)
- ✅ Processed data: Clean, validate (ready for training)
- ✅ Version by timestamp (dễ rollback)

### 2. Processing pipeline

```python
from app.services.etl.data_pipeline import get_data_pipeline

pipeline = get_data_pipeline(db)

# Step 1: Fetch
fetch_result = pipeline.fetch_and_save_raw_data(
    external_api_url="http://api.com/data"
)

# Step 2: Process
process_result = pipeline.process_raw_data(
    raw_file=fetch_result["raw_file"]
)

# Step 3: Load
load_result = pipeline.load_processed_data_to_db(
    processed_file=process_result["processed_file"]
)

# Step 4: Train từ processed file
from app.services.topic.bertopic_trainer import get_trainer
trainer = get_trainer(db)
train_result = trainer.train_from_articles(
    from_processed_file=process_result["processed_file"],
    min_topic_size=10
)
```

### 3. Incremental updates

```bash
# Chỉ xử lý data mới
curl -X POST http://localhost:7777/api/data/full-etl?limit=100

# Quick update pipeline
curl -X POST http://localhost:7777/api/orchestrator/quick-update?limit=100
```

## ⚙️ Configuration

### Environment variables

```bash
# Data directories
export DATA_DIR=data
export RAW_DIR=data/raw
export PROCESSED_DIR=data/processed

# External API
export EXTERNAL_API_URL=http://192.168.30.28:8000
export EXTERNAL_API_TOKEN=your_token
```

### Processing options

```python
# Customize cleaner
from app.services.etl.text_cleaner import TextCleaner

cleaner = TextCleaner(
    remove_html=True,
    remove_urls=True,
    remove_emails=True,
    lowercase=False  # Keep original case for Vietnamese
)
```

## 🔍 Monitoring

### Check pipeline status

```bash
# List recent files
curl http://localhost:7777/api/data/files/processed | jq '.files[0:5]'

# Check training sessions
curl http://localhost:7777/api/topics/sessions

# System status
curl http://localhost:7777/api/orchestrator/status
```

## 🚨 Troubleshooting

### Problem: External API timeout

```bash
# Solution: Fetch với limit nhỏ hơn
curl -X POST .../fetch-external -d '{"params": {"limit": 100}}'
```

### Problem: Processing fails

```bash
# Check raw file format
cat data/raw/raw_file.json | jq '.[0]'

# Verify data structure
curl -X POST .../process -d '{"raw_file": "..."}'
```

### Problem: Training out of memory

```bash
# Train từ processed file với limit
curl -X POST .../train -d '{
  "from_processed_file": "...",
  "limit": 500
}'
```

## 📚 API Reference

See: http://localhost:7777/docs
- Section: **📊 Data Pipeline**
- Endpoints: `/api/data/*`

---

**Quy trình chuẩn: External API → Raw → Processed → DB → Training**
