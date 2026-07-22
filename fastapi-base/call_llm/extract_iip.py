#!/usr/bin/env python3
"""
Extract: IIP (Industrial Production Index)

Source: Articles, Important Posts
Target: iip_detail

Extracts industrial production index using LLM
"""


import sys
import os
import json
from typing import Optional, Dict
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dual_model_client import extract_with_dual_model, call_llm
from base_extractor import setup_logger

logger = setup_logger('iip')


def extract_iip_data(content: str, url: Optional[str], province: str = "Hưng Yên") -> Optional[Dict]:
    """
    Extract IIP data from content using Dual Model (Gemini + GPT).
    """
    # Define extraction schema for IIP
    schema = {
        "province": "string",
        "year": "integer | null",
        "quarter": "integer | null",
        "month": "integer | null",
        "iip_index": "float | null",
        "iip_growth_rate": "float | null",
        "mining_iip": "float | null",
        "manufacturing_iip": "float | null",
        "electricity_iip": "float | null",
        "notes": "string | null"
    }
    
    # Field descriptions
    field_descriptions = {
        "iip_index": "Chỉ số sản xuất công nghiệp (thường 100-150)",
        "iip_growth_rate": "Tốc độ tăng trưởng IIP (%)",
        "mining_iip": "IIP ngành khai khoáng",
        "manufacturing_iip": "IIP ngành chế biến, chế tạo",
        "electricity_iip": "IIP ngành sản xuất điện"
    }
    
    try:
        # Use dual model extraction
        data = extract_with_dual_model(
            content=content,
            title="IIP Data Extraction",
            extraction_schema=schema,
            category="chỉ số sản xuất công nghiệp (IIP)",
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
        
        for key in ["iip_index", "iip_growth_rate", "mining_iip", "manufacturing_iip", "electricity_iip"]:
            if data.get(key) is not None:
                try:
                    data[key] = float(data[key])
                except (ValueError, TypeError):
                    data[key] = None
        
        return data
        
    except Exception as e:
        logger.error(f"Error extracting IIP data: {e}")
        return None


def save_to_iip(db: Session, data: Dict) -> bool:
    """Save IIP data to database"""
    try:
        from sqlalchemy import text
        
        sql = text("""
            INSERT INTO iip_detail (
                province, year, quarter, month,
                iip_index, iip_growth_rate,
                manufacturing_index, processing_index, mining_index, 
                electricity_index, water_supply_index,
                data_status, data_source, document_type, notes
            ) VALUES (
                :province, :year, :quarter, :month,
                :iip_index, :iip_growth_rate,
                :manufacturing_index, :processing_index, :mining_index,
                :electricity_index, :water_supply_index,
                :data_status, :data_source, :document_type, :notes
            )
            ON CONFLICT (province, year, COALESCE(month, 0), COALESCE(quarter, 0))
            DO UPDATE SET
                iip_index = EXCLUDED.iip_index,
                iip_growth_rate = EXCLUDED.iip_growth_rate,
                manufacturing_index = EXCLUDED.manufacturing_index,
                processing_index = EXCLUDED.processing_index,
                mining_index = EXCLUDED.mining_index,
                electricity_index = EXCLUDED.electricity_index,
                water_supply_index = EXCLUDED.water_supply_index,
                data_status = EXCLUDED.data_status,
                data_source = EXCLUDED.data_source,
                notes = EXCLUDED.notes
        """)
        
        db.execute(sql, data)
        db.commit()
        logger.info(f"✅ Saved IIP: {data.get('province')} {data.get('year')}/{data.get('month', 'Q' + str(data.get('quarter', '')))}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving IIP: {e}")
        db.rollback()
        return False


def extract_iip_from_crawl(url: str = "https://thongkehungyen.nso.gov.vn") -> list:
    """
    Extract IIP data from external crawl
    
    This is a placeholder for web crawling functionality.
    In production, this would:
    1. Use requests or Playwright to fetch the page
    2. Parse HTML tables or content
    3. Extract IIP data
    4. Return structured data list
    
    Example return format:
    [
        {
            "province": "Hưng Yên",
            "year": 2024,
            "month": 12,
            "iip_index": 115.3,
            "iip_growth_rate": 8.5,
            "document_type": "external",
            "data_source": "thongkehungyen.nso.gov.vn"
        }
    ]
    """
    logger.info(f"🌐 Crawling IIP data from {url}")
    
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
        
        logger.warning("⚠️  IIP crawling logic not yet implemented")
        logger.info("💡 To implement:")
        logger.info("   1. Inspect https://thongkehungyen.nso.gov.vn for IIP data location")
        logger.info("   2. Parse relevant tables or content sections")
        logger.info("   3. Extract IIP index, growth rate, sector indices")
        logger.info("   4. Return structured data list")
        
        return []
        
    except requests.RequestException as e:
        logger.error(f"❌ HTTP request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Crawling error: {e}")
        return []

