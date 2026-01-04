# Custom Topics - Quick Start Guide

## 🎯 Tổng Quan

Hệ thống hiện hỗ trợ **2 cách phân loại topics**:

1. **BERTopic** (Auto-discovery) - Tự động phát hiện topics từ dữ liệu
2. **Custom Topics** (Manual definition) - Tự định nghĩa topics trước, phân loại bài vào

---

## 🚀 Setup

### 1. Run Migration
```bash
cd /home/ai_team/lab/pipeline_mxh/fastapi-base

# Apply migration
docker-compose exec app alembic upgrade head

# Hoặc chạy file migration trực tiếp
docker-compose exec app python -c "from alembic.versions.add_custom_topics import upgrade; upgrade()"
```

### 2. Seed Topics Mẫu
```bash
# Seed 12 topics phổ biến (Chính trị, Kinh tế, Y tế, ...)
docker-compose exec app python seed_custom_topics.py
```

### 3. Restart API
```bash
docker-compose restart app
```

### 4. Verify
```bash
# Check API docs
open http://localhost:7777/docs

# Check topics
curl http://localhost:7777/api/v1/custom-topics/
```

---

## 📝 Sử Dụng

### 1. Xem Danh Sách Topics

```bash
curl http://localhost:7777/api/v1/custom-topics/
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Chính trị Việt Nam",
    "slug": "chinh-tri-viet-nam",
    "keywords": ["quốc hội", "chính phủ", "bộ trưởng"],
    "min_confidence": 0.6,
    "color": "#DC2626",
    "icon": "🏛️",
    "article_count": 0
  }
]
```

### 2. Tạo Topic Mới

```bash
curl -X POST http://localhost:7777/api/v1/custom-topics/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "name": "Crypto & Blockchain",
    "description": "Tin tức về tiền mã hóa và công nghệ blockchain",
    "keywords": ["bitcoin", "ethereum", "crypto", "blockchain", "NFT"],
    "example_docs": [
      "Bitcoin vượt mốc 50,000 USD",
      "Ethereum 2.0 chính thức ra mắt"
    ],
    "min_confidence": 0.6,
    "color": "#F59E0B",
    "icon": "₿"
  }'
```

### 3. Phân Loại Bài Viết

#### A. Phân loại TẤT CẢ bài chưa có custom topic
```bash
curl -X POST http://localhost:7777/api/v1/custom-topics/classify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "all_unclassified": true,
    "method": "hybrid",
    "save_results": true
  }'
```

#### B. Phân loại SPECIFIC articles
```bash
curl -X POST http://localhost:7777/api/v1/custom-topics/classify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "article_ids": [1, 2, 3, 4, 5],
    "method": "hybrid",
    "save_results": true
  }'
```

#### C. Phân loại lại TẤT CẢ (re-classify)
```bash
curl -X POST http://localhost:7777/api/v1/custom-topics/classify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "all_articles": true,
    "method": "hybrid",
    "save_results": true,
    "min_confidence": 0.5
  }'
```

**Response:**
```json
{
  "total_articles": 200,
  "total_topics": 12,
  "processing_time_ms": 45000,
  "results": [
    {
      "article_id": 1,
      "article_title": "Quốc hội thông qua luật mới",
      "topics": [
        {
          "topic_id": 1,
          "topic_name": "Chính trị Việt Nam",
          "confidence": 0.85,
          "method": "hybrid",
          "is_accepted": true
        }
      ],
      "processing_time_ms": 225
    }
  ],
  "summary": {
    "saved": 350,
    "skipped": 120,
    "errors": 0
  }
}
```

### 4. Xem Topics của 1 Bài Viết

```bash
curl "http://localhost:7777/api/v1/custom-topics/articles/1/topics?min_confidence=0.5"
```

**Response:**
```json
[
  {
    "topic_id": 1,
    "topic_name": "Chính trị Việt Nam",
    "confidence": 0.85,
    "method": "hybrid",
    "is_accepted": true
  },
  {
    "topic_id": 2,
    "topic_name": "Pháp luật",
    "confidence": 0.62,
    "method": "hybrid",
    "is_accepted": true
  }
]
```

### 5. Xem Bài Viết của 1 Topic

```bash
curl "http://localhost:7777/api/v1/custom-topics/topics/1/articles?min_confidence=0.6&limit=20"
```

