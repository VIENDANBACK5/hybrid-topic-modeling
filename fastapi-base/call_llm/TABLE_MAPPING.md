# Mapping: type_newspaper → Bảng detail

## Tổng quan
Mỗi `type_newspaper` trong `important_posts` được extract vào các bảng detail tương ứng.

---

## 1. **politics** → Xây dựng Đảng (3 posts)

### Bảng đích:
- ✅ `cadre_statistics_detail` - Thống kê số lượng cán bộ/biên chế
- ✅ `party_discipline_detail` - Kỷ luật Đảng/vi phạm
- ✅ `cadre_quality_detail` - Chất lượng cán bộ/đào tạo

### File: 
[`extract_xay_dung_dang.py`](extract_xay_dung_dang.py)

### Ví dụ dữ liệu:
- "Hưng Yên tạm giao gần 6500 biên chế năm 2025"
- "Kỷ luật 15 đảng viên vi phạm"

---

## 2. **medical** → Y tế (37 posts)

### Bảng đích:
- ✅ `health_statistics_detail` - Thống kê cơ sở y tế/bác sĩ/giường bệnh
- ✅ `health_insurance_detail` - Bảo hiểm y tế/phủ bì BHYT
- ✅ `preventive_health_detail` - Y tế dự phòng/tiêm chủng

### File:
[`extract_medical.py`](extract_medical.py)

### Ví dụ dữ liệu:
- "Bệnh viện đa khoa tỉnh có 500 giường bệnh"
- "Tỷ lệ tiêm chủng đạt 95%"

---

## 3. **education** → Giáo dục (22 posts)

### Bảng đích:
- ✅ `highschool_graduation_detail` - Tốt nghiệp THPT/tỷ lệ đỗ tốt nghiệp
- ✅ `tvet_employment_detail` - Dạy nghề/việc làm sau đào tạo

### File:
[`extract_education.py`](extract_education.py)

### Ví dụ dữ liệu:
- "Tỷ lệ tốt nghiệp THPT đạt 98%"
- "Sở GD&ĐT tuyển dụng viên chức"

---

## 4. **security** → An ninh - Trật tự (36 posts)

### Bảng đích:
- ✅ `security_detail` - An ninh chung/tội phạm
- ✅ `crime_prevention_detail` - Phòng chống tội phạm
- ✅ `traffic_safety_detail` - An toàn giao thông/tai nạn
- ✅ `public_order_detail` - Trật tự công cộng

### File:
[`extract_security.py`](extract_security.py)

### Ví dụ dữ liệu:
- "Số vụ tai nạn giao thông giảm 20%"
- "Phá 150 vụ án hình sự"

---

## 5. **society** → Văn hóa - Xã hội (5 posts)

### Bảng đích:
- ✅ `culture_lifestyle_stats_detail` - Văn hóa/lối sống/phong trào
- ✅ `cultural_infrastructure_detail` - Cơ sở văn hóa/di tích
- ✅ `culture_sport_access_detail` - Thể thao/thể dục thể thao
- ✅ `social_security_coverage_detail` - Bảo trợ xã hội/chính sách xã hội

### File:
[`extract_society.py`](extract_society.py)

### Ví dụ dữ liệu:
- "Xây dựng 50 nhà văn hóa cộng đồng"
- "Hỗ trợ 1000 hộ nghèo"

---

## 6. **transportation** → Giao thông (10 posts) ⚠️ TODO

### Bảng đích:
- ⏳ `transport_infrastructure_detail` - Hạ tầng giao thông
- ⏳ `traffic_congestion_detail` - Ùn tắc giao thông

### File:
`extract_transportation.py` (chưa tạo)

---

## 7. **policy** → Chính sách (2 posts) ⚠️ TODO

### Bảng đích:
- ⏳ `egovernment_detail` - Chính phủ điện tử
- ⏳ `par_index_detail` - Chỉ số PAR (cải cách hành chính)
- ⏳ `sipas_detail` - Chỉ số SIPAS

### File:
`extract_policy.py` (chưa tạo)

---

## 8. **environment** → Môi trường (0 posts) ⚠️ Không có data

### Bảng đích:
- ⏳ `air_quality_detail` - Chất lượng không khí
- ⏳ `waste_management_detail` - Quản lý chất thải
- ⏳ `climate_resilience_detail` - Khí hậu/biến đổi khí hậu

### File:
`extract_environment.py` (chưa tạo)

---

## 9. **management** → Quản lý ⚠️ Không có trong DB

Không có posts với type_newspaper='management' trong important_posts

---

## Các bảng detail khác (không map với important_posts)

Các bảng này được fill từ nguồn khác (articles table hoặc external API):

### Kinh tế:
- `grdp_detail` - GRDP
- `cpi_detail` - CPI
- `iip_detail` - IIP
- `export_detail` - Xuất khẩu
- `investment_detail` - Đầu tư
- `agri_production_detail` - Nông nghiệp
- `retail_services_detail` - Bán lẻ/dịch vụ
- `budget_revenue_detail` - Ngân sách

### Chỉ số:
- `hdi_detail` - HDI
- `eqi_detail` - EQI
- `haq_index_detail` - HAQ

### Khác:
- `corruption_prevention_detail` - Phòng chống tham nhũng
- `social_budget_detail` - Ngân sách xã hội
- `planning_progress_detail` - Tiến độ quy hoạch

---

## Tóm tắt mapping

| type_newspaper | Posts | Bảng đích | File | Status |
|---------------|-------|-----------|------|--------|
| **politics** | 3 | 3 bảng | extract_xay_dung_dang.py | ✅ Done |
| **medical** | 37 | 3 bảng | extract_medical.py | ✅ Done |
| **education** | 22 | 2 bảng | extract_education.py | ✅ Done |
| **security** | 36 | 4 bảng | extract_security.py | ✅ Done |
| **society** | 5 | 4 bảng | extract_society.py | ✅ Done |
| transportation | 10 | 2 bảng | - | ⏳ TODO |
| policy | 2 | 3 bảng | - | ⏳ TODO |
| environment | 0 | 3 bảng | - | ⏳ TODO |
| economy | 37 | - | (không xử lý) | - |

**Tổng: 16 bảng detail được cover bởi 5 file extraction**
