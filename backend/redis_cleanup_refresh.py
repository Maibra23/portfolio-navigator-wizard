#!/usr/bin/env python3
"""
Redis Cleanup and Refresh Script
Uses the Redis-first data service with updated parameters
"""

import redis
import json
import gzip
import pandas as pd
from datetime import datetime, timedelta
import logging
from utils.redis_first_data_service import redis_first_data_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main cleanup and refresh function"""
    logger.info("🚀 Starting Redis cleanup and refresh process...")
    
    # Get Redis client from the Redis-first data service
    r = redis_first_data_service.redis_client
    if not r:
        logger.error("❌ Redis client not available")
        return
    
    # Update the global parameters in the Redis-first data service
    if hasattr(redis_first_data_service, 'enhanced_data_fetcher') and redis_first_data_service.enhanced_data_fetcher:
        redis_first_data_service.enhanced_data_fetcher.YAHOO_REQUEST_DELAY = (1.2, 2.5)  # Random delay between 1.2-2.5 seconds
        redis_first_data_service.enhanced_data_fetcher.MAX_RETRIES = 3  # Reduced retries to avoid triggering blocks
        redis_first_data_service.enhanced_data_fetcher.RETRY_DELAY = 5  # Longer base retry delay
        
        logger.info("📊 Updated EnhancedDataFetcher parameters:")
        logger.info(f"   YAHOO_REQUEST_DELAY: {redis_first_data_service.enhanced_data_fetcher.YAHOO_REQUEST_DELAY}")
        logger.info(f"   MAX_RETRIES: {redis_first_data_service.enhanced_data_fetcher.MAX_RETRIES}")
        logger.info(f"   RETRY_DELAY: {redis_first_data_service.enhanced_data_fetcher.RETRY_DELAY}")
    
    # Get total tickers
    total_tickers = len(redis_first_data_service.all_tickers)
    logger.info(f"📊 Total tickers to process: {total_tickers}")
    
    # Process each ticker
    for i, ticker in enumerate(redis_first_data_service.all_tickers):
        if i % 100 == 0:
            logger.info(f"🔄 Progress: {i}/{total_tickers} tickers processed...")
        
        try:
            # Check if ticker has both prices and sector data
            if not redis_first_data_service._is_cached(ticker, 'prices') or not redis_first_data_service._is_cached(ticker, 'sector'):
                logger.warning(f"⚠️ {ticker}: Missing data, skipping cleanup")
                continue
            
            # Load cached data for validation
            cached_prices = redis_first_data_service._load_from_cache(ticker, 'prices')
            cached_sector = redis_first_data_service._load_from_cache(ticker, 'sector')
            
            # Validate price data
            if cached_prices is None or not redis_first_data_service._validate_price_data(cached_prices, ticker):
                logger.warning(f"⚠️ {ticker}: Invalid price data, will refresh")
                continue
            
            # Check data freshness (TTL)
            price_key = redis_first_data_service._get_cache_key(ticker, 'prices')
            sector_key = redis_first_data_service._get_cache_key(ticker, 'sector')
            metrics_key = redis_first_data_service._get_cache_key(ticker, 'metrics')
            
            # Check TTL for each data type
            price_ttl = r.ttl(price_key)
            sector_ttl = r.ttl(sector_key)
            metrics_ttl = r.ttl(metrics_key) if r.exists(metrics_key) else -1
            
            # If any data is close to expiring (less than 7 days), refresh it
            if price_ttl < 604800 or sector_ttl < 604800:  # 7 days in seconds
                logger.info(f"🔄 {ticker}: Data expiring soon, refreshing...")
                
                # Delete old data
                if redis_first_data_service.redis_client.exists(price_key):
                    redis_first_data_service.redis_client.delete(price_key)
                if redis_first_data_service.redis_client.exists(sector_key):
                    redis_first_data_service.redis_client.delete(sector_key)
                if redis_first_data_service.redis_client.exists(metrics_key):
                    redis_first_data_service.redis_client.delete(metrics_key)
                
                logger.info(f"✅ {ticker}: Old data cleared, ready for refresh")
            
        except Exception as e:
            logger.error(f"❌ Error processing {ticker}: {e}")
            continue
    
    logger.info("🎉 Redis cleanup and refresh process completed!")
    
    # Show final cache status
    cache_status = redis_first_data_service.get_cache_status()
    logger.info(f"📊 Final cache status: {cache_status}")

if __name__ == "__main__":
    main()
