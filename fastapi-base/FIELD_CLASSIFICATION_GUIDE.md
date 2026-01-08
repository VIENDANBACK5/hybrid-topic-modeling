# Hệ thống phân loại bài viết theo lĩnh vực

Hệ thống phân loại tự động bài viết vào 10 lĩnh vực chính dựa trên từ khóa và nội dung.

## 📋 Các lĩnh vực

1. **Kinh tế & Việc làm** - Đầu tư, doanh nghiệp, việc làm, nông nghiệp, thương mại, du lịch
2. **Y tế & Chăm sóc sức khỏe** - Bệnh viện, bảo hiểm y tế, dịch bệnh, khám chữa bệnh
3. **Giáo dục & Đào tạo** - Trường học, học phí, tuyển sinh, giáo viên
4. **Hạ tầng & Giao thông** - Đường xá, điện nước, dự án, giao thông
5. **Môi trường & Biến đổi khí hậu** - Ô nhiễm, rác thải, ngập lụt, thiên tai
6. **An sinh xã hội & Chính sách** - Trợ cấp, hỗ trợ người nghèo, bảo hiểm xã hội
7. **An ninh, Trật tự & Quốc phòng** - An ninh trật tự, tội phạm, tai nạn
8. **Hành chính công & Quản lý Nhà nước** - Thủ tục hành chính, dịch vụ công, cải cách
9. **Xây dựng Đảng & Hệ thống chính trị** - Cán bộ, tham nhũng, tổ chức đảng
10. **Văn hóa, Thể thao & Đời sống tinh thần** - Lễ hội, văn hóa, thể thao, giải trí

## 🗄️ Cấu trúc Database

### Bảng `fields`
Lưu thông tin các lĩnh vực:
- `id`: ID lĩnh vực
- `name`: Tên lĩnh vực
- `description`: Mô tả chi tiết
- `keywords`: Danh sách từ khóa (JSON)
- `order_index`: Thứ tự hiển thị

### Bảng `article_field_classifications`
Lưu phân loại bài viết:
- `article_id`: ID bài viết
- `field_id`: ID lĩnh vực
- `confidence_score`: Độ tin cậy (0-1)
- `matched_keywords`: Từ khóa matched (JSON)
- `classification_method`: Phương pháp phân loại

### Bảng `field_statistics`
Thống kê theo lĩnh vực:
- `field_id`: ID lĩnh vực
- `total_articles`: Tổng số bài viết
- `articles_today/week/month`: Số bài theo thời gian
- `avg_likes/shares/comments`: Engagement trung bình
- `source_distribution`: Phân bố theo nguồn (JSON)
- `province_distribution`: Phân bố theo tỉnh (JSON)

## 🚀 Cài đặt và Sử dụng

### 1. Chạy Migration

```bash
cd /home/ai_team/lab/pipeline_mxh/fastapi-base

# Cần set biến môi trường database trước
export POSTGRES_USER=your_user
export POSTGRES_PASSWORD=your_password
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=your_database

# Chạy migration
alembic upgrade head
```

### 2. Seed dữ liệu lĩnh vực

```bash
# Seed 10 lĩnh vực
python scripts/seed_field_classification.py --seed
```

### 3. Phân loại bài viết

```bash
# Phân loại tất cả bài viết
python scripts/seed_field_classification.py --classify

# Phân loại với giới hạn
python scripts/seed_field_classification.py --classify --limit 1000

# Chạy toàn bộ (seed + classify + stats)
python scripts/seed_field_classification.py --all
```

### 4. Xem thống kê

```bash
python scripts/seed_field_classification.py --stats
```

## 📡 API Endpoints

### Quản lý lĩnh vực

```bash
# Lấy danh sách lĩnh vực
GET /api/v1/fields/

# Lấy thông tin một lĩnh vực
GET /api/v1/fields/{field_id}

# Tạo lĩnh vực mới
POST /api/v1/fields/
{
  "name": "Tên lĩnh vực",
  "description": "Mô tả",
  "keywords": ["từ khóa 1", "từ khóa 2"],
  "order_index": 1
}

# Cập nhật lĩnh vực
PUT /api/v1/fields/{field_id}

# Xóa lĩnh vực
DELETE /api/v1/fields/{field_id}

# Seed dữ liệu (10 lĩnh vực mặc định)
POST /api/v1/fields/seed
```

### Phân loại bài viết

