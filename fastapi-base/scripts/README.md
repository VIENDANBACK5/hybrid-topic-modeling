# Utility Scripts

Các script utility để setup và populate data.

## Scripts

### `seed_custom_topics.py`
Seed custom topics vào database (12 topics mặc định).

### `load_all_data.py`
Load data từ external API (192.168.30.28:8000) vào database.

### `sync_external_api.py`
Sync data từ external API, update theo schedule.

### `fill_all_tables.py`
Fill các bảng statistics với data để test.

## Usage

```bash
# From root directory
export POSTGRES_PORT=5555
python scripts/seed_custom_topics.py
python scripts/load_all_data.py
```

## Note

Các script này chỉ dùng cho setup/testing, không phải core system.
Core functionality đã được tích hợp vào `app/services/` và `app/api/`.