**Response:**
```json
{
  "topic_id": 1,
  "topic_name": "Chính trị Việt Nam",
  "total_articles": 45,
  "articles": [
    {
      "article_id": 1,
      "title": "Quốc hội thông qua luật mới",
      "confidence": 0.85,
      "method": "hybrid",
      "published_date": "2024-01-03T10:30:00",
      "classified_at": "2024-01-04T08:20:15"
    }
  ]
}
```

### 6. Xem Thống Kê Tổng Quan

```bash
curl http://localhost:7777/api/v1/custom-topics/stats/overview
```

**Response:**
```json
{
  "total_topics": 12,
  "active_topics": 12,
  "total_classified_articles": 180,
  "total_unclassified_articles": 20,
  "avg_topics_per_article": 1.75,
  "classification_methods": {
    "hybrid": 300,
    "keyword": 50,
    "embedding": 0
  },
  "top_topics": [
    {
      "topic_id": 1,
      "topic_name": "Chính trị Việt Nam",
      "article_count": 45,
      "avg_confidence": 0.72,
      "method_distribution": {},
      "recent_articles": []
    }
  ]
}
```

---

## 🎯 Phương Pháp Phân Loại

### 1. **Keyword Matching** (`method: "keyword"`)
- ✅ Nhanh nhất
- ✅ Dễ debug
- ❌ Không hiểu ngữ cảnh
- **Use case:** Dataset nhỏ (<1000 bài), keywords rõ ràng

### 2. **Embedding Similarity** (`method: "embedding"`)
- ✅ Chính xác cao nhất
- ✅ Hiểu ngữ cảnh, bắt được từ đồng nghĩa
- ❌ Chậm, cần nhiều RAM
- **Use case:** Dataset lớn (>10,000 bài), cần độ chính xác cao

### 3. **Hybrid** (`method: "hybrid"`) - **KHUYÊN DÙNG**
- ✅ Cân bằng tốc độ và độ chính xác
- ✅ Quick filter với keywords, semantic với embedding
- ✅ Phù hợp mọi quy mô
- **Use case:** Mặc định cho mọi trường hợp

---

## 📊 Tiêu Chuẩn Topic Tốt

### ✅ Good Example
```json
{
  "name": "Chính trị Việt Nam",
  "description": "Tin tức chính trị trong nước, quốc hội, chính phủ",
  "keywords": [
    "quốc hội", "chính phủ", "bộ trưởng", "thủ tướng", "chủ tịch nước",
    "nghị quyết", "chính sách", "luật", "nghị định"
  ],
  "example_docs": [
    "Quốc hội thông qua nghị quyết về phát triển kinh tế",
    "Chính phủ ban hành chính sách mới hỗ trợ doanh nghiệp",
    "Thủ tướng yêu cầu đẩy nhanh tiến độ các dự án"
  ],
  "negative_keywords": ["cổ phiếu", "bóng đá"],
  "min_confidence": 0.6
}
```

**Tại sao tốt:**
- ✅ Tên rõ ràng, cụ thể
- ✅ Có 9 keywords liên quan chặt chẽ
- ✅ Có 3 câu văn mẫu để model học ngữ cảnh
- ✅ Có negative keywords để tránh nhầm lẫn
- ✅ min_confidence hợp lý (0.6)

### ❌ Bad Example
```json
{
  "name": "Tin tức",
  "keywords": ["tin", "bài viết", "thông tin"],
  "min_confidence": 0.3
}
```

**Tại sao tệ:**
- ❌ Tên quá chung chung
- ❌ Keywords quá chung, không phân biệt được
- ❌ Không có example docs
- ❌ min_confidence quá thấp (sẽ có nhiều false positive)

---

## 🔧 Advanced Usage

### 1. Update Topic

```bash
curl -X PUT http://localhost:7777/api/v1/custom-topics/1 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "keywords": ["quốc hội", "chính phủ", "bộ trưởng", "thủ tướng", "nghị quyết"],
    "min_confidence": 0.65
  }'
```

**Note:** Sau khi update topic, nên chạy lại classification để cập nhật kết quả.

### 2. Xóa Topic

```bash
# Soft delete (khuyên dùng)
curl -X DELETE "http://localhost:7777/api/v1/custom-topics/1" \
  -H "X-API-Key: dev-key-12345"

# Hard delete (mất hết data mapping)
curl -X DELETE "http://localhost:7777/api/v1/custom-topics/1?hard_delete=true" \
  -H "X-API-Key: dev-key-12345"
```

### 3. Áp Dụng Template

