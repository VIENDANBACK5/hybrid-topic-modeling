"""
Schedule script để fetch AQI data định kỳ
Chạy với cron hoặc systemd timer

Ví dụ crontab:
# Fetch AQI mỗi giờ
0 * * * * cd /path/to/project && python scripts/schedule_aqi_fetch.py

# Fetch AQI mỗi 6 giờ
0 */6 * * * cd /path/to/project && python scripts/schedule_aqi_fetch.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.aqi_service import AQIService


async def fetch_aqi_data():
    """Fetch AQI data and save to database"""
    db: Session = SessionLocal()
    
    try:
        service = AQIService(db)
        
        # Fetch for Hưng Yên in historical mode
        result = await service.fetch_and_fill_aqi_data(
            province="Hưng Yên",
            store_mode="historical"
        )
        
        print(f"AQI Fetch completed:")
        print(f"   Province: {result['province']}")
        print(f"   Stations processed: {result['stations_processed']}")
        print(f"   Records created: {result['records_created']}")
        print(f"   Records updated: {result['records_updated']}")
        
        if result['errors']:
            print(f"Errors: {result['errors']}")
            
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(fetch_aqi_data())
