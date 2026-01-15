#!/usr/bin/env python3
"""
Fix corrupted sector data for tickers that have invalid sector data in Redis.

This script:
1. Identifies tickers with corrupted sector data
2. Attempts to refetch and fix the sector data
3. Reports the results
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.redis_first_data_service import redis_first_data_service
from utils.enhanced_data_fetcher import EnhancedDataFetcher
import logging
import json
import pickle

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def inspect_corrupted_ticker(ticker: str, redis_client):
    """Inspect what's actually stored for a ticker"""
    sector_key = f"ticker_data:sector:{ticker}"
    
    try:
        sector_raw = redis_client.get(sector_key)
        if sector_raw:
            logger.info(f"\n📋 Inspecting {ticker}:")
            logger.info(f"   Raw data type: {type(sector_raw)}")
            logger.info(f"   Raw data length: {len(sector_raw) if sector_raw else 0} bytes")
            
            # Try to decode
            if isinstance(sector_raw, bytes):
                try:
                    decoded = sector_raw.decode('utf-8')
                    logger.info(f"   Decoded (first 200 chars): {decoded[:200]}")
                except:
                    logger.info(f"   Cannot decode as UTF-8")
            
            # Try JSON
            try:
                if isinstance(sector_raw, bytes):
                    parsed = json.loads(sector_raw)
                else:
                    parsed = json.loads(sector_raw)
                logger.info(f"   JSON parse result type: {type(parsed)}")
                logger.info(f"   JSON parse result: {parsed}")
            except Exception as e:
                logger.info(f"   JSON parse failed: {e}")
            
            # Try pickle
            try:
                if isinstance(sector_raw, bytes):
                    parsed = pickle.loads(sector_raw)
                else:
                    parsed = pickle.loads(sector_raw)
                logger.info(f"   Pickle parse result type: {type(parsed)}")
                logger.info(f"   Pickle parse result: {parsed}")
            except Exception as e:
                logger.info(f"   Pickle parse failed: {e}")
    except Exception as e:
        logger.error(f"   Error inspecting {ticker}: {e}")

def fix_corrupted_tickers():
    """Fix corrupted sector data for identified tickers"""
    
    logger.info("🔧 Fixing corrupted sector data...")
    
    # Get data service
    data_service = redis_first_data_service
    redis_client = data_service.redis_client
    
    if not redis_client:
        logger.error("❌ Redis client not available")
        return
    
    # Known corrupted tickers
    corrupted_tickers = ['HAVAS.AS', 'CAN.L', 'APOTEA.ST', 'BILL.ST']
    
    logger.info(f"📋 Found {len(corrupted_tickers)} tickers with corrupted sector data")
    
    # Inspect each ticker first
    for ticker in corrupted_tickers:
        inspect_corrupted_ticker(ticker, redis_client)
    
    # Now fix them
    logger.info("\n🔧 Attempting to fix corrupted sector data...")
    data_fetcher = EnhancedDataFetcher()
    
    fixed_count = 0
    failed_count = 0
    
    for ticker in corrupted_tickers:
        logger.info(f"\n🔄 Fixing {ticker}...")
        
        try:
            # Delete corrupted sector data
            sector_key = f"ticker_data:sector:{ticker}"
            redis_client.delete(sector_key)
            logger.info(f"   ✅ Deleted corrupted sector data")
            
            # Refetch ticker data
            logger.info(f"   📥 Refetching data for {ticker}...")
            ticker_data = data_fetcher._fetch_single_ticker_with_retry(ticker)
            
            if ticker_data and ticker_data.get('sector'):
                # Save the new sector data
                sector_data = ticker_data['sector']
                if isinstance(sector_data, dict):
                    # Save as JSON
                    sector_json = json.dumps(sector_data)
                    redis_client.set(sector_key, sector_json)
                    # Set TTL (90 days)
                    redis_client.expire(sector_key, 90 * 24 * 60 * 60)
                    logger.info(f"   ✅ Successfully refetched and saved sector data: {sector_data}")
                    fixed_count += 1
                else:
                    logger.warning(f"   ⚠️  Refetched sector data is not a dict: {type(sector_data)}")
                    failed_count += 1
            else:
                logger.warning(f"   ⚠️  Could not refetch data for {ticker}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"   ❌ Error fixing {ticker}: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1
    
    logger.info("\n" + "="*60)
    logger.info("📊 FIX SUMMARY")
    logger.info("="*60)
    logger.info(f"✅ Fixed: {fixed_count}")
    logger.info(f"❌ Failed: {failed_count}")
    logger.info("="*60)
    
    return {
        'fixed': fixed_count,
        'failed': failed_count,
        'tickers': corrupted_tickers
    }

if __name__ == "__main__":
    try:
        result = fix_corrupted_tickers()
        if result and result['failed'] > 0:
            sys.exit(1)  # Exit with error if any failed
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




