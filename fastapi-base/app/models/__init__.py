from app.models.model_base import Base
from app.models.model_article import Article
from app.models.model_sentiment import SentimentAnalysis
from app.models.model_custom_topic import (
    CustomTopic,
    ArticleCustomTopic,
    TopicClassificationLog,
    TopicTemplate
)
from app.models.model_bertopic_discovered import (
    BertopicDiscoveredTopic,
    ArticleBertopicTopic,
    TopicTrainingSession
)
from app.models.model_statistics import (
    TrendReport,
    HotTopic,
    KeywordStats,
    TopicMentionStats,
    WebsiteActivityStats,
    SocialActivityStats,
    DailySnapshot
)
from app.models.model_trends import (
    TrendAlert,
    HashtagStats,
    ViralContent,
    CategoryTrendStats
)
from app.models.model_field_classification import (
    Field,
    ArticleFieldClassification,
    FieldStatistics
)
from app.models.model_field_summary import FieldSummary
from app.models.model_field_sentiment import FieldSentiment
from app.models.model_economic_indicators import (
    EconomicIndicator,
    EconomicIndicatorGPT
)
from app.models.model_grdp_detail import GRDPDetail

# 27 Indicator Detail Models (9 lĩnh vực × 3 chỉ số)
from app.models.model_indicator_details import (
    # Lĩnh vực 1: Xây dựng Đảng & Hệ thống chính trị
    CorruptionPreventionDetail,
    CadreQualityDetail,
    PartyDisciplineDetail,
    # Lĩnh vực 2: Văn hóa, Thể thao & Đời sống tinh thần
    CultureSportAccessDetail,
    CulturalInfrastructureDetail,
    CultureSocializationDetail,
    # Lĩnh vực 3: Môi trường & Biến đổi khí hậu
    AirQualityDetail,
    ClimateResilienceDetail,
    WasteManagementDetail,
    # Lĩnh vực 4: An sinh xã hội & Chính sách
    HDIDetail,
    SocialSecurityCoverageDetail,
    SocialBudgetDetail,
    # Lĩnh vực 5: An ninh, Trật tự & Quốc phòng
    PublicOrderDetail,
    CrimePreventionDetail,
    TrafficSafetyDetail,
    # Lĩnh vực 6: Hành chính công & Quản lý Nhà nước
    PARIndexDetail,
    SIPASDetail,
    EGovernmentDetail,
    # Lĩnh vực 7: Y tế & Chăm sóc sức khỏe
    HealthInsuranceDetail,
    HAQIndexDetail,
    PreventiveHealthDetail,
    # Lĩnh vực 8: Giáo dục & Đào tạo
    EQIDetail,
    HighschoolGraduationDetail,
    TVETEmploymentDetail,
    # Lĩnh vực 9: Hạ tầng & Giao thông
    TransportInfrastructureDetail,
    TrafficCongestionDetail,
    PlanningProgressDetail,
    # Registry
    INDICATOR_DETAIL_MODELS,
    FIELD_INDICATORS,
)

# Archived: model_user, model_crawl_history, model_source
