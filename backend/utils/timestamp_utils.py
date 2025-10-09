#!/usr/bin/env python3
"""
Timestamp Utilities for Portfolio Navigator Wizard

This module provides robust timestamp normalization functions to handle
various timestamp formats from different data sources and exchanges.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Union, Any
import logging

logger = logging.getLogger(__name__)

def normalize_timestamp(timestamp: Any) -> str:
    """
    Normalize any timestamp format to ISO string format.
    
    Handles:
    - Unix timestamps (milliseconds and seconds)
    - ISO date strings
    - Pandas Timestamps
    - Datetime objects
    - String dates in various formats
    
    Args:
        timestamp: Any timestamp format
        
    Returns:
        str: ISO format timestamp string (YYYY-MM-DD HH:MM:SS)
        
    Raises:
        ValueError: If timestamp cannot be parsed
    """
    if timestamp is None:
        return None
        
    try:
        # Handle string timestamps
        if isinstance(timestamp, str):
            # Try parsing as ISO format first
            try:
                dt = pd.to_datetime(timestamp)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                # Try parsing as Unix timestamp string
                try:
                    ts = float(timestamp)
                    return normalize_timestamp(ts)
                except:
                    # Try various date formats
                    dt = pd.to_datetime(timestamp, infer_datetime_format=True)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle numeric timestamps (Unix)
        elif isinstance(timestamp, (int, float)):
            # Determine if it's milliseconds or seconds
            if timestamp > 1e12:  # Likely milliseconds
                dt = pd.to_datetime(timestamp, unit='ms')
            else:  # Likely seconds
                dt = pd.to_datetime(timestamp, unit='s')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle pandas Timestamp
        elif isinstance(timestamp, pd.Timestamp):
            return timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle datetime objects
        elif isinstance(timestamp, datetime):
            return timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle numpy datetime64
        elif isinstance(timestamp, np.datetime64):
            dt = pd.to_datetime(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        else:
            # Try pandas to_datetime as fallback
            dt = pd.to_datetime(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
            
    except Exception as e:
        logger.warning(f"Failed to normalize timestamp {timestamp}: {e}")
        return None

def detect_timestamp_format(timestamp: Any) -> str:
    """
    Detect the format of a timestamp.
    
    Args:
        timestamp: Any timestamp format
        
    Returns:
        str: Description of the detected format
    """
    if timestamp is None:
        return "None"
    
    if isinstance(timestamp, str):
        if timestamp.isdigit():
            return "Unix timestamp string"
        elif 'T' in timestamp or '-' in timestamp:
            return "ISO date string"
        else:
            return "Date string"
    
    elif isinstance(timestamp, (int, float)):
        if timestamp > 1e12:
            return "Unix milliseconds"
        else:
            return "Unix seconds"
    
    elif isinstance(timestamp, pd.Timestamp):
        return "Pandas Timestamp"
    
    elif isinstance(timestamp, datetime):
        return "Python datetime"
    
    elif isinstance(timestamp, np.datetime64):
        return "NumPy datetime64"
    
    else:
        return "Unknown format"

def validate_timestamp_range(first_date: str, last_date: str) -> bool:
    """
    Validate that first_date is before last_date.
    
    Args:
        first_date: First date in ISO format
        last_date: Last date in ISO format
        
    Returns:
        bool: True if valid range, False otherwise
    """
    try:
        if not first_date or not last_date:
            return False
            
        first_dt = pd.to_datetime(first_date)
        last_dt = pd.to_datetime(last_date)
        
        return first_dt < last_dt
    except:
        return False

def get_date_range_info(first_date: str, last_date: str) -> dict:
    """
    Get information about a date range.
    
    Args:
        first_date: First date in ISO format
        last_date: Last date in ISO format
        
    Returns:
        dict: Information about the date range
    """
    try:
        if not first_date or not last_date:
            return {"error": "Missing dates"}
            
        first_dt = pd.to_datetime(first_date)
        last_dt = pd.to_datetime(last_date)
        
        duration = last_dt - first_dt
        years = duration.days / 365.25
        
        return {
            "first_date": first_date,
            "last_date": last_date,
            "duration_days": duration.days,
            "duration_years": round(years, 2),
            "is_valid": first_dt < last_dt,
            "data_freshness": "fresh" if duration.days < 30 else "moderate" if duration.days < 365 else "stale"
        }
    except Exception as e:
        return {"error": str(e)}

def convert_to_unix_ms(timestamp: str) -> int:
    """
    Convert ISO timestamp to Unix milliseconds.
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        int: Unix timestamp in milliseconds
    """
    try:
        dt = pd.to_datetime(timestamp)
        return int(dt.timestamp() * 1000)
    except:
        return None

def convert_to_unix_s(timestamp: str) -> int:
    """
    Convert ISO timestamp to Unix seconds.
    
    Args:
        timestamp: ISO format timestamp string
        
    Returns:
        int: Unix timestamp in seconds
    """
    try:
        dt = pd.to_datetime(timestamp)
        return int(dt.timestamp())
    except:
        return None

# Test function
def test_timestamp_normalization():
    """Test the timestamp normalization with various formats."""
    test_cases = [
        "1285891200000",  # Unix milliseconds
        "1285891200",     # Unix seconds
        "2010-09-01 00:00:00",  # ISO string
        "2010-09-01",     # Date string
        pd.Timestamp("2010-09-01"),
        datetime(2010, 9, 1),
        np.datetime64("2010-09-01"),
    ]
    
    print("Testing timestamp normalization:")
    for test_case in test_cases:
        try:
            normalized = normalize_timestamp(test_case)
            format_detected = detect_timestamp_format(test_case)
            print(f"Input: {test_case} ({format_detected}) -> Output: {normalized}")
        except Exception as e:
            print(f"Error with {test_case}: {e}")

if __name__ == "__main__":
    test_timestamp_normalization()
