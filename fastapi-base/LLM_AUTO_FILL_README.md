# LLM Auto-Fill System - 4 New Extraction Services

## 📋 Tổng quan

Đã tạo thành công 4 extraction services mới sử dụng LLM để tự động trích xuất dữ liệu từ bảng `important_posts`:

### ✅ Services đã tạo:

1. **Kinh tế số (Digital Economy)** - `extract_digital_economy.py`
2. **Thu hút FDI** - `extract_fdi.py`  
3. **Chuyển đổi số (Digital Transformation)** - `extract_digital_transformation.py`
4. **Chỉ số Sản xuất Công nghiệp (PII)** - `extract_pii.py`

---

## 📂 Files đã tạo

### 1. Extraction Services
```
fastapi-base/call_llm/
├── extract_digital_economy.py          # Kinh tế số
├── extract_fdi.py                       # Thu hút FDI
├── extract_digital_transformation.py   # Chuyển đổi số
└── extract_pii.py                       # PII
```

### 2. API Endpoints
- **File**: `app/api/api_llm_extraction.py`
- **Endpoints đã thêm**: 8 endpoints (4 async + 4 sync)

### 3. Test Script
- **File**: `test_new_extractions.py`
- Script để test các endpoints mới

---

## 🎯 Chi tiết từng Service

### 1. Kinh tế số (Digital Economy)

**Bảng đích**: `digital_economy_detail`

**Dữ liệu trích xuất**:
- GDP kinh tế số, tỷ trọng trong GDP
- Thương mại điện tử (TMĐT): doanh thu, người dùng, giao dịch
- Thanh toán điện tử: giá trị, giao dịch, ví điện tử
- Doanh nghiệp công nghệ số, startup, unicorn
- Fintech, Edtech, Healthtech revenue
- Hạ tầng số: Internet, băng thông, 4G/5G
- Xuất khẩu dịch vụ số, phần mềm
- Nhân lực số, đào tạo IT

**API Endpoints**:
- `POST /llm-extraction/extract-digital-economy` (async)
- `POST /llm-extraction/extract-digital-economy/sync` (sync)

**Filter keywords**:
- kinh tế số, thương mại điện tử, tmđt, e-commerce
- thanh toán điện tử, fintech, startup, công nghệ số

---

### 2. Thu hút FDI

**Bảng đích**: `fdi_detail`

**Dữ liệu trích xuất**:
- Vốn FDI: đăng ký, giải ngân, tích lũy
- Số lượng dự án: mới, tăng vốn, góp vốn
- Phân bổ theo ngành: sản xuất, BĐS, xây dựng, CNTT
- Phân bổ theo quốc gia: Nhật, Hàn, Singapore, Trung Quốc, etc.
- Hình thức: 100% NN, liên doanh, hợp đồng
- Tác động: GRDP, xuất khẩu, việc làm, thu NS
- Khu công nghiệp, khu kinh tế

**API Endpoints**:
- `POST /llm-extraction/extract-fdi` (async)
- `POST /llm-extraction/extract-fdi/sync` (sync)

**Filter keywords**:
- fdi, đầu tư nước ngoài, đầu tư trực tiếp
- vốn nước ngoài, dự án fdi, khu công nghiệp

---

### 3. Chuyển đổi số (Digital Transformation)

**Bảng đích**: `digital_transformation_detail`

**Dữ liệu trích xuất**:
- Chỉ số CĐS tổng hợp, xếp hạng, mức độ trưởng thành
- Chính quyền điện tử: dịch vụ công trực tuyến, mức độ 3/4
- Hệ thống thông tin: cổng TTĐT, CSDL tích hợp
- Hạ tầng số: Cloud, data center, băng thông, 5G
- CĐS doanh nghiệp: SME, DN lớn, AI, IoT, Big Data
- Năng lực số: kỹ năng số, đào tạo
- Ứng dụng: AI, IoT, Blockchain, Smart City
- CĐS nông nghiệp, y tế

**API Endpoints**:
- `POST /llm-extraction/extract-digital-transformation` (async)
- `POST /llm-extraction/extract-digital-transformation/sync` (sync)

