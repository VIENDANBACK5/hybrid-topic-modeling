"""Digital Economy Detail Model - Kinh tế số chi tiết

Kinh tế số (Digital Economy) là phần kinh tế dựa trên công nghệ số, bao gồm:
- Thương mại điện tử (e-commerce)
- Dịch vụ số (fintech, edtech, healthtech)
- Nền tảng số (platform economy)
- Nội dung số (digital content)
- Công nghiệp công nghệ thông tin

Chỉ số này đo lường:
- Quy mô kinh tế số (% GDP)
- Số lượng doanh nghiệp công nghệ số
- Doanh thu từ thương mại điện tử
- Số lượng giao dịch thanh toán điện tử
- Tốc độ tăng trưởng của các ngành số
"""
from sqlalchemy import Column, Numeric, String, Integer, Index
from app.models.model_economic_base import EconomicIndicatorBase


class DigitalEconomyDetail(EconomicIndicatorBase):
    """
    Chỉ số Kinh tế số chi tiết (Digital Economy Indicators)
    Đo lường sự phát triển của nền kinh tế số
    """
    __tablename__ = "digital_economy_detail"
    
    # === QUY MÔ KINH TẾ SỐ ===
    digital_economy_gdp = Column(Numeric, comment='GDP từ kinh tế số (tỷ VNĐ)')
    digital_economy_gdp_share = Column(Numeric, comment='Tỷ trọng kinh tế số trong GDP (%)')
    digital_economy_growth_rate = Column(Numeric, comment='Tốc độ tăng trưởng kinh tế số (%)')
    
    # === THƯƠNG MẠI ĐIỆN TỬ ===
    ecommerce_revenue = Column(Numeric, comment='Doanh thu thương mại điện tử (tỷ VNĐ)')
    ecommerce_users = Column(Integer, comment='Số lượng người dùng TMĐT (người)')
    ecommerce_transactions = Column(Integer, comment='Số lượng giao dịch TMĐT')
    ecommerce_growth_rate = Column(Numeric, comment='Tốc độ tăng trưởng TMĐT (%)')
    
    # === THANH TOÁN ĐIỆN TỬ ===
    digital_payment_volume = Column(Numeric, comment='Giá trị thanh toán điện tử (tỷ VNĐ)')
    digital_payment_transactions = Column(Integer, comment='Số lượng giao dịch thanh toán điện tử')
    digital_wallet_users = Column(Integer, comment='Số người dùng ví điện tử (người)')
    cashless_payment_rate = Column(Numeric, comment='Tỷ lệ thanh toán không dùng tiền mặt (%)')
    
    # === DOANH NGHIỆP CÔNG NGHỆ SỐ ===
    digital_companies = Column(Integer, comment='Số lượng doanh nghiệp công nghệ số')
    tech_startups = Column(Integer, comment='Số lượng startup công nghệ')
    unicorn_companies = Column(Integer, comment='Số lượng công ty kỳ lân (unicorn)')
    digital_companies_revenue = Column(Numeric, comment='Doanh thu doanh nghiệp số (tỷ VNĐ)')
    
    # === DỊCH VỤ SỐ ===
    fintech_revenue = Column(Numeric, comment='Doanh thu Fintech (tỷ VNĐ)')
    edtech_revenue = Column(Numeric, comment='Doanh thu Edtech (tỷ VNĐ)')
    healthtech_revenue = Column(Numeric, comment='Doanh thu Healthtech (tỷ VNĐ)')
    digital_content_revenue = Column(Numeric, comment='Doanh thu nội dung số (tỷ VNĐ)')
    
    # === HẠ TẦNG SỐ ===
    internet_penetration = Column(Numeric, comment='Tỷ lệ phủ sóng Internet (%)')
    broadband_subscribers = Column(Integer, comment='Số thuê bao băng thông rộng')
    mobile_internet_users = Column(Integer, comment='Số người dùng Internet di động')
    average_internet_speed = Column(Numeric, comment='Tốc độ Internet trung bình (Mbps)')
    
    # === XUẤT KHẨU DỊCH VỤ SỐ ===
    digital_service_exports = Column(Numeric, comment='Xuất khẩu dịch vụ số (triệu USD)')
    software_exports = Column(Numeric, comment='Xuất khẩu phần mềm (triệu USD)')
    it_outsourcing_revenue = Column(Numeric, comment='Doanh thu gia công phần mềm (triệu USD)')
    
    # === NHÂN LỰC SỐ ===
    digital_workforce = Column(Integer, comment='Số lao động trong lĩnh vực số (người)')
    it_graduates = Column(Integer, comment='Số sinh viên tốt nghiệp IT/năm')
    digital_skills_training = Column(Integer, comment='Số người được đào tạo kỹ năng số')
    
    # === ĐẦU TƯ VÀO KINH TẾ SỐ ===
    digital_investment = Column(Numeric, comment='Đầu tư vào kinh tế số (tỷ VNĐ)')
    venture_capital_digital = Column(Numeric, comment='Vốn đầu tư mạo hiểm vào startup số (triệu USD)')
    
    __table_args__ = (
        Index('idx_digital_economy_province_year', 'province', 'year'),
        Index('idx_digital_economy_period', 'year', 'quarter', 'month'),
    )
