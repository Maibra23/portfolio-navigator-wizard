#!/usr/bin/env python3
"""
Standalone Script: Clear and Regenerate Strategy Portfolio Buckets
This script directly operates on Redis to clear existing strategy buckets and regenerate new ones
"""

import redis
import logging
from datetime import datetime
import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.redis_first_data_service import redis_first_data_service
from utils.port_analytics import PortfolioAnalytics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_strategy_buckets():
    """Clear all existing strategy portfolio buckets from Redis"""
    try:
        logger.info("🧹 Clearing all strategy portfolio buckets...")
        
        # Get Redis client
        redis_client = redis_first_data_service.redis_client
        
        # Get all strategy bucket keys
        strategy_keys = redis_client.keys("strategy_bucket:*")
        cleared_count = 0
        
        for key in strategy_keys:
            try:
                redis_client.delete(key)
                cleared_count += 1
                logger.info(f"✅ Cleared key: {key}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clear key {key}: {e}")
        
        logger.info(f"✅ Successfully cleared {cleared_count}/{len(strategy_keys)} strategy bucket keys")
        return cleared_count
        
    except Exception as e:
        logger.error(f"❌ Error clearing strategy buckets: {e}")
        return 0

def regenerate_strategy_buckets():
    """Regenerate strategy buckets using the enhanced portfolio system"""
    try:
        logger.info("🚀 Regenerating strategy buckets using enhanced portfolio system...")
        
        # Initialize portfolio analytics
        portfolio_analytics = PortfolioAnalytics()
        
        # Initialize enhanced portfolio generator
        enhanced_generator = EnhancedPortfolioGenerator(redis_first_data_service, portfolio_analytics)
        
        # Generate strategy buckets using enhanced system
        strategy_buckets = enhanced_generator.generate_strategy_portfolio_buckets_enhanced()
        
        if not strategy_buckets:
            logger.error("❌ Failed to generate enhanced strategy portfolios")
            return False
        
        # Store in Redis using enhanced storage
        redis_manager = RedisPortfolioManager(redis_first_data_service.redis_client)
        storage_results = redis_manager.store_enhanced_strategy_buckets(strategy_buckets)
        
        if not storage_results.get('success', False):
            logger.error(f"❌ Failed to store strategy buckets: {storage_results}")
            return False
        
        # Count total buckets stored
        total_buckets = storage_results.get('total_buckets_stored', 0)
        logger.info(f"✅ Successfully regenerated {total_buckets} strategy portfolios using enhanced system")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error regenerating strategy buckets: {e}")
        return False

def main():
    """Main function to clear and regenerate strategy buckets"""
    try:
        logger.info("🚀 Starting Strategy Portfolio Buckets Clear and Regeneration...")
        
        # Step 1: Clear existing strategy buckets
        cleared_count = clear_strategy_buckets()
        
        if cleared_count == 0:
            logger.warning("⚠️ No strategy buckets were cleared")
        else:
            logger.info(f"✅ Cleared {cleared_count} strategy buckets")
        
        # Step 2: Regenerate strategy buckets
        logger.info("🔄 Starting regeneration process...")
        success = regenerate_strategy_buckets()
        
        if success:
            logger.info("🎉 Strategy portfolio buckets successfully cleared and regenerated!")
            
            # Verify the new buckets
            redis_client = redis_first_data_service.redis_client
            new_keys = redis_client.keys("strategy_bucket:*")
            logger.info(f"📊 New strategy buckets in Redis: {len(new_keys)}")
            
            # Show some sample keys
            if new_keys:
                logger.info("📋 Sample new keys:")
                for key in new_keys[:5]:
                    logger.info(f"   - {key}")
            
            return True
        else:
            logger.error("❌ Failed to regenerate strategy buckets")
            return False
            
    except Exception as e:
        logger.error(f"❌ Fatal error in main process: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 SUCCESS: Strategy portfolio buckets cleared and regenerated!")
            sys.exit(0)
        else:
            print("\n❌ FAILED: Strategy portfolio buckets regeneration failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
