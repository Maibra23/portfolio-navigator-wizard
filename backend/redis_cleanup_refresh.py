#!/usr/bin/env python3
"""
Redis Cleanup and Refresh Script
Clears corrupted ticker data and refreshes with fresh yfinance data
Uses the main enhanced_data_fetcher system with updated parameters
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.enhanced_data_fetcher import enhanced_data_fetcher
from utils.ticker_store import ticker_store
import logging
import time
import random
from datetime import datetime, timedelta
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_rate_limiting_parameters():
    """Update the rate limiting parameters as requested"""
    logger.info("🔧 Updating rate limiting parameters...")
    
    # Update the global parameters in the enhanced_data_fetcher
    enhanced_data_fetcher.YAHOO_REQUEST_DELAY = (1.2, 2.5)  # Random delay between 1.2-2.5 seconds
    enhanced_data_fetcher.MAX_RETRIES = 3  # Reduced retries to avoid triggering blocks
    enhanced_data_fetcher.RETRY_DELAY = 5  # Longer base retry delay
    
    logger.info("✅ Rate limiting parameters updated:")
    logger.info(f"   YAHOO_REQUEST_DELAY: {enhanced_data_fetcher.YAHOO_REQUEST_DELAY}")
    logger.info(f"   MAX_RETRIES: {enhanced_data_fetcher.MAX_RETRIES}")
    logger.info(f"   RETRY_DELAY: {enhanced_data_fetcher.RETRY_DELAY}")

def identify_corrupted_tickers():
    """Identify tickers with corrupted or invalid data"""
    logger.info("🔍 Identifying corrupted tickers...")
    
    corrupted_tickers = []
    total_tickers = len(enhanced_data_fetcher.all_tickers)
    
    for i, ticker in enumerate(enhanced_data_fetcher.all_tickers):
        if (i + 1) % 50 == 0:
            logger.info(f"   Progress: {i + 1}/{total_tickers} tickers checked")
        
        try:
            # Check if ticker is cached
            if not enhanced_data_fetcher._is_cached(ticker, 'prices') or not enhanced_data_fetcher._is_cached(ticker, 'sector'):
                corrupted_tickers.append(ticker)
                continue
            
            # Load and validate cached data
            cached_prices = enhanced_data_fetcher._load_from_cache(ticker, 'prices')
            cached_sector = enhanced_data_fetcher._load_from_cache(ticker, 'sector')
            
            # Check if data is corrupted
            is_corrupted = False
            
            # Validate price data
            if cached_prices is None or not enhanced_data_fetcher._validate_price_data(cached_prices, ticker):
                is_corrupted = True
                logger.debug(f"   {ticker}: Price data validation failed")
            
            # Validate sector data
            if cached_sector is None or not isinstance(cached_sector, dict):
                is_corrupted = True
                logger.debug(f"   {ticker}: Sector data validation failed")
            elif cached_sector.get('sector') == 'Unknown' and cached_sector.get('industry') == 'Unknown':
                # Check if this is a known company that should have sector info
                if ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']:  # Major companies
                    is_corrupted = True
                    logger.debug(f"   {ticker}: Major company with unknown sector")
            
            if is_corrupted:
                corrupted_tickers.append(ticker)
                
        except Exception as e:
            logger.debug(f"   {ticker}: Error during validation: {str(e)}")
            corrupted_tickers.append(ticker)
    
    logger.info(f"✅ Identified {len(corrupted_tickers)} corrupted/missing tickers out of {total_tickers}")
    return corrupted_tickers

def clear_corrupted_data(corrupted_tickers):
    """Clear corrupted ticker data from Redis"""
    if not corrupted_tickers:
        logger.info("✅ No corrupted data to clear")
        return
    
    logger.info(f"🗑️ Clearing corrupted data for {len(corrupted_tickers)} tickers...")
    
    cleared_count = 0
    for ticker in corrupted_tickers:
        try:
            # Clear prices, sector, and metrics data
            price_key = enhanced_data_fetcher._get_cache_key(ticker, 'prices')
            sector_key = enhanced_data_fetcher._get_cache_key(ticker, 'sector')
            metrics_key = enhanced_data_fetcher._get_cache_key(ticker, 'metrics')
            
            # Delete from Redis
            if enhanced_data_fetcher.r.exists(price_key):
                enhanced_data_fetcher.r.delete(price_key)
            if enhanced_data_fetcher.r.exists(sector_key):
                enhanced_data_fetcher.r.delete(sector_key)
            if enhanced_data_fetcher.r.exists(metrics_key):
                enhanced_data_fetcher.r.delete(metrics_key)
            
            cleared_count += 1
            
        except Exception as e:
            logger.error(f"❌ Error clearing {ticker}: {str(e)}")
    
    logger.info(f"✅ Cleared data for {cleared_count} tickers")

def refresh_corrupted_tickers(corrupted_tickers):
    """Refresh corrupted tickers with fresh data using the main system"""
    if not corrupted_tickers:
        logger.info("✅ No tickers to refresh")
        return
    
    logger.info(f"🔄 Refreshing {len(corrupted_tickers)} tickers with fresh data...")
    
    # Update date range to beginning of current month
    current_date = datetime.now()
    start_of_month = current_date.replace(day=1)
    enhanced_data_fetcher.START_DATE = start_of_month - timedelta(days=15*365)  # 15 years back
    enhanced_data_fetcher.END_DATE = start_of_month
    
    logger.info(f"📅 Date range: {enhanced_data_fetcher.START_DATE.strftime('%Y-%m-%d')} to {enhanced_data_fetcher.END_DATE.strftime('%Y-%m-%d')}")
    
    success_count = 0
    error_count = 0
    
    for i, ticker in enumerate(corrupted_tickers):
        try:
            logger.info(f"🔄 Refreshing {ticker} ({i + 1}/{len(corrupted_tickers)})")
            
            # Use the main system's fetch method
            data = enhanced_data_fetcher._fetch_single_ticker_with_retry(ticker)
            
            if data and enhanced_data_fetcher._validate_price_data(data.get('prices', pd.Series()), ticker):
                success_count += 1
                logger.info(f"✅ {ticker}: Successfully refreshed")
            else:
                error_count += 1
                logger.warning(f"⚠️ {ticker}: Refresh failed or validation failed")
            
            # Apply random delay between requests
            if i < len(corrupted_tickers) - 1:  # Don't delay after last ticker
                delay = random.uniform(1.2, 2.5)
                logger.debug(f"   Waiting {delay:.1f}s before next request...")
                time.sleep(delay)
                
        except Exception as e:
            error_count += 1
            logger.error(f"❌ Error refreshing {ticker}: {str(e)}")
    
    logger.info(f"✅ Refresh completed: {success_count} successful, {error_count} failed")

def verify_coverage():
    """Verify that we have 100% coverage after refresh"""
    logger.info("🔍 Verifying coverage after refresh...")
    
    try:
        cache_status = enhanced_data_fetcher.get_cache_status()
        
        if cache_status.get('redis') == 'available':
            price_coverage = cache_status.get('price_cache_coverage', 0)
            sector_coverage = cache_status.get('sector_cache_coverage', 0)
            
            logger.info(f"📊 Final Coverage:")
            logger.info(f"   Price data: {price_coverage:.1f}%")
            logger.info(f"   Sector data: {sector_coverage:.1f}%")
            
            if price_coverage >= 99.5 and sector_coverage >= 99.5:
                logger.info("🎉 SUCCESS: Achieved 100% coverage!")
                return True
            else:
                logger.warning(f"⚠️ Coverage below target: {price_coverage:.1f}% prices, {sector_coverage:.1f}% sectors")
                return False
        else:
            logger.error("❌ Redis not available for coverage verification")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error verifying coverage: {str(e)}")
        return False

def main():
    """Main function to clean and refresh Redis data"""
    logger.info("🚀 Starting Redis Cleanup and Refresh Process")
    logger.info("==================================================")
    
    try:
        # Step 1: Update rate limiting parameters
        update_rate_limiting_parameters()
        
        # Step 2: Identify corrupted tickers
        corrupted_tickers = identify_corrupted_tickers()
        
        if not corrupted_tickers:
            logger.info("✅ No corrupted data found - system is clean!")
            return
        
        # Step 3: Clear corrupted data
        clear_corrupted_data(corrupted_tickers)
        
        # Step 4: Refresh with fresh data
        refresh_corrupted_tickers(corrupted_tickers)
        
        # Step 5: Verify coverage
        success = verify_coverage()
        
        if success:
            logger.info("🎉 Redis cleanup and refresh completed successfully!")
            logger.info("✅ 100% coverage achieved with clean data")
        else:
            logger.warning("⚠️ Coverage verification failed - some issues may remain")
        
    except Exception as e:
        logger.error(f"❌ Redis cleanup and refresh failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
