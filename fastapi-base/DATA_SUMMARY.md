# TỔNG HỢP DỮ LIỆU THỐNG KÊ

## Đã xóa duplicates và thêm unique constraints

**Constraints đã thêm:**
- `uk_economic_source_dvhc` trên bảng `economic_statistics`
- `uk_political_source_dvhc` trên bảng `political_statistics`

Đảm bảo không có duplicate (source_post_id + dvhc)

---

## DỮ LIỆU KINH TẾ

### Xã Thư Vũ (2025)
- **Tổng giá trị sản xuất**: Trung bình ~2.982 tỷ đồng (có 3 số liệu khác nhau từ các bài viết)
  - 5.946 tỷ (giai đoạn 5 năm 2021-2025)
  - 1.500 tỷ (năm 2025)
- **Tốc độ tăng trưởng**: Trung bình 9,47%
- **Thu ngân sách**: 200 tỷ đồng
- **Hiệu suất thu NS**: 146%

### Phường Trà Lý (2025)
- **Tổng giá trị sản xuất**: Trung bình ~7.310 tỷ đồng (có nhiều số liệu)
  - 16.200 tỷ (giai đoạn 5 năm, không có năm cụ thể)
  - 16.276 tỷ (giai đoạn 2020-2025)
  - 3.795 tỷ (năm 2025)
  - 1.860 tỷ (xã Thái Ninh - có thể bị nhầm)
- **Tốc độ tăng trưởng**: Trung bình 7,47%
- **Thu ngân sách**: 319 tỷ đồng (năm 2025)
- **Hiệu suất thu NS**: 150,8%

---

## DỮ LIỆU CHÍNH TRỊ

### Xã Thư Vũ (2025)
- **Số tổ chức Đảng**: 50
- **Số Đảng viên**: ~1.485-1.499 (có 2 số liệu khác nhau)
  - Post 101: 1.485 Đảng viên, 29 chi bộ (quý III/2025)
  - Post 106: 1.499 Đảng viên (2025-2030)
- **Số chi bộ**: 29 (trong đó: 29 chi bộ thôn + các chi bộ cơ quan, trường học, y tế, quỹ tín dụng)

### Phường Trà Lý (2025)
- **Số tổ chức Đảng**: 62
- **Số Đảng viên**: 2.200
- **Số chi bộ**: 95
- **Đảng viên mới**: 70 người
- **Ghi chú**: Được thành lập từ 5 đơn vị sáp nhập, diện tích 20,94 km², dân số ~44.000 người

---

## VẤN ĐỀ ĐÃ PHÁT HIỆN VÀ KHẮC PHỤC

### Vấn đề ban đầu:
1. ✅ **Duplicate records**: Cùng 1 bài viết bị extract 2 lần
2. ✅ **Null values**: Nhiều trường bị null (đã clean)
3. ✅ **Số liệu gần giống**: 1500 vs 1499.999 vs 1499.99 (đã giữ lại 1 record)

### Nguyên nhân:
- Script chạy 2 lần với cùng posts
- Một số posts không có đủ thông tin nên LLM trả về null
- Các bài viết có số liệu hơi khác nhau (do nguồn hoặc thời điểm khác nhau)

### Giải pháp:
1. ✅ Xóa duplicates, giữ lại record có id nhỏ nhất
2. ✅ Thêm UNIQUE constraint (source_post_id + dvhc)
3. ⚠️  Cần review lại 1 số records có null để bổ sung thủ công nếu cần

---

## KẾT QUẢ CUỐI CÙNG

**Tổng số records:**
- Economic Statistics: **7 records** (3 xã Thư Vũ + 4 phường Trà Lý)
- Political Statistics: **3 records** (2 xã Thư Vũ + 1 phường Trà Lý)

**Chất lượng data:**
- ✅ Không còn duplicate
- ⚠️  Có một số null values (do bài viết không đề cập)
- ✅ Đã có unique constraint để tránh duplicate trong tương lai
