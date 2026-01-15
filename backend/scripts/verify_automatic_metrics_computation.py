#!/usr/bin/env python3
"""
Verify that metrics are automatically computed when fetching ticker data

This script:
1. Tests fetching a ticker that doesn't exist in cache
2. Verifies that metrics are automatically computed and saved
3. Confirms the metrics format matches system expectations
"""

import sys
import os
import logging
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.enhanced_data_fetcher import EnhancedDataFetcher
from utils.redis_first_data_service import RedisFirstDataService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_metrics_format(metrics: dict) -> tuple[bool, list[str]]:
    """Verify metrics have the required fields in standard format"""
    required_fields = ['expected_return', 'volatility']
    optional_fields = ['annualized_return', 'risk', 'max_drawdown', 'sharpe_ratio']
    
    missing = []
    for field in required_fields:
        if field not in metrics:
            missing.append(field)
    
    issues = []
    if missing:
        issues.append(f"Missing required fields: {', '.join(missing)}")
    
    # Check if values are valid numbers
    for field in required_fields:
        if field in metrics:
            value = metrics[field]
            if value is None:
                issues.append(f"{field} is None")
            elif not isinstance(value, (int, float)):
                issues.append(f"{field} is not a number: {type(value)}")
    
    return len(issues) == 0, issues

def test_automatic_metrics_computation():
    """Test that metrics are automatically computed when fetching"""
    try:
        logger.info("=" * 80)
        logger.info("🧪 Testing Automatic Metrics Computation")
        logger.info("=" * 80)
        
        # Initialize services
        logger.info("\n📋 Step 1: Initializing services...")
        data_service = RedisFirstDataService()
        data_fetcher = EnhancedDataFetcher()
        
        if not data_service.redis_client:
            logger.error("❌ Redis client not available")
            return False
        
        # Step 2: Find a test ticker (use one that's likely to be fetchable)
        logger.info("\n📋 Step 2: Selecting test ticker...")
        test_ticker = "AAPL"  # Apple - should be fetchable
        
        # Check if ticker is in master list
        if test_ticker.upper() not in [t.upper() for t in data_fetcher.all_tickers]:
            logger.warning(f"⚠️  {test_ticker} not in master list, trying anyway...")
            data_fetcher._allow_out_of_master = True
        
        # Step 3: Remove existing data to force fresh fetch
        logger.info(f"\n📋 Step 3: Clearing existing data for {test_ticker} to force fresh fetch...")
        price_key = data_service._get_cache_key(test_ticker, 'prices')
        sector_key = data_service._get_cache_key(test_ticker, 'sector')
        metrics_key = data_service._get_cache_key(test_ticker, 'metrics')
        
        data_service.redis_client.delete(price_key)
        data_service.redis_client.delete(sector_key)
        data_service.redis_client.delete(metrics_key)
        logger.info(f"✅ Cleared existing cache for {test_ticker}")
        
        # Step 4: Fetch ticker data (this should trigger automatic metrics computation)
        logger.info(f"\n📋 Step 4: Fetching {test_ticker} data (should auto-compute metrics)...")
        
        # Temporarily disable manual regeneration requirement
        original_manual_regen = os.environ.get('MANUAL_REGENERATION_REQUIRED', 'true')
        os.environ['MANUAL_REGENERATION_REQUIRED'] = 'false'
        
        try:
            ticker_data = data_fetcher.get_ticker_data(test_ticker)
            
            if not ticker_data:
                logger.error(f"❌ Failed to fetch data for {test_ticker}")
                return False
            
            logger.info(f"✅ Successfully fetched data for {test_ticker}")
            
            # Wait a moment for async operations
            time.sleep(1)
            
        finally:
            # Restore original setting
            os.environ['MANUAL_REGENERATION_REQUIRED'] = original_manual_regen
            if hasattr(data_fetcher, '_allow_out_of_master'):
                delattr(data_fetcher, '_allow_out_of_master')
        
        # Step 5: Verify metrics were automatically computed
        logger.info(f"\n📋 Step 5: Verifying metrics were automatically computed...")
        
        metrics = data_service._load_from_cache(test_ticker, 'metrics')
        
        if not metrics:
            logger.error(f"❌ Metrics were NOT automatically computed for {test_ticker}")
            logger.error("   This indicates the automatic metrics computation is not working")
            return False
        
        logger.info(f"✅ Metrics were automatically computed for {test_ticker}")
        
        # Step 6: Verify metrics format
        logger.info(f"\n📋 Step 6: Verifying metrics format...")
        is_valid, issues = verify_metrics_format(metrics)
        
        if not is_valid:
            logger.error(f"❌ Metrics format is invalid:")
            for issue in issues:
                logger.error(f"   - {issue}")
            logger.info(f"\n   Metrics content: {metrics}")
            return False
        
        logger.info(f"✅ Metrics format is valid")
        logger.info(f"   Expected Return: {metrics.get('expected_return', 'N/A'):.4f}")
        logger.info(f"   Volatility: {metrics.get('volatility', 'N/A'):.4f}")
        logger.info(f"   Data Points: {metrics.get('data_points', 'N/A')}")
        
        # Step 7: Summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ VERIFICATION SUMMARY")
        logger.info("=" * 80)
        logger.info("✅ Automatic metrics computation: WORKING")
        logger.info("✅ Metrics format: VALID")
        logger.info("✅ System is configured correctly")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in test: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_automatic_metrics_computation()
    sys.exit(0 if success else 1)

