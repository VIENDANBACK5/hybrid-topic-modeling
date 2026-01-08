# Hướng dẫn Fetch Newspaper Data

## Tổng quan

Đã thêm 2 endpoint mới để fetch dữ liệu newspaper từ external API với tính năng:
- ✅ Tự động phân trang (pagination) để lấy TẤT CẢ dữ liệu
- ✅ Kiểm tra trùng lặp với database (deduplication by URL)
- ✅ Chỉ lưu dữ liệu mới (không trùng)
- ✅ Hỗ trợ giới hạn số trang

## Endpoints mới

### 1. `/api/data/fetch-newspaper` - Chỉ fetch và lưu raw data

Fetch newspaper data và lưu vào `data/raw/`, không process hay load vào DB.

**Request:**
```bash
curl -X POST http://localhost:7777/api/data/fetch-newspaper \
  -H "Content-Type: application/json" \
  -d '{
    "base_api_url": "http://192.168.30.28:8000/api/v1/posts/by-type/newspaper",
    "page_size": 100,
    "max_pages": null,
    "sort_by": "id",
    "order": "desc"
  }'
```

**Parameters:**
- `base_api_url`: URL của API endpoint (required)
- `page_size`: Số records mỗi trang (default: 10)
- `max_pages`: Giới hạn số trang, `null` = unlimited (default: null)
- `sort_by`: Trường để sắp xếp (default: "id")
- `order`: Thứ tự sắp xếp: "asc" hoặc "desc" (default: "desc")

**Response:**
```json
{
  "status": "success",
  "message": "Fetched 250 new newspaper articles",
  "statistics": {
    "total_fetched": 300,
    "new_articles": 250,
    "duplicates_skipped": 50,
    "pages_processed": 3,
    "existing_urls_in_db": 1000
  },
  "raw_file": "data/raw/raw_newspaper_20260106_120000.json",
  "data_type": "newspaper"
}
```

### 2. `/api/data/fetch-newspaper-full-etl` - Full ETL Pipeline

Fetch → Process → Load to Database trong một bước.

**Request:**
```bash
curl -X POST http://localhost:7777/api/data/fetch-newspaper-full-etl \
  -H "Content-Type: application/json" \
  -d '{
    "base_api_url": "http://192.168.30.28:8000/api/v1/posts/by-type/newspaper",
    "page_size": 100,
    "sort_by": "id",
    "order": "desc"
  }'
```

**Query Parameters:**
- `update_existing`: Update records nếu đã tồn tại (default: false)

**Response:**
```json
{
  "status": "success",
  "message": "Full ETL completed: 250 new articles loaded",
  "results": {
    "steps": [
      {
        "name": "fetch",
        "status": "success",
        "statistics": {
          "total_fetched": 300,
          "new_articles": 250,
          "duplicates_skipped": 50,
          "pages_processed": 3
        }
      },
      {
        "name": "process",
        "status": "success",
        "file": "data/processed/processed_20260106_120000.json",
        "statistics": {
          "total": 250,
          "processed": 245,
          "skipped": 5
        }
      },
      {
        "name": "load",
        "status": "success",
        "statistics": {
          "inserted": 245,
          "updated": 0,
          "skipped": 5
        }
      }
    ]
  },
  "data_type": "newspaper"
}
```

## Sử dụng Python Script

Đã tạo script `fetch_newspaper_data.py` để dễ dàng fetch dữ liệu:

### Fetch + Process + Load (Full ETL) - RECOMMENDED

```bash
# Fetch tất cả dữ liệu newspaper và load vào DB
python fetch_newspaper_data.py --mode full-etl

# Fetch với page size lớn hơn (faster)
python fetch_newspaper_data.py --mode full-etl --page-size 200

# Giới hạn 5 trang đầu tiên
python fetch_newspaper_data.py --mode full-etl --page-size 100 --max-pages 5

# Update records nếu đã tồn tại
python fetch_newspaper_data.py --mode full-etl --update-existing
```

### Chỉ fetch raw data (không process/load)

```bash
# Chỉ fetch và lưu vào data/raw/
python fetch_newspaper_data.py --mode fetch-only

# Với page size và max pages
python fetch_newspaper_data.py --mode fetch-only --page-size 100 --max-pages 10
```

## Cách hoạt động

### Deduplication
- Kiểm tra URL của mỗi article với database
- Chỉ lưu articles có URL chưa tồn tại
- Tránh lưu dữ liệu trùng lặp

### Pagination
- Tự động fetch từng trang cho đến khi hết dữ liệu
- Dừng khi:
  - Không còn dữ liệu (response trống)
  - Số records < page_size (trang cuối)
  - Đạt max_pages (nếu có giới hạn)

### Statistics
Mỗi request trả về thống kê chi tiết:
- `total_fetched`: Tổng số records đã fetch
- `new_articles`: Số articles mới (chưa có trong DB)
- `duplicates_skipped`: Số articles trùng lặp (đã có trong DB)
- `pages_processed`: Số trang đã xử lý

## Ví dụ sử dụng

### 1. Fetch tất cả dữ liệu newspaper lần đầu
```bash
python fetch_newspaper_data.py --mode full-etl --page-size 200
```

### 2. Sync dữ liệu mới (chỉ fetch data chưa có)
```bash
python fetch_newspaper_data.py --mode full-etl --page-size 100
```

### 3. Fetch thử nghiệm (5 trang đầu)
```bash
python fetch_newspaper_data.py --mode full-etl --page-size 50 --max-pages 5
```

### 4. Chỉ fetch để kiểm tra (không load vào DB)
```bash
python fetch_newspaper_data.py --mode fetch-only --page-size 100
```

## Lưu ý

1. **API Server phải đang chạy**: Đảm bảo FastAPI server đang chạy ở `http://localhost:7777`

2. **External API phải accessible**: URL `http://192.168.30.28:8000/api/v1/posts/by-type/newspaper` phải truy cập được

3. **Database connection**: Cần kết nối DB để kiểm tra trùng lặp và load dữ liệu

4. **Page size tối ưu**: 
   - Page size nhỏ (10-50): An toàn hơn, nhiều requests
   - Page size lớn (100-200): Nhanh hơn, ít requests hơn
   - Khuyến nghị: 100

5. **Memory**: Với page size lớn và nhiều trang, có thể tốn nhiều RAM

## Files được tạo

- **Raw data**: `data/raw/raw_newspaper_YYYYMMDD_HHMMSS.json`
- **Processed data**: `data/processed/processed_YYYYMMDD_HHMMSS.json`

## Troubleshooting

### Lỗi connection refused
```
Error: Connection refused
```
→ API server chưa chạy, start bằng `docker-compose up` hoặc `uvicorn`

### Lỗi timeout
```
Error: Timeout
```
→ Giảm page_size hoặc kiểm tra kết nối network

### Không có dữ liệu mới
```
Message: No new articles found (all duplicates)
```
→ Tất cả dữ liệu đã có trong database, không có gì để fetch

### External API không phản hồi
```
Error: Failed to fetch page 1: ...
```
→ Kiểm tra URL của external API và network connectivity
