"""
Script để import dữ liệu chỉ số kinh tế từ file CSV hoặc từ GSO
Có thể import từ:
1. File CSV/Excel
2. GSO API (nếu có)
3. Nhập tay cho demo

Run: python scripts/import_economic_data.py [csv_file]
"""
import sys
import os
import csv
from datetime import datetime, date
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.model_economic_indicators import EconomicIndicator

print("Economic Indicators Import Tool")
print("=" * 60)

# Create database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def import_from_csv(csv_file: str):
    """Import dữ liệu từ file CSV"""
    print(f"\n📥 Importing from CSV: {csv_file}")
    
    if not os.path.exists(csv_file):
        print(f"File not found: {csv_file}")
        return
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            try:
                # Convert date strings to date objects
                period_start = datetime.strptime(row['period_start'], '%Y-%m-%d').date() if row.get('period_start') else None
                period_end = datetime.strptime(row['period_end'], '%Y-%m-%d').date() if row.get('period_end') else None
                
                # Convert numeric fields
                numeric_fields = [
                    'year', 'month', 'quarter',
                    'grdp', 'grdp_growth_rate', 'grdp_per_capita',
                    'iip', 'iip_growth_rate',
                    'agricultural_production_index', 'agricultural_growth_rate', 'agricultural_output',
                    'retail_services_total', 'retail_services_growth', 'retail_total', 'services_total',
                    'export_value', 'export_growth_rate', 'import_value', 'trade_balance',
                    'total_investment', 'fdi_registered', 'fdi_disbursed', 'domestic_investment', 'investment_growth_rate',
                    'state_budget_revenue', 'sbr_growth_rate', 'tax_revenue', 'non_tax_revenue',
                    'cpi', 'cpi_growth_rate', 'core_inflation',
                    'unemployment_rate', 'labor_force',
                    'is_verified', 'is_estimated'
                ]
                
                data = {
                    'period_type': row.get('period_type'),
                    'period_start': period_start,
                    'period_end': period_end,
                    'period_label': row.get('period_label'),
                    'province': row.get('province') or None,
                    'region': row.get('region') or None,
                    'data_source': row.get('data_source', 'CSV Import'),
                    'source_url': row.get('source_url') or None,
                    'notes': row.get('notes') or None,
                }
                
                # Add numeric fields
                for field in numeric_fields:
                    value = row.get(field)
                    if value and value.strip():
                        try:
                            if field in ['year', 'month', 'quarter', 'is_verified', 'is_estimated']:
                                data[field] = int(value)
                            else:
                                data[field] = float(value)
                        except ValueError:
                            data[field] = None
                    else:
                        data[field] = None
                
                indicator = EconomicIndicator(**data)
                db.add(indicator)
                count += 1
                
                if count % 10 == 0:
                    db.commit()
                    print(f"  Imported {count} records...")
                    
            except Exception as e:
                print(f"  Error importing row: {e}")
                print(f"     Row data: {row}")
                continue
        
        db.commit()
        print(f"\nSuccessfully imported {count} economic indicators!")


