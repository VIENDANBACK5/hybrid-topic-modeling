"""
Test OpenAI fill missing economic data
"""
from dotenv import load_dotenv
load_dotenv()

import os
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5555'
os.environ['POSTGRES_DB'] = 'DBHuYe'

import sys
sys.path.append('/home/ai_team/lab/pipeline_mxh/fastapi-base')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.openai_economic_service import fill_missing_fields

db_url = 'postgresql+psycopg2://postgres:postgres@localhost:5555/DBHuYe'
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def test_fill_missing():
    """Test fill missing data cho record có nhiều NULL"""
    
    print("🧪 Testing OpenAI fill missing data...\n")
    
    # Test data: Tháng 1/2026 (có nhiều NULL)
    test_data = {
        "id": 10,
        "period_label": "Tháng 1/2026",
        "province": None,
        "grdp_growth_rate": 8.5,
        "iip_growth_rate": None,  # NULL - cần fill
        "cpi_growth_rate": None,  # NULL - cần fill
        "export_value": None,  # NULL - cần fill
        "fdi_disbursed": None,  # NULL - cần fill
        "state_budget_revenue": None,  # NULL - cần fill
        "notes": "Dự báo tháng 1/2026",
        "is_estimated": 1
    }
    
    print("📋 Before (with NULLs):")
    for key, value in test_data.items():
        if key in ["iip_growth_rate", "cpi_growth_rate", "export_value", "fdi_disbursed", "state_budget_revenue"]:
            status = "✅" if value is not None else "❌ NULL"
            print(f"  {key:<25}: {value if value else 'NULL':<15} {status}")
    
    print("\n🤖 Calling OpenAI to fill missing fields...")
    
    # Fill missing
    filled_data = fill_missing_fields(test_data, use_openai=True)
    
    print("\n📊 After (filled by OpenAI):")
    for key, value in filled_data.items():
        if key in ["iip_growth_rate", "cpi_growth_rate", "export_value", "fdi_disbursed", "state_budget_revenue"]:
            was_null = test_data.get(key) is None
            status = "🆕 FILLED" if was_null and value is not None else ("✅" if value is not None else "❌ still NULL")
            print(f"  {key:<25}: {value if value else 'NULL':<15} {status}")
    
    print("\n" + "="*60)
    if filled_data.get("notes"):
        print(f"📝 Notes: {filled_data['notes']}")

if __name__ == "__main__":
    test_fill_missing()
