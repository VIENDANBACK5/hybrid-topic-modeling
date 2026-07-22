# Quick Reference - 4 New LLM Extraction Services

## 📋 Services Summary

| # | Service | Script | Target Table | API Endpoint (Async) | API Endpoint (Sync) |
|---|---------|--------|--------------|---------------------|---------------------|
| 1 | **Kinh tế số** | `extract_digital_economy.py` | `digital_economy_detail` | `/llm-extraction/extract-digital-economy` | `/llm-extraction/extract-digital-economy/sync` |
| 2 | **Thu hút FDI** | `extract_fdi.py` | `fdi_detail` | `/llm-extraction/extract-fdi` | `/llm-extraction/extract-fdi/sync` |
| 3 | **Chuyển đổi số** | `extract_digital_transformation.py` | `digital_transformation_detail` | `/llm-extraction/extract-digital-transformation` | `/llm-extraction/extract-digital-transformation/sync` |
| 4 | **Chỉ số SX Công nghiệp (PII)** | `extract_pii.py` | `pii_detail` | `/llm-extraction/extract-pii` | `/llm-extraction/extract-pii/sync` |

## 🚀 Quick Test Commands

### Test All Endpoints
```bash
python test_new_extractions.py
```

### Test Individual Endpoints (curl)
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

### Run Scripts Directly
```bash
cd /home/ai_team/lab/pipeline_mxh/fastapi-base

# Kinh tế số
python call_llm/extract_digital_economy.py

# FDI
python call_llm/extract_fdi.py

# Chuyển đổi số
python call_llm/extract_digital_transformation.py

# PII
python call_llm/extract_pii.py
```

## 📊 Key Features per Service

### 1. Kinh tế số (Digital Economy)
**Key Metrics**: GDP kinh tế số, TMĐT doanh thu, thanh toán điện tử, startup, fintech, internet penetration

### 2. FDI
**Key Metrics**: Vốn đăng ký/giải ngân, số dự án, phân bổ theo ngành/quốc gia, KCN, xuất khẩu FDI

### 3. Chuyển đổi số (DX)
**Key Metrics**: Chỉ số CĐS, chính quyền điện tử, dịch vụ công online, cloud, AI/IoT projects, smart city

### 4. PII
**Key Metrics**: Chỉ số IIP, giá trị SX công nghiệp, các ngành CN, năng suất, sản lượng thép/xi măng/điện

## 🔍 Quick Database Queries

```sql
-- Count extracted records
SELECT 
  'digital_economy' as table_name, COUNT(*) as records 
FROM digital_economy_detail WHERE data_source = 'LLM Extraction'
UNION ALL
SELECT 
  'fdi', COUNT(*) 
FROM fdi_detail WHERE data_source = 'LLM Extraction'
UNION ALL
SELECT 
  'digital_transformation', COUNT(*) 
FROM digital_transformation_detail WHERE data_source = 'LLM Extraction'
UNION ALL
SELECT 
  'pii', COUNT(*) 
FROM pii_detail WHERE data_source = 'LLM Extraction';

-- Recent extractions
SELECT source_post_id, province, year, created_at 
FROM digital_economy_detail 
WHERE data_source = 'LLM Extraction' 
ORDER BY created_at DESC LIMIT 10;
```

## ⚙️ Environment Variables

```bash
export OPENROUTER_API_KEY="your_key_here"
export LLM_MODEL="openai/gpt-4o-mini"
export BATCH_SIZE=50
export DELAY_BETWEEN_CALLS=1
```

## 📝 Log Files Location

```
call_llm/
├── digital_economy_extraction.log
├── fdi_extraction.log
├── digital_transformation_extraction.log
└── pii_extraction.log
```

## 🎯 Next Steps

1. ✅ **Test endpoints**: `python test_new_extractions.py`
2. ✅ **Check logs**: Xem các log files để verify extraction
3. ✅ **Verify data**: Query database để check kết quả
4. 🔄 **Monitor**: Theo dõi accuracy và performance
5. 🔧 **Tune**: Adjust prompts nếu cần cải thiện accuracy
