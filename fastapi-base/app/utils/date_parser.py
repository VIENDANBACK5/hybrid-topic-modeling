"""
Utility functions for parsing dates and extracting temporal information.
"""
from typing import Tuple, Optional
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


def parse_year_quarter_from_date(date_str: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse year and quarter from a date string.
    
    Args:
        date_str: Date string in various formats:
                  - "YYYY-MM-DD" (e.g., "2025-12-31")
                  - "DD/MM/YYYY" (e.g., "31/12/2025")
                  - "YYYY" (year only)
                  - Can also be None or empty
    
    Returns:
        Tuple of (year, quarter) where:
        - year: Integer year (e.g., 2025) or None
        - quarter: Integer 1-4 representing quarter, or None if only year available
        
    Examples:
        >>> parse_year_quarter_from_date("2025-12-31")
        (2025, 4)
        >>> parse_year_quarter_from_date("2025-03-15")
        (2025, 1)
        >>> parse_year_quarter_from_date("2025")
        (2025, None)
        >>> parse_year_quarter_from_date(None)
        (None, None)
    """
    if not date_str:
        return (None, None)
    
    try:
        # Handle string type
        if not isinstance(date_str, str):
            # If it's a datetime object, convert to string
            if isinstance(date_str, datetime):
                date_str = date_str.strftime("%Y-%m-%d")
            else:
                date_str = str(date_str)
        
        # Remove extra whitespace
        date_str = date_str.strip()
        
        # Pattern 1: YYYY-MM-DD (optionally with time)
        match = re.search(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            quarter = ((month - 1) // 3) + 1
            return (year, quarter)
        
        # Pattern 2: DD/MM/YYYY or DD-MM-YYYY (optionally with time)
        match = re.search(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
        if match:
            year = int(match.group(3))
            month = int(match.group(2))
            quarter = ((month - 1) // 3) + 1
            return (year, quarter)
        
        # Pattern 3: Year only (YYYY)
        match = re.match(r'^(\d{4})$', date_str)
        if match:
            year = int(match.group(1))
            return (year, None)
        
        # Pattern 4: Try datetime parsing as fallback
        iso_pattern = r'^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})'
        match = re.match(iso_pattern, date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            quarter = ((month - 1) // 3) + 1
            return (year, quarter)

        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m", "%m/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                month = dt.month
                quarter = ((month - 1) // 3) + 1
                return (dt.year, quarter)
            except ValueError:
                continue
        
        # If all patterns fail
        logger.warning(f"Could not parse date: {date_str}")
        return (None, None)
        
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}': {e}")
        return (None, None)