```bash
# Phân loại nhiều bài viết
POST /api/v1/fields/classify
{
  "article_ids": [1, 2, 3],  // Optional: nếu null thì classify tất cả
  "force_reclassify": false   // true = phân loại lại
}

# Phân loại một bài viết
POST /api/v1/fields/article/{article_id}/classify?force=false

# Lấy phân loại của một bài viết
GET /api/v1/fields/article/{article_id}/classification
```

### Thống kê

```bash
# Lấy phân bố bài viết theo lĩnh vực
GET /api/v1/fields/distribution/overview

# Lấy thống kê của tất cả lĩnh vực
GET /api/v1/fields/statistics/all

# Lấy thống kê của một lĩnh vực
GET /api/v1/fields/statistics/{field_id}

# Cập nhật thống kê
POST /api/v1/fields/statistics/update?field_id=1  // field_id optional
```

## 🔍 Cách thức hoạt động

### Phân loại dựa trên từ khóa

1. **Thu thập text**: Ghép title + content + summary của bài viết
2. **Chuẩn hóa**: Chuyển về lowercase, loại bỏ dấu câu
3. **Tìm keyword match**: So sánh với danh sách keywords của từng lĩnh vực
4. **Tính điểm**: Lĩnh vực nào match nhiều keyword nhất sẽ được chọn
5. **Confidence score**: Tính dựa trên số lượng keywords matched

### Cập nhật thống kê

- Đếm số bài viết theo thời gian (hôm nay, tuần này, tháng này)
- Tính engagement trung bình (likes, shares, comments)
- Phân bố theo nguồn và tỉnh thành
- Tự động cập nhật sau mỗi lần phân loại

## 📊 Response Examples

### Classification Stats
```json
{
  "total_articles": 1000,
  "classified_articles": 850,
  "unclassified_articles": 150,
  "field_distribution": {
    "Kinh tế & Việc làm": 250,
    "Y tế & Chăm sóc sức khỏe": 180,
    "Giáo dục & Đào tạo": 150
  },
  "classification_time": 12.5
}
```

### Field Distribution
```json
{
  "total_articles": 1000,
  "fields": [
    {
      "field_id": 1,
      "field_name": "Kinh tế & Việc làm",
      "article_count": 250,
      "percentage": 25.0
    }
  ],
  "last_updated": 1704672000.0
}
```

### Field Statistics
```json
{
  "field_id": 1,
  "field_name": "Kinh tế & Việc làm",
  "total_articles": 250,
  "articles_today": 15,
  "articles_this_week": 80,
  "articles_this_month": 250,
  "avg_likes": 45.5,
  "avg_shares": 12.3,
  "avg_comments": 8.7,
  "total_engagement": 16625,
  "source_distribution": {
    "vnexpress.net": 80,
    "tuoitre.vn": 60
  },
  "province_distribution": {
    "Hà Nội": 90,
    "TP HCM": 70
  }
}
```

## 🔧 Tùy chỉnh

### Thêm từ khóa cho lĩnh vực

```python
PUT /api/v1/fields/{field_id}
{
  "keywords": ["keyword1", "keyword2", "keyword3"]
}
```

### Thay đổi thứ tự hiển thị

```python
PUT /api/v1/fields/{field_id}
{
  "order_index": 5
}
```

### Phân loại lại toàn bộ

```bash
# Force reclassify tất cả bài viết
POST /api/v1/fields/classify
{
  "force_reclassify": true
}
```

## 📈 Best Practices

1. **Seed fields trước** khi phân loại bài viết
2. **Update statistics định kỳ** để có dữ liệu mới nhất
3. **Kiểm tra từ khóa** thường xuyên và bổ sung nếu cần
4. **Phân loại batch** cho hiệu suất tốt hơn
5. **Monitor confidence score** để đánh giá chất lượng phân loại

## 🐛 Troubleshooting

### Không phân loại được bài viết
- Kiểm tra xem đã seed fields chưa
- Kiểm tra bài viết có title/content không
- Xem log để biết lý do cụ thể

### Thống kê không cập nhật
- Gọi endpoint `/fields/statistics/update` để force update
- Kiểm tra database connection

### Phân loại sai
- Review và bổ sung keywords cho lĩnh vực
- Sử dụng force_reclassify=true để phân loại lại

## 📝 Notes

- Hệ thống hiện tại dùng **keyword matching** đơn giản
- Có thể mở rộng để dùng **ML models** trong tương lai
- Confidence score được normalize từ 0-1
- Một bài viết chỉ được phân vào 1 lĩnh vực (lĩnh vực match nhất)
