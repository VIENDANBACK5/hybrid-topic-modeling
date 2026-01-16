"""
27 Indicator Detail Models - 9 Fields × 3 Indicators each

Lĩnh vực 1: Xây dựng Đảng & Hệ thống chính trị
Lĩnh vực 2: Văn hóa, Thể thao & Đời sống tinh thần
Lĩnh vực 3: Môi trường & Biến đổi khí hậu
Lĩnh vực 4: An sinh xã hội & Chính sách
Lĩnh vực 5: An ninh, Trật tự & Quốc phòng
Lĩnh vực 6: Hành chính công & Quản lý Nhà nước
Lĩnh vực 7: Y tế & Chăm sóc sức khỏe
Lĩnh vực 8: Giáo dục & Đào tạo
Lĩnh vực 9: Hạ tầng & Giao thông
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.model_base import Base


# ========================================
# BASE MIXIN FOR ALL INDICATOR DETAIL TABLES
# ========================================

class IndicatorDetailMixin:
    """Common columns for all indicator detail tables"""
    id = Column(Integer, primary_key=True, autoincrement=True)
    economic_indicator_id = Column(Integer, ForeignKey('economic_indicators.id', ondelete='SET NULL'), nullable=True)
    
    # Định danh & thời gian
    province = Column(String(100), nullable=False, comment='Tên tỉnh/thành phố')
    year = Column(Integer, nullable=False, comment='Năm thống kê')
    quarter = Column(Integer, nullable=True, comment='Quý (1-4), NULL = cả năm')
    month = Column(Integer, nullable=True, comment='Tháng (1-12), NULL = cả năm/quý')
    
    # Xếp hạng & thay đổi
    rank_national = Column(Integer, nullable=True, comment='Xếp hạng so với cả nước')
    rank_regional = Column(Integer, nullable=True, comment='Xếp hạng trong vùng')
    yoy_change = Column(Float, nullable=True, comment='Thay đổi so với cùng kỳ năm trước (%)')
    
    # Metadata
    data_status = Column(String(20), nullable=False, default='official', comment='Trạng thái: official/estimated/forecast')
    data_source = Column(String(255), nullable=True, comment='Nguồn dữ liệu')
    notes = Column(Text, nullable=True, comment='Ghi chú')
    last_updated = Column(DateTime, server_default=func.now(), comment='Thời điểm cập nhật')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    @property
    def period_label(self) -> str:
        if self.month:
            return f"T{self.month}/{self.year}"
        if self.quarter:
            return f"Q{self.quarter}/{self.year}"
        return str(self.year)


# ========================================
# LĨNH VỰC 1: XÂY DỰNG ĐẢNG & HỆ THỐNG CHÍNH TRỊ
# ========================================

class CorruptionPreventionDetail(IndicatorDetailMixin, Base):
    """Mức độ phòng chống tham nhũng - Chỉ số niềm tin"""
    __tablename__ = "corruption_prevention_detail"
    
    corruption_perception_index = Column(Float, nullable=True, comment='Chỉ số cảm nhận tham nhũng (0-100)')
    reported_cases = Column(Integer, nullable=True, comment='Số vụ việc được báo cáo')
    resolved_cases = Column(Integer, nullable=True, comment='Số vụ việc được xử lý')
    resolution_rate = Column(Float, nullable=True, comment='Tỷ lệ xử lý (%)')
    citizen_trust_score = Column(Float, nullable=True, comment='Điểm niềm tin của người dân (0-100)')
    transparency_score = Column(Float, nullable=True, comment='Điểm minh bạch (0-100)')
    
    __table_args__ = (
        Index('ix_corruption_prevention_detail_province', 'province'),
        Index('ix_corruption_prevention_detail_year', 'year'),
    )


class CadreQualityDetail(IndicatorDetailMixin, Base):
    """Chất lượng đội ngũ cán bộ, đảng viên - Góc của mỗi chính sách"""
    __tablename__ = "cadre_quality_detail"
    
    total_cadres = Column(Integer, nullable=True, comment='Tổng số cán bộ')
    cadres_with_degree = Column(Integer, nullable=True, comment='Số cán bộ có bằng cấp')
    degree_rate = Column(Float, nullable=True, comment='Tỷ lệ có bằng cấp (%)')
    training_completion_rate = Column(Float, nullable=True, comment='Tỷ lệ hoàn thành đào tạo (%)')
    performance_score = Column(Float, nullable=True, comment='Điểm đánh giá hiệu suất (0-100)')
    citizen_satisfaction = Column(Float, nullable=True, comment='Mức độ hài lòng của dân (0-100)')
    policy_implementation_score = Column(Float, nullable=True, comment='Điểm thực thi chính sách (0-100)')
    
    __table_args__ = (
        Index('ix_cadre_quality_detail_province', 'province'),
        Index('ix_cadre_quality_detail_year', 'year'),
    )


class PartyDisciplineDetail(IndicatorDetailMixin, Base):
    """DCI - Mức độ tuân thủ kỷ luật Đảng - Đảm bảo kỷ cương"""
    __tablename__ = "party_discipline_detail"
    
    dci_score = Column(Float, nullable=True, comment='Điểm DCI tổng hợp (0-100)')
    discipline_violations = Column(Integer, nullable=True, comment='Số vi phạm kỷ luật')
    warnings_issued = Column(Integer, nullable=True, comment='Số cảnh cáo')
    dismissals = Column(Integer, nullable=True, comment='Số trường hợp kỷ luật')
    compliance_rate = Column(Float, nullable=True, comment='Tỷ lệ tuân thủ (%)')
    regulation_adherence_score = Column(Float, nullable=True, comment='Điểm tuân thủ quy định (0-100)')
    
    __table_args__ = (
        Index('ix_party_discipline_detail_province', 'province'),
        Index('ix_party_discipline_detail_year', 'year'),
    )


# ========================================
# LĨNH VỰC 2: VĂN HÓA, THỂ THAO & ĐỜI SỐNG TINH THẦN
# ========================================

class CultureSportAccessDetail(IndicatorDetailMixin, Base):
    """ACSS - Tiếp cận dịch vụ văn hóa thể thao - Quyền hưởng thụ"""
    __tablename__ = "culture_sport_access_detail"
    
    acss_score = Column(Float, nullable=True, comment='Điểm ACSS tổng hợp (0-100)')
    cultural_facilities_per_capita = Column(Float, nullable=True, comment='Số cơ sở văn hóa/10.000 dân')
    sport_facilities_per_capita = Column(Float, nullable=True, comment='Số cơ sở thể thao/10.000 dân')
    participation_rate = Column(Float, nullable=True, comment='Tỷ lệ tham gia hoạt động (%)')
    access_distance_km = Column(Float, nullable=True, comment='Khoảng cách tiếp cận trung bình (km)')
    affordability_score = Column(Float, nullable=True, comment='Điểm khả năng chi trả (0-100)')
    
    __table_args__ = (
        Index('ix_culture_sport_access_detail_province', 'province'),
        Index('ix_culture_sport_access_detail_year', 'year'),
    )


class CulturalInfrastructureDetail(IndicatorDetailMixin, Base):
    """Số lượng & chất lượng công trình văn hóa - Hạ tầng tinh thần"""
    __tablename__ = "cultural_infrastructure_detail"
    
    total_facilities = Column(Integer, nullable=True, comment='Tổng số công trình văn hóa')
    libraries = Column(Integer, nullable=True, comment='Số thư viện')
    museums = Column(Integer, nullable=True, comment='Số bảo tàng')
    theaters = Column(Integer, nullable=True, comment='Số nhà hát')
    cultural_houses = Column(Integer, nullable=True, comment='Số nhà văn hóa')
    heritage_sites = Column(Integer, nullable=True, comment='Số di tích lịch sử')
    quality_score = Column(Float, nullable=True, comment='Điểm chất lượng tổng hợp (0-100)')
    utilization_rate = Column(Float, nullable=True, comment='Tỷ lệ sử dụng (%)')
    
    __table_args__ = (
        Index('ix_cultural_infrastructure_detail_province', 'province'),
        Index('ix_cultural_infrastructure_detail_year', 'year'),
    )


class CultureSocializationDetail(IndicatorDetailMixin, Base):
    """Tỷ lệ xã hội hóa hoạt động văn hóa thể thao - Độ bền & sáng tạo"""
    __tablename__ = "culture_socialization_detail"
    
    socialization_rate = Column(Float, nullable=True, comment='Tỷ lệ xã hội hóa (%)')
    private_investment_billion = Column(Float, nullable=True, comment='Đầu tư tư nhân (tỷ VNĐ)')
    public_private_ratio = Column(Float, nullable=True, comment='Tỷ lệ công-tư')
    private_facilities = Column(Integer, nullable=True, comment='Số cơ sở tư nhân')
    community_events = Column(Integer, nullable=True, comment='Số sự kiện cộng đồng')
    volunteer_participation = Column(Integer, nullable=True, comment='Số người tham gia tình nguyện')
    sustainability_score = Column(Float, nullable=True, comment='Điểm bền vững (0-100)')
    
    __table_args__ = (
        Index('ix_culture_socialization_detail_province', 'province'),
        Index('ix_culture_socialization_detail_year', 'year'),
    )


# ========================================
# LĨNH VỰC 3: MÔI TRƯỜNG & BIẾN ĐỔI KHÍ HẬU
# ========================================

class AirQualityDetail(IndicatorDetailMixin, Base):
    """AQI - Chỉ số chất lượng không khí - Tác động trực tiếp đến sức khỏe"""
    __tablename__ = "air_quality_detail"
    
    aqi_score = Column(Float, nullable=True, comment='Chỉ số AQI trung bình')
    pm25 = Column(Float, nullable=True, comment='Nồng độ PM2.5 (μg/m³)')
    pm10 = Column(Float, nullable=True, comment='Nồng độ PM10 (μg/m³)')
    no2 = Column(Float, nullable=True, comment='Nồng độ NO2 (ppb)')
    so2 = Column(Float, nullable=True, comment='Nồng độ SO2 (ppb)')
    co = Column(Float, nullable=True, comment='Nồng độ CO (ppm)')
    o3 = Column(Float, nullable=True, comment='Nồng độ O3 (ppb)')
    good_days_pct = Column(Float, nullable=True, comment='Tỷ lệ ngày không khí tốt (%)')
    health_impact_score = Column(Float, nullable=True, comment='Điểm tác động sức khỏe (0-100)')
    
    __table_args__ = (
        Index('ix_air_quality_detail_province', 'province'),
        Index('ix_air_quality_detail_year', 'year'),
    )


class ClimateResilienceDetail(IndicatorDetailMixin, Base):
    """Khả năng chống chịu biến đổi khí hậu - Phòng ngừa rủi ro dài hạn"""
    __tablename__ = "climate_resilience_detail"
    
    resilience_score = Column(Float, nullable=True, comment='Điểm khả năng chống chịu (0-100)')
    flood_risk_score = Column(Float, nullable=True, comment='Điểm rủi ro lũ lụt (0-100)')
    drought_risk_score = Column(Float, nullable=True, comment='Điểm rủi ro hạn hán (0-100)')
    sea_level_rise_risk = Column(Float, nullable=True, comment='Rủi ro nước biển dâng (0-100)')
    adaptation_investment_billion = Column(Float, nullable=True, comment='Đầu tư thích ứng (tỷ VNĐ)')
    green_coverage_pct = Column(Float, nullable=True, comment='Tỷ lệ che phủ xanh (%)')
    disaster_preparedness_score = Column(Float, nullable=True, comment='Điểm chuẩn bị thiên tai (0-100)')
    
    __table_args__ = (
        Index('ix_climate_resilience_detail_province', 'province'),
        Index('ix_climate_resilience_detail_year', 'year'),
    )


class WasteManagementDetail(IndicatorDetailMixin, Base):
    """Quản lý & xử lý chất thải - Điểm nóng đô thị & nông thôn"""
    __tablename__ = "waste_management_detail"
    
    waste_collection_rate = Column(Float, nullable=True, comment='Tỷ lệ thu gom rác thải (%)')
    waste_treatment_rate = Column(Float, nullable=True, comment='Tỷ lệ xử lý rác thải (%)')
    recycling_rate = Column(Float, nullable=True, comment='Tỷ lệ tái chế (%)')
    total_waste_tons = Column(Float, nullable=True, comment='Tổng lượng rác thải (tấn)')
    hazardous_waste_tons = Column(Float, nullable=True, comment='Rác thải nguy hại (tấn)')
    landfill_capacity_pct = Column(Float, nullable=True, comment='Tỷ lệ sử dụng bãi chôn lấp (%)')
    wastewater_treatment_rate = Column(Float, nullable=True, comment='Tỷ lệ xử lý nước thải (%)')
    management_score = Column(Float, nullable=True, comment='Điểm quản lý tổng hợp (0-100)')
    
    __table_args__ = (
        Index('ix_waste_management_detail_province', 'province'),
        Index('ix_waste_management_detail_year', 'year'),
    )


# ========================================
# LĨNH VỰC 4: AN SINH XÃ HỘI & CHÍNH SÁCH
# ========================================

class HDIDetail(IndicatorDetailMixin, Base):
    """HDI - Chỉ số phát triển con người - Chỉ số vàng, chuẩn quốc tế"""
    __tablename__ = "hdi_detail"
    
    hdi_score = Column(Float, nullable=True, comment='Chỉ số HDI tổng hợp (0-1)')
    life_expectancy = Column(Float, nullable=True, comment='Tuổi thọ trung bình (năm)')
    mean_schooling_years = Column(Float, nullable=True, comment='Số năm đi học trung bình')
    expected_schooling_years = Column(Float, nullable=True, comment='Số năm đi học kỳ vọng')
    gni_per_capita = Column(Float, nullable=True, comment='Thu nhập bình quân/người (USD)')
    health_index = Column(Float, nullable=True, comment='Chỉ số sức khỏe')
    education_index = Column(Float, nullable=True, comment='Chỉ số giáo dục')
    income_index = Column(Float, nullable=True, comment='Chỉ số thu nhập')
    
    __table_args__ = (
        Index('ix_hdi_detail_province', 'province'),
        Index('ix_hdi_detail_year', 'year'),
    )


class SocialSecurityCoverageDetail(IndicatorDetailMixin, Base):
    """Tỷ lệ bao phủ an sinh xã hội - Độ rộng của lưới an sinh"""
    __tablename__ = "social_security_coverage_detail"
    
    coverage_rate = Column(Float, nullable=True, comment='Tỷ lệ bao phủ tổng (%)')
    health_insurance_coverage = Column(Float, nullable=True, comment='Bao phủ BHYT (%)')
    social_insurance_coverage = Column(Float, nullable=True, comment='Bao phủ BHXH (%)')
    unemployment_insurance_coverage = Column(Float, nullable=True, comment='Bao phủ BH thất nghiệp (%)')
    pension_coverage = Column(Float, nullable=True, comment='Bao phủ lương hưu (%)')
    beneficiaries_count = Column(Integer, nullable=True, comment='Số người thụ hưởng')
    vulnerable_group_coverage = Column(Float, nullable=True, comment='Bao phủ nhóm yếu thế (%)')
    
    __table_args__ = (
        Index('ix_social_security_coverage_detail_province', 'province'),
        Index('ix_social_security_coverage_detail_year', 'year'),
    )


class SocialBudgetDetail(IndicatorDetailMixin, Base):
    """Tỷ trọng chi ngân sách cho an sinh xã hội - Cam kết chính sách bằng tiền"""
    __tablename__ = "social_budget_detail"
    
    social_budget_pct = Column(Float, nullable=True, comment='Tỷ trọng chi ASXH/tổng ngân sách (%)')
    total_social_budget_billion = Column(Float, nullable=True, comment='Tổng chi ASXH (tỷ VNĐ)')
    health_budget_billion = Column(Float, nullable=True, comment='Chi y tế (tỷ VNĐ)')
    education_budget_billion = Column(Float, nullable=True, comment='Chi giáo dục (tỷ VNĐ)')
    poverty_reduction_billion = Column(Float, nullable=True, comment='Chi giảm nghèo (tỷ VNĐ)')
    per_capita_social_spending = Column(Float, nullable=True, comment='Chi ASXH/người (VNĐ)')
    budget_execution_rate = Column(Float, nullable=True, comment='Tỷ lệ giải ngân (%)')
    
    __table_args__ = (
        Index('ix_social_budget_detail_province', 'province'),
        Index('ix_social_budget_detail_year', 'year'),
    )


# ========================================
# LĨNH VỰC 5: AN NINH, TRẬT TỰ & QUỐC PHÒNG
# ========================================

class PublicOrderDetail(IndicatorDetailMixin, Base):
    """Mức độ bảo đảm an ninh trật tự xã hội - Chỉ số tổng hợp quan trọng nhất"""
    __tablename__ = "public_order_detail"
    
    public_order_score = Column(Float, nullable=True, comment='Điểm an ninh trật tự tổng hợp (0-100)')
    safety_perception_score = Column(Float, nullable=True, comment='Điểm cảm nhận an toàn (0-100)')
    crime_rate_per_100k = Column(Float, nullable=True, comment='Tỷ lệ tội phạm/100.000 dân')
    violent_crime_rate = Column(Float, nullable=True, comment='Tỷ lệ tội phạm bạo lực')
    property_crime_rate = Column(Float, nullable=True, comment='Tỷ lệ tội phạm tài sản')
    police_per_capita = Column(Float, nullable=True, comment='Số công an/10.000 dân')
    response_time_minutes = Column(Float, nullable=True, comment='Thời gian phản ứng trung bình (phút)')
    
    __table_args__ = (
        Index('ix_public_order_detail_province', 'province'),
        Index('ix_public_order_detail_year', 'year'),
    )


class CrimePreventionDetail(IndicatorDetailMixin, Base):
    """Tỷ lệ phòng chống & giảm tội phạm - Đo hiệu quả thực thi"""
    __tablename__ = "crime_prevention_detail"
    
    crime_reduction_rate = Column(Float, nullable=True, comment='Tỷ lệ giảm tội phạm (%)')
    case_clearance_rate = Column(Float, nullable=True, comment='Tỷ lệ phá án (%)')
    total_cases = Column(Integer, nullable=True, comment='Tổng số vụ án')
    solved_cases = Column(Integer, nullable=True, comment='Số vụ án được giải quyết')
    prevention_programs = Column(Integer, nullable=True, comment='Số chương trình phòng ngừa')
    community_watch_groups = Column(Integer, nullable=True, comment='Số tổ dân phòng')
    drug_crime_reduction = Column(Float, nullable=True, comment='Giảm tội phạm ma túy (%)')
    effectiveness_score = Column(Float, nullable=True, comment='Điểm hiệu quả (0-100)')
    
    __table_args__ = (
        Index('ix_crime_prevention_detail_province', 'province'),
        Index('ix_crime_prevention_detail_year', 'year'),
    )


class TrafficSafetyDetail(IndicatorDetailMixin, Base):
    """An toàn giao thông & xã hội - Gắn trực tiếp với đời sống hàng ngày"""
    __tablename__ = "traffic_safety_detail"
    
    traffic_safety_score = Column(Float, nullable=True, comment='Điểm an toàn giao thông (0-100)')
    accidents_total = Column(Integer, nullable=True, comment='Tổng số vụ tai nạn')
    fatalities = Column(Integer, nullable=True, comment='Số người tử vong')
    injuries = Column(Integer, nullable=True, comment='Số người bị thương')
    accidents_per_100k_vehicles = Column(Float, nullable=True, comment='Tai nạn/100.000 phương tiện')
    fatalities_per_100k_pop = Column(Float, nullable=True, comment='Tử vong/100.000 dân')
    drunk_driving_cases = Column(Integer, nullable=True, comment='Số vụ vi phạm nồng độ cồn')
    helmet_compliance_rate = Column(Float, nullable=True, comment='Tỷ lệ đội mũ bảo hiểm (%)')
    accident_reduction_rate = Column(Float, nullable=True, comment='Tỷ lệ giảm tai nạn (%)')
    
    __table_args__ = (
        Index('ix_traffic_safety_detail_province', 'province'),
        Index('ix_traffic_safety_detail_year', 'year'),
    )


# ========================================
# LĨNH VỰC 6: HÀNH CHÍNH CÔNG & QUẢN LÝ NHÀ NƯỚC
# ========================================

class PARIndexDetail(IndicatorDetailMixin, Base):
    """PAR Index - Chỉ số cải cách hành chính - Xương sống quản trị"""
    __tablename__ = "par_index_detail"
    
    par_index_score = Column(Float, nullable=True, comment='Điểm PAR Index tổng hợp (0-100)')
    institutional_reform_score = Column(Float, nullable=True, comment='Điểm cải cách thể chế')
    admin_procedure_score = Column(Float, nullable=True, comment='Điểm cải cách TTHC')
    organizational_reform_score = Column(Float, nullable=True, comment='Điểm cải cách tổ chức')
    civil_service_reform_score = Column(Float, nullable=True, comment='Điểm cải cách công chức')
    public_finance_reform_score = Column(Float, nullable=True, comment='Điểm cải cách tài chính công')
    egovernment_reform_score = Column(Float, nullable=True, comment='Điểm cải cách CPĐT')
    citizen_impact_score = Column(Float, nullable=True, comment='Điểm tác động đến người dân')
    
    __table_args__ = (
        Index('ix_par_index_detail_province', 'province'),
        Index('ix_par_index_detail_year', 'year'),
    )


class SIPASDetail(IndicatorDetailMixin, Base):
    """SIPAS - Chỉ số hài lòng của người dân - Góc nhìn từ khách hàng"""
    __tablename__ = "sipas_detail"
    
    sipas_score = Column(Float, nullable=True, comment='Điểm SIPAS tổng hợp (0-100)')
    service_access_score = Column(Float, nullable=True, comment='Điểm tiếp cận dịch vụ')
    procedure_simplicity_score = Column(Float, nullable=True, comment='Điểm đơn giản hóa thủ tục')
    staff_attitude_score = Column(Float, nullable=True, comment='Điểm thái độ cán bộ')
    processing_time_score = Column(Float, nullable=True, comment='Điểm thời gian xử lý')
    transparency_score = Column(Float, nullable=True, comment='Điểm minh bạch')
    online_service_score = Column(Float, nullable=True, comment='Điểm dịch vụ trực tuyến')
    complaint_resolution_score = Column(Float, nullable=True, comment='Điểm giải quyết khiếu nại')
    surveys_conducted = Column(Integer, nullable=True, comment='Số khảo sát thực hiện')
    respondents_count = Column(Integer, nullable=True, comment='Số người phản hồi')
    
    __table_args__ = (
        Index('ix_sipas_detail_province', 'province'),
        Index('ix_sipas_detail_year', 'year'),
    )


class EGovernmentDetail(IndicatorDetailMixin, Base):
    """Chỉ số chính phủ số / E-Government - Năng lực quản lý hiện đại"""
    __tablename__ = "egovernment_detail"
    
    egov_score = Column(Float, nullable=True, comment='Điểm E-Government tổng hợp (0-100)')
    online_services_count = Column(Integer, nullable=True, comment='Số dịch vụ công trực tuyến')
    level_4_services_count = Column(Integer, nullable=True, comment='Số DVC mức độ 4')
    online_transaction_rate = Column(Float, nullable=True, comment='Tỷ lệ giao dịch trực tuyến (%)')
    digital_document_rate = Column(Float, nullable=True, comment='Tỷ lệ hồ sơ số hóa (%)')
    one_stop_portal_usage = Column(Float, nullable=True, comment='Tỷ lệ sử dụng cổng DVC (%)')
    data_sharing_score = Column(Float, nullable=True, comment='Điểm chia sẻ dữ liệu')
    cybersecurity_score = Column(Float, nullable=True, comment='Điểm an ninh mạng')
    digital_literacy_rate = Column(Float, nullable=True, comment='Tỷ lệ biết sử dụng CNTT (%)')
    
    __table_args__ = (
        Index('ix_egovernment_detail_province', 'province'),
        Index('ix_egovernment_detail_year', 'year'),
    )


# ========================================
# LĨNH VỰC 7: Y TẾ & CHĂM SÓC SỨC KHỎE
# ========================================

class HealthInsuranceDetail(IndicatorDetailMixin, Base):
    """BHYT Coverage Rate - Tỷ lệ bao phủ bảo hiểm y tế"""
    __tablename__ = "health_insurance_detail"
    
    bhyt_coverage_rate = Column(Float, nullable=True, comment='Tỷ lệ bao phủ BHYT (%)')
    total_insured = Column(Integer, nullable=True, comment='Tổng số người có BHYT')
    voluntary_insured = Column(Integer, nullable=True, comment='Số người tham gia tự nguyện')
    mandatory_insured = Column(Integer, nullable=True, comment='Số người tham gia bắt buộc')
    poor_near_poor_coverage = Column(Float, nullable=True, comment='Bao phủ hộ nghèo/cận nghèo (%)')
    children_coverage = Column(Float, nullable=True, comment='Bao phủ trẻ em (%)')
    elderly_coverage = Column(Float, nullable=True, comment='Bao phủ người cao tuổi (%)')
    claims_amount_billion = Column(Float, nullable=True, comment='Chi trả BHYT (tỷ VNĐ)')
    
    __table_args__ = (
        Index('ix_health_insurance_detail_province', 'province'),
        Index('ix_health_insurance_detail_year', 'year'),
    )


class HAQIndexDetail(IndicatorDetailMixin, Base):
    """HAQ Index - Chất lượng dịch vụ y tế"""
    __tablename__ = "haq_index_detail"
    
    haq_score = Column(Float, nullable=True, comment='Điểm HAQ Index (0-100)')
    healthcare_access_score = Column(Float, nullable=True, comment='Điểm tiếp cận y tế')
    healthcare_quality_score = Column(Float, nullable=True, comment='Điểm chất lượng y tế')
    hospital_beds_per_10k = Column(Float, nullable=True, comment='Số giường bệnh/10.000 dân')
    doctors_per_10k = Column(Float, nullable=True, comment='Số bác sĩ/10.000 dân')
    nurses_per_10k = Column(Float, nullable=True, comment='Số điều dưỡng/10.000 dân')
    maternal_mortality_rate = Column(Float, nullable=True, comment='Tỷ lệ tử vong mẹ/100.000')
    infant_mortality_rate = Column(Float, nullable=True, comment='Tỷ lệ tử vong trẻ sơ sinh/1.000')
    treatment_success_rate = Column(Float, nullable=True, comment='Tỷ lệ điều trị thành công (%)')
    
    __table_args__ = (
        Index('ix_haq_index_detail_province', 'province'),
        Index('ix_haq_index_detail_year', 'year'),
    )


class PreventiveHealthDetail(IndicatorDetailMixin, Base):
    """Năng lực y tế dự phòng / Ứng phó dịch bệnh"""
    __tablename__ = "preventive_health_detail"
    
    preventive_health_score = Column(Float, nullable=True, comment='Điểm y tế dự phòng (0-100)')
    vaccination_coverage = Column(Float, nullable=True, comment='Tỷ lệ tiêm chủng (%)')
    health_screening_rate = Column(Float, nullable=True, comment='Tỷ lệ khám sàng lọc (%)')
    disease_surveillance_score = Column(Float, nullable=True, comment='Điểm giám sát dịch bệnh')
    epidemic_response_score = Column(Float, nullable=True, comment='Điểm ứng phó dịch bệnh')
    preventive_facilities = Column(Integer, nullable=True, comment='Số cơ sở y tế dự phòng')
    health_education_programs = Column(Integer, nullable=True, comment='Số chương trình giáo dục sức khỏe')
    clean_water_access_rate = Column(Float, nullable=True, comment='Tỷ lệ tiếp cận nước sạch (%)')
    sanitation_access_rate = Column(Float, nullable=True, comment='Tỷ lệ có công trình vệ sinh (%)')
    
    __table_args__ = (
        Index('ix_preventive_health_detail_province', 'province'),
        Index('ix_preventive_health_detail_year', 'year'),
    )


# ========================================
# LĨNH VỰC 8: GIÁO DỤC & ĐÀO TẠO
# ========================================

class EQIDetail(IndicatorDetailMixin, Base):
    """EQI - Chỉ số chất lượng giáo dục - Tổng biểu đầu ra giáo dục"""
    __tablename__ = "eqi_detail"
    
    eqi_score = Column(Float, nullable=True, comment='Điểm EQI tổng hợp (0-100)')
    literacy_rate = Column(Float, nullable=True, comment='Tỷ lệ biết chữ (%)')
    school_enrollment_rate = Column(Float, nullable=True, comment='Tỷ lệ nhập học (%)')
    primary_completion_rate = Column(Float, nullable=True, comment='Tỷ lệ hoàn thành tiểu học (%)')
    secondary_completion_rate = Column(Float, nullable=True, comment='Tỷ lệ hoàn thành THCS (%)')
    teacher_qualification_rate = Column(Float, nullable=True, comment='Tỷ lệ GV đạt chuẩn (%)')
    student_teacher_ratio = Column(Float, nullable=True, comment='Tỷ lệ học sinh/giáo viên')
    learning_outcome_score = Column(Float, nullable=True, comment='Điểm kết quả học tập')
    education_spending_per_student = Column(Float, nullable=True, comment='Chi tiêu GD/học sinh (VNĐ)')
    
    __table_args__ = (
        Index('ix_eqi_detail_province', 'province'),
        Index('ix_eqi_detail_year', 'year'),
    )


class HighschoolGraduationDetail(IndicatorDetailMixin, Base):
    """Tỷ lệ đỗ tốt nghiệp THPT - Chỉ số phổ biến, dễ truyền thông"""
    __tablename__ = "highschool_graduation_detail"
    
    graduation_rate = Column(Float, nullable=True, comment='Tỷ lệ đỗ tốt nghiệp (%)')
    total_candidates = Column(Integer, nullable=True, comment='Tổng số thí sinh')
    passed_candidates = Column(Integer, nullable=True, comment='Số thí sinh đỗ')
    average_score = Column(Float, nullable=True, comment='Điểm trung bình')
    math_avg_score = Column(Float, nullable=True, comment='Điểm TB môn Toán')
    literature_avg_score = Column(Float, nullable=True, comment='Điểm TB môn Văn')
    english_avg_score = Column(Float, nullable=True, comment='Điểm TB môn Anh')
    excellent_rate = Column(Float, nullable=True, comment='Tỷ lệ điểm giỏi (%)')
    fail_rate = Column(Float, nullable=True, comment='Tỷ lệ trượt (%)')
    
    __table_args__ = (
        Index('ix_highschool_graduation_detail_province', 'province'),
        Index('ix_highschool_graduation_detail_year', 'year'),
    )


class TVETEmploymentDetail(IndicatorDetailMixin, Base):
    """TVET Employment Rate - Gắn giáo dục với thị trường lao động"""
    __tablename__ = "tvet_employment_detail"
    
    employment_rate = Column(Float, nullable=True, comment='Tỷ lệ có việc làm sau tốt nghiệp (%)')
    total_graduates = Column(Integer, nullable=True, comment='Tổng số tốt nghiệp')
    employed_graduates = Column(Integer, nullable=True, comment='Số có việc làm')
    relevant_job_rate = Column(Float, nullable=True, comment='Tỷ lệ việc làm đúng ngành (%)')
    average_starting_salary = Column(Float, nullable=True, comment='Lương khởi điểm TB (VNĐ)')
    employer_satisfaction = Column(Float, nullable=True, comment='Mức độ hài lòng của DN (0-100)')
    tvet_enrollment = Column(Integer, nullable=True, comment='Số tuyển sinh GDNN')
    tvet_facilities = Column(Integer, nullable=True, comment='Số cơ sở GDNN')
    industry_partnership_count = Column(Integer, nullable=True, comment='Số liên kết với DN')
    
    __table_args__ = (
        Index('ix_tvet_employment_detail_province', 'province'),
        Index('ix_tvet_employment_detail_year', 'year'),
    )


# ========================================
# LĨNH VỰC 9: HẠ TẦNG & GIAO THÔNG
# ========================================

class TransportInfrastructureDetail(IndicatorDetailMixin, Base):
    """Chất lượng hạ tầng giao thông - Trục xương sống phát triển"""
    __tablename__ = "transport_infrastructure_detail"
    
    infrastructure_score = Column(Float, nullable=True, comment='Điểm hạ tầng GT tổng hợp (0-100)')
    road_length_km = Column(Float, nullable=True, comment='Tổng chiều dài đường (km)')
    paved_road_rate = Column(Float, nullable=True, comment='Tỷ lệ đường nhựa/bê tông (%)')
    road_density_km_per_km2 = Column(Float, nullable=True, comment='Mật độ đường (km/km²)')
    bridge_count = Column(Integer, nullable=True, comment='Số cầu')
    public_transport_coverage = Column(Float, nullable=True, comment='Độ phủ GTCC (%)')
    road_quality_score = Column(Float, nullable=True, comment='Điểm chất lượng đường')
    maintenance_budget_billion = Column(Float, nullable=True, comment='Ngân sách bảo trì (tỷ VNĐ)')
    
    __table_args__ = (
        Index('ix_transport_infrastructure_detail_province', 'province'),
        Index('ix_transport_infrastructure_detail_year', 'year'),
    )


class TrafficCongestionDetail(IndicatorDetailMixin, Base):
    """Chỉ số vận hành & ùn tắc giao thông - Đo hiệu quả sử dụng hạ tầng"""
    __tablename__ = "traffic_congestion_detail"
    
    congestion_index = Column(Float, nullable=True, comment='Chỉ số ùn tắc (0-100, cao = tệ)')
    average_speed_kmh = Column(Float, nullable=True, comment='Tốc độ trung bình (km/h)')
    peak_hour_delay_minutes = Column(Float, nullable=True, comment='Độ trễ giờ cao điểm (phút)')
    congestion_points = Column(Integer, nullable=True, comment='Số điểm ùn tắc')
    traffic_flow_score = Column(Float, nullable=True, comment='Điểm lưu thông')
    public_transport_usage_rate = Column(Float, nullable=True, comment='Tỷ lệ sử dụng GTCC (%)')
    vehicle_per_1000_pop = Column(Float, nullable=True, comment='Số phương tiện/1.000 dân')
    smart_traffic_coverage = Column(Float, nullable=True, comment='Độ phủ giao thông thông minh (%)')
    
    __table_args__ = (
        Index('ix_traffic_congestion_detail_province', 'province'),
        Index('ix_traffic_congestion_detail_year', 'year'),
    )


class PlanningProgressDetail(IndicatorDetailMixin, Base):
    """Mức độ thực hiện quy hoạch & tiến độ dự án - Rất dấu dầu trong quản lý"""
    __tablename__ = "planning_progress_detail"
    
    planning_compliance_score = Column(Float, nullable=True, comment='Điểm tuân thủ quy hoạch (0-100)')
    total_projects = Column(Integer, nullable=True, comment='Tổng số dự án')
    on_schedule_projects = Column(Integer, nullable=True, comment='Số dự án đúng tiến độ')
    delayed_projects = Column(Integer, nullable=True, comment='Số dự án chậm tiến độ')
    on_schedule_rate = Column(Float, nullable=True, comment='Tỷ lệ đúng tiến độ (%)')
    budget_execution_rate = Column(Float, nullable=True, comment='Tỷ lệ giải ngân (%)')
    total_investment_billion = Column(Float, nullable=True, comment='Tổng vốn đầu tư (tỷ VNĐ)')
    disbursed_billion = Column(Float, nullable=True, comment='Đã giải ngân (tỷ VNĐ)')
    land_clearance_completion_rate = Column(Float, nullable=True, comment='Tỷ lệ GPMB hoàn thành (%)')
    
    __table_args__ = (
        Index('ix_planning_progress_detail_province', 'province'),
        Index('ix_planning_progress_detail_year', 'year'),
    )


# ========================================
# REGISTRY - All 27 detail models
# ========================================

INDICATOR_DETAIL_MODELS = {
    # Lĩnh vực 1: Xây dựng Đảng & Hệ thống chính trị
    'corruption_prevention': CorruptionPreventionDetail,
    'cadre_quality': CadreQualityDetail,
    'party_discipline': PartyDisciplineDetail,
    
    # Lĩnh vực 2: Văn hóa, Thể thao & Đời sống tinh thần
    'culture_sport_access': CultureSportAccessDetail,
    'cultural_infrastructure': CulturalInfrastructureDetail,
    'culture_socialization': CultureSocializationDetail,
    
    # Lĩnh vực 3: Môi trường & Biến đổi khí hậu
    'air_quality': AirQualityDetail,
    'climate_resilience': ClimateResilienceDetail,
    'waste_management': WasteManagementDetail,
    
    # Lĩnh vực 4: An sinh xã hội & Chính sách
    'hdi': HDIDetail,
    'social_security_coverage': SocialSecurityCoverageDetail,
    'social_budget': SocialBudgetDetail,
    
    # Lĩnh vực 5: An ninh, Trật tự & Quốc phòng
    'public_order': PublicOrderDetail,
    'crime_prevention': CrimePreventionDetail,
    'traffic_safety': TrafficSafetyDetail,
    
    # Lĩnh vực 6: Hành chính công & Quản lý Nhà nước
    'par_index': PARIndexDetail,
    'sipas': SIPASDetail,
    'egovernment': EGovernmentDetail,
    
    # Lĩnh vực 7: Y tế & Chăm sóc sức khỏe
    'health_insurance': HealthInsuranceDetail,
    'haq_index': HAQIndexDetail,
    'preventive_health': PreventiveHealthDetail,
    
    # Lĩnh vực 8: Giáo dục & Đào tạo
    'eqi': EQIDetail,
    'highschool_graduation': HighschoolGraduationDetail,
    'tvet_employment': TVETEmploymentDetail,
    
    # Lĩnh vực 9: Hạ tầng & Giao thông
    'transport_infrastructure': TransportInfrastructureDetail,
    'traffic_congestion': TrafficCongestionDetail,
    'planning_progress': PlanningProgressDetail,
}

# Field mapping for reference
FIELD_INDICATORS = {
    'xay_dung_dang': ['corruption_prevention', 'cadre_quality', 'party_discipline'],
    'van_hoa_the_thao': ['culture_sport_access', 'cultural_infrastructure', 'culture_socialization'],
    'moi_truong': ['air_quality', 'climate_resilience', 'waste_management'],
    'an_sinh_xa_hoi': ['hdi', 'social_security_coverage', 'social_budget'],
    'an_ninh_trat_tu': ['public_order', 'crime_prevention', 'traffic_safety'],
    'hanh_chinh_cong': ['par_index', 'sipas', 'egovernment'],
    'y_te': ['health_insurance', 'haq_index', 'preventive_health'],
    'giao_duc': ['eqi', 'highschool_graduation', 'tvet_employment'],
    'ha_tang_giao_thong': ['transport_infrastructure', 'traffic_congestion', 'planning_progress'],
}
