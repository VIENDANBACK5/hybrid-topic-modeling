"""Add 27 indicator detail tables for 9 fields (3 indicators each)

Revision ID: add_27_indicator_details
Revises: 20260115_183855
Create Date: 2026-01-16

9 Lĩnh vực × 3 Chỉ số = 27 bảng:

1. Xây dựng Đảng & Hệ thống chính trị:
   - corruption_prevention_detail (Mức độ phòng chống tham nhũng)
   - cadre_quality_detail (Chất lượng đội ngũ cán bộ, đảng viên)
   - party_discipline_detail (DCI - Mức độ tuân thủ kỷ luật Đảng)

2. Văn hóa, Thể thao & Đời sống tinh thần:
   - culture_sport_access_detail (ACSS - Tiếp cận dịch vụ văn hóa thể thao)
   - cultural_infrastructure_detail (Số lượng & chất lượng công trình văn hóa)
   - culture_socialization_detail (Tỷ lệ xã hội hóa hoạt động văn hóa thể thao)

3. Môi trường & Biến đổi khí hậu:
   - air_quality_detail (AQI - Chỉ số chất lượng không khí)
   - climate_resilience_detail (Khả năng chống chịu biến đổi khí hậu)
   - waste_management_detail (Quản lý & xử lý chất thải)

4. An sinh xã hội & Chính sách:
   - hdi_detail (HDI - Chỉ số phát triển con người)
   - social_security_coverage_detail (Tỷ lệ bao phủ an sinh xã hội)
   - social_budget_detail (Tỷ trọng chi ngân sách cho an sinh xã hội)

5. An ninh, Trật tự & Quốc phòng:
   - public_order_detail (Mức độ bảo đảm an ninh trật tự xã hội)
   - crime_prevention_detail (Tỷ lệ phòng chống & giảm tội phạm)
   - traffic_safety_detail (An toàn giao thông & xã hội)

6. Hành chính công & Quản lý Nhà nước:
   - par_index_detail (PAR Index - Chỉ số cải cách hành chính)
   - sipas_detail (SIPAS - Chỉ số hài lòng của người dân)
   - egovernment_detail (Chỉ số chính phủ số / E-Government)

7. Y tế & Chăm sóc sức khỏe:
   - health_insurance_detail (BHYT Coverage Rate)
   - haq_index_detail (HAQ Index - Chất lượng dịch vụ y tế)
   - preventive_health_detail (Năng lực y tế dự phòng)

8. Giáo dục & Đào tạo:
   - eqi_detail (EQI - Chỉ số chất lượng giáo dục)
   - highschool_graduation_detail (Tỷ lệ đỗ tốt nghiệp THPT)
   - tvet_employment_detail (TVET Employment Rate)

9. Hạ tầng & Giao thông:
   - transport_infrastructure_detail (Chất lượng hạ tầng giao thông)
   - traffic_congestion_detail (Chỉ số vận hành & ùn tắc giao thông)
   - planning_progress_detail (Mức độ thực hiện quy hoạch & tiến độ dự án)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_27_indicator_details'
down_revision: Union[str, None] = '20260115_183855'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def create_base_columns():
    """Common base columns for all detail tables"""
    return [
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('economic_indicator_id', sa.Integer(), nullable=True),
        sa.Column('province', sa.String(length=100), nullable=False, comment='Tên tỉnh/thành phố'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Năm thống kê'),
        sa.Column('quarter', sa.Integer(), nullable=True, comment='Quý (1-4), NULL = cả năm'),
        sa.Column('month', sa.Integer(), nullable=True, comment='Tháng (1-12), NULL = cả năm/quý'),
    ]


def create_metadata_columns():
    """Common metadata columns for all detail tables"""
    return [
        sa.Column('rank_national', sa.Integer(), nullable=True, comment='Xếp hạng so với cả nước'),
        sa.Column('rank_regional', sa.Integer(), nullable=True, comment='Xếp hạng trong vùng'),
        sa.Column('yoy_change', sa.Float(), nullable=True, comment='Thay đổi so với cùng kỳ năm trước (%)'),
        sa.Column('data_status', sa.String(length=20), nullable=False, server_default='official',
                  comment='Trạng thái: official/estimated/forecast'),
        sa.Column('data_source', sa.String(length=255), nullable=True, comment='Nguồn dữ liệu'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Ghi chú'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), comment='Thời điểm cập nhật'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    ]


def create_indexes(table_name: str):
    """Create standard indexes for a detail table"""
    op.create_index(f'ix_{table_name}_province', table_name, ['province'])
    op.create_index(f'ix_{table_name}_year', table_name, ['year'])
    op.create_index(f'ix_{table_name}_quarter', table_name, ['quarter'])
    op.create_index(f'ix_{table_name}_economic_indicator_id', table_name, ['economic_indicator_id'])
    op.create_index(f'ix_{table_name}_data_status', table_name, ['data_status'])
    
    # Unique constraint for province + year + quarter + data_status
    op.create_index(f'ix_{table_name}_unique', table_name,
                    ['province', 'year', 'quarter', 'data_status'],
                    unique=True,
                    postgresql_where=sa.text('quarter IS NOT NULL'))
    
    op.create_index(f'ix_{table_name}_unique_yearly', table_name,
                    ['province', 'year', 'data_status'],
                    unique=True,
                    postgresql_where=sa.text('quarter IS NULL'))


def drop_indexes(table_name: str):
    """Drop standard indexes for a detail table"""
    op.drop_index(f'ix_{table_name}_unique_yearly', table_name)
    op.drop_index(f'ix_{table_name}_unique', table_name)
    op.drop_index(f'ix_{table_name}_data_status', table_name)
    op.drop_index(f'ix_{table_name}_economic_indicator_id', table_name)
    op.drop_index(f'ix_{table_name}_quarter', table_name)
    op.drop_index(f'ix_{table_name}_year', table_name)
    op.drop_index(f'ix_{table_name}_province', table_name)


def upgrade() -> None:
    """Create all 27 indicator detail tables"""
    
    # ========================================
    # LĨNH VỰC 1: XÂY DỰNG ĐẢNG & HỆ THỐNG CHÍNH TRỊ
    # ========================================
    
    # 1.1 corruption_prevention_detail - Mức độ phòng chống tham nhũng
    op.create_table('corruption_prevention_detail',
        *create_base_columns(),
        sa.Column('corruption_perception_index', sa.Float(), nullable=True, comment='Chỉ số cảm nhận tham nhũng (0-100)'),
        sa.Column('reported_cases', sa.Integer(), nullable=True, comment='Số vụ việc được báo cáo'),
        sa.Column('resolved_cases', sa.Integer(), nullable=True, comment='Số vụ việc được xử lý'),
        sa.Column('resolution_rate', sa.Float(), nullable=True, comment='Tỷ lệ xử lý (%)'),
        sa.Column('citizen_trust_score', sa.Float(), nullable=True, comment='Điểm niềm tin của người dân (0-100)'),
        sa.Column('transparency_score', sa.Float(), nullable=True, comment='Điểm minh bạch (0-100)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('corruption_prevention_detail')
    
    # 1.2 cadre_quality_detail - Chất lượng đội ngũ cán bộ, đảng viên
    op.create_table('cadre_quality_detail',
        *create_base_columns(),
        sa.Column('total_cadres', sa.Integer(), nullable=True, comment='Tổng số cán bộ'),
        sa.Column('cadres_with_degree', sa.Integer(), nullable=True, comment='Số cán bộ có bằng cấp'),
        sa.Column('degree_rate', sa.Float(), nullable=True, comment='Tỷ lệ có bằng cấp (%)'),
        sa.Column('training_completion_rate', sa.Float(), nullable=True, comment='Tỷ lệ hoàn thành đào tạo (%)'),
        sa.Column('performance_score', sa.Float(), nullable=True, comment='Điểm đánh giá hiệu suất (0-100)'),
        sa.Column('citizen_satisfaction', sa.Float(), nullable=True, comment='Mức độ hài lòng của dân (0-100)'),
        sa.Column('policy_implementation_score', sa.Float(), nullable=True, comment='Điểm thực thi chính sách (0-100)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('cadre_quality_detail')
    
    # 1.3 party_discipline_detail - DCI - Mức độ tuân thủ kỷ luật Đảng
    op.create_table('party_discipline_detail',
        *create_base_columns(),
        sa.Column('dci_score', sa.Float(), nullable=True, comment='Điểm DCI tổng hợp (0-100)'),
        sa.Column('discipline_violations', sa.Integer(), nullable=True, comment='Số vi phạm kỷ luật'),
        sa.Column('warnings_issued', sa.Integer(), nullable=True, comment='Số cảnh cáo'),
        sa.Column('dismissals', sa.Integer(), nullable=True, comment='Số trường hợp kỷ luật'),
        sa.Column('compliance_rate', sa.Float(), nullable=True, comment='Tỷ lệ tuân thủ (%)'),
        sa.Column('regulation_adherence_score', sa.Float(), nullable=True, comment='Điểm tuân thủ quy định (0-100)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('party_discipline_detail')
    
    # ========================================
    # LĨNH VỰC 2: VĂN HÓA, THỂ THAO & ĐỜI SỐNG TINH THẦN
    # ========================================
    
    # 2.1 culture_sport_access_detail - ACSS - Tiếp cận dịch vụ văn hóa thể thao
    op.create_table('culture_sport_access_detail',
        *create_base_columns(),
        sa.Column('acss_score', sa.Float(), nullable=True, comment='Điểm ACSS tổng hợp (0-100)'),
        sa.Column('cultural_facilities_per_capita', sa.Float(), nullable=True, comment='Số cơ sở văn hóa/10.000 dân'),
        sa.Column('sport_facilities_per_capita', sa.Float(), nullable=True, comment='Số cơ sở thể thao/10.000 dân'),
        sa.Column('participation_rate', sa.Float(), nullable=True, comment='Tỷ lệ tham gia hoạt động (%)'),
        sa.Column('access_distance_km', sa.Float(), nullable=True, comment='Khoảng cách tiếp cận trung bình (km)'),
        sa.Column('affordability_score', sa.Float(), nullable=True, comment='Điểm khả năng chi trả (0-100)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('culture_sport_access_detail')
    
    # 2.2 cultural_infrastructure_detail - Số lượng & chất lượng công trình văn hóa
    op.create_table('cultural_infrastructure_detail',
        *create_base_columns(),
        sa.Column('total_facilities', sa.Integer(), nullable=True, comment='Tổng số công trình văn hóa'),
        sa.Column('libraries', sa.Integer(), nullable=True, comment='Số thư viện'),
        sa.Column('museums', sa.Integer(), nullable=True, comment='Số bảo tàng'),
        sa.Column('theaters', sa.Integer(), nullable=True, comment='Số nhà hát'),
        sa.Column('cultural_houses', sa.Integer(), nullable=True, comment='Số nhà văn hóa'),
        sa.Column('heritage_sites', sa.Integer(), nullable=True, comment='Số di tích lịch sử'),
        sa.Column('quality_score', sa.Float(), nullable=True, comment='Điểm chất lượng tổng hợp (0-100)'),
        sa.Column('utilization_rate', sa.Float(), nullable=True, comment='Tỷ lệ sử dụng (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('cultural_infrastructure_detail')
    
    # 2.3 culture_socialization_detail - Tỷ lệ xã hội hóa hoạt động văn hóa thể thao
    op.create_table('culture_socialization_detail',
        *create_base_columns(),
        sa.Column('socialization_rate', sa.Float(), nullable=True, comment='Tỷ lệ xã hội hóa (%)'),
        sa.Column('private_investment_billion', sa.Float(), nullable=True, comment='Đầu tư tư nhân (tỷ VNĐ)'),
        sa.Column('public_private_ratio', sa.Float(), nullable=True, comment='Tỷ lệ công-tư'),
        sa.Column('private_facilities', sa.Integer(), nullable=True, comment='Số cơ sở tư nhân'),
        sa.Column('community_events', sa.Integer(), nullable=True, comment='Số sự kiện cộng đồng'),
        sa.Column('volunteer_participation', sa.Integer(), nullable=True, comment='Số người tham gia tình nguyện'),
        sa.Column('sustainability_score', sa.Float(), nullable=True, comment='Điểm bền vững (0-100)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('culture_socialization_detail')
    
    # ========================================
    # LĨNH VỰC 3: MÔI TRƯỜNG & BIẾN ĐỔI KHÍ HẬU
    # ========================================
    
    # 3.1 air_quality_detail - AQI - Chỉ số chất lượng không khí
    op.create_table('air_quality_detail',
        *create_base_columns(),
        sa.Column('aqi_score', sa.Float(), nullable=True, comment='Chỉ số AQI trung bình'),
        sa.Column('pm25', sa.Float(), nullable=True, comment='Nồng độ PM2.5 (μg/m³)'),
        sa.Column('pm10', sa.Float(), nullable=True, comment='Nồng độ PM10 (μg/m³)'),
        sa.Column('no2', sa.Float(), nullable=True, comment='Nồng độ NO2 (ppb)'),
        sa.Column('so2', sa.Float(), nullable=True, comment='Nồng độ SO2 (ppb)'),
        sa.Column('co', sa.Float(), nullable=True, comment='Nồng độ CO (ppm)'),
        sa.Column('o3', sa.Float(), nullable=True, comment='Nồng độ O3 (ppb)'),
        sa.Column('good_days_pct', sa.Float(), nullable=True, comment='Tỷ lệ ngày không khí tốt (%)'),
        sa.Column('health_impact_score', sa.Float(), nullable=True, comment='Điểm tác động sức khỏe (0-100)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('air_quality_detail')
    
    # 3.2 climate_resilience_detail - Khả năng chống chịu biến đổi khí hậu
    op.create_table('climate_resilience_detail',
        *create_base_columns(),
        sa.Column('resilience_score', sa.Float(), nullable=True, comment='Điểm khả năng chống chịu (0-100)'),
        sa.Column('flood_risk_score', sa.Float(), nullable=True, comment='Điểm rủi ro lũ lụt (0-100)'),
        sa.Column('drought_risk_score', sa.Float(), nullable=True, comment='Điểm rủi ro hạn hán (0-100)'),
        sa.Column('sea_level_rise_risk', sa.Float(), nullable=True, comment='Rủi ro nước biển dâng (0-100)'),
        sa.Column('adaptation_investment_billion', sa.Float(), nullable=True, comment='Đầu tư thích ứng (tỷ VNĐ)'),
        sa.Column('green_coverage_pct', sa.Float(), nullable=True, comment='Tỷ lệ che phủ xanh (%)'),
        sa.Column('disaster_preparedness_score', sa.Float(), nullable=True, comment='Điểm chuẩn bị thiên tai (0-100)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('climate_resilience_detail')
    
    # 3.3 waste_management_detail - Quản lý & xử lý chất thải
    op.create_table('waste_management_detail',
        *create_base_columns(),
        sa.Column('waste_collection_rate', sa.Float(), nullable=True, comment='Tỷ lệ thu gom rác thải (%)'),
        sa.Column('waste_treatment_rate', sa.Float(), nullable=True, comment='Tỷ lệ xử lý rác thải (%)'),
        sa.Column('recycling_rate', sa.Float(), nullable=True, comment='Tỷ lệ tái chế (%)'),
        sa.Column('total_waste_tons', sa.Float(), nullable=True, comment='Tổng lượng rác thải (tấn)'),
        sa.Column('hazardous_waste_tons', sa.Float(), nullable=True, comment='Rác thải nguy hại (tấn)'),
        sa.Column('landfill_capacity_pct', sa.Float(), nullable=True, comment='Tỷ lệ sử dụng bãi chôn lấp (%)'),
        sa.Column('wastewater_treatment_rate', sa.Float(), nullable=True, comment='Tỷ lệ xử lý nước thải (%)'),
        sa.Column('management_score', sa.Float(), nullable=True, comment='Điểm quản lý tổng hợp (0-100)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('waste_management_detail')
    
    # ========================================
    # LĨNH VỰC 4: AN SINH XÃ HỘI & CHÍNH SÁCH
    # ========================================
    
    # 4.1 hdi_detail - HDI - Chỉ số phát triển con người
    op.create_table('hdi_detail',
        *create_base_columns(),
        sa.Column('hdi_score', sa.Float(), nullable=True, comment='Chỉ số HDI tổng hợp (0-1)'),
        sa.Column('life_expectancy', sa.Float(), nullable=True, comment='Tuổi thọ trung bình (năm)'),
        sa.Column('mean_schooling_years', sa.Float(), nullable=True, comment='Số năm đi học trung bình'),
        sa.Column('expected_schooling_years', sa.Float(), nullable=True, comment='Số năm đi học kỳ vọng'),
        sa.Column('gni_per_capita', sa.Float(), nullable=True, comment='Thu nhập bình quân/người (USD)'),
        sa.Column('health_index', sa.Float(), nullable=True, comment='Chỉ số sức khỏe'),
        sa.Column('education_index', sa.Float(), nullable=True, comment='Chỉ số giáo dục'),
        sa.Column('income_index', sa.Float(), nullable=True, comment='Chỉ số thu nhập'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('hdi_detail')
    
    # 4.2 social_security_coverage_detail - Tỷ lệ bao phủ an sinh xã hội
    op.create_table('social_security_coverage_detail',
        *create_base_columns(),
        sa.Column('coverage_rate', sa.Float(), nullable=True, comment='Tỷ lệ bao phủ tổng (%)'),
        sa.Column('health_insurance_coverage', sa.Float(), nullable=True, comment='Bao phủ BHYT (%)'),
        sa.Column('social_insurance_coverage', sa.Float(), nullable=True, comment='Bao phủ BHXH (%)'),
        sa.Column('unemployment_insurance_coverage', sa.Float(), nullable=True, comment='Bao phủ BH thất nghiệp (%)'),
        sa.Column('pension_coverage', sa.Float(), nullable=True, comment='Bao phủ lương hưu (%)'),
        sa.Column('beneficiaries_count', sa.Integer(), nullable=True, comment='Số người thụ hưởng'),
        sa.Column('vulnerable_group_coverage', sa.Float(), nullable=True, comment='Bao phủ nhóm yếu thế (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('social_security_coverage_detail')
    
    # 4.3 social_budget_detail - Tỷ trọng chi ngân sách cho an sinh xã hội
    op.create_table('social_budget_detail',
        *create_base_columns(),
        sa.Column('social_budget_pct', sa.Float(), nullable=True, comment='Tỷ trọng chi ASXH/tổng ngân sách (%)'),
        sa.Column('total_social_budget_billion', sa.Float(), nullable=True, comment='Tổng chi ASXH (tỷ VNĐ)'),
        sa.Column('health_budget_billion', sa.Float(), nullable=True, comment='Chi y tế (tỷ VNĐ)'),
        sa.Column('education_budget_billion', sa.Float(), nullable=True, comment='Chi giáo dục (tỷ VNĐ)'),
        sa.Column('poverty_reduction_billion', sa.Float(), nullable=True, comment='Chi giảm nghèo (tỷ VNĐ)'),
        sa.Column('per_capita_social_spending', sa.Float(), nullable=True, comment='Chi ASXH/người (VNĐ)'),
        sa.Column('budget_execution_rate', sa.Float(), nullable=True, comment='Tỷ lệ giải ngân (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('social_budget_detail')
    
    # ========================================
    # LĨNH VỰC 5: AN NINH, TRẬT TỰ & QUỐC PHÒNG
    # ========================================
    
    # 5.1 public_order_detail - Mức độ bảo đảm an ninh trật tự xã hội
    op.create_table('public_order_detail',
        *create_base_columns(),
        sa.Column('public_order_score', sa.Float(), nullable=True, comment='Điểm an ninh trật tự tổng hợp (0-100)'),
        sa.Column('safety_perception_score', sa.Float(), nullable=True, comment='Điểm cảm nhận an toàn (0-100)'),
        sa.Column('crime_rate_per_100k', sa.Float(), nullable=True, comment='Tỷ lệ tội phạm/100.000 dân'),
        sa.Column('violent_crime_rate', sa.Float(), nullable=True, comment='Tỷ lệ tội phạm bạo lực'),
        sa.Column('property_crime_rate', sa.Float(), nullable=True, comment='Tỷ lệ tội phạm tài sản'),
        sa.Column('police_per_capita', sa.Float(), nullable=True, comment='Số công an/10.000 dân'),
        sa.Column('response_time_minutes', sa.Float(), nullable=True, comment='Thời gian phản ứng trung bình (phút)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('public_order_detail')
    
    # 5.2 crime_prevention_detail - Tỷ lệ phòng chống & giảm tội phạm
    op.create_table('crime_prevention_detail',
        *create_base_columns(),
        sa.Column('crime_reduction_rate', sa.Float(), nullable=True, comment='Tỷ lệ giảm tội phạm (%)'),
        sa.Column('case_clearance_rate', sa.Float(), nullable=True, comment='Tỷ lệ phá án (%)'),
        sa.Column('total_cases', sa.Integer(), nullable=True, comment='Tổng số vụ án'),
        sa.Column('solved_cases', sa.Integer(), nullable=True, comment='Số vụ án được giải quyết'),
        sa.Column('prevention_programs', sa.Integer(), nullable=True, comment='Số chương trình phòng ngừa'),
        sa.Column('community_watch_groups', sa.Integer(), nullable=True, comment='Số tổ dân phòng'),
        sa.Column('drug_crime_reduction', sa.Float(), nullable=True, comment='Giảm tội phạm ma túy (%)'),
        sa.Column('effectiveness_score', sa.Float(), nullable=True, comment='Điểm hiệu quả (0-100)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('crime_prevention_detail')
    
    # 5.3 traffic_safety_detail - An toàn giao thông & xã hội
    op.create_table('traffic_safety_detail',
        *create_base_columns(),
        sa.Column('traffic_safety_score', sa.Float(), nullable=True, comment='Điểm an toàn giao thông (0-100)'),
        sa.Column('accidents_total', sa.Integer(), nullable=True, comment='Tổng số vụ tai nạn'),
        sa.Column('fatalities', sa.Integer(), nullable=True, comment='Số người tử vong'),
        sa.Column('injuries', sa.Integer(), nullable=True, comment='Số người bị thương'),
        sa.Column('accidents_per_100k_vehicles', sa.Float(), nullable=True, comment='Tai nạn/100.000 phương tiện'),
        sa.Column('fatalities_per_100k_pop', sa.Float(), nullable=True, comment='Tử vong/100.000 dân'),
        sa.Column('drunk_driving_cases', sa.Integer(), nullable=True, comment='Số vụ vi phạm nồng độ cồn'),
        sa.Column('helmet_compliance_rate', sa.Float(), nullable=True, comment='Tỷ lệ đội mũ bảo hiểm (%)'),
        sa.Column('accident_reduction_rate', sa.Float(), nullable=True, comment='Tỷ lệ giảm tai nạn (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('traffic_safety_detail')
    
    # ========================================
    # LĨNH VỰC 6: HÀNH CHÍNH CÔNG & QUẢN LÝ NHÀ NƯỚC
    # ========================================
    
    # 6.1 par_index_detail - PAR Index - Chỉ số cải cách hành chính
    op.create_table('par_index_detail',
        *create_base_columns(),
        sa.Column('par_index_score', sa.Float(), nullable=True, comment='Điểm PAR Index tổng hợp (0-100)'),
        sa.Column('institutional_reform_score', sa.Float(), nullable=True, comment='Điểm cải cách thể chế'),
        sa.Column('admin_procedure_score', sa.Float(), nullable=True, comment='Điểm cải cách TTHC'),
        sa.Column('organizational_reform_score', sa.Float(), nullable=True, comment='Điểm cải cách tổ chức'),
        sa.Column('civil_service_reform_score', sa.Float(), nullable=True, comment='Điểm cải cách công chức'),
        sa.Column('public_finance_reform_score', sa.Float(), nullable=True, comment='Điểm cải cách tài chính công'),
        sa.Column('egovernment_reform_score', sa.Float(), nullable=True, comment='Điểm cải cách CPĐT'),
        sa.Column('citizen_impact_score', sa.Float(), nullable=True, comment='Điểm tác động đến người dân'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('par_index_detail')
    
    # 6.2 sipas_detail - SIPAS - Chỉ số hài lòng của người dân
    op.create_table('sipas_detail',
        *create_base_columns(),
        sa.Column('sipas_score', sa.Float(), nullable=True, comment='Điểm SIPAS tổng hợp (0-100)'),
        sa.Column('service_access_score', sa.Float(), nullable=True, comment='Điểm tiếp cận dịch vụ'),
        sa.Column('procedure_simplicity_score', sa.Float(), nullable=True, comment='Điểm đơn giản hóa thủ tục'),
        sa.Column('staff_attitude_score', sa.Float(), nullable=True, comment='Điểm thái độ cán bộ'),
        sa.Column('processing_time_score', sa.Float(), nullable=True, comment='Điểm thời gian xử lý'),
        sa.Column('transparency_score', sa.Float(), nullable=True, comment='Điểm minh bạch'),
        sa.Column('online_service_score', sa.Float(), nullable=True, comment='Điểm dịch vụ trực tuyến'),
        sa.Column('complaint_resolution_score', sa.Float(), nullable=True, comment='Điểm giải quyết khiếu nại'),
        sa.Column('surveys_conducted', sa.Integer(), nullable=True, comment='Số khảo sát thực hiện'),
        sa.Column('respondents_count', sa.Integer(), nullable=True, comment='Số người phản hồi'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('sipas_detail')
    
    # 6.3 egovernment_detail - Chỉ số chính phủ số / E-Government
    op.create_table('egovernment_detail',
        *create_base_columns(),
        sa.Column('egov_score', sa.Float(), nullable=True, comment='Điểm E-Government tổng hợp (0-100)'),
        sa.Column('online_services_count', sa.Integer(), nullable=True, comment='Số dịch vụ công trực tuyến'),
        sa.Column('level_4_services_count', sa.Integer(), nullable=True, comment='Số DVC mức độ 4'),
        sa.Column('online_transaction_rate', sa.Float(), nullable=True, comment='Tỷ lệ giao dịch trực tuyến (%)'),
        sa.Column('digital_document_rate', sa.Float(), nullable=True, comment='Tỷ lệ hồ sơ số hóa (%)'),
        sa.Column('one_stop_portal_usage', sa.Float(), nullable=True, comment='Tỷ lệ sử dụng cổng DVC (%)'),
        sa.Column('data_sharing_score', sa.Float(), nullable=True, comment='Điểm chia sẻ dữ liệu'),
        sa.Column('cybersecurity_score', sa.Float(), nullable=True, comment='Điểm an ninh mạng'),
        sa.Column('digital_literacy_rate', sa.Float(), nullable=True, comment='Tỷ lệ biết sử dụng CNTT (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('egovernment_detail')
    
    # ========================================
    # LĨNH VỰC 7: Y TẾ & CHĂM SÓC SỨC KHỎE
    # ========================================
    
    # 7.1 health_insurance_detail - BHYT Coverage Rate
    op.create_table('health_insurance_detail',
        *create_base_columns(),
        sa.Column('bhyt_coverage_rate', sa.Float(), nullable=True, comment='Tỷ lệ bao phủ BHYT (%)'),
        sa.Column('total_insured', sa.Integer(), nullable=True, comment='Tổng số người có BHYT'),
        sa.Column('voluntary_insured', sa.Integer(), nullable=True, comment='Số người tham gia tự nguyện'),
        sa.Column('mandatory_insured', sa.Integer(), nullable=True, comment='Số người tham gia bắt buộc'),
        sa.Column('poor_near_poor_coverage', sa.Float(), nullable=True, comment='Bao phủ hộ nghèo/cận nghèo (%)'),
        sa.Column('children_coverage', sa.Float(), nullable=True, comment='Bao phủ trẻ em (%)'),
        sa.Column('elderly_coverage', sa.Float(), nullable=True, comment='Bao phủ người cao tuổi (%)'),
        sa.Column('claims_amount_billion', sa.Float(), nullable=True, comment='Chi trả BHYT (tỷ VNĐ)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('health_insurance_detail')
    
    # 7.2 haq_index_detail - HAQ Index - Chất lượng dịch vụ y tế
    op.create_table('haq_index_detail',
        *create_base_columns(),
        sa.Column('haq_score', sa.Float(), nullable=True, comment='Điểm HAQ Index (0-100)'),
        sa.Column('healthcare_access_score', sa.Float(), nullable=True, comment='Điểm tiếp cận y tế'),
        sa.Column('healthcare_quality_score', sa.Float(), nullable=True, comment='Điểm chất lượng y tế'),
        sa.Column('hospital_beds_per_10k', sa.Float(), nullable=True, comment='Số giường bệnh/10.000 dân'),
        sa.Column('doctors_per_10k', sa.Float(), nullable=True, comment='Số bác sĩ/10.000 dân'),
        sa.Column('nurses_per_10k', sa.Float(), nullable=True, comment='Số điều dưỡng/10.000 dân'),
        sa.Column('maternal_mortality_rate', sa.Float(), nullable=True, comment='Tỷ lệ tử vong mẹ/100.000'),
        sa.Column('infant_mortality_rate', sa.Float(), nullable=True, comment='Tỷ lệ tử vong trẻ sơ sinh/1.000'),
        sa.Column('treatment_success_rate', sa.Float(), nullable=True, comment='Tỷ lệ điều trị thành công (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('haq_index_detail')
    
    # 7.3 preventive_health_detail - Năng lực y tế dự phòng
    op.create_table('preventive_health_detail',
        *create_base_columns(),
        sa.Column('preventive_health_score', sa.Float(), nullable=True, comment='Điểm y tế dự phòng (0-100)'),
        sa.Column('vaccination_coverage', sa.Float(), nullable=True, comment='Tỷ lệ tiêm chủng (%)'),
        sa.Column('health_screening_rate', sa.Float(), nullable=True, comment='Tỷ lệ khám sàng lọc (%)'),
        sa.Column('disease_surveillance_score', sa.Float(), nullable=True, comment='Điểm giám sát dịch bệnh'),
        sa.Column('epidemic_response_score', sa.Float(), nullable=True, comment='Điểm ứng phó dịch bệnh'),
        sa.Column('preventive_facilities', sa.Integer(), nullable=True, comment='Số cơ sở y tế dự phòng'),
        sa.Column('health_education_programs', sa.Integer(), nullable=True, comment='Số chương trình giáo dục sức khỏe'),
        sa.Column('clean_water_access_rate', sa.Float(), nullable=True, comment='Tỷ lệ tiếp cận nước sạch (%)'),
        sa.Column('sanitation_access_rate', sa.Float(), nullable=True, comment='Tỷ lệ có công trình vệ sinh (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('preventive_health_detail')
    
    # ========================================
    # LĨNH VỰC 8: GIÁO DỤC & ĐÀO TẠO
    # ========================================
    
    # 8.1 eqi_detail - EQI - Chỉ số chất lượng giáo dục
    op.create_table('eqi_detail',
        *create_base_columns(),
        sa.Column('eqi_score', sa.Float(), nullable=True, comment='Điểm EQI tổng hợp (0-100)'),
        sa.Column('literacy_rate', sa.Float(), nullable=True, comment='Tỷ lệ biết chữ (%)'),
        sa.Column('school_enrollment_rate', sa.Float(), nullable=True, comment='Tỷ lệ nhập học (%)'),
        sa.Column('primary_completion_rate', sa.Float(), nullable=True, comment='Tỷ lệ hoàn thành tiểu học (%)'),
        sa.Column('secondary_completion_rate', sa.Float(), nullable=True, comment='Tỷ lệ hoàn thành THCS (%)'),
        sa.Column('teacher_qualification_rate', sa.Float(), nullable=True, comment='Tỷ lệ GV đạt chuẩn (%)'),
        sa.Column('student_teacher_ratio', sa.Float(), nullable=True, comment='Tỷ lệ học sinh/giáo viên'),
        sa.Column('learning_outcome_score', sa.Float(), nullable=True, comment='Điểm kết quả học tập'),
        sa.Column('education_spending_per_student', sa.Float(), nullable=True, comment='Chi tiêu GD/học sinh (VNĐ)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('eqi_detail')
    
    # 8.2 highschool_graduation_detail - Tỷ lệ đỗ tốt nghiệp THPT
    op.create_table('highschool_graduation_detail',
        *create_base_columns(),
        sa.Column('graduation_rate', sa.Float(), nullable=True, comment='Tỷ lệ đỗ tốt nghiệp (%)'),
        sa.Column('total_candidates', sa.Integer(), nullable=True, comment='Tổng số thí sinh'),
        sa.Column('passed_candidates', sa.Integer(), nullable=True, comment='Số thí sinh đỗ'),
        sa.Column('average_score', sa.Float(), nullable=True, comment='Điểm trung bình'),
        sa.Column('math_avg_score', sa.Float(), nullable=True, comment='Điểm TB môn Toán'),
        sa.Column('literature_avg_score', sa.Float(), nullable=True, comment='Điểm TB môn Văn'),
        sa.Column('english_avg_score', sa.Float(), nullable=True, comment='Điểm TB môn Anh'),
        sa.Column('excellent_rate', sa.Float(), nullable=True, comment='Tỷ lệ điểm giỏi (%)'),
        sa.Column('fail_rate', sa.Float(), nullable=True, comment='Tỷ lệ trượt (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('highschool_graduation_detail')
    
    # 8.3 tvet_employment_detail - TVET Employment Rate
    op.create_table('tvet_employment_detail',
        *create_base_columns(),
        sa.Column('employment_rate', sa.Float(), nullable=True, comment='Tỷ lệ có việc làm sau tốt nghiệp (%)'),
        sa.Column('total_graduates', sa.Integer(), nullable=True, comment='Tổng số tốt nghiệp'),
        sa.Column('employed_graduates', sa.Integer(), nullable=True, comment='Số có việc làm'),
        sa.Column('relevant_job_rate', sa.Float(), nullable=True, comment='Tỷ lệ việc làm đúng ngành (%)'),
        sa.Column('average_starting_salary', sa.Float(), nullable=True, comment='Lương khởi điểm TB (VNĐ)'),
        sa.Column('employer_satisfaction', sa.Float(), nullable=True, comment='Mức độ hài lòng của DN (0-100)'),
        sa.Column('tvet_enrollment', sa.Integer(), nullable=True, comment='Số tuyển sinh GDNN'),
        sa.Column('tvet_facilities', sa.Integer(), nullable=True, comment='Số cơ sở GDNN'),
        sa.Column('industry_partnership_count', sa.Integer(), nullable=True, comment='Số liên kết với DN'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('tvet_employment_detail')
    
    # ========================================
    # LĨNH VỰC 9: HẠ TẦNG & GIAO THÔNG
    # ========================================
    
    # 9.1 transport_infrastructure_detail - Chất lượng hạ tầng giao thông
    op.create_table('transport_infrastructure_detail',
        *create_base_columns(),
        sa.Column('infrastructure_score', sa.Float(), nullable=True, comment='Điểm hạ tầng GT tổng hợp (0-100)'),
        sa.Column('road_length_km', sa.Float(), nullable=True, comment='Tổng chiều dài đường (km)'),
        sa.Column('paved_road_rate', sa.Float(), nullable=True, comment='Tỷ lệ đường nhựa/bê tông (%)'),
        sa.Column('road_density_km_per_km2', sa.Float(), nullable=True, comment='Mật độ đường (km/km²)'),
        sa.Column('bridge_count', sa.Integer(), nullable=True, comment='Số cầu'),
        sa.Column('public_transport_coverage', sa.Float(), nullable=True, comment='Độ phủ GTCC (%)'),
        sa.Column('road_quality_score', sa.Float(), nullable=True, comment='Điểm chất lượng đường'),
        sa.Column('maintenance_budget_billion', sa.Float(), nullable=True, comment='Ngân sách bảo trì (tỷ VNĐ)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('transport_infrastructure_detail')
    
    # 9.2 traffic_congestion_detail - Chỉ số vận hành & ùn tắc giao thông
    op.create_table('traffic_congestion_detail',
        *create_base_columns(),
        sa.Column('congestion_index', sa.Float(), nullable=True, comment='Chỉ số ùn tắc (0-100, cao = tệ)'),
        sa.Column('average_speed_kmh', sa.Float(), nullable=True, comment='Tốc độ trung bình (km/h)'),
        sa.Column('peak_hour_delay_minutes', sa.Float(), nullable=True, comment='Độ trễ giờ cao điểm (phút)'),
        sa.Column('congestion_points', sa.Integer(), nullable=True, comment='Số điểm ùn tắc'),
        sa.Column('traffic_flow_score', sa.Float(), nullable=True, comment='Điểm lưu thông'),
        sa.Column('public_transport_usage_rate', sa.Float(), nullable=True, comment='Tỷ lệ sử dụng GTCC (%)'),
        sa.Column('vehicle_per_1000_pop', sa.Float(), nullable=True, comment='Số phương tiện/1.000 dân'),
        sa.Column('smart_traffic_coverage', sa.Float(), nullable=True, comment='Độ phủ giao thông thông minh (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('traffic_congestion_detail')
    
    # 9.3 planning_progress_detail - Mức độ thực hiện quy hoạch & tiến độ dự án
    op.create_table('planning_progress_detail',
        *create_base_columns(),
        sa.Column('planning_compliance_score', sa.Float(), nullable=True, comment='Điểm tuân thủ quy hoạch (0-100)'),
        sa.Column('total_projects', sa.Integer(), nullable=True, comment='Tổng số dự án'),
        sa.Column('on_schedule_projects', sa.Integer(), nullable=True, comment='Số dự án đúng tiến độ'),
        sa.Column('delayed_projects', sa.Integer(), nullable=True, comment='Số dự án chậm tiến độ'),
        sa.Column('on_schedule_rate', sa.Float(), nullable=True, comment='Tỷ lệ đúng tiến độ (%)'),
        sa.Column('budget_execution_rate', sa.Float(), nullable=True, comment='Tỷ lệ giải ngân (%)'),
        sa.Column('total_investment_billion', sa.Float(), nullable=True, comment='Tổng vốn đầu tư (tỷ VNĐ)'),
        sa.Column('disbursed_billion', sa.Float(), nullable=True, comment='Đã giải ngân (tỷ VNĐ)'),
        sa.Column('land_clearance_completion_rate', sa.Float(), nullable=True, comment='Tỷ lệ GPMB hoàn thành (%)'),
        *create_metadata_columns(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    create_indexes('planning_progress_detail')


def downgrade() -> None:
    """Drop all 27 indicator detail tables"""
    
    # List of all tables in reverse order
    tables = [
        # Lĩnh vực 9
        'planning_progress_detail',
        'traffic_congestion_detail',
        'transport_infrastructure_detail',
        # Lĩnh vực 8
        'tvet_employment_detail',
        'highschool_graduation_detail',
        'eqi_detail',
        # Lĩnh vực 7
        'preventive_health_detail',
        'haq_index_detail',
        'health_insurance_detail',
        # Lĩnh vực 6
        'egovernment_detail',
        'sipas_detail',
        'par_index_detail',
        # Lĩnh vực 5
        'traffic_safety_detail',
        'crime_prevention_detail',
        'public_order_detail',
        # Lĩnh vực 4
        'social_budget_detail',
        'social_security_coverage_detail',
        'hdi_detail',
        # Lĩnh vực 3
        'waste_management_detail',
        'climate_resilience_detail',
        'air_quality_detail',
        # Lĩnh vực 2
        'culture_socialization_detail',
        'cultural_infrastructure_detail',
        'culture_sport_access_detail',
        # Lĩnh vực 1
        'party_discipline_detail',
        'cadre_quality_detail',
        'corruption_prevention_detail',
    ]
    
    for table in tables:
        drop_indexes(table)
        op.drop_table(table)
