"""Digital Transformation Detail Model - Chuyển đổi số chi tiết

Chuyển đổi số (Digital Transformation - DX) là quá trình ứng dụng công nghệ số 
vào hoạt động của doanh nghiệp, cơ quan nhà nước và xã hội để:
- Cải thiện hiệu quả làm việc
- Tối ưu hóa quy trình
- Nâng cao chất lượng dịch vụ công
- Tăng cường trải nghiệm người dùng

Chỉ số này đo lường:
- Mức độ chuyển đổi số trong doanh nghiệp
- Chuyển đổi số trong chính quyền số
- Hạ tầng và nền tảng số
- Năng lực số của người dân
- Hiệu quả từ chuyển đổi số
"""
from sqlalchemy import Column, Numeric, String, Integer, Index
from app.models.model_economic_base import EconomicIndicatorBase


class DigitalTransformationDetail(EconomicIndicatorBase):
    """
    Chỉ số Chuyển đổi số (Digital Transformation)
    Đo lường tiến độ và hiệu quả chuyển đổi số
    """
    __tablename__ = "digital_transformation_detail"
    
    # === CHỈ SỐ TỔNG HỢP ===
    dx_index = Column(Numeric, comment='Chỉ số chuyển đổi số tổng hợp (0-100)')
    dx_readiness_index = Column(Numeric, comment='Chỉ số sẵn sàng chuyển đổi số (0-100)')
    dx_maturity_level = Column(String, comment='Mức độ trưởng thành CĐS (basic/intermediate/advanced/leading)')
    dx_ranking = Column(Integer, comment='Xếp hạng CĐS toàn quốc')
    
    # === CHÍNH QUYỀN SỐ (E-GOVERNMENT) ===
    egov_index = Column(Numeric, comment='Chỉ số chính quyền điện tử (0-100)')
    online_public_services = Column(Integer, comment='Số dịch vụ công trực tuyến')
    level3_services = Column(Integer, comment='Số dịch vụ công mức độ 3')
    level4_services = Column(Integer, comment='Số dịch vụ công mức độ 4')
    online_service_usage_rate = Column(Numeric, comment='Tỷ lệ sử dụng dịch vụ công trực tuyến (%)')
    
    # === HỆ THỐNG THÔNG TIN ===
    government_portals = Column(Integer, comment='Số cổng thông tin điện tử')
    integrated_databases = Column(Integer, comment='Số cơ sở dữ liệu được tích hợp')
    shared_databases = Column(Integer, comment='Số CSDL dùng chung')
    data_sharing_rate = Column(Numeric, comment='Tỷ lệ chia sẻ dữ liệu liên thông (%)')
    
    # === HẠ TẦNG SỐ ===
    cloud_adoption_rate = Column(Numeric, comment='Tỷ lệ sử dụng điện toán đám mây (%)')
    data_centers = Column(Integer, comment='Số trung tâm dữ liệu')
    broadband_coverage = Column(Numeric, comment='Tỷ lệ phủ sóng băng thông rộng (%)')
    fiber_optic_coverage = Column(Numeric, comment='Tỷ lệ phủ sóng cáp quang (%)')
    fiveg_coverage = Column(Numeric, comment='Tỷ lệ phủ sóng 5G (%)')
    
    # === CHUYỂN ĐỔI SỐ DOANH NGHIỆP ===
    sme_dx_adoption = Column(Numeric, comment='Tỷ lệ SME thực hiện CĐS (%)')
    large_company_dx_adoption = Column(Numeric, comment='Tỷ lệ DN lớn thực hiện CĐS (%)')
    companies_using_cloud = Column(Integer, comment='Số DN sử dụng cloud')
    companies_using_ai = Column(Integer, comment='Số DN ứng dụng AI')
    companies_using_iot = Column(Integer, comment='Số DN ứng dụng IoT')
    companies_using_big_data = Column(Integer, comment='Số DN sử dụng Big Data')
    
    # === NĂNG LỰC SỐ ===
    digital_literacy_rate = Column(Numeric, comment='Tỷ lệ biết chữ số (%)')
    digital_skills_workforce = Column(Numeric, comment='Tỷ lệ lao động có kỹ năng số (%)')
    digital_training_programs = Column(Integer, comment='Số chương trình đào tạo kỹ năng số')
    people_trained_digital = Column(Integer, comment='Số người được đào tạo CĐS')
    
    # === ỨNG DỤNG CÔNG NGHỆ ===
    ai_projects = Column(Integer, comment='Số dự án AI triển khai')
    iot_projects = Column(Integer, comment='Số dự án IoT triển khai')
    blockchain_projects = Column(Integer, comment='Số dự án Blockchain')
    smart_city_projects = Column(Integer, comment='Số dự án thành phố thông minh')
    
    # === CHUYỂN ĐỔI SỐ NÔNG NGHIỆP ===
    smart_agriculture_area = Column(Numeric, comment='Diện tích nông nghiệp thông minh (ha)')
    agricultural_iot_adoption = Column(Numeric, comment='Tỷ lệ ứng dụng IoT nông nghiệp (%)')
    agricultural_digital_platforms = Column(Integer, comment='Số nền tảng số nông nghiệp')
    
    # === CHUYỂN ĐỔI SỐ Y TẾ ===
    telemedicine_facilities = Column(Integer, comment='Số cơ sở y tế khám chữa bệnh từ xa')
    electronic_health_records = Column(Integer, comment='Số hồ sơ sức khỏe điện tử')
    online_medical_appointments = Column(Integer, comment='Số lượt đặt khám trực tuyến')
    
    # === CHUYỂN ĐỔI SỐ GIÁO DỤC ===
    elearning_platforms = Column(Integer, comment='Số nền tảng học trực tuyến')
    schools_with_digital_infrastructure = Column(Integer, comment='Số trường có hạ tầng số')
    digital_textbooks_adoption = Column(Numeric, comment='Tỷ lệ sử dụng sách giáo khoa số (%)')
    
    # === AN TOÀN, AN NINH MẠNG ===
    cybersecurity_incidents = Column(Integer, comment='Số sự cố an ninh mạng')
    certified_security_staff = Column(Integer, comment='Số nhân lực an toàn thông tin có chứng chỉ')
    cybersecurity_budget = Column(Numeric, comment='Ngân sách an toàn an ninh mạng (tỷ VNĐ)')
    
    # === ĐẦU TƯ CHUYỂN ĐỔI SỐ ===
    dx_investment = Column(Numeric, comment='Đầu tư cho CĐS (tỷ VNĐ)')
    dx_public_investment = Column(Numeric, comment='Đầu tư công cho CĐS (tỷ VNĐ)')
    dx_private_investment = Column(Numeric, comment='Đầu tư tư nhân cho CĐS (tỷ VNĐ)')
    
    # === HIỆU QUẢ CHUYỂN ĐỔI SỐ ===
    cost_reduction_from_dx = Column(Numeric, comment='Tiết kiệm chi phí từ CĐS (tỷ VNĐ)')
    time_saved_from_dx = Column(Numeric, comment='Tiết kiệm thời gian từ CĐS (%)')
    productivity_increase_from_dx = Column(Numeric, comment='Tăng năng suất từ CĐS (%)')
    citizen_satisfaction_egov = Column(Numeric, comment='Độ hài lòng dịch vụ công số (0-10)')
    
    __table_args__ = (
        Index('idx_dx_province_year', 'province', 'year'),
        Index('idx_dx_period', 'year', 'quarter', 'month'),
    )
