"""
Ví dụ về cách sử dụng trường summary mới trong economic_indicators

Trường summary đã được thêm vào bảng economic_indicators để lưu trữ
tóm tắt ngắn về tình hình kinh tế của kỳ đó.

Sau khi chạy migration (alembic upgrade head), bạn có thể:
"""

# ============================================
# 1. TẠO MỚI CHỈ SỐ KINH TẾ VỚI TÓM TẮT
# ============================================

example_create_payload = {
    "period_type": "quarterly",
    "period_start": "2025-01-01",
    "period_end": "2025-09-30",
    "period_label": "9 tháng đầu năm 2025",
    "year": 2025,
    "quarter": 3,
    "province": "Hưng Yên",
    "region": "Bắc",
    
    # Các chỉ số kinh tế
    "grdp_growth_rate": 8.01,
    "iip_growth_rate": 9.5,
    "retail_services_growth": 12.3,
    "total_investment": 15000.0,
    "state_budget_revenue": 8500.0,
    "sbr_growth_rate": 15.2,
    
    # Tóm tắt ngắn - FIELD MỚI
    "summary": "Kinh tế Hưng Yên 9 tháng đầu năm 2025 duy trì đà tăng trưởng tích cực, GRDP tăng 8,01%, công nghiệp chế biến – chế tạo và thương mại dịch vụ là động lực chính. Đầu tư và thu ngân sách tăng mạnh, tạo nền tảng vững chắc cho mục tiêu tăng trưởng cao năm 2026.",
    
    "data_source": "Cục Thống kê Hưng Yên",
    "is_verified": 1
}

# ============================================
# 2. CẬP NHẬT TÓM TẮT CHO CHỈ SỐ CÓ SẴN
# ============================================

example_update_payload = {
    "summary": "Kinh tế Hà Nội Quý 4/2025 tăng trưởng ấn tượng với GRDP đạt 7.8%, dẫn đầu bởi ngành dịch vụ và công nghiệp công nghệ cao. FDI giải ngân tăng 25%, thu hút nhiều dự án lớn trong lĩnh vực bán dẫn và AI."
}

# ============================================
# 3. QUERY VÀ HIỂN THỊ TÓM TẮT TRÊN DASHBOARD
# ============================================

"""
API Endpoint: GET /api/v1/economic-indicators/

Response sẽ bao gồm trường summary:
{
  "data": [
    {
      "id": 1,
      "period_label": "9 tháng đầu năm 2025",
      "province": "Hưng Yên",
      "grdp_growth_rate": 8.01,
      "iip_growth_rate": 9.5,
      "summary": "Kinh tế Hưng Yên 9 tháng đầu năm 2025 duy trì đà tăng trưởng tích cực...",
      ...
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
"""

# ============================================
# 4. HIỂN THỊ TÓM TẮT TRÊN DASHBOARD (Frontend)
# ============================================

dashboard_card_example = """
<!-- Card hiển thị chỉ số kinh tế với tóm tắt -->
<div class="economic-indicator-card">
    <div class="card-header">
        <h3>{{ indicator.province }} - {{ indicator.period_label }}</h3>
        <span class="growth-badge">GRDP: {{ indicator.grdp_growth_rate }}%</span>
    </div>
    
    <div class="card-body">
        <!-- Các chỉ số chính -->
        <div class="metrics-grid">
            <div class="metric">
                <span class="label">IIP</span>
                <span class="value">{{ indicator.iip_growth_rate }}%</span>
            </div>
            <div class="metric">
                <span class="label">Bán lẻ & DV</span>
                <span class="value">{{ indicator.retail_services_growth }}%</span>
            </div>
            <div class="metric">
                <span class="label">Thu NS</span>
                <span class="value">{{ indicator.sbr_growth_rate }}%</span>
            </div>
        </div>
        
        <!-- TÓM TẮT NGẮN - HIỂN THỊ NỔI BẬT -->
        <div class="summary-section">
            <h4>Đánh giá tổng quan</h4>
            <p class="summary-text">{{ indicator.summary }}</p>
        </div>
    </div>
    
    <div class="card-footer">
        <span class="source">Nguồn: {{ indicator.data_source }}</span>
        <a href="/economic-indicators/{{ indicator.id }}">Xem chi tiết →</a>
    </div>
</div>
"""

# ============================================
# 5. CURL EXAMPLES
# ============================================

curl_create = """
# Tạo mới chỉ số kinh tế với summary
curl -X POST "http://localhost:8548/api/v1/economic-indicators/" \\
  -H "Content-Type: application/json" \\
  -d '{
    "period_type": "quarterly",
    "period_start": "2025-01-01",
    "period_end": "2025-09-30",
    "period_label": "9 tháng đầu năm 2025",
    "year": 2025,
    "quarter": 3,
    "province": "Hưng Yên",
    "grdp_growth_rate": 8.01,
    "iip_growth_rate": 9.5,
    "summary": "Kinh tế Hưng Yên 9 tháng đầu năm 2025 duy trì đà tăng trưởng tích cực, GRDP tăng 8,01%, công nghiệp chế biến – chế tạo và thương mại dịch vụ là động lực chính."
  }'
"""

