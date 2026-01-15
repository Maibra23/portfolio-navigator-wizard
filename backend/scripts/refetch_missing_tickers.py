#!/usr/bin/env python3
"""
Refetch tickers with missing data

This script:
1. Identifies tickers with missing data (missing prices, sector, or both)
2. Refetches them using the established fetching system
3. Shows progress with progress bars
"""

import sys
import os
import logging
from typing import List, Set
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_first_data_service import RedisFirstDataService
from utils.enhanced_data_fetcher import EnhancedDataFetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_tickers_with_missing_data(data_service: RedisFirstDataService) -> List[str]:
    """Get list of tickers that have missing data (prices, sector, or both)"""
    if not data_service.redis_client:
        logger.error("❌ Redis client not available")
        return []
    
    try:
        # Get all ticker keys
        price_keys = data_service.redis_client.keys("ticker_data:prices:*")
        sector_keys = data_service.redis_client.keys("ticker_data:sector:*")
        
        # Get unique tickers with any data in Redis
        tickers_with_data = set()
        for key in price_keys:
            if isinstance(key, bytes):
                key = key.decode()
            ticker = key.replace("ticker_data:prices:", "")
            tickers_with_data.add(ticker)
        
        for key in sector_keys:
            if isinstance(key, bytes):
                key = key.decode()
            ticker = key.replace("ticker_data:sector:", "")
            tickers_with_data.add(ticker)
        
        # Find tickers with missing data
        missing_tickers = []
        
        for ticker in tqdm(tickers_with_data, desc="Checking ticker data", leave=False):
            price_key = data_service._get_cache_key(ticker, 'prices')
            sector_key = data_service._get_cache_key(ticker, 'sector')
            
            has_prices = data_service.redis_client.exists(price_key) > 0
            has_sector = data_service.redis_client.exists(sector_key) > 0
            
            if not has_prices or not has_sector:
                missing_tickers.append(ticker)
        
        return sorted(missing_tickers)
    
    except Exception as e:
        logger.error(f"Error getting tickers with missing data: {e}")
        return []

def refetch_ticker(ticker: str, data_fetcher: EnhancedDataFetcher, data_service: RedisFirstDataService) -> dict:
    """Refetch a single ticker by forcing a fresh fetch"""
    result = {
        'ticker': ticker,
        'success': False,
        'error': None,
        'price_count': 0,
        'added_to_master': False
    }
    
    try:
        # Check what's missing
        price_key = data_service._get_cache_key(ticker, 'prices')
        sector_key = data_service._get_cache_key(ticker, 'sector')
        
        has_prices = data_service.redis_client.exists(price_key) > 0
        has_sector = data_service.redis_client.exists(sector_key) > 0
        
        # If both exist, skip (shouldn't happen, but check anyway)
        if has_prices and has_sector:
            result['error'] = "Data already complete"
            return result
        
        # Check if ticker is in master list
        in_master = ticker.upper() in [t.upper() for t in data_fetcher.all_tickers]
        
        # If not in master, allow out-of-master fetching
        if not in_master:
            data_fetcher._allow_out_of_master = True
        
        # Force fetch using _fetch_single_ticker_with_retry
        # This bypasses cache checks and fetches fresh data
        ticker_data = data_fetcher._fetch_single_ticker_with_retry(ticker)
        
        if ticker_data and 'prices' in ticker_data:
            prices = ticker_data.get('prices')
            if prices is not None and len(prices) > 0:
                result['success'] = True
                result['price_count'] = len(prices)
                
                # Verify it's now cached
                has_prices_after = data_service.redis_client.exists(price_key) > 0
                has_sector_after = data_service.redis_client.exists(sector_key) > 0
                
                if has_prices_after and has_sector_after:
                    # If not in master list and fetch was successful, add to master
                    if not in_master:
                        try:
                            # Get current master list
                            master_list = data_service.all_tickers
                            if ticker.upper() not in [t.upper() for t in master_list]:
                                # Add to master list
                                master_list.append(ticker.upper())
                                # Update Redis
                                import json
                                import gzip
                                from datetime import timedelta
                                try:
                                    compressed_data = gzip.compress(json.dumps(master_list).encode())
                                    data_service.redis_client.setex(
                                        "master_ticker_list",
                                        timedelta(hours=24),
                                        compressed_data
                                    )
                                    result['added_to_master'] = True
                                    data_fetcher.all_tickers = master_list
                                    logger.debug(f"  ✅ Added {ticker} to master list")
                                except Exception:
                                    # Fallback to uncompressed
                                    data_service.redis_client.setex(
                                        "master_ticker_list",
                                        timedelta(hours=24),
                                        json.dumps(master_list).encode()
                                    )
                                    result['added_to_master'] = True
                                    data_fetcher.all_tickers = master_list
                                    logger.debug(f"  ✅ Added {ticker} to master list")
                        except Exception as e:
                            logger.warning(f"  ⚠️  Could not add {ticker} to master list: {e}")
                else:
                    result['error'] = "Data fetched but not properly cached"
                    result['success'] = False
            else:
                result['error'] = "No price data returned"
        else:
            result['error'] = "No data returned"
            
    except Exception as e:
        result['error'] = str(e)
        logger.debug(f"Error refetching {ticker}: {e}")
    finally:
        # Clean up out-of-master flag
        if hasattr(data_fetcher, '_allow_out_of_master'):
            delattr(data_fetcher, '_allow_out_of_master')
    
    return result

