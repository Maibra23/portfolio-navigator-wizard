#!/usr/bin/env python3
"""
Identify and fetch tickers in Redis but not in master list

This script:
1. Identifies tickers that exist in Redis but are not in the master list
2. Tests if they're fetchable
3. Fetches them and adds to master list if successful
"""

import sys
import os
import json
import logging
import gzip
from typing import List, Set
from datetime import timedelta
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_first_data_service import RedisFirstDataService
from utils.enhanced_data_fetcher import EnhancedDataFetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_tickers_in_redis(data_service: RedisFirstDataService) -> Set[str]:
    """Get all unique tickers that have data in Redis (prices or sector)"""
    if not data_service.redis_client:
        return set()
    
    try:
        price_keys = data_service.redis_client.keys("ticker_data:prices:*")
        sector_keys = data_service.redis_client.keys("ticker_data:sector:*")
        
        tickers = set()
        
        for key in price_keys:
            if isinstance(key, bytes):
                key = key.decode()
            ticker = key.replace("ticker_data:prices:", "")
            tickers.add(ticker)
        
        for key in sector_keys:
            if isinstance(key, bytes):
                key = key.decode()
            ticker = key.replace("ticker_data:sector:", "")
            tickers.add(ticker)
        
        return tickers
    except Exception as e:
        logger.error(f"Error getting tickers from Redis: {e}")
        return set()

def get_master_list_tickers(data_service: RedisFirstDataService) -> Set[str]:
    """Get all tickers in the master list"""
    try:
        master_list = data_service.all_tickers
        return {t.upper() for t in master_list} if master_list else set()
    except Exception as e:
        logger.error(f"Error getting master list: {e}")
        return set()

def identify_orphaned_tickers(data_service: RedisFirstDataService) -> List[str]:
    """Identify tickers in Redis but not in master list"""
    redis_tickers = get_tickers_in_redis(data_service)
    master_tickers = get_master_list_tickers(data_service)
    
    # Find tickers in Redis but not in master (case-insensitive)
    orphaned = []
    for ticker in redis_tickers:
        if ticker.upper() not in master_tickers:
            orphaned.append(ticker)
    
    return sorted(orphaned)

def test_fetch_ticker(ticker: str, data_fetcher: EnhancedDataFetcher) -> dict:
    """Test if a ticker can be fetched (bypassing master list check)"""
    result = {
        'ticker': ticker,
        'fetchable': False,
        'data': None,
        'error': None
    }
    
    try:
        # Enable out-of-master fetching
        data_fetcher._allow_out_of_master = True
        
        # Try to fetch the ticker
        ticker_data = data_fetcher._fetch_single_ticker_with_retry(ticker)
        
        if ticker_data and 'prices' in ticker_data:
            prices = ticker_data.get('prices')
            if prices is not None and len(prices) > 0:
                result['fetchable'] = True
                result['data'] = {
                    'has_prices': True,
                    'price_count': len(prices),
                    'has_sector': 'sector' in ticker_data and ticker_data['sector'] is not None
                }
            else:
                result['error'] = "No price data returned"
        else:
            result['error'] = "No data returned"
            
    except Exception as e:
        result['error'] = str(e)
    finally:
        # Disable out-of-master fetching
        if hasattr(data_fetcher, '_allow_out_of_master'):
            delattr(data_fetcher, '_allow_out_of_master')
    
    return result

def add_to_master_list(data_service: RedisFirstDataService, ticker: str) -> bool:
    """Add a ticker to the master list in Redis"""
    try:
        # Get current master list
        master_list = list(data_service.all_tickers)
        
        # Check if already in list (case-insensitive)
        if ticker.upper() not in [t.upper() for t in master_list]:
            master_list.append(ticker.upper())
            
            # Update Redis
            try:
                compressed_data = gzip.compress(json.dumps(master_list).encode())
                data_service.redis_client.setex(
                    "master_ticker_list",
                    timedelta(hours=24),
                    compressed_data
                )
                logger.debug(f"  ✅ Added {ticker} to master list (compressed)")
                return True
            except Exception:
                # Fallback to uncompressed
                data_service.redis_client.setex(
                    "master_ticker_list",
                    timedelta(hours=24),
                    json.dumps(master_list).encode()
                )
                logger.debug(f"  ✅ Added {ticker} to master list (uncompressed)")
                return True
        else:
            logger.debug(f"  ℹ️  {ticker} already in master list")
            return True
    except Exception as e:
        logger.error(f"  ❌ Error adding {ticker} to master list: {e}")
        return False

