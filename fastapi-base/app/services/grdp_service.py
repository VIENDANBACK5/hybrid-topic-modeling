"""
GRDP Service - Consolidated
Tất cả logic extraction, field extractors, aggregation trong 1 file

Architecture:
1. Field Extractors (ETL) - Regex patterns để extract từng field
2. Data Aggregator - Merge data từ nhiều nguồn
3. Main Extractor - Orchestration: articles → economic_indicators → LLM
"""
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from app.models.model_article import Article
from app.models.model_economic_indicators import EconomicIndicator
from app.models.model_grdp_detail import GRDPDetail

logger = logging.getLogger(__name__)

