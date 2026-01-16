"""
Social Indicator Extractor - Trích xuất chỉ số xã hội từ articles

9 Lĩnh vực × 3 Chỉ số = 27 bảng detail

Pipeline:
    Articles → LLM Classification → Regex Extraction → Validation → DB

NGUYÊN TẮC:
- LLM CHỈ dùng để classify và detect relevance
- Số liệu = REGEX ONLY từ văn bản gốc
- KHÔNG sinh ảo, KHÔNG bịa số - không có thì để NULL
"""
import re
import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# LLM imports
try:
    from openai import OpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


# =============================================================================
# CATEGORY MAPPING - Map article.category to field_key
# =============================================================================
# CHUẨN HÓA: Category chỉ có 8 giá trị mặc định (1-1 mapping)

CATEGORY_TO_FIELD = {
    # 8 giá trị category chuẩn
    "medical": "y_te",                      # Y tế & Chăm sóc sức khỏe
    "education": "giao_duc",                # Giáo dục & Đào tạo
    "transportation": "ha_tang_giao_thong", # Hạ tầng & Giao thông
    "environment": "moi_truong",            # Môi trường & Biến đổi khí hậu
    "policy": "an_sinh_xa_hoi",             # An sinh xã hội & Chính sách
    "security": "an_ninh_trat_tu",          # An ninh, Trật tự & Quốc phòng
    "management": "hanh_chinh_cong",        # Hành chính công & Quản lý Nhà nước
    "politics": "xay_dung_dang",            # Xây dựng Đảng & Hệ thống chính trị
    "society": "van_hoa_the_thao",          # Văn hóa, Thể thao & Đời sống tinh thần
}

# Reverse mapping: field_key -> list of categories
FIELD_TO_CATEGORIES = {}
for cat, field in CATEGORY_TO_FIELD.items():
    if field not in FIELD_TO_CATEGORIES:
        FIELD_TO_CATEGORIES[field] = []
    FIELD_TO_CATEGORIES[field].append(cat)


# =============================================================================
# FIELD DEFINITIONS - 9 Lĩnh vực với keywords và patterns
# =============================================================================

