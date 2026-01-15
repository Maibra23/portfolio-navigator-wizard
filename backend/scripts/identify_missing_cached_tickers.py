#!/usr/bin/env python3
"""
Identify tickers that are missing from Redis cache and why they're missing.

This script identifies tickers that should be in the master list but don't have
complete cache data (both prices and sector) in Redis.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.redis_first_data_service import redis_first_data_service
from utils.enhanced_data_fetcher import EnhancedDataFetcher
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def identify_missing_tickers():
    """Identify which tickers are missing from cache and why"""
    
    logger.info("🔍 Identifying missing cached tickers...")
    
    # Get data service
    data_service = redis_first_data_service
    redis_client = data_service.redis_client
    
    if not redis_client:
        logger.error("❌ Redis client not available")
        return
    
    # Get all tickers from master list
    all_tickers = data_service.all_tickers
    logger.info(f"📋 Master list contains {len(all_tickers)} tickers")
    
    # Check each ticker for missing data
    missing_tickers = {
        'missing_prices': [],
        'missing_sector': [],
        'missing_both': [],
        'invalid_sector': [],
        'invalid_metrics': []
    }
    
    logger.info("🔍 Checking cache status for all tickers...")
    
    for ticker in all_tickers:
        price_key = f"ticker_data:prices:{ticker}"
        sector_key = f"ticker_data:sector:{ticker}"
        metrics_key = f"ticker_data:metrics:{ticker}"
        
        has_prices = redis_client.exists(price_key) > 0
        has_sector = redis_client.exists(sector_key) > 0
        has_metrics = redis_client.exists(metrics_key) > 0
        
        # Check what's missing
        if not has_prices and not has_sector:
            missing_tickers['missing_both'].append(ticker)
        elif not has_prices:
            missing_tickers['missing_prices'].append(ticker)
        elif not has_sector:
            missing_tickers['missing_sector'].append(ticker)
        else:
            # Both exist, but check if sector data is valid (this is what causes skips)
            try:
                sector_data = data_service._load_from_cache(ticker, 'sector')
                if not sector_data or not isinstance(sector_data, dict):
                    missing_tickers['invalid_sector'].append(ticker)
                    logger.debug(f"⚠️ {ticker}: Sector data exists but is invalid (not a dict)")
            except Exception as e:
                logger.debug(f"⚠️ Error checking sector data for {ticker}: {e}")
                missing_tickers['invalid_sector'].append(ticker)
            
            # Also check if metrics data exists and is valid
            try:
                metrics_data = data_service._load_from_cache(ticker, 'metrics')
                # Metrics are optional, but if they exist and are invalid, log it
                if metrics_data is not None and not isinstance(metrics_data, dict):
                    if ticker not in missing_tickers['invalid_metrics']:
                        missing_tickers['invalid_metrics'].append(ticker)
            except Exception as e:
                logger.debug(f"⚠️ Error checking metrics data for {ticker}: {e}")
    
    # Print summary
    total_missing = (
        len(missing_tickers['missing_both']) +
        len(missing_tickers['missing_prices']) +
        len(missing_tickers['missing_sector']) +
        len(missing_tickers['invalid_sector'])
    )
    
    # Also check for tickers that would be skipped due to invalid sector parsing
    # This matches the logic in strategy_portfolio_optimizer._get_stocks_from_redis_only
    logger.info("\n🔍 Checking for tickers with invalid sector data (would be skipped)...")
    invalid_sector_details = []
    for ticker in all_tickers:
        price_key = f"ticker_data:prices:{ticker}"
        sector_key = f"ticker_data:sector:{ticker}"
        
        if redis_client.exists(price_key) > 0 and redis_client.exists(sector_key) > 0:
            # Both keys exist, check if sector can be parsed
            try:
                import json as json_lib
                import pickle
                
                sector_raw = redis_client.get(sector_key)
                if sector_raw:
                    cached_sector = None
                    try:
                        cached_sector = json_lib.loads(sector_raw)
                    except:
                        try:
                            cached_sector = pickle.loads(sector_raw)
                        except:
                            pass
                    
                    if not cached_sector or not isinstance(cached_sector, dict):
                        invalid_sector_details.append({
                            'ticker': ticker,
                            'reason': 'Sector data exists but cannot be parsed or is not a dict',
                            'raw_type': type(sector_raw).__name__ if sector_raw else 'None'
                        })
            except Exception as e:
                invalid_sector_details.append({
                    'ticker': ticker,
                    'reason': f'Error parsing sector data: {e}',
                    'raw_type': 'Error'
                })
    
    logger.info("\n" + "="*60)
    logger.info("📊 MISSING CACHE DATA SUMMARY")
    logger.info("="*60)
    logger.info(f"Total tickers in master list: {len(all_tickers)}")
    logger.info(f"Total missing/invalid: {total_missing}")
    logger.info(f"Complete cache: {len(all_tickers) - total_missing}")
    
    if missing_tickers['missing_both']:
        logger.info(f"\n❌ Missing BOTH prices and sector ({len(missing_tickers['missing_both'])}):")
        for ticker in missing_tickers['missing_both']:
            logger.info(f"   - {ticker}")
    
    if missing_tickers['missing_prices']:
        logger.info(f"\n⚠️  Missing PRICES only ({len(missing_tickers['missing_prices'])}):")
        for ticker in missing_tickers['missing_prices']:
            logger.info(f"   - {ticker}")
    
    if missing_tickers['missing_sector']:
        logger.info(f"\n⚠️  Missing SECTOR only ({len(missing_tickers['missing_sector'])}):")
        for ticker in missing_tickers['missing_sector']:
            logger.info(f"   - {ticker}")
    
    if missing_tickers['invalid_sector']:
        logger.info(f"\n⚠️  Invalid SECTOR data ({len(missing_tickers['invalid_sector'])}):")
        for ticker in missing_tickers['invalid_sector']:
            logger.info(f"   - {ticker}")
    
    if invalid_sector_details:
        logger.info(f"\n❌ Tickers with EXISTING but INVALID sector data ({len(invalid_sector_details)}):")
        for detail in invalid_sector_details:
            logger.info(f"   - {detail['ticker']}: {detail['reason']}")
        logger.info("\n💡 These tickers have both price and sector keys in Redis,")
        logger.info("   but the sector data cannot be parsed as a dict, so they're skipped.")
    
    # Identify the 4 tickers that would be skipped
    skipped_tickers = (
        missing_tickers['missing_both'] +
        missing_tickers['missing_prices'] +
        missing_tickers['missing_sector'] +
        missing_tickers['invalid_sector']
    )
    
    if skipped_tickers:
        logger.info(f"\n🎯 Tickers that would be SKIPPED ({len(skipped_tickers)}):")
        for ticker in skipped_tickers[:10]:  # Show first 10
            logger.info(f"   - {ticker}")
        if len(skipped_tickers) > 10:
            logger.info(f"   ... and {len(skipped_tickers) - 10} more")
    
    logger.info("\n" + "="*60)
    
    # Check if we can fetch them
    if skipped_tickers:
        logger.info("\n🔍 Checking if missing tickers are fetchable...")
        data_fetcher = EnhancedDataFetcher()
        
        fetchable = []
        not_fetchable = []
        
        for ticker in skipped_tickers[:10]:  # Check first 10
            try:
                # Test if ticker is fetchable
                ticker_data = data_fetcher.get_ticker_data(ticker)
                if ticker_data and ticker_data.get('prices') is not None:
                    fetchable.append(ticker)
                    logger.info(f"   ✅ {ticker}: Fetchable")
                else:
                    not_fetchable.append(ticker)
                    logger.info(f"   ❌ {ticker}: Not fetchable")
            except Exception as e:
                not_fetchable.append(ticker)
                logger.info(f"   ❌ {ticker}: Error - {e}")
        
        if fetchable:
            logger.info(f"\n💡 Recommendation: Fetch {len(fetchable)} fetchable tickers")
            logger.info("   Run: python3 backend/scripts/refetch_missing_tickers.py")
    
    return {
        'missing_tickers': missing_tickers,
        'skipped_tickers': skipped_tickers,
        'total_missing': total_missing
    }

if __name__ == "__main__":
    try:
        result = identify_missing_tickers()
        if result and result['total_missing'] > 0:
            sys.exit(1)  # Exit with error if there are missing tickers
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

