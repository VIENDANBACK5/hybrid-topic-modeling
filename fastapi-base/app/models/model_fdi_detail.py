"""FDI (Foreign Direct Investment) Detail Model - Thu hút FDI chi tiết

FDI - Đầu tư Trực tiếp Nước ngoài là hình thức đầu tư mà nhà đầu tư nước ngoài 
đầu tư vốn trực tiếp vào các dự án, doanh nghiệp tại Việt Nam.

Chỉ số này đo lường:
- Vốn FDI đăng ký và giải ngân
- Số lượng dự án FDI mới và tăng vốn
- Phân bổ FDI theo ngành nghề, quốc gia
- Hiệu quả sử dụng vốn FDI
- Tác động của FDI đến kinh tế địa phương
"""
from sqlalchemy import Column, Numeric, String, Integer, Index
from app.models.model_economic_base import EconomicIndicatorBase


class FDIDetail(EconomicIndicatorBase):
    """
    Chỉ số Thu hút Đầu tư Trực tiếp Nước ngoài (FDI)
    Đo lường khả năng và hiệu quả thu hút đầu tư nước ngoài
    """
    __tablename__ = "fdi_detail"
    
    # === VỐN FDI ĐĂNG KÝ ===
    registered_capital = Column(Numeric, comment='Vốn FDI đăng ký (triệu USD)')
    new_projects_capital = Column(Numeric, comment='Vốn đăng ký dự án mới (triệu USD)')
    additional_capital = Column(Numeric, comment='Vốn đăng ký tăng thêm (triệu USD)')
    capital_contribution = Column(Numeric, comment='Vốn góp mua cổ phần (triệu USD)')
    
    # === VỐN FDI GIẢI NGÂN ===
    disbursed_capital = Column(Numeric, comment='Vốn FDI giải ngân (triệu USD)')
    disbursement_rate = Column(Numeric, comment='Tỷ lệ giải ngân so với đăng ký (%)')
    accumulated_disbursement = Column(Numeric, comment='Vốn giải ngân lũy kế (triệu USD)')
    
    # === SỐ LƯỢNG DỰ ÁN ===
    total_projects = Column(Integer, comment='Tổng số dự án (mới + tăng vốn + góp vốn)')
    new_projects = Column(Integer, comment='Số dự án đầu tư mới')
    adjusted_projects = Column(Integer, comment='Số lượt dự án tăng vốn')
    share_purchase_projects = Column(Integer, comment='Số lượt góp vốn mua cổ phần')
    
    # === PHÂN THEO NGÀNH NGHỀ ===
    manufacturing_fdi = Column(Numeric, comment='FDI vào sản xuất chế biến (triệu USD)')
    realestate_fdi = Column(Numeric, comment='FDI vào bất động sản (triệu USD)')
    retail_fdi = Column(Numeric, comment='FDI vào bán lẻ (triệu USD)')
    construction_fdi = Column(Numeric, comment='FDI vào xây dựng (triệu USD)')
    technology_fdi = Column(Numeric, comment='FDI vào công nghệ thông tin (triệu USD)')
    energy_fdi = Column(Numeric, comment='FDI vào điện, khí đốt, nước (triệu USD)')
    agriculture_fdi = Column(Numeric, comment='FDI vào nông lâm ngư nghiệp (triệu USD)')
    
    # === PHÂN THEO QUỐC GIA/KHU VỰC ===
    japan_fdi = Column(Numeric, comment='FDI từ Nhật Bản (triệu USD)')
    korea_fdi = Column(Numeric, comment='FDI từ Hàn Quốc (triệu USD)')
    singapore_fdi = Column(Numeric, comment='FDI từ Singapore (triệu USD)')
    china_fdi = Column(Numeric, comment='FDI từ Trung Quốc (triệu USD)')
    taiwan_fdi = Column(Numeric, comment='FDI từ Đài Loan (triệu USD)')
    hongkong_fdi = Column(Numeric, comment='FDI từ Hồng Kông (triệu USD)')
    thailand_fdi = Column(Numeric, comment='FDI từ Thái Lan (triệu USD)')
    usa_fdi = Column(Numeric, comment='FDI từ Hoa Kỳ (triệu USD)')
    eu_fdi = Column(Numeric, comment='FDI từ EU (triệu USD)')
    
    # === HÌNH THỨC ĐẦU TƯ ===
    wholly_owned_fdi = Column(Numeric, comment='FDI 100% vốn nước ngoài (triệu USD)')
    joint_venture_fdi = Column(Numeric, comment='FDI liên doanh (triệu USD)')
    bcc_fdi = Column(Numeric, comment='FDI hợp đồng hợp tác kinh doanh (triệu USD)')
    
    # === TÁC ĐỘNG KINH TẾ ===
    fdi_contribution_grdp = Column(Numeric, comment='Đóng góp FDI vào GRDP (%)')
    fdi_export_value = Column(Numeric, comment='Giá trị xuất khẩu từ FDI (triệu USD)')
    fdi_export_share = Column(Numeric, comment='Tỷ trọng xuất khẩu FDI/tổng XK (%)')
    fdi_employment = Column(Integer, comment='Số lao động trong khu vực FDI (người)')
    fdi_tax_revenue = Column(Numeric, comment='Thu ngân sách từ FDI (tỷ VNĐ)')
    
    # === KHU CÔNG NGHIỆP/KHU KINH TẾ ===
    industrial_zones = Column(Integer, comment='Số khu công nghiệp có FDI')
    economic_zones = Column(Integer, comment='Số khu kinh tế có FDI')
    occupancy_rate = Column(Numeric, comment='Tỷ lệ lấp đầy KCN/KKT (%)')
    
    # === CHẤT LƯỢNG DOANH NGHIỆP FDI ===
    fortune500_investors = Column(Integer, comment='Số nhà đầu tư Fortune 500')
    high_tech_projects = Column(Integer, comment='Số dự án công nghệ cao')
    rd_centers = Column(Integer, comment='Số trung tâm R&D của FDI')
    
    # === TỶ TRỌNG VÀ XẾP HẠNG ===
    fdi_per_capita = Column(Numeric, comment='FDI bình quân đầu người (USD/người)')
    fdi_density = Column(Numeric, comment='Mật độ FDI (USD/km²)')
    national_ranking = Column(Integer, comment='Xếp hạng thu hút FDI toàn quốc')
    
    __table_args__ = (
        Index('idx_fdi_province_year', 'province', 'year'),
        Index('idx_fdi_period', 'year', 'quarter', 'month'),
    )