FIELD_DEFINITIONS = {
    # LĨNH VỰC 1: Xây dựng Đảng & Hệ thống chính trị
    "xay_dung_dang": {
        "name": "Xây dựng Đảng & Hệ thống chính trị",
        "indicators": {
            "corruption_prevention": {
                "name": "Mức độ phòng chống tham nhũng",
                "keywords": ["tham nhũng", "phòng chống tham nhũng", "tiêu cực", "kê khai tài sản", 
                            "minh bạch", "thanh tra", "kiểm toán", "xử lý kỷ luật"],
                "patterns": {
                    "corruption_perception_index": r"(?:chỉ số|điểm)\s*(?:cảm nhận)?\s*tham nhũng[:\s]+(\d+[.,]?\d*)",
                    "reported_cases": r"(?:phát hiện|báo cáo|xử lý)\s*(\d+)\s*(?:vụ|vụ việc|trường hợp)",
                    "resolved_cases": r"(?:xử lý|kết luận|giải quyết)\s*(\d+)\s*(?:vụ|vụ việc)",
                    "resolution_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:xử lý|giải quyết)[:\s]+(\d+[.,]?\d*)\s*%",
                }
            },
            "cadre_quality": {
                "name": "Chất lượng đội ngũ cán bộ, đảng viên",
                "keywords": ["cán bộ", "đảng viên", "công chức", "viên chức", "đào tạo cán bộ",
                            "bồi dưỡng", "nâng cao trình độ", "học vị", "bằng cấp"],
                "patterns": {
                    "total_cadres": r"(?:tổng số|có)\s*(\d+(?:[.,]\d+)?)\s*(?:cán bộ|công chức|viên chức)",
                    "cadres_with_degree": r"(\d+(?:[.,]\d+)?)\s*(?:cán bộ|người)\s*(?:có|đạt)\s*(?:bằng|trình độ)",
                    "degree_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:có bằng|đạt chuẩn|trình độ)[:\s]+(\d+[.,]?\d*)\s*%",
                    "training_completion_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:hoàn thành|tham gia)\s*(?:đào tạo|bồi dưỡng)[:\s]+(\d+[.,]?\d*)\s*%",
                }
            },
            "party_discipline": {
                "name": "Mức độ tuân thủ kỷ luật Đảng (DCI)",
                "keywords": ["kỷ luật đảng", "vi phạm", "cảnh cáo", "khiển trách", "khai trừ",
                            "kiểm tra đảng viên", "giám sát", "thi hành kỷ luật"],
                "patterns": {
                    "discipline_violations": r"(\d+)\s*(?:trường hợp|đảng viên|người)\s*vi phạm",
                    "warnings_issued": r"(?:cảnh cáo|khiển trách)\s*(\d+)\s*(?:trường hợp|đảng viên|người)",
                    "dismissals": r"(?:khai trừ|cách chức|kỷ luật)\s*(\d+)\s*(?:trường hợp|đảng viên|người)",
                    "compliance_rate": r"(?:tỷ lệ|tỉ lệ)\s*tuân thủ[:\s]+(\d+[.,]?\d*)\s*%",
                }
            }
        }
    },
    
    # LĨNH VỰC 2: Văn hóa, Thể thao & Đời sống tinh thần
    "van_hoa_the_thao": {
        "name": "Văn hóa, Thể thao & Đời sống tinh thần",
        "indicators": {
            "culture_sport_access": {
                "name": "Tiếp cận dịch vụ văn hóa thể thao (ACSS)",
                "keywords": ["văn hóa", "thể thao", "thể dục", "vận động viên", "huy chương",
                            "câu lạc bộ", "nhà văn hóa", "sân vận động", "bể bơi"],
                "patterns": {
                    "participation_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:tham gia|luyện tập)[:\s]+(\d+[.,]?\d*)\s*%",
                    "cultural_facilities_per_capita": r"(\d+[.,]?\d*)\s*(?:cơ sở|điểm)/\s*(?:vạn|10\.?000)\s*dân",
                }
            },
            "cultural_infrastructure": {
                "name": "Số lượng & chất lượng công trình văn hóa",
                "keywords": ["thư viện", "bảo tàng", "nhà hát", "rạp chiếu phim", "di tích",
                            "di sản", "nhà văn hóa", "trung tâm văn hóa"],
                "patterns": {
                    "libraries": r"(\d+)\s*thư viện",
                    "museums": r"(\d+)\s*bảo tàng",
                    "theaters": r"(\d+)\s*nhà hát",
                    "cultural_houses": r"(\d+)\s*nhà văn hóa",
                    "heritage_sites": r"(\d+)\s*di tích",
                    "total_facilities": r"(?:tổng số|có)\s*(\d+)\s*(?:công trình|cơ sở)\s*văn hóa",
                }
            },
            "culture_socialization": {
                "name": "Xã hội hóa hoạt động văn hóa thể thao",
                "keywords": ["xã hội hóa", "tư nhân", "đầu tư văn hóa", "doanh nghiệp văn hóa",
                            "sự kiện văn hóa", "lễ hội"],
                "patterns": {
                    "socialization_rate": r"(?:tỷ lệ|tỉ lệ)\s*xã hội hóa[:\s]+(\d+[.,]?\d*)\s*%",
                    "private_investment_billion": r"(?:đầu tư|vốn)\s*(?:tư nhân|xã hội hóa)[:\s]+(\d+(?:[.,]\d+)?)\s*tỷ",
                    "community_events": r"(?:tổ chức|có)\s*(\d+)\s*(?:sự kiện|lễ hội|hoạt động)",
                }
            }
        }
    },
    
    # LĨNH VỰC 3: Môi trường & Biến đổi khí hậu
    "moi_truong": {
        "name": "Môi trường & Biến đổi khí hậu",
        "indicators": {
            "air_quality": {
                "name": "Chỉ số chất lượng không khí (AQI)",
                "keywords": ["chất lượng không khí", "ô nhiễm không khí", "AQI", "bụi mịn", 
                            "PM2.5", "PM10", "khí thải"],
                "patterns": {
                    "aqi_score": r"(?:AQI|chỉ số\s*(?:chất lượng)?\s*không khí)[:\s]+(\d+[.,]?\d*)",
                    "pm25": r"PM2[.,]5[:\s]+(\d+[.,]?\d*)",
                    "pm10": r"PM10[:\s]+(\d+[.,]?\d*)",
                    "good_days_pct": r"(\d+[.,]?\d*)\s*%\s*(?:ngày|số ngày)\s*(?:không khí)?\s*(?:tốt|đạt)",
                }
            },
            "climate_resilience": {
                "name": "Khả năng chống chịu biến đổi khí hậu",
                "keywords": ["biến đổi khí hậu", "thiên tai", "lũ lụt", "hạn hán", "bão",
                            "nước biển dâng", "thích ứng", "phòng chống thiên tai"],
                "patterns": {
                    "flood_risk_score": r"(?:rủi ro|nguy cơ)\s*lũ[:\s]+(\d+[.,]?\d*)",
                    "green_coverage_pct": r"(?:tỷ lệ|tỉ lệ)\s*(?:che phủ|phủ xanh|rừng)[:\s]+(\d+[.,]?\d*)\s*%",
                    "adaptation_investment_billion": r"(?:đầu tư|vốn)\s*(?:thích ứng|phòng chống)[:\s]+(\d+(?:[.,]\d+)?)\s*tỷ",
                }
            },
            "waste_management": {
                "name": "Quản lý & xử lý chất thải",
                "keywords": ["rác thải", "chất thải", "thu gom rác", "xử lý rác", "tái chế",
                            "bãi rác", "nước thải", "xử lý nước thải"],
                "patterns": {
                    "waste_collection_rate": r"(?:tỷ lệ|tỉ lệ)\s*thu gom[:\s]+(\d+[.,]?\d*)\s*%",
                    "waste_treatment_rate": r"(?:tỷ lệ|tỉ lệ)\s*xử lý[:\s]+(\d+[.,]?\d*)\s*%",
                    "recycling_rate": r"(?:tỷ lệ|tỉ lệ)\s*tái chế[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_waste_tons": r"(\d+(?:[.,]\d+)?)\s*(?:tấn|nghìn tấn)\s*(?:rác|chất thải)",
                    "wastewater_treatment_rate": r"(?:tỷ lệ|tỉ lệ)\s*xử lý\s*nước thải[:\s]+(\d+[.,]?\d*)\s*%",
                }
            }
        }
    },
    
    # LĨNH VỰC 4: An sinh xã hội & Chính sách
    "an_sinh_xa_hoi": {
        "name": "An sinh xã hội & Chính sách",
        "indicators": {
            "hdi": {
                "name": "Chỉ số phát triển con người (HDI)",
                "keywords": ["HDI", "phát triển con người", "tuổi thọ", "giáo dục", "thu nhập bình quân"],
                "patterns": {
                    "hdi_score": r"(?:HDI|chỉ số\s*phát triển\s*con người)[:\s]+(\d+[.,]?\d*)",
                    "life_expectancy": r"tuổi thọ[:\s]+(\d+[.,]?\d*)\s*(?:tuổi|năm)?",
                    "mean_schooling_years": r"(?:số năm|năm)\s*(?:đi học|học)[:\s]+(\d+[.,]?\d*)",
                    "gni_per_capita": r"(?:thu nhập|GNI)[:\s]+(\d+(?:[.,]\d+)?)\s*(?:USD|đô la)",
                }
            },
            "social_security_coverage": {
                "name": "Tỷ lệ bao phủ an sinh xã hội",
                "keywords": ["bảo hiểm xã hội", "BHXH", "bảo hiểm y tế", "BHYT", "lương hưu",
                            "trợ cấp", "bảo hiểm thất nghiệp", "an sinh"],
                "patterns": {
                    "coverage_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:bao phủ|tham gia)\s*(?:an sinh|BHXH)[:\s]+(\d+[.,]?\d*)\s*%",
                    "health_insurance_coverage": r"(?:tỷ lệ|tỉ lệ)\s*(?:bao phủ|tham gia)\s*(?:BHYT|bảo hiểm y tế)[:\s]+(\d+[.,]?\d*)\s*%",
                    "social_insurance_coverage": r"(?:tỷ lệ|tỉ lệ)\s*(?:bao phủ|tham gia)\s*(?:BHXH|bảo hiểm xã hội)[:\s]+(\d+[.,]?\d*)\s*%",
                    "beneficiaries_count": r"(\d+(?:[.,]\d+)?)\s*(?:người|lao động)\s*(?:tham gia|thụ hưởng)",
                }
            },
            "social_budget": {
                "name": "Chi ngân sách cho an sinh xã hội",
                "keywords": ["ngân sách an sinh", "chi xã hội", "trợ cấp xã hội", "giảm nghèo",
                            "bảo trợ xã hội", "hỗ trợ người nghèo"],
                "patterns": {
                    "social_budget_pct": r"(?:tỷ lệ|tỉ lệ|tỷ trọng)\s*chi\s*(?:an sinh|xã hội)[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_social_budget_billion": r"chi\s*(?:an sinh|xã hội)[:\s]+(\d+(?:[.,]\d+)?)\s*tỷ",
                    "poverty_reduction_billion": r"chi\s*(?:giảm nghèo|xóa đói)[:\s]+(\d+(?:[.,]\d+)?)\s*tỷ",
                    "budget_execution_rate": r"(?:tỷ lệ|tỉ lệ)\s*giải ngân[:\s]+(\d+[.,]?\d*)\s*%",
                }
            }
        }
    },
    
    # LĨNH VỰC 5: An ninh, Trật tự & Quốc phòng
    "an_ninh_trat_tu": {
        "name": "An ninh, Trật tự & Quốc phòng",
        "indicators": {
            "public_order": {
                "name": "Bảo đảm an ninh trật tự xã hội",
                "keywords": ["an ninh", "trật tự", "an toàn xã hội", "tội phạm", "vi phạm pháp luật"],
                "patterns": {
                    "crime_rate_per_100k": r"(\d+[.,]?\d*)\s*(?:vụ|tội phạm)/\s*100[.,]?000\s*dân",
                    "police_per_capita": r"(\d+[.,]?\d*)\s*(?:công an|cảnh sát)/\s*(?:vạn|10\.?000)\s*dân",
                }
            },
            "crime_prevention": {
                "name": "Phòng chống & giảm tội phạm",
                "keywords": ["phòng chống tội phạm", "phá án", "bắt giữ", "khởi tố", "truy tố",
                            "ma túy", "trộm cắp", "cướp giật"],
                "patterns": {
                    "crime_reduction_rate": r"(?:giảm|giảm|giảm)\s*(\d+[.,]?\d*)\s*%\s*(?:tội phạm|vụ án)",
                    "case_clearance_rate": r"(?:tỷ lệ|tỉ lệ)\s*phá án[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_cases": r"(?:xảy ra|phát hiện)\s*(\d+)\s*(?:vụ|vụ án)",
                    "solved_cases": r"(?:phá|điều tra làm rõ)\s*(\d+)\s*(?:vụ|vụ án)",
                }
            },
            "traffic_safety": {
                "name": "An toàn giao thông",
                "keywords": ["tai nạn giao thông", "an toàn giao thông", "TNGT", "tử vong giao thông",
                            "vi phạm giao thông", "nồng độ cồn"],
                "patterns": {
                    "accidents_total": r"(?:xảy ra|có)\s*(\d+)\s*(?:vụ)?\s*tai nạn",
                    "fatalities": r"(?:tử vong|chết)\s*(\d+)\s*(?:người|trường hợp)",
                    "injuries": r"(?:bị thương)\s*(\d+)\s*(?:người|trường hợp)",
                    "accident_reduction_rate": r"(?:giảm)\s*(\d+[.,]?\d*)\s*%\s*(?:tai nạn|TNGT)",
                    "drunk_driving_cases": r"(\d+)\s*(?:vụ|trường hợp)\s*(?:vi phạm)?\s*nồng độ cồn",
                }
            }
        }
    },
    
    # LĨNH VỰC 6: Hành chính công & Quản lý Nhà nước
    "hanh_chinh_cong": {
        "name": "Hành chính công & Quản lý Nhà nước",
        "indicators": {
            "par_index": {
                "name": "Chỉ số cải cách hành chính (PAR Index)",
                "keywords": ["PAR Index", "cải cách hành chính", "CCHC", "thủ tục hành chính",
                            "dịch vụ công", "một cửa"],
                "patterns": {
                    "par_index_score": r"(?:PAR\s*Index|chỉ số\s*CCHC)[:\s]+(\d+[.,]?\d*)",
                    "admin_procedure_score": r"(?:điểm|chỉ số)\s*(?:thủ tục|TTHC)[:\s]+(\d+[.,]?\d*)",
                }
            },
            "sipas": {
                "name": "Chỉ số hài lòng của người dân (SIPAS)",
                "keywords": ["SIPAS", "hài lòng", "sự hài lòng", "đánh giá người dân", "khảo sát"],
                "patterns": {
                    "sipas_score": r"(?:SIPAS|chỉ số\s*hài lòng)[:\s]+(\d+[.,]?\d*)",
                    "service_access_score": r"(?:điểm|chỉ số)\s*tiếp cận[:\s]+(\d+[.,]?\d*)",
                    "respondents_count": r"(\d+(?:[.,]\d+)?)\s*(?:người|phản hồi|khảo sát)",
                }
            },
            "egovernment": {
                "name": "Chính phủ số / E-Government",
                "keywords": ["chính phủ số", "chính quyền số", "dịch vụ công trực tuyến", 
                            "chuyển đổi số", "số hóa", "DVCTT mức độ 4"],
                "patterns": {
                    "online_services_count": r"(\d+)\s*dịch vụ\s*(?:công)?\s*trực tuyến",
                    "level_4_services_count": r"(\d+)\s*(?:dịch vụ|DVCTT)\s*mức độ 4",
                    "online_transaction_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:giao dịch|hồ sơ)\s*trực tuyến[:\s]+(\d+[.,]?\d*)\s*%",
                    "digital_document_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:số hóa|điện tử hóa)[:\s]+(\d+[.,]?\d*)\s*%",
                }
            }
        }
    },
    
    # LĨNH VỰC 7: Y tế & Chăm sóc sức khỏe
    "y_te": {
        "name": "Y tế & Chăm sóc sức khỏe",
        "indicators": {
            "health_insurance": {
                "name": "Bao phủ Bảo hiểm Y tế (BHYT)",
                "keywords": ["bảo hiểm y tế", "BHYT", "thẻ BHYT", "khám chữa bệnh BHYT"],
                "patterns": {
                    "bhyt_coverage_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:bao phủ|tham gia)\s*BHYT[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_insured": r"(\d+(?:[.,]\d+)?)\s*(?:người|thẻ)\s*(?:có|tham gia)\s*BHYT",
                    "claims_amount_billion": r"chi\s*(?:trả|thanh toán)\s*BHYT[:\s]+(\d+(?:[.,]\d+)?)\s*tỷ",
                }
            },
            "haq_index": {
                "name": "Chất lượng dịch vụ y tế (HAQ Index)",
                "keywords": ["HAQ", "chất lượng y tế", "bệnh viện", "giường bệnh", "bác sĩ",
                            "y tá", "điều dưỡng", "cơ sở y tế"],
                "patterns": {
                    "hospital_beds_per_10k": r"(\d+[.,]?\d*)\s*giường\s*(?:bệnh)?/\s*(?:vạn|10\.?000)\s*dân",
                    "doctors_per_10k": r"(\d+[.,]?\d*)\s*bác sĩ/\s*(?:vạn|10\.?000)\s*dân",
                    "nurses_per_10k": r"(\d+[.,]?\d*)\s*(?:điều dưỡng|y tá)/\s*(?:vạn|10\.?000)\s*dân",
                    "infant_mortality_rate": r"(?:tỷ lệ|tỉ lệ)\s*tử vong\s*(?:trẻ|sơ sinh)[:\s]+(\d+[.,]?\d*)",
                }
            },
            "preventive_health": {
                "name": "Y tế dự phòng",
                "keywords": ["tiêm chủng", "vaccine", "vắc xin", "phòng dịch", "y tế dự phòng",
                            "sàng lọc", "khám sức khỏe định kỳ"],
                "patterns": {
                    "vaccination_coverage": r"(?:tỷ lệ|tỉ lệ)\s*tiêm\s*(?:chủng|vaccine)[:\s]+(\d+[.,]?\d*)\s*%",
                    "health_screening_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:sàng lọc|khám)[:\s]+(\d+[.,]?\d*)\s*%",
                    "clean_water_access_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:sử dụng|tiếp cận)\s*nước sạch[:\s]+(\d+[.,]?\d*)\s*%",
                    "sanitation_access_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:có)?\s*(?:nhà|công trình)\s*vệ sinh[:\s]+(\d+[.,]?\d*)\s*%",
                }
            }
        }
    },
    
    # LĨNH VỰC 8: Giáo dục & Đào tạo
    "giao_duc": {
        "name": "Giáo dục & Đào tạo",
        "indicators": {
            "eqi": {
                "name": "Chỉ số chất lượng giáo dục (EQI)",
                "keywords": ["chất lượng giáo dục", "tỷ lệ biết chữ", "nhập học", "hoàn thành",
                            "giáo viên", "học sinh", "trường học"],
                "patterns": {
                    "literacy_rate": r"(?:tỷ lệ|tỉ lệ)\s*biết chữ[:\s]+(\d+[.,]?\d*)\s*%",
                    "school_enrollment_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:đi học|nhập học|ra lớp)[:\s]+(\d+[.,]?\d*)\s*%",
                    "primary_completion_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:hoàn thành|tốt nghiệp)\s*tiểu học[:\s]+(\d+[.,]?\d*)\s*%",
                    "teacher_qualification_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:giáo viên|GV)\s*đạt chuẩn[:\s]+(\d+[.,]?\d*)\s*%",
                    "student_teacher_ratio": r"(\d+[.,]?\d*)\s*học sinh/\s*(?:giáo viên|GV)",
                }
            },
            "highschool_graduation": {
                "name": "Tỷ lệ tốt nghiệp THPT",
                "keywords": ["tốt nghiệp THPT", "thi tốt nghiệp", "kỳ thi quốc gia", "điểm thi",
                            "thí sinh", "đỗ tốt nghiệp"],
                "patterns": {
                    "graduation_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:đỗ|tốt nghiệp)[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_candidates": r"(\d+(?:[.,]\d+)?)\s*thí sinh",
                    "passed_candidates": r"(\d+(?:[.,]\d+)?)\s*(?:thí sinh|em)\s*(?:đỗ|đạt)",
                    "average_score": r"điểm\s*(?:trung bình|TB)[:\s]+(\d+[.,]?\d*)",
                }
            },
            "tvet_employment": {
                "name": "Việc làm sau đào tạo nghề (TVET)",
                "keywords": ["đào tạo nghề", "giáo dục nghề nghiệp", "GDNN", "việc làm sau tốt nghiệp",
                            "học nghề", "trường nghề", "cao đẳng nghề"],
                "patterns": {
                    "employment_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:có việc làm|việc làm)[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_graduates": r"(\d+(?:[.,]\d+)?)\s*(?:học viên|sinh viên)\s*tốt nghiệp",
                    "tvet_enrollment": r"tuyển sinh[:\s]+(\d+(?:[.,]\d+)?)\s*(?:học viên|người|chỉ tiêu)",
                    "tvet_facilities": r"(\d+)\s*(?:cơ sở|trường)\s*(?:GDNN|đào tạo nghề)",
                }
            }
        }
    },
    
    # LĨNH VỰC 9: Hạ tầng & Giao thông
    "ha_tang_giao_thong": {
        "name": "Hạ tầng & Giao thông",
        "indicators": {
            "transport_infrastructure": {
                "name": "Chất lượng hạ tầng giao thông",
                "keywords": ["hạ tầng giao thông", "đường bộ", "cầu", "đường cao tốc",
                            "giao thông công cộng", "xe buýt"],
                "patterns": {
                    "road_length_km": r"(?:tổng|chiều dài)[:\s]+(\d+(?:[.,]\d+)?)\s*km\s*đường",
                    "paved_road_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:đường|mặt đường)\s*(?:nhựa|bê tông)[:\s]+(\d+[.,]?\d*)\s*%",
                    "bridge_count": r"(\d+)\s*cầu",
                }
            },
            "traffic_congestion": {
                "name": "Vận hành & ùn tắc giao thông",
                "keywords": ["ùn tắc", "kẹt xe", "lưu lượng", "tốc độ giao thông",
                            "điểm đen giao thông"],
                "patterns": {
                    "congestion_points": r"(\d+)\s*(?:điểm|nút)\s*(?:ùn tắc|đen)",
                    "average_speed_kmh": r"tốc độ\s*(?:trung bình|TB)[:\s]+(\d+[.,]?\d*)\s*km/h",
                    "public_transport_usage_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:sử dụng|đi)\s*(?:GTCC|xe buýt)[:\s]+(\d+[.,]?\d*)\s*%",
                }
            },
            "planning_progress": {
                "name": "Tiến độ dự án & quy hoạch",
                "keywords": ["dự án", "tiến độ", "quy hoạch", "giải ngân", "đầu tư công",
                            "giải phóng mặt bằng", "GPMB"],
                "patterns": {
                    "total_projects": r"(?:tổng số|có)\s*(\d+)\s*dự án",
                    "on_schedule_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:đúng tiến độ|hoàn thành)[:\s]+(\d+[.,]?\d*)\s*%",
                    "budget_execution_rate": r"(?:tỷ lệ|tỉ lệ)\s*giải ngân[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_investment_billion": r"(?:tổng|vốn)\s*đầu tư[:\s]+(\d+(?:[.,]\d+)?)\s*tỷ",
                    "land_clearance_completion_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:GPMB|giải phóng)[:\s]+(\d+[.,]?\d*)\s*%",
                }
            }
        }
    }
}


