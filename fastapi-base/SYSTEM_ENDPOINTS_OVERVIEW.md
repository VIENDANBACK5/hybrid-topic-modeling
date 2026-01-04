# 🎯 HỆ THỐNG ENDPOINTS - OVERVIEW

## 📊 2 LUỒNG CHÍNH

### **LUỒNG 1: DATA PIPELINE (ETL)**
> Lấy data → Xử lý → Lưu file → Load DB

### **LUỒNG 2: TRAINING & FILL DB**
> Train topics → Classify → Sentiment → Statistics → Fill tables

---

## 🔄 LUỒNG 1: DATA PIPELINE (ETL)

### Step 1: Lấy data từ external API
```bash
POST /api/data/fetch-external
```
**Input:** External API URL  
**Output:** `data/raw/raw_20260104_120000.json`

**Example:**
```bash
curl -X POST http://localhost:7777/api/data/fetch-external \
  -H "Content-Type: application/json" \
  -d '{
    "api_url": "http://192.168.30.28:8000/api/articles",
    "params": {"limit": 500}
  }'
```

### Step 2: Xử lý raw data
```bash
POST /api/data/process
```
**Input:** Raw file path  
**Output:** `data/processed/processed_20260104_120000.json`

**Processing:**
- ✅ Clean HTML tags, special chars
- ✅ Normalize structure
- ✅ Validate content
- ✅ Extract metadata

**Example:**
```bash
curl -X POST http://localhost:7777/api/data/process \
  -H "Content-Type: application/json" \
  -d '{
    "raw_file": "data/raw/raw_20260104_120000.json"
  }'
```

### Step 3: Load vào database
```bash
POST /api/data/load-to-db
```
**Input:** Processed file path  
**Output:** Insert/update articles table

**Example:**
```bash
curl -X POST http://localhost:7777/api/data/load-to-db \
  -H "Content-Type: application/json" \
  -d '{
    "processed_file": "data/processed/processed_20260104_120000.json",
    "update_existing": false
  }'
```

### ⚡ ONE-COMMAND: Full ETL
```bash
POST /api/data/full-etl
```
**Actions:** Fetch → Process → Load (tất cả trong 1 call)

**Example:**
```bash
curl -X POST "http://localhost:7777/api/data/full-etl?external_api_url=http://192.168.30.28:8000/api/articles&limit=500"
```

---

## 🤖 LUỒNG 2: TRAINING & FILL DATABASE

### Option A: Full Pipeline (ALL-IN-ONE)
```bash
POST /api/orchestrator/run-full-pipeline
```
**Actions:**
1. ✅ Classify topics (12 custom topics)
2. ✅ Analyze sentiment & link to topics
3. ✅ Calculate statistics (trends, hot topics)
4. ✅ Regenerate keywords với GPT
5. ✅ Train BERTopic (discover new topics)

**Example:**
```bash
curl -X POST http://localhost:7777/api/orchestrator/run-full-pipeline
```

**Result:**
- ✅ `article_custom_topics` - Classified articles
- ✅ `sentiment_analysis` - Sentiment scores
- ✅ `topic_mention_stats` - Topic statistics
- ✅ `keyword_stats` - Top keywords
- ✅ `bertopic_discovered_topics` - Discovered topics
- ✅ `article_bertopic_topics` - Article-topic mappings
- ✅ `trend_reports` - Weekly trends
- ✅ `hot_topics` - Trending topics

### Option B: Quick Update (Hàng ngày)
```bash
POST /api/orchestrator/quick-update
```
**Actions:** Chỉ classify + sentiment + keywords (skip training)

**Example:**
```bash
curl -X POST "http://localhost:7777/api/orchestrator/quick-update?limit=100"
```

### Option C: Riêng từng phần

#### Train BERTopic only
```bash
POST /api/topics/train
```
**Input:** Processed file hoặc database  
**Output:** Discovered topics

**Example:**
```bash
# Train từ processed file
curl -X POST http://localhost:7777/api/topics/train \
  -H "Content-Type: application/json" \
  -d '{
    "from_processed_file": "data/processed/processed_20260104_120000.json",
    "min_topic_size": 10,
    "enable_topicgpt": true
  }'

# Train từ database
curl -X POST http://localhost:7777/api/topics/train \
  -d '{"limit": 500}'
```

#### Enhance với TopicGPT
```bash
POST /api/topicgpt/enhance/custom-topics
POST /api/topicgpt/refine/discovered-topics
POST /api/topicgpt/categorize-articles
POST /api/topicgpt/generate-summaries
```

**Example:**
```bash
# Enhance 12 custom topics
curl -X POST http://localhost:7777/api/topicgpt/enhance/custom-topics

# Categorize articles
curl -X POST "http://localhost:7777/api/topicgpt/categorize-articles?limit=100"
```

---

## 🎯 WORKFLOWS THỰC TẾ

### Workflow 1: Data mới từ external API → Train toàn bộ

