#!/usr/bin/env python3
"""
Base Extractor - Shared Utilities for All Extraction Scripts

Provides common functions:
- LLM API calls
- Database operations (fetch posts, save to detail tables)
- JSON parsing helpers
- Logging setup
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# =============================================================================
# CONFIGURATION
# =============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7777")
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
DELAY_BETWEEN_CALLS = float(os.getenv("DELAY_BETWEEN_CALLS", "2"))  # seconds
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/DBHuYe")


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logger(script_name: str, log_file: str = None) -> logging.Logger:
    """
    Setup logger for extraction script
    
    Args:
        script_name: Name of the script (e.g., 'cadre_statistics')
        log_file: Optional custom log file path
    
    Returns:
        Configured logger instance
    """
    if log_file is None:
        log_file = f'call_llm/{script_name}_extraction.log'
    
    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# =============================================================================
# LLM API FUNCTIONS
# =============================================================================

def call_llm(prompt: str, max_retries: int = 3, title: str = "Extractor") -> Optional[str]:
    """
    Call OpenRouter LLM API
    
    Args:
        prompt: The prompt to send to LLM
        max_retries: Number of retry attempts
        title: Title for the API request
    
    Returns:
        LLM response content or None if failed
    """
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY not found in environment variables")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": title
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 3000
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None
    
    return None


def parse_llm_json(response: str, logger: logging.Logger = None) -> Optional[Dict]:
    """
    Parse JSON from LLM response
    
    Args:
        response: LLM response string
        logger: Optional logger for error messages
    
    Returns:
        Parsed JSON dict or None if parsing failed
    """
    try:
        # Find JSON in response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            if logger:
                logger.warning("No JSON found in LLM response")
            return None
        
        data = json.loads(response[json_start:json_end])
        
        # Check for no_data flag
        if data.get("no_data"):
            return None
        
        return data
        
    except json.JSONDecodeError as e:
        if logger:
            logger.error(f"JSON decode error: {e}")
        return None
    except Exception as e:
        if logger:
            logger.error(f"Error parsing LLM JSON: {e}")
        return None


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def get_posts_from_db(
    type_newspaper: str,
    limit: int = 100,
    logger: logging.Logger = None
) -> List[Dict]:
    """
    Fetch posts from important_posts table
    
    Args:
        type_newspaper: Filter by type (e.g., 'politics', 'economy', 'education')
        limit: Maximum number of posts to fetch
        logger: Optional logger
    
    Returns:
        List of post dictionaries
    """
    try:
        engine = create_engine(DB_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        query = text("""
            SELECT id, title, content, url, dvhc, published_date, document_type
            FROM important_posts
            WHERE type_newspaper = :type_newspaper
            ORDER BY id DESC
            LIMIT :limit
        """)
        
        result = session.execute(query, {
            "type_newspaper": type_newspaper,
            "limit": limit
        })
        
        posts = []
        for row in result:
            posts.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "url": row[3],
                "province": row[4] or "Hưng Yên",
                "published_date": row[5],
                "document_type": row[6] or "external"
            })
        
        session.close()
        
        if logger:
            logger.info(f"Found {len(posts)} posts from important_posts (type={type_newspaper})")
        
        return posts
        
    except Exception as e:
        if logger:
            logger.error(f"Error fetching posts from DB: {e}")
        return []


def save_to_detail_table(
    data: Dict,
    table_name: str,
    logger: logging.Logger = None
) -> bool:
    """
    Save data to detail table via API
    
    Args:
        data: Data dictionary to save
        table_name: Target table name (e.g., 'cadre_statistics_detail')
        logger: Optional logger
    
    Returns:
        True if successful, False otherwise
    """
    # Map url to economic_indicator_id if needed
    if "url" in data:
        data["economic_indicator_id"] = data.pop("url")
    
    endpoint = f"{API_BASE_URL}/api/indicators/{table_name}"
    
    try:
        response = requests.post(endpoint, json=data, timeout=30)
        
        if response.status_code in [200, 201]:
            if logger:
                logger.info(f"✅ Saved to {table_name}")
            return True
        elif response.status_code == 409 or "duplicate" in response.text.lower():
            if logger:
                logger.info(f"ℹ️  {table_name} already exists (skip)")
            return True
        else:
            if logger:
                logger.error(f"Error saving to {table_name}: {response.status_code} - {response.text[:200]}")
            return False
            
    except Exception as e:
        if logger:
            logger.error(f"Exception saving to {table_name}: {e}")
        return False


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def log_extraction_start(
    logger: logging.Logger,
    script_name: str,
    field_name: str,
    batch_size: int
):
    """Log extraction start message"""
    logger.info("=" * 80)
    logger.info(f"BẮT ĐẦU LLM EXTRACTION - {field_name}")
    logger.info(f"Script: {script_name}")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"LLM Model: {LLM_MODEL}")
    logger.info(f"📦 Batch size: {batch_size}")
    logger.info("=" * 80)


def log_article_info(logger: logging.Logger, article: Dict, index: int, total: int):
    """Log article processing info"""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Progress: {index}/{total}")
    logger.info(f"URL ID: {article.get('id')}")
    logger.info(f"Title: {article.get('title', '')[:100]}")
    logger.info(f"Province: {article.get('province')}")
    logger.info(f"Document Type: {article.get('document_type')}")
    logger.info(f"Content length: {len(article.get('content', ''))} chars")


def log_extraction_summary(
    logger: logging.Logger,
    total_processed: int,
    total_extracted: int,
    field_name: str
):
    """Log extraction summary"""
    logger.info("\n" + "=" * 80)
    logger.info("KẾT QUẢ EXTRACTION")
    logger.info("=" * 80)
    logger.info(f"Đã xử lý: {total_processed} articles")
    logger.info(f"✅ {field_name} extracted: {total_extracted}")
    logger.info("=" * 80)


# =============================================================================
# VALIDATION
# =============================================================================

def validate_api_key():
    """Validate that LLM API key is present"""
    if not LLM_API_KEY:
        raise ValueError("Missing LLM_API_KEY. Set OPENROUTER_API_KEY or OPENAI_API_KEY environment variable.")