# =============================================================================
# LLM CLASSIFIER - Chỉ dùng để classify, KHÔNG extract số
# =============================================================================

class LLMClassifier:
    """Use LLM to classify if article is relevant to a field/indicator"""
    
    def __init__(self):
        self.client = None
        self.model = None
        if LLM_AVAILABLE and OPENAI_API_KEY:
            if OPENAI_API_KEY.startswith("sk-or-v1-"):
                self.client = OpenAI(
                    api_key=OPENAI_API_KEY,
                    base_url="https://openrouter.ai/api/v1"
                )
                self.model = "openai/gpt-4o-mini"
            else:
                self.client = OpenAI(api_key=OPENAI_API_KEY)
                self.model = "gpt-4o-mini"
    
    def classify_article(
        self, 
        title: str, 
        content: str, 
        field_key: str
    ) -> Dict[str, Any]:
        """
        Classify if article is relevant to a field and which indicators
        
        Returns:
            {
                "is_relevant": bool,
                "relevant_indicators": ["indicator1", "indicator2"],
                "confidence": float,
                "province": str or None,
                "year": int or None,
                "quarter": int or None,
                "month": int or None
            }
        """
        if not self.client:
            # Fallback to keyword matching
            return self._keyword_classify(title, content, field_key)
        
        field_def = FIELD_DEFINITIONS.get(field_key)
        if not field_def:
            return {"is_relevant": False, "relevant_indicators": [], "confidence": 0}
        
        # Build indicator list for prompt
        indicator_list = "\n".join([
            f"- {ind_key}: {ind_def['name']}"
            for ind_key, ind_def in field_def['indicators'].items()
        ])
        
        prompt = f"""Phân tích bài viết sau và trả lời:

TIÊU ĐỀ: {title}

NỘI DUNG (trích): {content[:2000]}

LĨNH VỰC: {field_def['name']}
CÁC CHỈ SỐ TRONG LĨNH VỰC:
{indicator_list}

Trả lời dạng JSON (chỉ JSON, không giải thích):
{{
    "is_relevant": true/false,  // Bài viết có liên quan đến lĩnh vực này không?
    "relevant_indicators": ["indicator_key1", "indicator_key2"],  // Các chỉ số liên quan (dùng key)
    "confidence": 0.0-1.0,  // Độ tin cậy
    "province": "tên tỉnh" hoặc null,  // Địa phương được đề cập
    "year": năm hoặc null,  // Năm của dữ liệu
    "quarter": 1-4 hoặc null,  // Quý nếu có
    "month": 1-12 hoặc null  // Tháng nếu có
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia phân tích dữ liệu. Chỉ trả về JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content_resp = response.choices[0].message.content.strip()
            
            # Extract JSON
            if "```json" in content_resp:
                content_resp = content_resp.split("```json")[1].split("```")[0].strip()
            elif "```" in content_resp:
                content_resp = content_resp.split("```")[1].split("```")[0].strip()
            
            return json.loads(content_resp)
            
        except Exception as e:
            logger.error(f"LLM classify error: {e}")
            return self._keyword_classify(title, content, field_key)
    
    def _keyword_classify(
        self, 
        title: str, 
        content: str, 
        field_key: str
    ) -> Dict[str, Any]:
        """Fallback: keyword-based classification"""
        field_def = FIELD_DEFINITIONS.get(field_key)
        if not field_def:
            return {"is_relevant": False, "relevant_indicators": [], "confidence": 0}
        
        text = f"{title} {content}".lower()
        relevant_indicators = []
        
        for ind_key, ind_def in field_def['indicators'].items():
            keyword_count = sum(1 for kw in ind_def['keywords'] if kw.lower() in text)
            if keyword_count >= 2:  # At least 2 keywords match
                relevant_indicators.append(ind_key)
        
        # Extract period info
        year = self._extract_year(text)
        quarter = self._extract_quarter(text)
        month = self._extract_month(text)
        province = self._extract_province(text)
        
        return {
            "is_relevant": len(relevant_indicators) > 0,
            "relevant_indicators": relevant_indicators,
            "confidence": min(len(relevant_indicators) * 0.3, 0.9),
            "province": province,
            "year": year,
            "quarter": quarter,
            "month": month
        }
    
    def _extract_year(self, text: str) -> Optional[int]:
        match = re.search(r'năm\s*(20\d{2})', text)
        if match:
            return int(match.group(1))
        match = re.search(r'(20\d{2})', text)
        if match:
            return int(match.group(1))
        return datetime.now().year
    
    def _extract_quarter(self, text: str) -> Optional[int]:
        match = re.search(r'quý\s*([IVX]+|[1-4])', text, re.IGNORECASE)
        if match:
            q = match.group(1).upper()
            quarter_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, '1': 1, '2': 2, '3': 3, '4': 4}
            return quarter_map.get(q)
        return None
    
    def _extract_month(self, text: str) -> Optional[int]:
        match = re.search(r'tháng\s*(\d{1,2})', text)
        if match:
            m = int(match.group(1))
            if 1 <= m <= 12:
                return m
        return None
    
    def _extract_province(self, text: str) -> Optional[str]:
        provinces = [
            "Hưng Yên", "Hà Nội", "TP.HCM", "Hồ Chí Minh", "Đà Nẵng", "Hải Phòng",
            "Cần Thơ", "Bình Dương", "Đồng Nai", "Bắc Ninh", "Hải Dương",
            "Thái Bình", "Nam Định", "Ninh Bình", "Hà Nam", "Vĩnh Phúc"
        ]
        text_lower = text.lower()
        for p in provinces:
            if p.lower() in text_lower:
                return p
        return None


# =============================================================================
# VALUE EXTRACTOR - Extract numbers using REGEX only
# =============================================================================

class ValueExtractor:
    """Extract numeric values from text using REGEX - NO LLM"""
    
    @staticmethod
    def extract_values(
        text: str, 
        patterns: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Extract all values matching the patterns
        
        Args:
            text: Text to extract from
            patterns: Dict of field_name -> regex_pattern
        
        Returns:
            Dict of field_name -> extracted_value (or None)
        """
        results = {}
        text = text.replace('\xa0', ' ')  # normalize nbsp
        
        for field_name, pattern in patterns.items():
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value_str = match.group(1).replace(',', '.').replace(' ', '')
                    try:
                        value = float(value_str)
                        results[field_name] = value
                    except ValueError:
                        results[field_name] = None
                else:
                    results[field_name] = None
            except Exception as e:
                logger.debug(f"Regex error for {field_name}: {e}")
                results[field_name] = None
        
        return results


