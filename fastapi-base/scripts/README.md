# Utility Scripts

Các script utility để setup và populate data.

## Scripts Hiệu Lực

### `seed_custom_topics.py`
Seed custom topics vào database (12 topics mặc định).

### `fill_all_tables.py`
Fill các bảng statistics với data để test.

### `run_full_pipeline.sh`
Chạy full pipeline từ fetch → process → train.

## Scripts Đã Archive (xem `_archived/`)

Các scripts sau đã được thay thế bởi API endpoints:
- `load_all_data.py` → `/api/fetch/{data_type}`
- `sync_external_api.py` → `/api/process/{data_type}`

## Usage

```bash
# From root directory
export POSTGRES_PORT=5555
python scripts/seed_custom_topics.py
python scripts/fill_all_tables.py
```

## API Endpoints Mới

### Fetch Data từ External API:
```bash
curl -X POST http://localhost:7777/api/fetch/facebook -H "Content-Type: application/json" -d '{"page_size": 100}'
curl -X POST http://localhost:7777/api/fetch/tiktok
curl -X POST http://localhost:7777/api/fetch/threads
curl -X POST http://localhost:7777/api/fetch/newspaper
```

### Process Raw Data:
```bash
curl -X POST http://localhost:7777/api/process/facebook
curl -X POST http://localhost:7777/api/process/tiktok
curl -X POST http://localhost:7777/api/process/threads
curl -X POST http://localhost:7777/api/process/newspaper
```

### Load to Database:
```bash
curl -X POST http://localhost:7777/api/process/load-to-db \
  -H "Content-Type: application/json" \
  -d '{"processed_file": "data/processed/facebook/processed_xxx.json"}'
```

## Note

Các script này chỉ dùng cho setup/testing, không phải core system.
Core functionality đã được tích hợp vào `app/services/` và `app/api/`.
