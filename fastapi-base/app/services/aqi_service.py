"""
AQI Service - Lấy dữ liệu chất lượng không khí từ AQICN API
Fill vào bảng air_quality_detail
"""
import logging
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# AQI API Configuration
AQI_API_BASE = "https://api.waqi.info"
AQI_TOKEN = "f938aab2e2530653b0bb9a5555cb48589eeab57d"

# Province to Station ID mapping (from https://aqicn.org/data-platform)
PROVINCE_STATION_MAP = {
    "Hưng Yên": "13683",  # Sở TNMT - 437 Nguyễn Văn Linh, Tp Hưng Yên
}


class AQIService:
    """Service to fetch AQI data and fill air_quality_detail table"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def fetch_and_fill_aqi_data(
        self,
        province: str = "Hưng Yên",
        limit_stations: Optional[int] = None,
        store_mode: str = "historical"  # "latest" hoặc "historical"
    ) -> Dict[str, Any]:
        """
        Fetch AQI data from AQICN API and fill air_quality_detail table
        
        Args:
            province: Province name
            limit_stations: Limit number of stations to process
            store_mode: "latest" = update existing quarter record, "historical" = save new record with timestamp
        
        Returns:
            Summary of operation
        """
        results = {
            "province": province,
            "stations_processed": 0,
            "records_created": 0,
            "records_updated": 0,
            "errors": []
        }
        
        # Get station ID for province
        station_id = PROVINCE_STATION_MAP.get(province)
        if not station_id:
            return {
                **results,
                "errors": [f"Province '{province}' not found in mapping. Available: {list(PROVINCE_STATION_MAP.keys())}"]
            }
        
        try:
            # Fetch data from AQI API using feed endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{AQI_API_BASE}/feed/@{station_id}/",
                    params={"token": AQI_TOKEN}
                )
                response.raise_for_status()
                data = response.json()
            
            if data.get("status") != "ok":
                return {
                    **results,
                    "errors": [f"API error: {data.get('message', 'Unknown error')}"]
                }
            
            # Process single station data
            station_data = data.get("data")
            if not station_data:
                return {
                    **results,
                    "errors": ["No data returned from API"]
                }
            
            try:
                # Process current measurement
                station_result = self._process_station(station_data, province, store_mode)
                results["stations_processed"] = 1
                if station_result.get("created"):
                    results["records_created"] += station_result.get("created", 0)
                if station_result.get("updated"):
                    results["records_updated"] += station_result.get("updated", 0)
                
                # Process forecast data (daily predictions)
                if store_mode == "historical":
                    # KHÔNG xóa forecast cũ - giữ lại để tracking độ chính xác của dự báo
                    # Official data và forecast data tồn tại song song
                    
                    forecast_result = self._process_forecast(station_data, province)
                    results["records_created"] += forecast_result.get("created", 0)
                    
            except Exception as e:
                logger.error(f"Error processing station: {e}")
                results["errors"].append(str(e))
            
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching AQI data: {e}")
            return {
                **results,
                "errors": [f"HTTP error: {str(e)}"]
            }
        except Exception as e:
            logger.error(f"Error fetching AQI data: {e}")
            return {
                **results,
                "errors": [f"Unexpected error: {str(e)}"]
            }
    
    def _process_station(
        self,
        station_data: Dict[str, Any],
        province: str,
        store_mode: str = "historical"
    ) -> Dict[str, bool]:
        """
        Process single station data and insert/update in DB
        
        Args:
            station_data: Raw data from API
            province: Province name
            store_mode: "latest" = update quarter record, "historical" = always create new
        
        Returns:
            {"created": bool, "updated": bool}
        """
        from app.models.model_indicator_details import AirQualityDetail
        
        # Extract data from feed API structure
        city_info = station_data.get("city", {})
        station_name = city_info.get("name", "Unknown")
        
        # AQI value
        aqi_value = station_data.get("aqi")
        if aqi_value == "-":
            aqi_value = None
        else:
            try:
                aqi_value = float(aqi_value)
            except (ValueError, TypeError):
                aqi_value = None
        
        # PM2.5, PM10 from iaqi
        iaqi = station_data.get("iaqi", {})
        pm25 = self._extract_pollutant_value(iaqi.get("pm25"))
        pm10 = self._extract_pollutant_value(iaqi.get("pm10"))
        no2 = self._extract_pollutant_value(iaqi.get("no2"))
        so2 = self._extract_pollutant_value(iaqi.get("so2"))
        co = self._extract_pollutant_value(iaqi.get("co"))
        o3 = self._extract_pollutant_value(iaqi.get("o3"))
        
        # Time
        time_data = station_data.get("time", {})
        timestamp_str = time_data.get("iso")
        if timestamp_str:
            try:
                measurement_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except Exception:
                measurement_time = datetime.now()
        else:
            measurement_time = datetime.now()
        
        year = measurement_time.year
        quarter = (measurement_time.month - 1) // 3 + 1
        month = measurement_time.month
        
        # Calculate good days percentage (placeholder - cần tính toán thực tế)
        good_days_pct = self._calculate_good_days_pct(aqi_value)
        
        # Check if record exists based on store_mode
        if store_mode == "latest":
            # Update mode: Find existing record for this quarter
            existing = self.db.query(AirQualityDetail).filter(
                AirQualityDetail.province == province,
                AirQualityDetail.year == year,
                AirQualityDetail.quarter == quarter
            ).first()
        else:
            # Historical mode: Always create new record
            existing = None
        
        if existing:
            # Update existing record
            if aqi_value is not None:
                existing.aqi_score = aqi_value
            if pm25 is not None:
                existing.pm25 = pm25
            if pm10 is not None:
                existing.pm10 = pm10
            if no2 is not None:
                existing.no2 = no2
            if so2 is not None:
                existing.so2 = so2
            if co is not None:
                existing.co = co
            if o3 is not None:
                existing.o3 = o3
            if good_days_pct is not None:
                existing.good_days_pct = good_days_pct
            
            existing.data_source = f"AQICN API - {station_name}"
            existing.updated_at = datetime.now()
            
            self.db.commit()
            return {"created": False, "updated": True}
        else:
            # Create new record
            new_record = AirQualityDetail(
                province=province,
                year=year,
                quarter=quarter,
                month=month,
                aqi_score=aqi_value,
                pm25=pm25,
                pm10=pm10,
                no2=no2,
                so2=so2,
                co=co,
                o3=o3,
                good_days_pct=good_days_pct,
                data_source=f"AQICN API - {station_name} (measured: {measurement_time.strftime('%Y-%m-%d %H:%M')})",
                data_status="official"
                # last_updated sẽ dùng server_default=func.now() để lưu thời điểm cập nhật thực tế
            )
            
            self.db.add(new_record)
            try:
                self.db.commit()
                return {"created": True, "updated": False}
            except Exception as e:
                self.db.rollback()
                # If duplicate (unique constraint violation), skip silently
                if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
                    logger.debug(f"Record already exists for {province} at {measurement_time}, skipping")
                    return {"created": False, "updated": False}
                else:
                    raise
    
    def _process_forecast(
        self,
        station_data: Dict[str, Any],
        province: str
    ) -> Dict[str, int]:
        """
        Process forecast data and create records for future dates
        Fill tất cả data mà API cung cấp (pm25, pm10, no2, so2, co, o3 nếu có)
        CHỈ tạo forecast cho ngày TƯƠNG LAI (> hôm nay)
        
        Returns:
            {"created": int} - number of forecast records created
        """
        from app.models.model_indicator_details import AirQualityDetail
        from datetime import datetime as dt, date
        
        forecast = station_data.get("forecast", {})
        daily = forecast.get("daily", {})
        
        if not daily:
            return {"created": 0}
        
        city_info = station_data.get("city", {})
        station_name = city_info.get("name", "Unknown")
        
        # Get today's date for comparison
        today = date.today()
        
        # Get forecast arrays for all pollutants (nếu API có)
        pm25_forecast = daily.get("pm25", [])
        pm10_forecast = daily.get("pm10", [])
        no2_forecast = daily.get("no2", [])
        so2_forecast = daily.get("so2", [])
        co_forecast = daily.get("co", [])
        o3_forecast = daily.get("o3", [])
        
        created_count = 0
        
        # Process each day in forecast
        for i, pm25_data in enumerate(pm25_forecast):
            try:
                day_str = pm25_data.get("day")  # Format: "2026-01-15"
                if not day_str:
                    continue
                
                # Parse date
                forecast_date = dt.strptime(day_str, "%Y-%m-%d")
                
                # SKIP nếu là ngày quá khứ hoặc hôm nay (chỉ lưu forecast cho tương lai)
                if forecast_date.date() <= today:
                    continue
                
                # Get data for same day from all pollutants
                pm10_data = pm10_forecast[i] if i < len(pm10_forecast) else {}
                no2_data = no2_forecast[i] if i < len(no2_forecast) else {}
                so2_data = so2_forecast[i] if i < len(so2_forecast) else {}
                co_data = co_forecast[i] if i < len(co_forecast) else {}
                o3_data = o3_forecast[i] if i < len(o3_forecast) else {}
                
                # Extract average values (fill đầy đủ tất cả data có sẵn)
                pm25_avg = pm25_data.get("avg")
                pm10_avg = pm10_data.get("avg")
                no2_avg = no2_data.get("avg")
                so2_avg = so2_data.get("avg")
                co_avg = co_data.get("avg")
                o3_avg = o3_data.get("avg")
                
                # Calculate AQI from PM2.5 (simplified)
                aqi_value = pm25_avg if pm25_avg else None
                
                year = forecast_date.year
                quarter = (forecast_date.month - 1) // 3 + 1
                month = forecast_date.month
                
                # Check if forecast record already exists for this specific date
                # Dùng data_source để identify forecast cho ngày cụ thể
                forecast_marker = f"forecast:{forecast_date.strftime('%Y-%m-%d')}"
                existing = self.db.query(AirQualityDetail).filter(
                    AirQualityDetail.province == province,
                    AirQualityDetail.year == year,
                    AirQualityDetail.quarter == quarter,
                    AirQualityDetail.month == month,
                    AirQualityDetail.data_status == "forecast",
                    AirQualityDetail.data_source.like(f"%{forecast_marker}%")
                ).first()
                
                if existing:
                    # Skip if forecast already exists for this exact date
                    continue
                
                # Create forecast record - Fill đầy đủ tất cả data API cung cấp
                forecast_record = AirQualityDetail(
                    province=province,
                    year=year,
                    quarter=quarter,
                    month=month,
                    aqi_score=aqi_value,
                    pm25=pm25_avg,
                    pm10=pm10_avg,
                    no2=no2_avg,      # Sẽ fill nếu API có
                    so2=so2_avg,      # Sẽ fill nếu API có
                    co=co_avg,        # Sẽ fill nếu API có
                    o3=o3_avg,        # Sẽ fill nếu API có
                    good_days_pct=self._calculate_good_days_pct(aqi_value),
                    data_source=f"AQICN API Forecast - {station_name} ({forecast_marker})",
                    data_status="forecast"
                    # last_updated sẽ dùng server_default=func.now() = thời điểm tạo forecast này
                )
                
                self.db.add(forecast_record)
                try:
                    self.db.flush()  # Flush để check constraint ngay
                    created_count += 1
                except Exception as insert_error:
                    self.db.rollback()
                    # Skip if duplicate
                    if "unique constraint" in str(insert_error).lower():
                        logger.debug(f"Forecast already exists for {province} at {forecast_date}, skipping")
                        continue
                    else:
                        logger.warning(f"Error inserting forecast for {forecast_date}: {insert_error}")
                        continue
                
            except Exception as e:
                logger.warning(f"Error processing forecast day {i}: {e}")
                continue
        
        if created_count > 0:
            self.db.commit()
        
        return {"created": created_count}
    
    def _cleanup_old_forecasts(self, province: str) -> int:
        """
        [DEPRECATED] Không còn xóa forecast records nữa
        
        Forecast data được GIỮ LẠI như lịch sử để:
        - Đối chiếu độ chính xác của dự báo
        - Phân tích xu hướng dự báo vs thực tế
        - Tracking lịch sử đầy đủ
        
        Official data và forecast data tồn tại song song, phân biệt bằng data_status
        
        Returns:
            0 (không xóa gì)
        """
        logger.info(f"Forecast cleanup disabled - keeping all forecast records for {province}")
        return 0
    
    @staticmethod
    def _extract_pollutant_value(pollutant_data: Optional[Dict]) -> Optional[float]:
        """Extract pollutant value from IAQI data"""
        if not pollutant_data:
            return None
        
        value = pollutant_data.get("v")
        if value == "-" or value is None:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _calculate_good_days_pct(aqi_value: Optional[float]) -> Optional[float]:
        """
        Calculate good days percentage based on current AQI
        
        Placeholder - trong thực tế cần query historical data
        """
        if aqi_value is None:
            return None
        
        # Simple estimation: AQI < 50 = good
        # This is placeholder logic
        if aqi_value < 50:
            return 100.0
        elif aqi_value < 100:
            return 70.0
        elif aqi_value < 150:
            return 40.0
        else:
            return 20.0


__all__ = ["AQIService"]