curl_update = """
# Cập nhật summary cho chỉ số có sẵn
curl -X PUT "http://localhost:8548/api/v1/economic-indicators/1" \\
  -H "Content-Type: application/json" \\
  -d '{
    "summary": "Kinh tế Hà Nội Quý 4/2025 tăng trưởng ấn tượng với GRDP đạt 7.8%..."
  }'
"""

curl_query = """
# Query chỉ số kinh tế (kết quả sẽ bao gồm summary)
curl -X GET "http://localhost:8548/api/v1/economic-indicators/?province=Hưng Yên&year=2025"
"""

# ============================================
# 6. PYTHON CODE EXAMPLE
# ============================================

python_example = """
import requests

# Tạo mới indicator với summary
def create_indicator_with_summary():
    url = "http://localhost:8548/api/v1/economic-indicators/"
    data = {
        "period_type": "quarterly",
        "period_start": "2025-01-01",
        "period_end": "2025-09-30",
        "period_label": "9 tháng đầu năm 2025",
        "year": 2025,
        "quarter": 3,
        "province": "Hưng Yên",
        "grdp_growth_rate": 8.01,
        "summary": "Kinh tế Hưng Yên 9 tháng đầu năm 2025 duy trì đà tăng trưởng tích cực, GRDP tăng 8,01%, công nghiệp chế biến – chế tạo và thương mại dịch vụ là động lực chính. Đầu tư và thu ngân sách tăng mạnh, tạo nền tảng vững chắc cho mục tiêu tăng trưởng cao năm 2026."
    }
    response = requests.post(url, json=data)
    return response.json()

# Lấy và hiển thị summary
def display_indicators():
    url = "http://localhost:8548/api/v1/economic-indicators/"
    params = {"province": "Hưng Yên", "year": 2025}
    response = requests.get(url, params=params)
    data = response.json()
    
    for indicator in data['data']:
        print(f"\\n{'='*60}")
        print(f"Tỉnh: {indicator['province']} - {indicator['period_label']}")
        print(f"GRDP: {indicator.get('grdp_growth_rate', 'N/A')}%")
        print(f"\\nTóm tắt:")
        print(f"{indicator.get('summary', 'Chưa có tóm tắt')}")
        print(f"{'='*60}")

if __name__ == "__main__":
    # create_indicator_with_summary()
    display_indicators()
"""

# ============================================
# 7. GỢI Ý NỘI DUNG CHO TRƯỜNG SUMMARY
# ============================================

summary_guidelines = """
Gợi ý nội dung cho trường summary (2-4 câu, khoảng 150-250 từ):

1. Câu đầu: Đánh giá tổng quan
   - Tình hình kinh tế chung (tích cực, ổn định, chững lại, v.v.)
   - Tốc độ tăng trưởng GRDP
   - Các ngành động lực chính

2. Câu giữa: Các điểm nhấn
   - Chỉ số nổi bật (xuất khẩu, FDI, đầu tư, thu ngân sách)
   - So sánh với cùng kỳ năm trước (nếu có)
   - Các thành tựu đáng chú ý

3. Câu cuối: Triển vọng/Kết luận
   - Động lực tăng trưởng cho kỳ tiếp theo
   - Nền tảng cho mục tiêu dài hạn
   - Thách thức cần lưu ý (nếu có)

Ví dụ mẫu:
- "Kinh tế [Tỉnh] [Kỳ] duy trì đà tăng trưởng [tích cực/ổn định/mạnh mẽ], 
   GRDP tăng [X]%, [ngành A] và [ngành B] là động lực chính. 
   [Chỉ số nổi bật] tăng [Y]%, đóng góp quan trọng vào tăng trưởng chung. 
   [Triển vọng/kết luận về tương lai]."
"""

print("File ví dụ đã được tạo thành công!")
print("Các thay đổi đã thực hiện:")
print("  1. Model: Đã thêm trường 'summary' (Text, nullable=True)")
print("  2. Schema: Đã thêm 'summary' vào Base, Update, Response schemas")
print("  3. Migration: Đã tạo file migration để thêm cột vào database")
print("  4. API: Trường summary sẽ tự động được xử lý bởi các endpoint hiện có")
print("")
print("Để áp dụng migration:")
print("   cd /home/ai_team/lab/pipeline_mxh/fastapi-base")
print("   alembic upgrade head")
print("")
print("📖 Xem file này để biết cách sử dụng!")
