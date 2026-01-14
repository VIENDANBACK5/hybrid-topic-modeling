"""
Script để seed dữ liệu lĩnh vực và chạy phân loại bài viết
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from app.core.database import SessionLocal
from app.models.model_field_classification import Field, ArticleFieldClassification, FieldStatistics
from app.services.classification.field_classifier import FieldClassificationService


def seed_fields():
    """Seed 10 lĩnh vực từ bảng phân loại"""
    db = SessionLocal()
    
    try:
        print("🌱 Bắt đầu seed dữ liệu lĩnh vực...")
        
        fields_data = [
            {
                "name": "Kinh tế & Việc làm",
                "description": "Thủ tục đầu tư, doanh nghiệp, khu công nghiệp; Việc làm, thất nghiệp, thu nhập; Nông nghiệp - nông thôn (sản xuất, tiêu thu nông sản, thiên tai); Thương mại, giá cả, thị trường; Du lịch, dịch vụ; Ngân sách, tài chính gia phương",
                "keywords": ["kinh tế", "doanh nghiệp", "đầu tư", "khu công nghiệp", "việc làm", "thất nghiệp", "thu nhập", "nông nghiệp", "nông thôn", "nông sản", "thiên tai", "thương mại", "giá cả", "thị trường", "du lịch", "dịch vụ", "ngân sách", "tài chính"]
            },
            {
                "name": "Y tế & Chăm sóc sức khỏe",
                "description": "Chất lượng khám chữa bệnh; Bệnh viện, trạm y tế; Giá dịch vụ y tế, thẻ bảo hiểm y tế; Dịch bệnh, tiêm chủng, an toàn y tế",
                "keywords": ["bệnh viện", "bác sĩ", "bảo hiểm y tế", "viện phí", "dịch bệnh", "khám chữa bệnh", "trạm y tế", "giá dịch vụ y tế", "tiêm chủng", "an toàn y tế"]
            },
            {
                "name": "Giáo dục & Đào tạo",
                "description": "Chất lượng trường lớp; Học phí, thu - chi giáo dục; Tuyển sinh, thi tú; Cơ hội tiếp cận giáo dục",
                "keywords": ["học phí", "trường học", "giáo viên", "thi cử", "tuyển sinh", "chất lượng trường lớp", "thu chi giáo dục", "cơ hội tiếp cận giáo dục", "học sinh", "sinh viên"]
            },
            {
                "name": "Hạ tầng & Giao thông",
                "description": "Đường xá, cầu cống, kết xe; Điện, nước, vệ sinh công cộng; Dự án hạ tầng, chậm tiến độ",
                "keywords": ["đường xá", "kết xe", "mất điện", "nước sạch", "dự án", "cầu cống", "điện", "nước", "vệ sinh công cộng", "hạ tầng", "chậm tiến độ", "giao thông"]
            },
            {
                "name": "Môi trường & Biến đổi khí hậu",
                "description": "Rác thải, ô nhiễm (không khí, nước); Xử lý chất thải; Ngập lụt, hạn hán, thiên tai; Biến đổi khí hậu",
                "keywords": ["ô nhiễm", "rác thải", "ngập lụt", "môi trường", "xử lý chất thải", "hạn hán", "thiên tai", "biến đổi khí hậu", "không khí", "nước thải"]
            },
            {
                "name": "An sinh xã hội & Chính sách",
                "description": "Giảm nghèo, hỗ trợ dân; Người có công, người cao tuổi; Bảo hiểm xã hội; Chính sách hỗ trợ dân sinh",
                "keywords": ["trợ cấp", "hỗ trợ", "người nghèo", "bảo hiểm xã hội", "giảm nghèo", "người có công", "người cao tuổi", "chính sách", "dân sinh"]
            },
            {
                "name": "An ninh, Trật tự & Quốc phòng",
                "description": "An ninh trật tự; Tội phạm, tai nạn; Khiếu kiện động người; Quốc phòng",
                "keywords": ["mất trật tự", "trộm cắp", "tai nạn", "khiếu kiện", "an ninh", "trật tự", "tội phạm", "quốc phòng", "an toàn"]
            },
            {
                "name": "Hành chính công & Quản lý Nhà nước",
                "description": "Thủ tục hành chính; Dịch vụ công; Cải cách hành chính (CCHC); Minh bạch, thái độ cán bộ",
                "keywords": ["thủ tục", "hành chính", "giấy tờ", "chậm trễ", "thái độ", "nhũng nhiễu", "dịch vụ công", "cải cách", "minh bạch", "cán bộ"]
            },
            {
                "name": "Xây dựng Đảng & Hệ thống chính trị",
                "description": "Công tác cán bộ; Phòng chống tham nhũng; Hoạt động của Mặt trận, Đoàn thể",
                "keywords": ["cán bộ", "tham nhũng", "kỷ luật", "tổ chức đảng", "phòng chống", "mặt trận", "đoàn thể", "đảng", "chính trị"]
            },
            {
                "name": "Văn hóa, Thể thao & Đời sống tinh thần",
                "description": "Hoạt động văn hóa, lễ hội; Thể thao, vui chơi giải trí; Bảo tồn di sản",
                "keywords": ["lễ hội", "văn hóa", "thể thao", "vui chơi", "hoạt động văn hóa", "giải trí", "bảo tồn", "di sản", "âm nhạc", "nghệ thuật"]
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for i, field_data in enumerate(fields_data):
            existing = db.query(Field).filter(Field.name == field_data["name"]).first()
            
            if existing:
                # Update nếu đã tồn tại
                existing.description = field_data["description"]
                existing.keywords = field_data["keywords"]
                existing.order_index = i + 1
                existing.updated_at = time.time()
                updated_count += 1
                print(f"   ✏️  Cập nhật: {field_data['name']}")
            else:
                # Tạo mới
                field = Field(
                    name=field_data["name"],
                    description=field_data["description"],
                    keywords=field_data["keywords"],
                    order_index=i + 1,
                    created_at=time.time(),
                    updated_at=time.time()
                )
                db.add(field)
                created_count += 1
                print(f"   ✅ Tạo mới: {field_data['name']}")
        
        db.commit()
        
        total = db.query(Field).count()
        print(f"\n✨ Hoàn thành!")
        print(f"   - Tạo mới: {created_count} lĩnh vực")
        print(f"   - Cập nhật: {updated_count} lĩnh vực")
        print(f"   - Tổng số: {total} lĩnh vực\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi seed dữ liệu: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def classify_all_articles(limit: int = None):
    """Phân loại tất cả bài viết"""
    db = SessionLocal()
    
    try:
        print("🔍 Bắt đầu phân loại bài viết...")
        
        service = FieldClassificationService(db)
        
        # Đếm số bài viết
        from app.models.model_article import Article
        total_articles = db.query(Article).count()
        
        if total_articles == 0:
            print("⚠️  Không có bài viết nào trong database!")
            return False
        
        print(f"   📊 Tổng số bài viết: {total_articles}")
        
        # Phân loại
        result = service.classify_articles_batch(limit=limit, force=False)
        
        print(f"\n📈 Kết quả phân loại:")
        print(f"   - Đã xử lý: {result['total_processed']} bài")
        print(f"   - Phân loại thành công: {result['classified']} bài")
        print(f"   - Không phân loại được: {result['failed']} bài")
        print(f"   - Thời gian xử lý: {result['processing_time']:.2f}s")
        
        if result['field_distribution']:
            print(f"\n📊 Phân bố theo lĩnh vực:")
            for field_name, count in sorted(
                result['field_distribution'].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                print(f"   - {field_name}: {count} bài")
        
        # Cập nhật thống kê
        print(f"\n📊 Cập nhật thống kê...")
        service.update_field_statistics()
        print(f"   ✅ Đã cập nhật thống kê!")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi phân loại: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def show_statistics():
    """Hiển thị thống kê phân loại"""
    db = SessionLocal()
    
    try:
        print("\n📊 THỐNG KÊ PHÂN LOẠI BÀI VIẾT\n")
        print("=" * 80)
        
        # Lấy tổng quan
        from app.models.model_article import Article
        total_articles = db.query(Article).count()
        classified_count = db.query(ArticleFieldClassification).count()
        
        print(f"📰 Tổng số bài viết: {total_articles}")
        print(f"✅ Đã phân loại: {classified_count}")
        print(f"⏳ Chưa phân loại: {total_articles - classified_count}")
        
        if classified_count > 0:
            print(f"📈 Tỷ lệ phân loại: {classified_count * 100 / total_articles:.1f}%")
        
        print("\n" + "=" * 80)
        
        # Thống kê chi tiết theo lĩnh vực
        stats = db.query(FieldStatistics).join(Field).order_by(Field.order_index).all()
        
        if stats:
            print("\n🏷️  CHI TIẾT THEO LĨNH VỰC\n")
            
            for stat in stats:
                print(f"\n📌 {stat.field_name}")
                print(f"   Tổng số bài: {stat.total_articles}")
                print(f"   Hôm nay: {stat.articles_today} | Tuần này: {stat.articles_this_week} | Tháng này: {stat.articles_this_month}")
                
                if stat.total_engagement > 0:
                    print(f"   💬 Engagement: Likes {stat.avg_likes:.1f} | Shares {stat.avg_shares:.1f} | Comments {stat.avg_comments:.1f}")
                
                if stat.province_distribution:
                    top_provinces = sorted(
                        stat.province_distribution.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:3]
                    provinces_str = ", ".join([f"{p}: {c}" for p, c in top_provinces])
                    print(f"   📍 Top tỉnh: {provinces_str}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"❌ Lỗi khi hiển thị thống kê: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed và phân loại bài viết theo lĩnh vực")
    parser.add_argument("--seed", action="store_true", help="Seed dữ liệu lĩnh vực")
    parser.add_argument("--classify", action="store_true", help="Phân loại bài viết")
    parser.add_argument("--stats", action="store_true", help="Hiển thị thống kê")
    parser.add_argument("--limit", type=int, help="Giới hạn số bài viết phân loại")
    parser.add_argument("--all", action="store_true", help="Chạy tất cả (seed + classify + stats)")
    
    args = parser.parse_args()
    
    if args.all or (not args.seed and not args.classify and not args.stats):
        # Mặc định chạy tất cả
        print("🚀 Chạy toàn bộ quy trình...\n")
        success = seed_fields()
        if success:
            classify_all_articles(limit=args.limit)
            show_statistics()
    else:
        if args.seed:
            seed_fields()
        
        if args.classify:
            classify_all_articles(limit=args.limit)
        
        if args.stats:
            show_statistics()