**Filter keywords**:
- chuyển đổi số, cds, digital transformation
- chính quyền điện tử, dịch vụ công trực tuyến
- cloud, smart city, thành phố thông minh

---

### 4. Chỉ số Sản xuất Công nghiệp (PII)

**Bảng đích**: `pii_detail`

**Dữ liệu trích xuất**:
- Chỉ số IIP tổng hợp, tăng trưởng
- Giá trị sản xuất công nghiệp
- Các ngành: khai khoáng, chế biến, điện, nước
- Ngành chi tiết: thực phẩm, dệt may, da giày, gỗ, hóa chất, điện tử, ô tô
- Phân theo loại hình: nhà nước, tư nhân, FDI
- Cơ cấu công nghiệp, công nghệ cao
- Năng suất lao động, công suất
- Sản lượng cụ thể: thép, xi măng, phân bón, điện
- Doanh nghiệp và lao động công nghiệp

**API Endpoints**:
- `POST /llm-extraction/extract-pii` (async)
- `POST /llm-extraction/extract-pii/sync` (sync)

**Filter keywords**:
- sản xuất công nghiệp, công nghiệp, chế biến chế tạo
- iip, khu công nghiệp, giá trị sản xuất, sản lượng

---

## 🚀 Cách sử dụng

### 1. Khởi động FastAPI server

```bash
cd /home/ai_team/lab/pipeline_mxh/fastapi-base
uvicorn app.main:app --host 0.0.0.0 --port 7777 --reload
```

### 2. Test endpoints

#### Option A: Sử dụng test script
```bash
python test_new_extractions.py
```

#### Option B: Gọi trực tiếp bằng curl

**Async (trigger background task)**:
```bash
# Kinh tế số
curl -X POST http://localhost:7777/llm-extraction/extract-digital-economy

# FDI
curl -X POST http://localhost:7777/llm-extraction/extract-fdi

# Chuyển đổi số
curl -X POST http://localhost:7777/llm-extraction/extract-digital-transformation

# PII
curl -X POST http://localhost:7777/llm-extraction/extract-pii
```

**Sync (chờ kết quả)**:
```bash
# Kinh tế số
curl -X POST http://localhost:7777/llm-extraction/extract-digital-economy/sync

# FDI
curl -X POST http://localhost:7777/llm-extraction/extract-fdi/sync

# Chuyển đổi số
curl -X POST http://localhost:7777/llm-extraction/extract-digital-transformation/sync

# PII
curl -X POST http://localhost:7777/llm-extraction/extract-pii/sync
```

#### Option C: Swagger UI
Mở browser: http://localhost:7777/docs
- Tìm section "LLM Extraction"
- Thử các endpoints mới

### 3. Chạy trực tiếp script

```bash
# Kinh tế số
python call_llm/extract_digital_economy.py

# FDI
python call_llm/extract_fdi.py

# Chuyển đổi số
python call_llm/extract_digital_transformation.py

# PII
python call_llm/extract_pii.py
```

---

## ⚙️ Cấu hình

Các biến môi trường cần thiết:

```bash
# LLM API Configuration
OPENROUTER_API_KEY=your_api_key_here    # hoặc OPENAI_API_KEY
LLM_MODEL=openai/gpt-4o-mini           # Model để sử dụng
BATCH_SIZE=50                           # Số posts xử lý mỗi lần
DELAY_BETWEEN_CALLS=1                   # Delay giữa các LLM calls (giây)

# API Configuration
API_BASE_URL=http://localhost:7777
```

---

## 📊 Cấu trúc Response

### Async Endpoint Response (202 Accepted):
```json
{
  "status": "accepted",
  "message": "LLM extraction đã được khởi chạy ở background",
  "field": "Kinh tế số",
  "table": "digital_economy_detail",
  "timestamp": "2026-01-22T10:30:00"
}
```

### Sync Endpoint Response (200 OK):
```json
{
  "status": "success",
  "field": "Kinh tế số",
  "table": "digital_economy_detail",
  "result": {
    "processed": 50,
    "extracted": 15
  },
  "timestamp": "2026-01-22T10:35:00"
}
```

