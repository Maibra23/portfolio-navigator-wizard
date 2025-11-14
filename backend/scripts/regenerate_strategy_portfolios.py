#!/usr/bin/env python3
"""
Regenerate all strategy portfolios with the refactored logic
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils.redis_first_data_service import RedisFirstDataService
    from utils.strategy_portfolio_optimizer import StrategyPortfolioOptimizer
    from utils.redis_portfolio_manager import RedisPortfolioManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def regenerate_all_strategy_portfolios():
    """Regenerate all strategy portfolios with refactored logic"""
    try:
        # Initialize services
        redis_service = RedisFirstDataService()
        if not redis_service or not redis_service.redis_client:
            raise ConnectionError("❌ Cannot connect to Redis")
        
        redis_manager = RedisPortfolioManager(redis_service.redis_client)
        
        # Initialize strategy optimizer
        optimizer = StrategyPortfolioOptimizer(redis_service, redis_manager)
        
        logger.info("🚀 Starting regeneration of all strategy portfolios...")
        logger.info("📋 This will generate:")
        logger.info("  - 3 strategies × 6 pure portfolios = 18 pure portfolios")
        logger.info("  - 3 strategies × 5 risk profiles × 6 portfolios = 90 personalized portfolios")
        logger.info("  - Total: 108 portfolios")
        logger.info("")
        
        # Clear existing strategy portfolios first
        logger.info("🗑️  Clearing existing strategy portfolios from Redis...")
        clear_result = optimizer.clear_all_strategy_caches()
        if clear_result.get('success'):
            logger.info(f"✅ Cleared {clear_result.get('deleted_count', 0)} existing strategy portfolio keys")
        else:
            logger.warning(f"⚠️  Failed to clear existing portfolios: {clear_result.get('error', 'Unknown error')}")
        logger.info("")
        
        # Pre-generate all strategy portfolios
        summary = optimizer.pre_generate_all_strategy_portfolios()
        
        if summary.get('success'):
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ REGENERATION COMPLETE!")
            logger.info("=" * 60)
            logger.info(f"Total Portfolios Generated: {summary['total_portfolios_generated']}")
            logger.info(f"Total Portfolios Stored: {summary['total_portfolios_stored']}")
            logger.info(f"Total Time: {summary['total_elapsed_seconds']:.1f}s")
            
            # Show per-strategy breakdown
            logger.info("")
            logger.info("Per-Strategy Breakdown:")
            for strategy, result in summary['strategies'].items():
                logger.info(f"  {strategy}:")
                logger.info(f"    Pure: {result['pure_count']} portfolios")
                logger.info(f"    Personalized: {result['personalized_count']} portfolios")
                logger.info(f"    Time: {result.get('elapsed_seconds', 0):.1f}s")
            
            return True
        else:
            logger.error("❌ Regeneration failed")
            if summary.get('errors'):
                for error in summary['errors']:
                    logger.error(f"  Error: {error}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error regenerating strategy portfolios: {e}")
        raise

if __name__ == "__main__":
    logger.info("🔄 Starting strategy portfolio regeneration...")
    try:
        success = regenerate_all_strategy_portfolios()
        if success:
            logger.info("✅ Regeneration successful!")
            sys.exit(0)
        else:
            logger.error("❌ Regeneration failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Regeneration failed: {e}")
        sys.exit(1)