```bash
# List templates
curl http://localhost:7777/api/v1/custom-topics/templates

# Apply template
curl -X POST http://localhost:7777/api/v1/custom-topics/templates/apply \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "template_id": 1,
    "override_existing": false
  }'
```

---

## 🔍 Troubleshooting

### Issue 1: Classification quá chậm
**Solution:**
- Dùng method `keyword` thay vì `hybrid`
- Giảm số lượng example_docs
- Tăng min_confidence để filter sớm

### Issue 2: Độ chính xác thấp
**Solution:**
- Thêm keywords liên quan
- Thêm example_docs
- Dùng method `embedding` hoặc `hybrid`
- Tăng keywords_weight

### Issue 3: Topics chồng chéo
**Solution:**
- Thêm negative_keywords
- Tăng min_confidence
- Review và refine keywords của từng topic

### Issue 4: Bài viết không được phân loại
**Solution:**
- Giảm min_confidence
- Kiểm tra keywords có phù hợp không
- Thêm example_docs
- Check bài viết có nội dung không (title + content)

---

## 📈 Best Practices

1. **Start Small:** Tạo 5-10 topics quan trọng nhất trước
2. **Iterate:** Chạy classification → Review kết quả → Adjust keywords
3. **Use Hybrid:** Method `hybrid` là best choice cho hầu hết cases
4. **Set Thresholds:** min_confidence 0.5-0.7 là hợp lý
5. **Add Examples:** Example docs giúp improve accuracy đáng kể
6. **Monitor Stats:** Dùng `/stats/overview` để theo dõi quality
7. **Update Regularly:** Review và update topics theo thời gian

---

## 🎯 Use Cases

### Use Case 1: News Portal
- **Goal:** Phân loại tin tức vào các chuyên mục
- **Topics:** Chính trị, Kinh tế, Xã hội, Thể thao, ...
- **Method:** Hybrid
- **min_confidence:** 0.6

### Use Case 2: Content Moderation
- **Goal:** Phát hiện nội dung nhạy cảm
- **Topics:** Bạo lực, Hate speech, Spam, ...
- **Method:** Embedding (high accuracy)
- **min_confidence:** 0.7 (strict)

### Use Case 3: Market Research
- **Goal:** Phân loại feedback khách hàng
- **Topics:** Sản phẩm, Giá cả, Dịch vụ, Vận chuyển, ...
- **Method:** Keyword (fast)
- **min_confidence:** 0.5

---

## 🆚 So Sánh BERTopic vs Custom Topics

| | BERTopic | Custom Topics |
|---|---|---|
| **Cách hoạt động** | Auto-discover từ data | Tự định nghĩa trước |
| **Control** | Thấp | Cao |
| **Setup** | Không cần | Cần define keywords |
| **Flexibility** | Thấp | Cao |
| **Use case** | Khám phá insights | Phân loại theo nghiệp vụ |
| **Update** | Phải re-train | Chỉnh keywords |

**Khuyến nghị:** Dùng CẢ 2!
- BERTopic: Để discover topics mới, insights
- Custom Topics: Để phân loại theo nghiệp vụ cố định

---

## 📚 API Reference

Xem đầy đủ: http://localhost:7777/docs#/📌%20Custom%20Topics

**Endpoints:**
- `GET /api/v1/custom-topics/` - List topics
- `POST /api/v1/custom-topics/` - Create topic
- `GET /api/v1/custom-topics/{id}` - Get topic detail
- `PUT /api/v1/custom-topics/{id}` - Update topic
- `DELETE /api/v1/custom-topics/{id}` - Delete topic
- `POST /api/v1/custom-topics/classify` - Classify articles
- `GET /api/v1/custom-topics/articles/{id}/topics` - Get article's topics
- `GET /api/v1/custom-topics/topics/{id}/articles` - Get topic's articles
- `GET /api/v1/custom-topics/stats/overview` - Statistics

---

## 🎉 Summary

✅ **Đã implement đầy đủ Custom Topics**
✅ **Song song với BERTopic (không thay thế)**
✅ **12 topics mẫu sẵn sàng sử dụng**
✅ **3 phương pháp classification (keyword, embedding, hybrid)**
✅ **API đầy đủ để CRUD topics và phân loại**
✅ **Chi tiết, chuẩn chỉ, production-ready**

**Next Steps:**
1. Run migration + seed data
2. Test API với Postman/curl
3. Phân loại 200 bài hiện có
4. Review kết quả và tune parameters
5. Scale lên 7692 bài khi ready
