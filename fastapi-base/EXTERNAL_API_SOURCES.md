# 📊 External API Sources for Economic Indicators

## Hiện trạng

### ✅ Đang sử dụng:
1. **AQICN API** (Air Quality)
   - File: `app/services/aqi_service.py`
   - Endpoint: `https://api.waqi.info`
   - Status: ✅ Hoạt động tốt
   - Bảng: `air_quality_detail`

2. **Web Scraping** (Economic Indicators)
   - Source: `https://thongkehungyen.nso.gov.vn`
   - File: `app/services/universal_economic_extractor.py`
   - Status: ✅ Hoạt động
   - Bảng: `iip_detail`, `agri_production_detail`, `cpi_detail`, `retail_services_detail`, `investment_detail`, `budget_revenue_detail`

### ❌ Chưa có API cho:
- IIP (Industrial Production Index)
- GRDP (Provincial GDP)
- Agricultural Production
- Retail & Services
- Investment
- Budget Revenue
- Export/Import

---

## 🌐 Các API công khai có thể sử dụng

### 1. ⭐ World Bank API (RECOMMEND - FREE)

**Base URL:** `https://api.worldbank.org/v2/`

**Docs:** https://datahelpdesk.worldbank.org/knowledgebase/articles/889392

#### Indicators có sẵn cho Vietnam:

```bash
# GDP Growth Rate
curl "https://api.worldbank.org/v2/country/VN/indicator/NY.GDP.MKTP.KD.ZG?format=json&date=2020:2025"

# CPI Inflation
curl "https://api.worldbank.org/v2/country/VN/indicator/FP.CPI.TOTL.ZG?format=json&date=2020:2025"

# Exports of goods and services (% GDP)
curl "https://api.worldbank.org/v2/country/VN/indicator/NE.EXP.GNFS.ZS?format=json&date=2020:2025"

# Foreign direct investment, net inflows
curl "https://api.worldbank.org/v2/country/VN/indicator/BX.KLT.DINV.CD.WD?format=json&date=2020:2025"

# Industrial production index
curl "https://api.worldbank.org/v2/country/VN/indicator/NV.IND.TOTL.KD?format=json&date=2020:2025"
```

#### Response Example:
```json
{
  "indicator": {
    "id": "NY.GDP.MKTP.KD.ZG",
    "value": "GDP growth (annual %)"
  },
  "country": {"id": "VN", "value": "Viet Nam"},
  "date": "2024",
  "value": 7.09,
  "decimal": 1
}
```

**Ưu điểm:**
- ✅ Miễn phí, không cần API key
- ✅ Reliable, từ World Bank
- ✅ JSON format chuẩn
- ✅ Historical data đầy đủ

**Nhược điểm:**
- ❌ Chỉ có data cấp quốc gia (không có cấp tỉnh)
- ❌ Update chậm (quarterly/yearly)

---

### 2. IMF API

**Base URL:** `http://dataservices.imf.org/REST/SDMX_JSON.svc/`

**Docs:** https://datahelp.imf.org/knowledgebase/articles/667681-using-json-restful-web-service

```bash
# Get Vietnam macroeconomic data
curl "http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/IFS/Q.VN.NGDP_R_K_SA_IX"
```

**Ưu điểm:**
- ✅ Miễn phí
- ✅ Macro indicators đầy đủ

**Nhược điểm:**
- ❌ API format phức tạp (SDMX)
- ❌ Chỉ có cấp quốc gia

---

### 3. Asian Development Bank (ADB)

**Portal:** https://data.adb.org/

**Ưu điểm:**
- ✅ Có data khu vực Châu Á
- ✅ Infrastructure data

**Nhược điểm:**
- ⚠️ Cần registration
- ❌ Limited API access

---

### 4. Trading Economics API (PAID)

**Website:** https://tradingeconomics.com/vietnam/indicators

**Pricing:** $250-$750/month

**Ưu điểm:**
- ✅ Real-time data
- ✅ Comprehensive indicators
- ✅ Historical + Forecast

**Nhược điểm:**
- ❌ **Trả phí**
- ❌ Expensive

---

## 🎯 Recommendations

### Phase 1: Implement World Bank API Service
Tạo service mới để:
1. Lấy GDP growth, CPI, Export, FDI từ World Bank
2. Fill vào `grdp_detail`, `cpi_detail`, `export_detail`, `investment_detail`
3. Dùng làm **backup/validation** cho data từ web scraping

### Phase 2: Hybrid Approach
- **Cấp quốc gia**: World Bank API (yearly)
- **Cấp tỉnh**: Web scraping thongkehungyen.nso.gov.vn (monthly/quarterly)

### Phase 3: Consider Trading Economics
Nếu cần real-time data và có budget.

---

## 📝 Implementation Plan

### File mới cần tạo:
```
app/services/worldbank_service.py
```

### API endpoints cần:
```python
POST /api/economic/fetch-worldbank
  - Fetch data từ World Bank API
  - Fill vào các bảng detail
  - Return summary

GET /api/economic/worldbank-indicators
  - List các indicators có sẵn
```

### World Bank Indicator Mapping:
| Vietnam Indicator | World Bank Code | Table |
|-------------------|-----------------|-------|
| GDP Growth | NY.GDP.MKTP.KD.ZG | grdp_detail |
| CPI Inflation | FP.CPI.TOTL.ZG | cpi_detail |
| Exports | NE.EXP.GNFS.ZS | export_detail |
| FDI Inflows | BX.KLT.DINV.CD.WD | investment_detail |
| Industry VA | NV.IND.TOTL.KD | iip_detail |

---

## ⚠️ Important Notes

1. **Province-level data**: Không có API public
   - Phải tiếp tục web scraping từ GSO/Provincial sites

2. **Data frequency**:
   - World Bank: Yearly (chậm update)
   - Web scraping: Monthly/Quarterly (real-time hơn)

3. **Data validation**:
   - Dùng World Bank làm baseline
   - Compare với local scraping data

4. **Rate limits**:
   - World Bank: No official limit
   - Best practice: Add delay between requests

---

## 🔗 Useful Links

- World Bank Indicators Database: https://data.worldbank.org/indicator
- Vietnam Statistics Portal: https://www.gso.gov.vn/en/statistical-data/
- Hung Yen Statistics: https://thongkehungyen.nso.gov.vn
- AQICN API Docs: https://aqicn.org/json-api/doc/

