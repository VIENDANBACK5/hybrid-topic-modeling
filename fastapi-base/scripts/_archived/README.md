# Archived Scripts

Các scripts đã được thay thế bởi API endpoints mới.

## Scripts đã archive:

### 1. `load_all_data.py` 
- **Ngày archive**: 2025-01-06
- **Lý do**: Đã được thay thế bởi `/api/fetch/{data_type}` endpoints
- **Thay thế bằng**: 
  - `POST /api/fetch/facebook`
  - `POST /api/fetch/tiktok`
  - `POST /api/fetch/threads`
  - `POST /api/fetch/newspaper`

### 2. `sync_external_api.py`
- **Ngày archive**: 2025-01-06
- **Lý do**: Logic transform_document đã được tích hợp vào processors mới
- **Thay thế bằng**: 
  - `app/services/etl/processors/facebook_processor.py`
  - `app/services/etl/processors/tiktok_processor.py`
  - `app/services/etl/processors/threads_processor.py`
  - `app/services/etl/processors/newspaper_processor.py`

## Cách sử dụng API mới:

```bash
# Fetch data từ external API
curl -X POST http://localhost:7777/api/fetch/facebook \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100}'

# Process raw data
curl -X POST http://localhost:7777/api/process/facebook

# Load to database
curl -X POST http://localhost:7777/api/process/load-to-db \
  -H "Content-Type: application/json" \
  -d '{"processed_file": "data/processed/facebook/processed_20250106.json"}'
```