# =============================================================================
# LLM EXTRACTOR - Extract with context understanding (EXPENSIVE but SMART)
# =============================================================================

class SmartExtractor:
    """
    Smart Extractor - Kết hợp LLM + Regex
    
    Strategy:
    1. Thử LLM trước (nếu có API key) - context-aware, thông minh
    2. Fallback/Merge với Regex - đảm bảo không bỏ sót
    3. Priority: LLM results > Regex results
    """
    
    def __init__(self):
        self.llm_available = False
        self.client = None
        self.model = None
        
        if LLM_AVAILABLE and OPENAI_API_KEY:
            try:
                if OPENAI_API_KEY.startswith("sk-or-v1-"):
                    self.client = OpenAI(
                        api_key=OPENAI_API_KEY,
                        base_url="https://openrouter.ai/api/v1"
                    )
                    self.model = "openai/gpt-4o-mini"
                else:
                    self.client = OpenAI(api_key=OPENAI_API_KEY)
                    self.model = "gpt-4o-mini"
                self.llm_available = True
                logger.info("SmartExtractor: LLM mode enabled (context-aware)")
            except Exception as e:
                logger.warning(f"SmartExtractor: LLM init failed, using regex only: {e}")
        else:
            logger.info("SmartExtractor: Regex mode only (no LLM API key)")
    
    def extract_values(
        self,
        text: str,
        indicator_key: str,
        indicator_def: Dict,
        patterns: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Extract values using LLM (smart) + Regex (fallback)
        
        Strategy:
        1. Try LLM first if available - hiểu context phức tạp
        2. Always try Regex as backup
        3. Merge results: LLM values override Regex if not null
        
        Returns:
            Dict of field_name -> extracted_value (or None)
        """
        results = {}
        
        # Step 1: Try LLM extraction (context-aware)
        llm_results = {}
        if self.llm_available and self.client:
            try:
                llm_results = self._extract_with_llm(text, indicator_key, indicator_def, patterns)
                logger.debug(f"LLM extracted {sum(1 for v in llm_results.values() if v is not None)}/{len(patterns)} fields")
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}, falling back to regex")
        
        # Step 2: Always try Regex extraction (fast, pattern-based)
        regex_results = ValueExtractor.extract_values(text, patterns)
        logger.debug(f"Regex extracted {sum(1 for v in regex_results.values() if v is not None)}/{len(patterns)} fields")
        
        # Step 3: Merge results (LLM priority > Regex)
        for field_name in patterns.keys():
            llm_value = llm_results.get(field_name)
            regex_value = regex_results.get(field_name)
            
            # Priority: LLM > Regex
            if llm_value is not None:
                results[field_name] = llm_value
            elif regex_value is not None:
                results[field_name] = regex_value
            else:
                results[field_name] = None
        
        return results
    
    def _extract_with_llm(
        self,
        text: str,
        indicator_key: str,
        indicator_def: Dict,
        patterns: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Extract values using LLM with structured output
        """
        if not self.client:
            return {}
        
        # Build field descriptions
        field_descriptions = []
        for field_name in patterns.keys():
            field_label = field_name.replace('_', ' ').title()
            field_descriptions.append(f"- {field_name}: {field_label}")
        
        fields_text = "\n".join(field_descriptions)
        
        prompt = f"""Trích xuất SỐ LIỆU CHÍNH XÁC từ văn bản sau.

VĂN BẢN:
{text[:3000]}

CHỈ SỐ CẦN TRÍCH XUẤT: {indicator_def['name']}

CÁC TRƯỜNG DỮ LIỆU:
{fields_text}

QUI TẮC:
1. CHỈ trích xuất số có trong văn bản gốc
2. KHÔNG bịa, KHÔNG suy đoán
3. Nếu không tìm thấy → null
4. Chuyển đổi đơn vị về số thực:
   - "123,5 tỷ" → 123500000000
   - "45.6%" → 45.6
   - "2.500 người" → 2500
5. Hiểu context: "giảm 30%" vs "đạt 70%" là khác nhau
6. Phân biệt: số kế hoạch vs số thực hiện (ưu tiên số thực hiện)
7. Nếu có nhiều số cùng loại, lấy số CHÍNH THỨC/MỚI NHẤT

Trả về JSON (chỉ JSON, không giải thích):
{{
  "field_name_1": số hoặc null,
  "field_name_2": số hoặc null,
  ...
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia trích xuất dữ liệu số. Chỉ trả về JSON với số chính xác từ văn bản."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        extracted = json.loads(content)
        
        # Validate and convert to float
        results = {}
        for field_name in patterns.keys():
            value = extracted.get(field_name)
            if value is not None and value != "null":
                try:
                    results[field_name] = float(value)
                except (ValueError, TypeError):
                    results[field_name] = None
            else:
                results[field_name] = None
        
        return results


# =============================================================================
# SOCIAL INDICATOR SERVICE - Main service
# =============================================================================

# =============================================================================
# SOCIAL INDICATOR SERVICE - Main service
# =============================================================================

class SocialIndicatorService:
    """Main service for extracting social indicators from articles"""
    
    def __init__(self, db: Session):
        self.db = db
        self.classifier = LLMClassifier()
        self.extractor = SmartExtractor()  # Tự động dùng LLM + Regex
        """Convert Vietnamese number format to float"""
        if not value_str:
            return None
        
        # Remove spaces and replace comma with dot
        value_str = value_str.strip().replace(' ', '').replace(',', '.')
        
        # Handle "nghìn", "triệu", "tỷ"
        multiplier = 1
        if 'tỷ' in value_str.lower():
            multiplier = 1_000_000_000
            value_str = re.sub(r'tỷ', '', value_str, flags=re.IGNORECASE)
        elif 'triệu' in value_str.lower():
            multiplier = 1_000_000
            value_str = re.sub(r'triệu', '', value_str, flags=re.IGNORECASE)
        elif 'nghìn' in value_str.lower() or 'ngàn' in value_str.lower():
            multiplier = 1_000
            value_str = re.sub(r'nghìn|ngàn', '', value_str, flags=re.IGNORECASE)
        


# =============================================================================
# SOCIAL INDICATOR SERVICE - Main service
# =============================================================================

class SocialIndicatorService:
    """Main service for extracting social indicators from articles"""
    
    def __init__(self, db: Session):
        self.db = db
        self.classifier = LLMClassifier()
        self.extractor = SmartExtractor()  # Tự động dùng LLM + Regex
    
    def get_model_class(self, indicator_key: str):
        """Get SQLAlchemy model class for an indicator"""
        from app.models.model_indicator_details import INDICATOR_DETAIL_MODELS
        return INDICATOR_DETAIL_MODELS.get(indicator_key)
    
    def process_field(
        self,
        field_key: str,
        limit: int = 100,
        year_filter: Optional[int] = None,
        province_filter: Optional[str] = None,
        use_category_filter: bool = True
    ) -> Dict[str, Any]:
        """
        Process articles for a specific field and fill indicator tables
        
        Args:
            field_key: Key of the field (e.g., 'xay_dung_dang')
            limit: Max number of articles to process
            year_filter: Filter articles by year
            province_filter: Filter by province
            use_category_filter: If True, filter by category column first (faster)
        
        Returns:
            Summary of processing results
        """
        field_def = FIELD_DEFINITIONS.get(field_key)
        if not field_def:
            return {"error": f"Unknown field: {field_key}"}
        
        from app.models.model_article import Article
        from sqlalchemy import or_, func
        
        # Get categories for this field
        categories = FIELD_TO_CATEGORIES.get(field_key, [])
        
        # Build query
        query = self.db.query(Article)
        
        # Strategy 1: Filter by category if available and enabled
        if use_category_filter and categories:
            # Check if any articles have category set
            sample_with_category = self.db.query(Article).filter(
                Article.category.isnot(None),
                Article.category != ''
            ).limit(1).first()
            
            if sample_with_category:
                # Use category filter - MUCH FASTER
                category_filters = [
                    func.lower(Article.category) == cat.lower() 
                    for cat in categories
                ]
                query = query.filter(or_(*category_filters))
                logger.info(f"Filtering by categories: {categories}")
            else:
                # Fallback to keyword search if no categories are set
                logger.info("No articles with category found, using keyword search")
                query = self._add_keyword_filters(query, field_def, Article)
        else:
            # Strategy 2: Keyword-based search (slower but works without categories)
            query = self._add_keyword_filters(query, field_def, Article)
        
        # Add additional filters
        if province_filter:
            query = query.filter(Article.province == province_filter)
        
        if year_filter:
            query = query.filter(
                func.extract('year', Article.published_date) == year_filter
            )
        
        # Execute query
        articles = query.order_by(Article.published_date.desc()).limit(limit).all()
        
        results = {
            "field": field_def['name'],
            "field_key": field_key,
            "categories_used": categories if use_category_filter else [],
            "articles_found": len(articles),
            "articles_processed": 0,
            "records_created": 0,
            "indicators_filled": {},
            "errors": []
        }
        
        for article in articles:
            try:
                article_result = self._process_article_for_field(
                    article, field_key, field_def
                )
                if article_result.get("records_created", 0) > 0:
                    results["articles_processed"] += 1
                    results["records_created"] += article_result["records_created"]
                    for ind_key, count in article_result.get("by_indicator", {}).items():
                        results["indicators_filled"][ind_key] = results["indicators_filled"].get(ind_key, 0) + count
            except Exception as e:
                logger.error(f"Error processing article {article.id}: {e}")
                results["errors"].append(f"Article {article.id}: {str(e)}")
        
        return results
    
    def _add_keyword_filters(self, query, field_def: Dict, Article):
        """Add keyword-based filters to query (fallback when no category)"""
        from sqlalchemy import or_
        
        all_keywords = []
        for ind_def in field_def['indicators'].values():
            all_keywords.extend(ind_def['keywords'])
        
        # Limit keywords to avoid too complex query
        unique_keywords = list(set(all_keywords))[:15]
        
        keyword_filters = [
            Article.content.ilike(f'%{kw}%') for kw in unique_keywords
        ] + [
            Article.title.ilike(f'%{kw}%') for kw in unique_keywords
        ]
        
        return query.filter(or_(*keyword_filters))
    
    def _process_article_for_field(
        self,
        article,
        field_key: str,
        field_def: Dict
    ) -> Dict[str, Any]:
        """Process a single article for a field"""
        result = {"records_created": 0, "by_indicator": {}}
        
        # Classify article
        classification = self.classifier.classify_article(
            article.title or "",
            article.content or "",
            field_key
        )
        
        if not classification.get("is_relevant"):
            return result
        
        # Extract period info
        year = classification.get("year") or datetime.now().year
        quarter = classification.get("quarter")
        month = classification.get("month")
        province = classification.get("province") or article.province or "Hưng Yên"
        
        # Process each relevant indicator
        for ind_key in classification.get("relevant_indicators", []):
            ind_def = field_def['indicators'].get(ind_key)
            if not ind_def:
                continue
            
            # Extract values using SmartExtractor (LLM + Regex tự động)
            extracted = self.extractor.extract_values(
                article.content or "",
                ind_key,
                ind_def,
                ind_def.get('patterns', {})
            )
            
            # Check if we got any values
            non_null_values = {k: v for k, v in extracted.items() if v is not None}
            if not non_null_values:
                continue
            
            # Get model class
            model_class = self.get_model_class(ind_key)
            if not model_class:
                logger.warning(f"No model class for indicator: {ind_key}")
                continue
            
            # Check if record already exists
            existing = self.db.query(model_class).filter(
                model_class.province == province,
                model_class.year == year,
                model_class.quarter == quarter if quarter else model_class.quarter.is_(None),
            ).first()
            
            if existing:
                # Update existing record with new values (only if null)
                updated = False
                for field_name, value in non_null_values.items():
                    if hasattr(existing, field_name) and getattr(existing, field_name) is None:
                        setattr(existing, field_name, value)
                        updated = True
                if updated:
                    existing.data_source = article.url
                    existing.updated_at = datetime.now()
                    self.db.commit()
            else:
                # Create new record
                record_data = {
                    "province": province,
                    "year": year,
                    "quarter": quarter,
                    "month": month,
                    "data_source": article.url,
                    "data_status": "official",
                    **non_null_values
                }
                
                new_record = model_class(**record_data)
                self.db.add(new_record)
                self.db.commit()
                
                result["records_created"] += 1
                result["by_indicator"][ind_key] = result["by_indicator"].get(ind_key, 0) + 1
        
        return result
    
    def get_field_summary(self, field_key: str) -> Dict[str, Any]:
        """Get summary of data in all indicators for a field"""
        field_def = FIELD_DEFINITIONS.get(field_key)
        if not field_def:
            return {"error": f"Unknown field: {field_key}"}
        
        summary = {
            "field": field_def['name'],
            "field_key": field_key,
            "indicators": {}
        }
        
        for ind_key, ind_def in field_def['indicators'].items():
            model_class = self.get_model_class(ind_key)
            if not model_class:
                continue
            
            count = self.db.query(model_class).count()
            latest = self.db.query(model_class).order_by(
                model_class.year.desc(),
                model_class.quarter.desc().nullsfirst()
            ).first()
            
            summary["indicators"][ind_key] = {
                "name": ind_def['name'],
                "total_records": count,
                "latest_year": latest.year if latest else None,
                "latest_quarter": latest.quarter if latest else None
            }
        
        return summary


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    'FIELD_DEFINITIONS',
    'CATEGORY_TO_FIELD',
    'FIELD_TO_CATEGORIES',
    'LLMClassifier',
    'ValueExtractor',
    'SocialIndicatorService'
]
