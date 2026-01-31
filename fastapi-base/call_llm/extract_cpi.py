#!/usr/bin/env python3
"""
Extract: CPI (Consumer Price Index)

Source: Articles, Important Posts
Target: cpi_detail

Extracts consumer price index data using LLM
"""


import sys
import os
import json
from typing import Optional, Dict
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dual_model_client import extract_with_dual_model, call_llm
from base_extractor import setup_logger

logger = setup_logger('cpi')


def extract_cpi_data(content: str, url: Optional[str], province: str = "Hưng Yên") -> Optional[Dict]:
    """
    Extract CPI data from content using Dual Model (Gemini + GPT).
    """
    # Define extraction schema for CPI
    schema = {
        "province": "string",
        "year": "integer | null",
        "quarter": "integer | null",
        "month": "integer | null",
        "cpi_index": "float | null",
        "inflation_rate": "float | null",
        "food_cpi": "float | null",
        "housing_cpi": "float | null",
        "transport_cpi": "float | null",
        "education_cpi": "float | null",
        "healthcare_cpi": "float | null",
        "notes": "string | null"
    }
    
    # Field descriptions
    field_descriptions = {
        "cpi_index": "Chỉ số giá tiêu dùng (thường 100-110, năm gốc = 100)",
        "inflation_rate": "Tỷ lệ lạm phát (%, ví dụ: 3.5)",
        "food_cpi": "CPI nhóm lương thực, thực phẩm",
        "housing_cpi": "CPI nhóm nhà ở, điện nước",
        "transport_cpi": "CPI nhóm giao thông",
        "education_cpi": "CPI nhóm giáo dục",
        "healthcare_cpi": "CPI nhóm y tế, chăm sóc sức khỏe"
    }
    
    try:
        # Use dual model extraction
        data = extract_with_dual_model(
            content=content,
            title="CPI Data Extraction",
            extraction_schema=schema,
            category="chỉ số giá tiêu dùng (CPI) và lạm phát",
            province=province,
            field_descriptions=field_descriptions
        )
        
        if not data:
            return None
        
        # Set metadata
        data["source_url"] = url if url and url.startswith("http") else None
        data["data_status"] = "extracted"
        
        # Convert numeric fields
        for key in ["year", "quarter", "month"]:
            if data.get(key) is not None:
                try:
                    data[key] = int(data[key])
                except (ValueError, TypeError):
                    data[key] = None
        
        for key in ["cpi_index", "inflation_rate", "food_cpi", "housing_cpi", 
                    "transport_cpi", "education_cpi", "healthcare_cpi"]:
            if data.get(key) is not None:
                try:
                    data[key] = float(data[key])
                except (ValueError, TypeError):
                    data[key] = None
        
        return data
        
    except Exception as e:
        logger.error(f"Error extracting CPI data: {e}")
        return None


def save_to_cpi(db: Session, data: Dict) -> bool:
    """Save CPI data to database"""
    try:
        from sqlalchemy import text
        
        sql = text("""
            INSERT INTO cpi_detail (
                province, year, quarter, month,
                cpi_index, inflation_rate, 
                food_cpi, housing_cpi, transport_cpi, education_cpi, healthcare_cpi,
                data_status, data_source, document_type, notes
            ) VALUES (
                :province, :year, :quarter, :month,
                :cpi_index, :inflation_rate,
                :food_cpi, :housing_cpi, :transport_cpi, :education_cpi, :healthcare_cpi,
                :data_status, :data_source, :document_type, :notes
            )
            ON CONFLICT (province, year, COALESCE(month, 0), COALESCE(quarter, 0))
            DO UPDATE SET
                cpi_index = EXCLUDED.cpi_index,
                inflation_rate = EXCLUDED.inflation_rate,
                food_cpi = EXCLUDED.food_cpi,
                housing_cpi = EXCLUDED.housing_cpi,
                transport_cpi = EXCLUDED.transport_cpi,
                education_cpi = EXCLUDED.education_cpi,
                healthcare_cpi = EXCLUDED.healthcare_cpi,
                data_status = EXCLUDED.data_status,
                data_source = EXCLUDED.data_source,
                notes = EXCLUDED.notes
        """)
        
        db.execute(sql, data)
        db.commit()
        logger.info(f"✅ Saved CPI: {data.get('province')} {data.get('year')}/{data.get('month', 'Q' + str(data.get('quarter', '')))}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving CPI: {e}")
        db.rollback()
        return False


def extract_cpi_from_crawl(url: str = "https://thongkehungyen.nso.gov.vn") -> list:
    """
    Extract CPI data from external crawl
    
    This is a placeholder for web crawling functionality.
    In production, this would:
    1. Use requests or Playwright to fetch the page
    2. Parse HTML tables or content
    3. Extract CPI data
    4. Return structured data list
    
    Example return format:
    [
        {
            "province": "Hưng Yên",
            "year": 2024,
            "month": 12,
            "cpi_index": 105.2,
            "inflation_rate": 3.5,
            "document_type": "external",
            "data_source": "thongkehungyen.nso.gov.vn"
        }
    ]
    """
    logger.info(f"🌐 Crawling CPI data from {url}")
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Fetch the page
        logger.info(f"📡 Fetching page...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        logger.info(f"✅ Page fetched successfully ({len(response.content)} bytes)")
        
        # TODO: Implement actual parsing logic based on website structure
        # This is a placeholder - actual implementation depends on website structure
        
        logger.warning("⚠️  CPI crawling logic not yet implemented")
        logger.info("💡 To implement:")
        logger.info("   1. Inspect https://thongkehungyen.nso.gov.vn for CPI data location")
        logger.info("   2. Parse relevant tables or content sections")
        logger.info("   3. Extract CPI index, inflation rate, category indices")
        logger.info("   4. Return structured data list")
        
        return []
        
    except requests.RequestException as e:
        logger.error(f"❌ HTTP request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Crawling error: {e}")
        return []

