"""PII (Provincial Industrial Index) Detail Model - Chỉ số sản xuất công nghiệp cấp tỉnh

PII - Provincial Industrial Index (Chỉ số sản xuất công nghiệp cấp tỉnh) đo lường 
sản lượng sản xuất công nghiệp của một địa phương theo thời gian.

Chỉ số này tương tự IIP (Index of Industrial Production) nhưng tập trung vào cấp tỉnh.

Chỉ số này đo lường:
- Sản lượng sản xuất công nghiệp
- Tăng trưởng các ngành công nghiệp
- Cơ cấu công nghiệp
- Hiệu quả sản xuất
- Đóng góp của từng ngành công nghiệp
"""
from sqlalchemy import Column, Numeric, String, Integer, Index
from app.models.model_economic_base import EconomicIndicatorBase


class PIIDetail(EconomicIndicatorBase):
    """
    Chỉ số Sản xuất Công nghiệp cấp Tỉnh (PII - Provincial Industrial Index)
    Đo lường sản lượng và tăng trưởng công nghiệp tại địa phương
    """
    __tablename__ = "pii_detail"
    
    # === CHỈ SỐ TỔNG HỢP ===
    pii_overall = Column(Numeric, comment='Chỉ số IIP tổng hợp (Index, base=100)')
    pii_growth_rate = Column(Numeric, comment='Tốc độ tăng trưởng IIP (%)')
    industrial_output_value = Column(Numeric, comment='Giá trị sản xuất công nghiệp (tỷ VNĐ)')
    
    # === PHÂN THEO NGÀNH CÔNG NGHIỆP (VSIC Level 1) ===
    # Khai khoáng
    mining_index = Column(Numeric, comment='Chỉ số khai khoáng (Index)')
    mining_output = Column(Numeric, comment='Giá trị sản xuất khai khoáng (tỷ VNĐ)')
    mining_growth = Column(Numeric, comment='Tăng trưởng khai khoáng (%)')
    
    # Công nghiệp chế biến, chế tạo
    manufacturing_index = Column(Numeric, comment='Chỉ số công nghiệp chế biến (Index)')
    manufacturing_output = Column(Numeric, comment='Giá trị sản xuất chế biến (tỷ VNĐ)')
    manufacturing_growth = Column(Numeric, comment='Tăng trưởng chế biến (%)')
    
    # Sản xuất và phân phối điện, khí đốt, nước nóng
    electricity_index = Column(Numeric, comment='Chỉ số điện, khí đốt (Index)')
    electricity_output = Column(Numeric, comment='Giá trị sản xuất điện, khí đốt (tỷ VNĐ)')
    electricity_growth = Column(Numeric, comment='Tăng trưởng điện, khí đốt (%)')
    
    # Cung cấp nước, xử lý rác thải
    water_waste_index = Column(Numeric, comment='Chỉ số cấp nước, xử lý rác (Index)')
    water_waste_output = Column(Numeric, comment='Giá trị cấp nước, xử lý rác (tỷ VNĐ)')
    water_waste_growth = Column(Numeric, comment='Tăng trưởng cấp nước, xử lý rác (%)')
    
    # === CÁC NGÀNH CÔNG NGHIỆP CHẾ TẠO CHI TIẾT ===
    # Chế biến thực phẩm
    food_processing_index = Column(Numeric, comment='Chỉ số chế biến thực phẩm (Index)')
    food_processing_output = Column(Numeric, comment='Sản lượng chế biến thực phẩm (tỷ VNĐ)')
    
    # Dệt may
    textile_index = Column(Numeric, comment='Chỉ số dệt may (Index)')
    textile_output = Column(Numeric, comment='Sản lượng dệt may (tỷ VNĐ)')
    
    # Da giày
    leather_footwear_index = Column(Numeric, comment='Chỉ số da giày (Index)')
    leather_footwear_output = Column(Numeric, comment='Sản lượng da giày (tỷ VNĐ)')
    
    # Gỗ và sản phẩm từ gỗ
    wood_products_index = Column(Numeric, comment='Chỉ số sản phẩm gỗ (Index)')
    wood_products_output = Column(Numeric, comment='Sản lượng sản phẩm gỗ (tỷ VNĐ)')
    
    # Hóa chất và sản phẩm hóa chất
    chemical_index = Column(Numeric, comment='Chỉ số hóa chất (Index)')
    chemical_output = Column(Numeric, comment='Sản lượng hóa chất (tỷ VNĐ)')
    
    # Cao su và plastic
    rubber_plastic_index = Column(Numeric, comment='Chỉ số cao su plastic (Index)')
    rubber_plastic_output = Column(Numeric, comment='Sản lượng cao su plastic (tỷ VNĐ)')
    
    # Kim loại
    metal_index = Column(Numeric, comment='Chỉ số kim loại (Index)')
    metal_output = Column(Numeric, comment='Sản lượng kim loại (tỷ VNĐ)')
    
    # Sản phẩm điện tử, máy tính
    electronics_index = Column(Numeric, comment='Chỉ số điện tử, máy tính (Index)')
    electronics_output = Column(Numeric, comment='Sản lượng điện tử, máy tính (tỷ VNĐ)')
    
    # Thiết bị điện
    electrical_equipment_index = Column(Numeric, comment='Chỉ số thiết bị điện (Index)')
    electrical_equipment_output = Column(Numeric, comment='Sản lượng thiết bị điện (tỷ VNĐ)')
    
    # Phương tiện vận tải
    vehicle_index = Column(Numeric, comment='Chỉ số phương tiện vận tải (Index)')
    vehicle_output = Column(Numeric, comment='Sản lượng phương tiện vận tải (tỷ VNĐ)')
    
    # === PHÂN THEO LOẠI HÌNH DOANH NGHIỆP ===
    state_owned_pii = Column(Numeric, comment='IIP khu vực nhà nước (Index)')
    private_pii = Column(Numeric, comment='IIP khu vực tư nhân (Index)')
    fdi_pii = Column(Numeric, comment='IIP khu vực FDI (Index)')
    
    state_owned_output = Column(Numeric, comment='Sản lượng khu vực nhà nước (tỷ VNĐ)')
    private_output = Column(Numeric, comment='Sản lượng khu vực tư nhân (tỷ VNĐ)')
    fdi_output = Column(Numeric, comment='Sản lượng khu vực FDI (tỷ VNĐ)')
    
    # === CƠ CẤU CÔNG NGHIỆP ===
    manufacturing_share = Column(Numeric, comment='Tỷ trọng chế biến chế tạo (%)')
    hightech_industry_share = Column(Numeric, comment='Tỷ trọng công nghiệp công nghệ cao (%)')
    supporting_industry_share = Column(Numeric, comment='Tỷ trọng công nghiệp hỗ trợ (%)')
    
    # === NĂNG SUẤT VÀ HIỆU QUẢ ===
    labor_productivity = Column(Numeric, comment='Năng suất lao động (triệu VNĐ/người)')
    capacity_utilization = Column(Numeric, comment='Tỷ lệ sử dụng công suất (%)')
    output_per_enterprise = Column(Numeric, comment='Sản lượng bình quân/DN (tỷ VNĐ)')
    
    # === SẢN LƯỢNG CỤ THỂ ===
    steel_production = Column(Numeric, comment='Sản lượng thép (nghìn tấn)')
    cement_production = Column(Numeric, comment='Sản lượng xi măng (nghìn tấn)')
    fertilizer_production = Column(Numeric, comment='Sản lượng phân bón (nghìn tấn)')
    electricity_production = Column(Numeric, comment='Sản lượng điện (triệu kWh)')
    
    # === DOANH NGHIỆP CÔNG NGHIỆP ===
    industrial_enterprises = Column(Integer, comment='Số doanh nghiệp công nghiệp')
    large_enterprises = Column(Integer, comment='Số DN công nghiệp lớn')
    sme_industrial = Column(Integer, comment='Số DN công nghiệp vừa và nhỏ')
    
    # === LAO ĐỘNG CÔNG NGHIỆP ===
    industrial_workers = Column(Integer, comment='Số lao động trong công nghiệp (người)')
    skilled_workers = Column(Integer, comment='Số lao động có tay nghề (người)')
    average_wage_industrial = Column(Numeric, comment='Lương bình quân công nghiệp (triệu VNĐ)')
    
    __table_args__ = (
        Index('idx_pii_province_year', 'province', 'year'),
        Index('idx_pii_period', 'year', 'quarter', 'month'),
    )
