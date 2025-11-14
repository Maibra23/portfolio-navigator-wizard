#!/usr/bin/env python3
"""
Clear all strategy portfolios from Redis
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils.redis_first_data_service import RedisFirstDataService
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_strategy_portfolios():
    """Clear all strategy portfolio keys from Redis"""
    try:
        redis_service = RedisFirstDataService()
        if not redis_service or not redis_service.redis_client:
            raise ConnectionError("❌ Cannot connect to Redis")
        
        redis_client = redis_service.redis_client
        
        # Find all strategy portfolio keys
        strategy_keys = redis_client.keys("strategy_portfolios:*")
        
        if not strategy_keys:
            logger.info("✅ No strategy portfolio keys found in Redis")
            return 0
        
        logger.info(f"🗑️  Found {len(strategy_keys)} strategy portfolio keys to delete")
        
        # Delete all keys
        deleted_count = 0
        for key in strategy_keys:
            try:
                redis_client.delete(key)
                deleted_count += 1
                logger.debug(f"  Deleted: {key.decode()}")
            except Exception as e:
                logger.error(f"❌ Error deleting key {key.decode()}: {e}")
        
        logger.info(f"✅ Successfully deleted {deleted_count} strategy portfolio keys")
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ Error clearing strategy portfolios: {e}")
        raise

if __name__ == "__main__":
    logger.info("🗑️  Starting strategy portfolio cleanup...")
    try:
        deleted = clear_strategy_portfolios()
        logger.info(f"✅ Cleanup complete: {deleted} keys deleted")
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        sys.exit(1)

