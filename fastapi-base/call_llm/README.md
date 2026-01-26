# LLM Extraction System - Hệ thống trích xuất thuần LLM

## Tổng quan

Hệ thống trích xuất dữ liệu **100% bằng LLM** từ bảng `important_posts` dựa trên `type_newspaper`.

## Cấu trúc file

```
call_llm/
├── __init__.py
├── extract_xay_dung_dang.py    # politics - Xây dựng Đảng (3 posts)
├── extract_medical.py           # medical - Y tế (37 posts) 
├── extract_education.py         # education - Giáo dục (22 posts)
├── extract_security.py          # security - An ninh (36 posts)
├── extract_society.py           # society - Văn hóa xã hội (5 posts)
└── README.md
```

## API Endpoints

Base URL: `http://localhost:7777/api/llm`

| Lĩnh vực | type_newspaper | Async Endpoint | Sync Endpoint | Posts |
|----------|---------------|----------------|---------------|-------|
| Xây dựng Đảng | politics | POST `/extract-politics` | POST `/extract-politics/sync` | 3 |
| Y tế | medical | POST `/extract-medical` | POST `/extract-medical/sync` | 37 |
| Giáo dục | education | POST `/extract-education` | POST `/extract-education/sync` | 22 |
| An ninh | security | POST `/extract-security` | POST `/extract-security/sync` | 36 |
| Văn hóa - Xã hội | society | POST `/extract-society` | POST `/extract-society/sync` | 5 |

## Cách sử dụng

### Test endpoint (Sync - có kết quả ngay):

```bash
# Y tế (37 posts)
curl -X POST http://localhost:7777/api/llm/extract-medical/sync | jq '.'

# Giáo dục (22 posts)
curl -X POST http://localhost:7777/api/llm/extract-education/sync | jq '.'

# An ninh (36 posts) 
curl -X POST http://localhost:7777/api/llm/extract-security/sync | jq '.'

# Xã hội (5 posts)
curl -X POST http://localhost:7777/api/llm/extract-society/sync | jq '.'

# Xây dựng Đảng (3 posts)
curl -X POST http://localhost:7777/api/llm/extract-politics/sync | jq '.'
```

### Production (Async - chạy background):

```bash
curl -X POST http://localhost:7777/api/llm/extract-medical
```

Response:
```json
{
  "status": "accepted",
  "message": "LLM extraction đã được khởi chạy ở background",
  "field": "Y tế",
  "type_newspaper": "medical",
  "timestamp": "2026-01-21T10:30:00"
}
```

## Tùy chỉnh Schema

Mỗi file extraction có prompt template cần customize theo bảng detail:

### Ví dụ: extract_medical.py

```python
def extract_health_statistics(content: str, post_id: int, province: str):
    prompt = f"""
Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "total_hospitals": null,      # Customize field này
  "total_clinics": null,         # Và field này
  "vaccination_rate": null       # Theo bảng health_statistics_detail
}}

Giải thích các trường:
- total_hospitals: Tổng số bệnh viện
- total_clinics: Tổng số phòng khám
...
"""
```

## TODO

- [ ] Kiểm tra schema của các bảng detail trong DB
- [ ] Customize prompt cho từng lĩnh vực theo đúng schema
- [ ] Tạo API endpoints để lưu vào DB (hiện chỉ extract, chưa save)
- [ ] Thêm 3 lĩnh vực còn thiếu:
  - `extract_transportation.py` (10 posts)
  - `extract_environment.py` (chưa có data)
  - `extract_policy.py` (2 posts)

## Logs

Mỗi lĩnh vực có file log riêng:
- `call_llm/medical_extraction.log`
- `call_llm/education_extraction.log`
- `call_llm/security_extraction.log`
- `call_llm/society_extraction.log`
- `call_llm/xay_dung_dang_extraction.log`

## Data Distribution

```
medical        : 37 posts ████████████████████
education      : 22 posts ████████████
security       : 36 posts ███████████████████
society        :  5 posts ███
politics       :  3 posts ██
policy         :  2 posts █
transportation : 10 posts █████
economy        : 37 posts (không có trong list yêu cầu)
```

## Rebuild để load code mới

```bash
cd /home/ai_team/lab/pipeline_mxh/fastapi-base
docker compose up -d --build app
```