---

## 📝 Logging

Mỗi extraction service tạo log file riêng:

```
call_llm/
├── digital_economy_extraction.log
├── fdi_extraction.log
├── digital_transformation_extraction.log
└── pii_extraction.log
```

Log format:
```
2026-01-22 10:30:00 - INFO - 🤖 BẮT ĐẦU LLM EXTRACTION - KINH TẾ SỐ
2026-01-22 10:30:05 - INFO - ✅ Lấy được 50 posts về kinh tế số từ DB
2026-01-22 10:30:10 - INFO - 🔍 Post ID: 12345
2026-01-22 10:30:15 - INFO - ✅ Saved to digital_economy_detail
2026-01-22 10:35:00 - INFO - ✅ Đã xử lý: 50 posts
2026-01-22 10:35:00 - INFO - 📊 Extracted: 15 records
```

---

## 🔍 Kiểm tra kết quả trong Database

```sql
-- Kinh tế số
SELECT COUNT(*), province, year 
FROM digital_economy_detail 
WHERE data_source = 'LLM Extraction'
GROUP BY province, year;

-- FDI
SELECT COUNT(*), province, year 
FROM fdi_detail 
WHERE data_source = 'LLM Extraction'
GROUP BY province, year;

-- Chuyển đổi số
SELECT COUNT(*), province, year 
FROM digital_transformation_detail 
WHERE data_source = 'LLM Extraction'
GROUP BY province, year;

-- PII
SELECT COUNT(*), province, year 
FROM pii_detail 
WHERE data_source = 'LLM Extraction'
GROUP BY province, year;
```

---

## 🎯 Đặc điểm của LLM Extraction

### ✅ Ưu điểm:
1. **Linh hoạt**: Không cần regex, LLM tự nhận diện patterns
2. **Thông minh**: Hiểu ngữ cảnh, xử lý được câu văn phức tạp
3. **Đa dạng**: Trích xuất được nhiều loại chỉ số khác nhau
4. **Robust**: Xử lý được dữ liệu không chuẩn

### ⚠️ Lưu ý:
1. **Chi phí**: Mỗi LLM call có cost
2. **Tốc độ**: Chậm hơn regex extraction
3. **Chính xác**: Cần verify kết quả, có thể có false positives
4. **API Key**: Cần có OPENROUTER_API_KEY hoặc OPENAI_API_KEY

---

## 🔄 Workflow

```
important_posts (DB)
    ↓
Filter by keywords
    ↓
LLM Extraction
    ↓
JSON Response
    ↓
Validate & Transform
    ↓
Save to target table
    ↓
Log results
```

---

## 📈 Monitoring

Để monitor extraction progress:

1. **Check logs**: Xem file logs trong `call_llm/`
2. **Check database**: Query target tables
3. **API Response**: Xem số lượng processed/extracted
4. **Background tasks**: FastAPI sẽ log background task execution

---

## 🐛 Troubleshooting

### Issue: "No API key found"
**Solution**: Set environment variable
```bash
export OPENROUTER_API_KEY="your_key_here"
```

### Issue: "No posts found"
**Solution**: Check important_posts table có data không, và filter keywords có match không

### Issue: "LLM timeout"
**Solution**: Tăng timeout hoặc giảm BATCH_SIZE

### Issue: "Database error"
**Solution**: Check database connection, table schema

---

## 📚 Tài liệu tham khảo

- [extract_statistics.py](call_llm/extract_statistics.py) - Mẫu extraction service
- [api_llm_extraction.py](app/api/api_llm_extraction.py) - API endpoints
- [TABLE_MAPPING.md](call_llm/TABLE_MAPPING.md) - Mapping bảng và fields

---

## ✅ Checklist

- [x] Tạo 4 extraction services
- [x] Tạo 8 API endpoints (4 async + 4 sync)
- [x] Tạo test script
- [x] Tạo documentation
- [ ] Test với data thật
- [ ] Verify kết quả trong database
- [ ] Monitor performance và accuracy

---

**Created**: 2026-01-22  
**Author**: AI Team  
**Version**: 1.0
