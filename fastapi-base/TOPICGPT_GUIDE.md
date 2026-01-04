# TopicGPT Integration Guide

## 🎨 TopicGPT - LLM-Powered Topic Intelligence

TopicGPT là service sử dụng GPT-4 để nâng cao chất lượng topic modeling.

## 🚀 Cấu hình

```bash
# Required
export OPENAI_API_KEY='sk-...'

# Optional
export TOPICGPT_API='openai'  # hoặc 'gemini'
export TOPICGPT_MODEL='gpt-4o-mini'  # cost-efficient
```

## 🎯 Khả năng TopicGPT

### 1️⃣ **Topic Modeling Enhancements**

#### Generate Topic Labels
```python
from app.services.topic.topicgpt_service import get_topicgpt_service

service = get_topicgpt_service()
label = service.generate_topic_label(
    keywords=["kinh tế", "thị trường", "đầu tư"],
    representative_docs=["Thị trường chứng khoán..."]
)
# Output: "Kinh tế & Thị trường"
```

#### Generate Descriptions
```python
description = service.generate_topic_description(
    topic_label="Giáo dục & Đào tạo",
    keywords=["học sinh", "trường học", "giáo viên"],
    representative_docs=[...]
)
```

#### Refine & Merge Similar Topics
```python
result = service.refine_topics(
    topics=[
        {"label": "Kinh tế địa phương", "keywords": ["kinh tế", "doanh nghiệp"]},
        {"label": "Phát triển kinh tế", "keywords": ["đầu tư", "kinh tế"]}
    ],
    merge_threshold=0.85
)
# Suggests: Merge topic 1 & 2 → "Phát triển Kinh tế Địa phương"
```

### 2️⃣ **Content Analysis**

#### Categorize Content
```python
result = service.categorize_content(
    text="Hôm nay, UBND tỉnh Hưng Yên tổ chức họp báo...",
    categories=["Chính trị", "Kinh tế", "Xã hội", ...]
)
# Output: {"category": "Chính trị", "confidence": 0.92}
```

#### Extract Keywords & Tags
```python
result = service.extract_keywords_and_tags(
    text="...",
    max_keywords=10
)
# Output: {
#   "keywords": ["hưng yên", "ubnd", "họp báo"],
#   "tags": ["#hungyentoday", "#chinhquyen", "#tintuc"]
# }
```

#### Generate Summaries
```python
summary = service.summarize_content(
    text="Long article...",
    max_length=100
)
```

#### Detect Similarity
```python
similarity = service.detect_similarity(
    text1="Article about economy...",
    text2="Another economic article..."
)
# Output: 0.87 (very similar)
```

## 📡 API Endpoints

### Check Status
```bash
curl http://localhost:7777/api/topicgpt/status
```

### Enhance Custom Topics
```bash
# Tạo descriptions cho 12 custom topics
curl -X POST http://localhost:7777/api/topicgpt/enhance/custom-topics
```

### Refine Discovered Topics
```bash
# Phân tích và suggest merge topics tương tự
curl -X POST "http://localhost:7777/api/topicgpt/refine/discovered-topics?merge_similar=true"
```

### Categorize Articles
```bash
# Phân loại 100 articles chưa có category
curl -X POST "http://localhost:7777/api/topicgpt/categorize-articles?limit=100"
```

### Generate Summaries
```bash
# Tạo summary cho 50 articles
curl -X POST "http://localhost:7777/api/topicgpt/generate-summaries?limit=50"
```

### Analyze Content
```bash
curl -X POST http://localhost:7777/api/topicgpt/analyze-content \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hôm nay, UBND tỉnh Hưng Yên...",
    "max_keywords": 10
  }'
```

## 🔄 Tích hợp vào Pipeline

TopicGPT **đã được enable by default** trong:

### 1. BERTopic Training
```bash
# Full pipeline with TopicGPT
curl -X POST http://localhost:7777/api/orchestrator/run-full-pipeline

# Train riêng với TopicGPT
curl -X POST http://localhost:7777/api/topics/train \
  -H "Content-Type: application/json" \
  -d '{"enable_topicgpt": true}'
```

**TopicGPT sẽ:**
- Generate natural labels cho discovered topics
- Tạo descriptions chi tiết
- Sử dụng representative documents để hiểu context

### 2. Custom Workflow
```python
from app.services.topic.topicgpt_enhancer import get_enhancer

db = SessionLocal()
enhancer = get_enhancer(db)

# Enhance custom topics
result = enhancer.enhance_custom_topics()

# Refine discovered topics
result = enhancer.refine_discovered_topics(merge_similar=True)

# Categorize articles
result = enhancer.categorize_articles(limit=100)

# Generate summaries
result = enhancer.generate_summaries(limit=50)

db.close()
```

## 💰 Cost Optimization

TopicGPT có **caching tự động**:
- Kết quả được cache trong `data/cache/topicgpt/cache.json`
- Giảm API calls cho queries giống nhau
- Tiết kiệm chi phí đáng kể

**Model mặc định:** `gpt-4o-mini` (cost-efficient)
- ~100x rẻ hơn GPT-4
- Quality vẫn cao cho Vietnamese content

## 📊 Use Cases

### Use Case 1: Enhance Topics Hàng tuần
```bash
# Sau khi train BERTopic
curl -X POST http://localhost:7777/api/topicgpt/refine/discovered-topics
```

### Use Case 2: Auto-categorize Articles Mới
```bash
# Chạy hàng ngày
curl -X POST "http://localhost:7777/api/topicgpt/categorize-articles?limit=100&uncategorized_only=true"
```

### Use Case 3: Generate Summaries cho Dashboard
```bash
# Tạo summaries cho trending articles
curl -X POST "http://localhost:7777/api/topicgpt/generate-summaries?limit=30"
```

### Use Case 4: Content Analysis API
```bash
# Real-time analysis cho new content
curl -X POST http://localhost:7777/api/topicgpt/analyze-content \
  -d '{"text": "New article content..."}'
```

## 🔧 Advanced Features

### Custom Categories
```python
service = get_topicgpt_service()
result = service.categorize_content(
    text="...",
    categories=[
        "Nông nghiệp",
        "Công nghiệp",
        "Dịch vụ",
        "Du lịch",
        "Đầu tư"
    ]
)
```

### Merge Topics Automatically
```python
enhancer = get_enhancer(db)
result = enhancer.refine_discovered_topics(
    merge_similar=True,
    merge_threshold=0.9  # Very similar only
)

# Apply merge suggestions manually
for merge in result["merge_suggestions"]:
    print(f"Merge topics {merge['topics']} → {merge['new_name']}")
```

## ⚠️ Important Notes

1. **API Key Required**: OPENAI_API_KEY must be set
2. **Rate Limits**: OpenAI has rate limits, use caching
3. **Cost**: Monitor usage with large datasets
4. **Language**: Optimized for Vietnamese content
5. **Quality**: GPT-4o-mini provides excellent results for topic modeling

## 📈 Performance

- **Speed**: ~2-3s per API call (cached: instant)
- **Quality**: Natural labels, accurate categorization
- **Cost**: ~$0.001 per 1000 tokens with gpt-4o-mini
- **Cache Hit Rate**: 60-80% for repeated queries

## 🎯 Next Steps

1. **Enable**: Set OPENAI_API_KEY
2. **Test**: `curl http://localhost:7777/api/topicgpt/status`
3. **Enhance**: `curl -X POST .../enhance/custom-topics`
4. **Automate**: Add to daily/weekly pipeline

---

**Documentation**: http://localhost:7777/docs (section "🎨 TopicGPT")