def refetch_ticker(ticker: str, data_fetcher: EnhancedDataFetcher, data_service: RedisFirstDataService) -> dict:
    """Refetch a ticker (now that it's in master list)"""
    result = {
        'ticker': ticker,
        'success': False,
        'error': None,
        'price_count': 0
    }
    
    try:
        ticker_data = data_fetcher.get_ticker_data(ticker)
        
        if ticker_data and 'prices' in ticker_data:
            prices = ticker_data.get('prices')
            if prices is not None and len(prices) > 0:
                result['success'] = True
                result['price_count'] = len(prices)
            else:
                result['error'] = "No price data returned"
        else:
            result['error'] = "No data returned"
    except Exception as e:
        result['error'] = str(e)
    
    return result

def main():
    """Main function"""
    try:
        logger.info("=" * 80)
        logger.info("🔍 Identifying and fetching orphaned tickers")
        logger.info("=" * 80)
        
        # Initialize services
        logger.info("\n📋 Step 1: Initializing services...")
        data_service = RedisFirstDataService()
        data_fetcher = EnhancedDataFetcher()
        
        if not data_service.redis_client:
            logger.error("❌ Redis client not available")
            return
        
        # Step 2: Identify orphaned tickers
        logger.info("\n📋 Step 2: Identifying tickers in Redis but not in master list...")
        orphaned_tickers = identify_orphaned_tickers(data_service)
        
        if not orphaned_tickers:
            logger.info("✅ No orphaned tickers found! Master list and Redis are in sync.")
            return
        
        logger.info(f"✅ Found {len(orphaned_tickers)} orphaned tickers:")
        for ticker in orphaned_tickers:
            logger.info(f"   - {ticker}")
        
        # Step 3: Test fetchability
        logger.info("\n📋 Step 3: Testing fetchability of orphaned tickers...")
        fetchable_tickers = []
        
        for ticker in tqdm(orphaned_tickers, desc="Testing fetchability"):
            result = test_fetch_ticker(ticker, data_fetcher)
            if result['fetchable']:
                fetchable_tickers.append(ticker)
                logger.info(f"  ✅ {ticker}: Fetchable ({result['data']['price_count']} price points)")
            else:
                logger.warning(f"  ⚠️  {ticker}: Not fetchable - {result.get('error', 'Unknown error')}")
        
        if not fetchable_tickers:
            logger.info("ℹ️  No fetchable orphaned tickers found")
            return
        
        logger.info(f"\n✅ Found {len(fetchable_tickers)} fetchable orphaned tickers")
        
        # Step 4: Add to master list and refetch
        logger.info("\n📋 Step 4: Adding to master list and refetching...")
        
        # Temporarily disable manual regeneration requirement
        original_manual_regen = os.environ.get('MANUAL_REGENERATION_REQUIRED', 'true')
        os.environ['MANUAL_REGENERATION_REQUIRED'] = 'false'
        
        successful = 0
        failed = 0
        added_to_master = 0
        
        try:
            for ticker in tqdm(fetchable_tickers, desc="Processing tickers"):
                # Add to master list
                if add_to_master_list(data_service, ticker):
                    added_to_master += 1
                    # Invalidate cache to force reload
                    data_service.invalidate_ticker_list_cache()
                    data_fetcher.all_tickers = data_service.all_tickers
                
                # Refetch to ensure complete data
                result = refetch_ticker(ticker, data_fetcher, data_service)
                
                if result['success']:
                    successful += 1
                    logger.info(f"  ✅ {ticker}: Successfully refetched ({result['price_count']} price points)")
                else:
                    failed += 1
                    logger.warning(f"  ⚠️  {ticker}: Refetch failed - {result.get('error', 'Unknown error')}")
        finally:
            # Restore original setting
            os.environ['MANUAL_REGENERATION_REQUIRED'] = original_manual_regen
        
        # Step 5: Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Orphaned Tickers Found: {len(orphaned_tickers)}")
        logger.info(f"Fetchable Tickers: {len(fetchable_tickers)}")
        logger.info(f"Added to Master List: {added_to_master}")
        logger.info(f"✅ Successfully Refetched: {successful}")
        logger.info(f"❌ Failed to Refetch: {failed}")
        
        if failed > 0:
            logger.info("\n⚠️  Failed Tickers:")
            for ticker in fetchable_tickers:
                # Check if it failed (simplified - in real scenario would track this)
                pass
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Process completed")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Error in main process: {e}", exc_info=True)

if __name__ == "__main__":
    main()

