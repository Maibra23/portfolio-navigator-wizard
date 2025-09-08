#!/usr/bin/env python3
"""
Debug Script for Redis Data Access
Investigates why sufficiency check shows 92.2% coverage but individual access returns 0 stocks
"""

import sys
import os
import logging
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.redis_first_data_service import redis_first_data_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_redis_data_access():
    """Debug Redis data access to understand the discrepancy"""
    logger.info("🔍 Debugging Redis Data Access")
    logger.info("=" * 60)
    
    try:
        # Check Redis connection
        logger.info("📊 Redis Connection Status:")
        logger.info(f"   • Redis client available: {redis_first_data_service.redis_client is not None}")
        logger.info(f"   • Total tickers: {len(redis_first_data_service.all_tickers)}")
        
        # Check a few specific tickers
        sample_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
        
        for ticker in sample_tickers:
            logger.info(f"\n🔍 Checking ticker: {ticker}")
            
            # Check cache existence
            has_prices = redis_first_data_service._is_cached(ticker, 'prices')
            has_sector = redis_first_data_service._is_cached(ticker, 'sector')
            has_metrics = redis_first_data_service._is_cached(ticker, 'metrics')
            
            logger.info(f"   • Prices cached: {has_prices}")
            logger.info(f"   • Sector cached: {has_sector}")
            logger.info(f"   • Metrics cached: {has_metrics}")
            
            # Try to load data
            if has_prices:
                try:
                    cached_prices = redis_first_data_service._load_from_cache(ticker, 'prices')
                    logger.info(f"   • Prices loaded: {cached_prices is not None}")
                    if cached_prices is not None:
                        logger.info(f"   • Price data points: {len(cached_prices)}")
                        logger.info(f"   • Latest price: {cached_prices.iloc[-1] if not cached_prices.empty else 'N/A'}")
                except Exception as e:
                    logger.error(f"   • Error loading prices: {e}")
            
            if has_sector:
                try:
                    cached_sector = redis_first_data_service._load_from_cache(ticker, 'sector')
                    logger.info(f"   • Sector loaded: {cached_sector is not None}")
                    if cached_sector is not None:
                        logger.info(f"   • Sector: {cached_sector.get('sector', 'N/A')}")
                        logger.info(f"   • Company: {cached_sector.get('companyName', 'N/A')}")
                except Exception as e:
                    logger.error(f"   • Error loading sector: {e}")
            
            if has_metrics:
                try:
                    cached_metrics = redis_first_data_service._load_from_cache(ticker, 'metrics')
                    logger.info(f"   • Metrics loaded: {cached_metrics is not None}")
                    if cached_metrics is not None:
                        logger.info(f"   • Risk: {cached_metrics.get('risk', 'N/A')}")
                        logger.info(f"   • Return: {cached_metrics.get('annualized_return', 'N/A')}")
                except Exception as e:
                    logger.error(f"   • Error loading metrics: {e}")
        
        # Check overall cache statistics
        logger.info(f"\n📊 Overall Cache Statistics:")
        total_tickers = len(redis_first_data_service.all_tickers)
        prices_cached = sum(1 for ticker in redis_first_data_service.all_tickers[:20] if redis_first_data_service._is_cached(ticker, 'prices'))
        sectors_cached = sum(1 for ticker in redis_first_data_service.all_tickers[:20] if redis_first_data_service._is_cached(ticker, 'sector'))
        metrics_cached = sum(1 for ticker in redis_first_data_service.all_tickers[:20] if redis_first_data_service._is_cached(ticker, 'metrics'))
        
        logger.info(f"   • Sample tickers checked: 20")
        logger.info(f"   • Prices cached: {prices_cached}/20 ({prices_cached/20*100:.1f}%)")
        logger.info(f"   • Sectors cached: {sectors_cached}/20 ({sectors_cached/20*100:.1f}%)")
        logger.info(f"   • Metrics cached: {metrics_cached}/20 ({metrics_cached/20*100:.1f}%)")
        
        # Check Redis keys directly
        logger.info(f"\n🔍 Redis Key Investigation:")
        redis_client = redis_first_data_service.redis_client
        
        # Check a few specific keys
        for ticker in sample_tickers:
            price_key = redis_first_data_service._get_cache_key(ticker, 'prices')
            sector_key = redis_first_data_service._get_cache_key(ticker, 'sector')
            metrics_key = redis_first_data_service._get_cache_key(ticker, 'metrics')
            
            logger.info(f"\n   • {ticker}:")
            logger.info(f"     - Price key: {price_key}")
            logger.info(f"     - Price exists: {redis_client.exists(price_key)}")
            logger.info(f"     - Sector key: {sector_key}")
            logger.info(f"     - Sector exists: {redis_client.exists(sector_key)}")
            logger.info(f"     - Metrics key: {metrics_key}")
            logger.info(f"     - Metrics exists: {redis_client.exists(metrics_key)}")
            
            # Check TTL
            if redis_client.exists(price_key):
                ttl = redis_client.ttl(price_key)
                logger.info(f"     - Price TTL: {ttl} seconds ({ttl/86400:.1f} days)")
            
            if redis_client.exists(sector_key):
                ttl = redis_client.ttl(sector_key)
                logger.info(f"     - Sector TTL: {ttl} seconds ({ttl/86400:.1f} days)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error debugging Redis data: {e}")
        return False

def main():
    """Run Redis data debugging"""
    logger.info("🚀 Starting Redis Data Debugging")
    logger.info("=" * 60)
    
    success = debug_redis_data_access()
    
    if success:
        logger.info("✅ Redis data debugging completed")
    else:
        logger.error("❌ Redis data debugging failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