def main():
    """Main function"""
    try:
        logger.info("=" * 80)
        logger.info("🚀 Starting ticker refetch process for missing data")
        logger.info("=" * 80)
        
        # Initialize services
        logger.info("\n📋 Step 1: Initializing services...")
        data_service = RedisFirstDataService()
        data_fetcher = EnhancedDataFetcher()
        
        if not data_service.redis_client:
            logger.error("❌ Redis client not available")
            return
        
        # Step 2: Get ticker status
        logger.info("\n📋 Step 2: Checking ticker status...")
        ticker_status = data_service.check_ticker_status()
        
        if ticker_status:
            missing_data_count = ticker_status.get('missing_data_count', 0)
            missing_prices_count = ticker_status.get('missing_prices_count', 0)
            missing_sector_count = ticker_status.get('missing_sector_count', 0)
            missing_both_count = ticker_status.get('missing_both_count', 0)
            
            logger.info(f"📊 Status Summary:")
            logger.info(f"   Missing Data Total: {missing_data_count}")
            logger.info(f"   - Missing Prices: {missing_prices_count}")
            logger.info(f"   - Missing Sector: {missing_sector_count}")
            logger.info(f"   - Missing Both: {missing_both_count}")
        
        # Step 3: Get list of tickers with missing data
        logger.info("\n📋 Step 3: Identifying tickers with missing data...")
        missing_tickers = get_tickers_with_missing_data(data_service)
        
        if not missing_tickers:
            logger.info("✅ No tickers with missing data found!")
            return
        
        logger.info(f"✅ Found {len(missing_tickers)} tickers with missing data")
        
        # Step 4: Refetch tickers
        logger.info("\n📋 Step 4: Refetching tickers with missing data...")
        logger.info(f"Refetching {len(missing_tickers)} tickers...")
        
        results = []
        successful = 0
        failed = 0
        
        # Temporarily disable manual regeneration requirement to allow refetching
        original_manual_regen = os.environ.get('MANUAL_REGENERATION_REQUIRED', 'true')
        os.environ['MANUAL_REGENERATION_REQUIRED'] = 'false'
        
        try:
            for ticker in tqdm(missing_tickers, desc="Refetching tickers"):
                result = refetch_ticker(ticker, data_fetcher, data_service)
                results.append(result)
                
                if result['success']:
                    successful += 1
                    logger.debug(f"  ✅ {ticker}: {result['price_count']} price points")
                else:
                    failed += 1
                    logger.warning(f"  ⚠️  {ticker}: {result.get('error', 'Unknown error')}")
        finally:
            # Restore original setting
            os.environ['MANUAL_REGENERATION_REQUIRED'] = original_manual_regen
        
        # Step 5: Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 REFETCH SUMMARY")
        logger.info("=" * 80)
        added_to_master = sum(1 for r in results if r.get('added_to_master', False))
        
        logger.info(f"Total Tickers Processed: {len(missing_tickers)}")
        logger.info(f"✅ Successful: {successful}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📝 Added to Master List: {added_to_master}")
        logger.info(f"Success Rate: {(successful/len(missing_tickers)*100):.1f}%")
        
        if failed > 0:
            logger.info("\n⚠️  Failed Tickers:")
            for result in results:
                if not result['success']:
                    logger.info(f"   - {result['ticker']}: {result.get('error', 'Unknown error')}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Refetch process completed")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Error in main process: {e}", exc_info=True)

if __name__ == "__main__":
    main()