```bash
# Step 1: Full ETL (fetch + process + load)
curl -X POST "http://localhost:7777/api/data/full-etl?external_api_url=http://192.168.30.28:8000/api/articles"

# Step 2: Full pipeline (classify + train + stats)
curl -X POST http://localhost:7777/api/orchestrator/run-full-pipeline
```

**Kết quả:** Tất cả tables filled, topics discovered!

### Workflow 2: Train từ processed file (không dùng DB)

```bash
# Step 1: Fetch + process (không load DB)
curl -X POST http://localhost:7777/api/data/fetch-external \
  -d '{"api_url": "http://api.com/data"}'
# → data/raw/raw_xxx.json

curl -X POST http://localhost:7777/api/data/process \
  -d '{"raw_file": "data/raw/raw_xxx.json"}'
# → data/processed/processed_xxx.json

# Step 2: Train trực tiếp từ file
curl -X POST http://localhost:7777/api/topics/train \
  -d '{"from_processed_file": "data/processed/processed_xxx.json"}'
```

**Kết quả:** Topics discovered, saved to `bertopic_discovered_topics`

### Workflow 3: Update hàng ngày (incremental)

```bash
# Fetch data mới (100 records)
curl -X POST "http://localhost:7777/api/data/full-etl?use_database=false&external_api_url=http://api.com/data&limit=100"

# Quick update (không train lại)
curl -X POST "http://localhost:7777/api/orchestrator/quick-update?limit=100"
```

**Kết quả:** Articles classified, sentiment analyzed, keywords updated

### Workflow 4: Re-train toàn bộ từ DB

```bash
# Export DB → processed file
curl -X POST "http://localhost:7777/api/data/export-db-to-raw?limit=1000"

# Process
curl -X POST http://localhost:7777/api/data/process \
  -d '{"raw_file": "data/raw/raw_from_db_xxx.json"}'

# Train
curl -X POST http://localhost:7777/api/topics/train \
  -d '{"from_processed_file": "data/processed/processed_xxx.json"}'
```

---

## 📊 TABLES ĐƯỢC FILL

### Sau LUỒNG 1 (ETL):
| Table | Description |
|-------|-------------|
| `articles` | Raw articles data |

### Sau LUỒNG 2 (Training & Fill):
| Table | Description | Filled by |
|-------|-------------|-----------|
| `article_custom_topics` | Article classifications | Classifier |
| `sentiment_analysis` | Sentiment scores | Sentiment service |
| `topic_mention_stats` | Topic statistics per period | Statistics service |
| `keyword_stats` | Top keywords với GPT | Statistics service |
| `bertopic_discovered_topics` | Discovered topics | BERTopic |
| `article_bertopic_topics` | Article-topic mappings | BERTopic |
| `topic_training_sessions` | Training history | BERTopic trainer |
| `trend_reports` | Weekly trends | Statistics service |
| `hot_topics` | Top trending topics | Statistics service |
| `daily_snapshots` | Daily metrics | Statistics service |

---

## 🎯 DECISION TREE

```
BẠN CẦN GÌ?

┌─ Lấy data mới từ API khác?
│  └─ POST /api/data/fetch-external
│     └─ POST /api/data/process
│        └─ POST /api/data/load-to-db
│
┌─ Fill tất cả tables với data có sẵn?
│  └─ POST /api/orchestrator/run-full-pipeline
│
┌─ Chỉ train topics (không cần classify)?
│  └─ POST /api/topics/train
│
┌─ Update nhanh data mới?
│  └─ POST /api/orchestrator/quick-update
│
┌─ Enhance topics với GPT?
│  └─ POST /api/topicgpt/enhance/custom-topics
│
└─ ALL-IN-ONE từ đầu đến cuối?
   └─ POST /api/data/full-etl (fetch + process + load)
      └─ POST /api/orchestrator/run-full-pipeline (train + fill)
```

---

## 🔍 CHECK STATUS

```bash
# System status
curl http://localhost:7777/api/orchestrator/status

# Files available
curl http://localhost:7777/api/data/files/processed

# Topics discovered
curl http://localhost:7777/api/topics/discovered?limit=20

# Training sessions
curl http://localhost:7777/api/topics/sessions
```

---

## 📚 API DOCUMENTATION

**Swagger UI:** http://localhost:7777/docs

**Sections:**
- 📊 Data Pipeline - ETL endpoints
- 🎯 Orchestrator - Full pipeline
- 🧠 Topic Training - BERTopic
- 🎨 TopicGPT - LLM enhancements
- 📈 Statistics - Keywords & stats

---

## ✅ TÓM TẮT

### LUỒNG 1: ETL
```
External API → data/raw/ → data/processed/ → Database (articles)
```

### LUỒNG 2: FILL DB
```
articles → classify → sentiment → keywords → train → ALL TABLES FILLED
```

### ONE-COMMAND
```bash
# Fetch + Process + Load + Train + Fill everything
curl -X POST "http://localhost:7777/api/data/full-etl?external_api_url=..."
curl -X POST "http://localhost:7777/api/orchestrator/run-full-pipeline"
```

**2 dòng lệnh = Full system ready! 🎉**
