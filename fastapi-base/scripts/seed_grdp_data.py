"""
Script để seed dữ liệu GRDP mẫu vào bảng grdp_detail

Chạy:
    docker compose exec app python scripts/seed_grdp_data.py
    
Hoặc trong container:
    python scripts/seed_grdp_data.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import get_engine
from app.models.model_grdp_detail import GRDPDetail
from datetime import datetime


def seed_grdp_data():
    """Seed dữ liệu GRDP mẫu cho một số tỉnh"""
    
    engine = get_engine()
    session = Session(engine)
    
    try:
        # Dữ liệu mẫu cho Hưng Yên
        grdp_samples = [
            # Hưng Yên - 2024
            {
                "province": "Hưng Yên",
                "year": 2024,
                "quarter": None,  # Cả năm
                "grdp_current_price": 58123.5,
                "grdp_per_capita": 85.2,
                "growth_rate": 8.2,
                "agriculture_sector_pct": 12.5,
                "industry_sector_pct": 45.3,
                "service_sector_pct": 42.2,
                "rank_national": 28,
                "data_status": "official",
                "data_source": "Cục Thống kê Hưng Yên"
            },
            # Hưng Yên - Q1/2025
            {
                "province": "Hưng Yên",
                "year": 2025,
                "quarter": 1,
                "grdp_current_price": 15234.8,
                "grdp_per_capita": 88.5,
                "growth_rate": 8.5,
                "agriculture_sector_pct": 11.8,
                "industry_sector_pct": 46.2,
                "service_sector_pct": 42.0,
                "forecast_year_end": 62500.0,
                "data_status": "official",
                "data_source": "Cục Thống kê Hưng Yên"
            },
            
            # Hà Nội - 2024
            {
                "province": "Hà Nội",
                "year": 2024,
                "quarter": None,
                "grdp_current_price": 985432.7,
                "grdp_per_capita": 156.8,
                "growth_rate": 7.8,
                "agriculture_sector_pct": 1.2,
                "industry_sector_pct": 28.5,
                "service_sector_pct": 70.3,
                "rank_national": 1,
                "data_status": "official",
                "data_source": "Cục Thống kê Hà Nội"
            },
            
            # TP.HCM - 2024
            {
                "province": "TP. Hồ Chí Minh",
                "year": 2024,
                "quarter": None,
                "grdp_current_price": 1542876.3,
                "grdp_per_capita": 198.5,
                "growth_rate": 7.5,
                "agriculture_sector_pct": 0.3,
                "industry_sector_pct": 24.8,
                "service_sector_pct": 74.9,
                "rank_national": 1,
                "data_status": "official",
                "data_source": "Cục Thống kê TP.HCM"
            },
            
            # Bắc Ninh - 2024
            {
                "province": "Bắc Ninh",
                "year": 2024,
                "quarter": None,
                "grdp_current_price": 142567.2,
                "grdp_per_capita": 189.3,
                "growth_rate": 12.5,
                "agriculture_sector_pct": 3.2,
                "industry_sector_pct": 71.5,
                "service_sector_pct": 25.3,
                "rank_national": 8,
                "data_status": "official",
                "data_source": "Cục Thống kê Bắc Ninh"
            },
            
            # Hải Phòng - 2024
            {
                "province": "Hải Phòng",
                "year": 2024,
                "quarter": None,
                "grdp_current_price": 312456.8,
                "grdp_per_capita": 142.7,
                "growth_rate": 9.2,
                "agriculture_sector_pct": 4.5,
                "industry_sector_pct": 52.3,
                "service_sector_pct": 43.2,
                "rank_national": 5,
                "data_status": "official",
                "data_source": "Cục Thống kê Hải Phòng"
            },
            
            # Dữ liệu ước tính cho 2025
            {
                "province": "Hưng Yên",
                "year": 2025,
                "quarter": None,
                "grdp_current_price": 63500.0,
                "grdp_per_capita": 92.0,
                "growth_rate": 9.2,
                "agriculture_sector_pct": 11.5,
                "industry_sector_pct": 47.0,
                "service_sector_pct": 41.5,
                "rank_national": 27,
                "data_status": "forecast",
                "data_source": "Dự báo UBND tỉnh Hưng Yên"
            },
        ]
        
        # Insert data
        count_created = 0
        count_existed = 0
        
        for data in grdp_samples:
            # Kiểm tra đã tồn tại chưa
            existing = session.query(GRDPDetail).filter(
                GRDPDetail.province == data['province'],
                GRDPDetail.year == data['year'],
                GRDPDetail.quarter == data['quarter'],
                GRDPDetail.data_status == data['data_status']
            ).first()
            
            if existing:
                print(f"⏭️  Đã tồn tại: {data['province']} - {data['quarter'] or 'Cả năm'}/{data['year']}")
                count_existed += 1
            else:
                grdp = GRDPDetail(**data)
                session.add(grdp)
                print(f"✅ Tạo mới: {data['province']} - {data['quarter'] or 'Cả năm'}/{data['year']} - GRDP: {data['grdp_current_price']} tỷ VNĐ")
                count_created += 1
        
        session.commit()
        
        print("\n" + "="*60)
        print(f"🎉 Hoàn thành!")
        print(f"   - Tạo mới: {count_created} records")
        print(f"   - Đã có sẵn: {count_existed} records")
        print(f"   - Tổng cộng: {count_created + count_existed} records")
        print("="*60)
        
        # Thống kê
        total_records = session.query(GRDPDetail).count()
        provinces = session.query(GRDPDetail.province).distinct().count()
        
        print(f"\n📊 Thống kê bảng grdp_detail:")
        print(f"   - Tổng số records: {total_records}")
        print(f"   - Số tỉnh/thành: {provinces}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Lỗi: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("🚀 Bắt đầu seed dữ liệu GRDP...")
    print()
    seed_grdp_data()