def create_sample_data():
    """Tạo dữ liệu mẫu cho demo - Dữ liệu kinh tế Việt Nam 2024-2025"""
    print("\nCreating sample economic data for Vietnam...")
    
    sample_data = [
        # Dữ liệu quý 4/2024 - Cả nước
        {
            'period_type': 'quarterly',
            'period_start': date(2024, 10, 1),
            'period_end': date(2024, 12, 31),
            'period_label': 'Quý 4/2024',
            'year': 2024,
            'quarter': 4,
            'province': None,
            'region': None,
            'grdp_growth_rate': 7.09,
            'iip_growth_rate': 8.6,
            'agricultural_growth_rate': 3.8,
            'retail_services_total': 1789.5,
            'retail_services_growth': 9.2,
            'export_value': 96100,
            'export_growth_rate': 14.8,
            'import_value': 88200,
            'total_investment': 512.3,
            'fdi_disbursed': 6250,
            'investment_growth_rate': 8.5,
            'state_budget_revenue': 485.2,
            'sbr_growth_rate': 15.3,
            'cpi_growth_rate': 3.63,
            'unemployment_rate': 2.31,
            'data_source': 'GSO - Tổng cục Thống kê',
            'is_verified': 1,
            'is_estimated': 0
        },
        # Dữ liệu quý 1/2025 - Cả nước (ước tính)
        {
            'period_type': 'quarterly',
            'period_start': date(2025, 1, 1),
            'period_end': date(2025, 3, 31),
            'period_label': 'Quý 1/2025',
            'year': 2025,
            'quarter': 1,
            'province': None,
            'region': None,
            'grdp_growth_rate': 6.5,
            'iip_growth_rate': 7.8,
            'agricultural_growth_rate': 3.2,
            'retail_services_total': 1650.0,
            'retail_services_growth': 8.5,
            'export_value': 88500,
            'export_growth_rate': 12.3,
            'import_value': 82000,
            'total_investment': 480.0,
            'fdi_disbursed': 5800,
            'investment_growth_rate': 7.2,
            'state_budget_revenue': 425.0,
            'sbr_growth_rate': 12.8,
            'cpi_growth_rate': 3.2,
            'unemployment_rate': 2.25,
            'data_source': 'GSO - Ước tính',
            'is_verified': 0,
            'is_estimated': 1
        },
        # Dữ liệu tháng 12/2024 - Hà Nội
        {
            'period_type': 'monthly',
            'period_start': date(2024, 12, 1),
            'period_end': date(2024, 12, 31),
            'period_label': 'Tháng 12/2024',
            'year': 2024,
            'month': 12,
            'province': 'Hà Nội',
            'region': 'Bắc',
            'grdp_growth_rate': 8.2,
            'iip_growth_rate': 9.5,
            'retail_services_total': 156.8,
            'retail_services_growth': 10.3,
            'export_value': 4200,
            'fdi_disbursed': 680,
            'state_budget_revenue': 42.5,
            'sbr_growth_rate': 16.2,
            'cpi_growth_rate': 3.8,
            'data_source': 'Cục Thống kê Hà Nội',
            'is_verified': 1
        },
        # Dữ liệu tháng 12/2024 - TP.HCM
        {
            'period_type': 'monthly',
            'period_start': date(2024, 12, 1),
            'period_end': date(2024, 12, 31),
            'period_label': 'Tháng 12/2024',
            'year': 2024,
            'month': 12,
            'province': 'TP. Hồ Chí Minh',
            'region': 'Nam',
            'grdp_growth_rate': 7.8,
            'iip_growth_rate': 8.9,
            'retail_services_total': 189.5,
            'retail_services_growth': 9.8,
            'export_value': 5800,
            'fdi_disbursed': 920,
            'state_budget_revenue': 58.3,
            'sbr_growth_rate': 14.5,
            'cpi_growth_rate': 3.5,
            'data_source': 'Cục Thống kê TP.HCM',
            'is_verified': 1
        },
        # Dữ liệu năm 2024 - Cả nước
        {
            'period_type': 'yearly',
            'period_start': date(2024, 1, 1),
            'period_end': date(2024, 12, 31),
            'period_label': 'Năm 2024',
            'year': 2024,
            'province': None,
            'region': None,
            'grdp': 9500000,
            'grdp_growth_rate': 7.09,
            'grdp_per_capita': 95.5,
            'iip_growth_rate': 8.6,
            'agricultural_growth_rate': 3.8,
            'retail_services_total': 6850.2,
            'retail_services_growth': 9.2,
            'export_value': 371500,
            'export_growth_rate': 14.8,
            'import_value': 342000,
            'trade_balance': 29500,
            'total_investment': 1980.5,
            'fdi_registered': 38548,
            'fdi_disbursed': 24200,
            'domestic_investment': 1560.0,
            'investment_growth_rate': 8.5,
            'state_budget_revenue': 1865.5,
            'sbr_growth_rate': 15.3,
            'tax_revenue': 1620.0,
            'non_tax_revenue': 245.5,
            'cpi': 103.63,
            'cpi_growth_rate': 3.63,
            'core_inflation': 2.95,
            'unemployment_rate': 2.31,
            'labor_force': 52.8,
            'data_source': 'GSO - Tổng cục Thống kê',
            'source_url': 'https://www.gso.gov.vn',
            'notes': 'Dữ liệu chính thức năm 2024',
            'is_verified': 1,
            'is_estimated': 0
        }
    ]
    
    count = 0
    for data in sample_data:
        try:
            indicator = EconomicIndicator(**data)
            db.add(indicator)
            count += 1
            print(f"  Added: {data['period_label']} - {data.get('province', 'Cả nước')}")
        except Exception as e:
            print(f"  Error: {e}")
            print(f"     Data: {data}")
    
    db.commit()
    print(f"\nCreated {count} sample economic indicators!")


def main():
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        import_from_csv(csv_file)
    else:
        print("\nNo CSV file provided. Creating sample data instead...")
        print("   Usage: python scripts/import_economic_data.py [csv_file]")
        create_sample_data()
    
    # Show summary
    print("\nCurrent data summary:")
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM economic_indicators'))
        total = result.scalar()
        print(f"   Total indicators in DB: {total}")
        
        result = conn.execute(text("""
            SELECT period_type, COUNT(*) as count
            FROM economic_indicators
            GROUP BY period_type
            ORDER BY count DESC
        """))
        print("\n   By period type:")
        for row in result:
            print(f"     - {row[0]}: {row[1]} records")
        
        result = conn.execute(text("""
            SELECT province, COUNT(*) as count
            FROM economic_indicators
            WHERE province IS NOT NULL
            GROUP BY province
            ORDER BY count DESC
        """))
        print("\n   By province:")
        for row in result:
            print(f"     - {row[0]}: {row[1]} records")
    
    db.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
