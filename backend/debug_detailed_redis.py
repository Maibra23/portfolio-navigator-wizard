#!/usr/bin/env python3
"""
Detailed Debug Script for Redis Data Access
Step-by-step investigation of why _get_stocks_from_redis_only returns 0 stocks
"""

import sys
import os
import logging
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.strategy_portfolio_optimizer import StrategyPortfolioOptimizer
from utils.redis_first_data_service import redis_first_data_service
from utils.redis_portfolio_manager import RedisPortfolioManager

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_detailed_redis_access():
    """Detailed step-by-step debugging of Redis data access"""
    logger.info("🔍 Detailed Redis Data Access Debugging")
    logger.info("=" * 60)
    
    try:
        # Create optimizer
        optimizer = StrategyPortfolioOptimizer(
            data_service=redis_first_data_service,
            redis_manager=RedisPortfolioManager(redis_first_data_service.redis_client)
        )
        
        logger.info("✅ StrategyPortfolioOptimizer created successfully")
        
        # Test with just 3 tickers to see exactly what happens
        test_tickers = ['AAPL', 'MSFT', 'GOOGL']
        
        for ticker in test_tickers:
            logger.info(f"\n🔍 STEP-BY-STEP DEBUG for {ticker}:")
            
            # Step 1: Check cache existence
            logger.info(f"   Step 1: Checking cache existence...")
            has_prices = redis_first_data_service._is_cached(ticker, 'prices')
            has_sector = redis_first_data_service._is_cached(ticker, 'sector')
            has_metrics = redis_first_data_service._is_cached(ticker, 'metrics')
            
            logger.info(f"     • has_prices: {has_prices}")
            logger.info(f"     • has_sector: {has_sector}")
            logger.info(f"     • has_metrics: {has_metrics}")
            
            # Step 2: Check the condition that's failing
            logger.info(f"   Step 2: Checking condition (has_prices and has_sector)...")
            condition_result = has_prices and has_sector
            logger.info(f"     • (has_prices and has_sector) = {condition_result}")
            
            if not condition_result:
                logger.warning(f"     • ❌ Condition failed - ticker will be skipped")
                continue
            
            # Step 3: Try to load data
            logger.info(f"   Step 3: Loading cached data...")
            try:
                cached_prices = redis_first_data_service._load_from_cache(ticker, 'prices')
                cached_sector = redis_first_data_service._load_from_cache(ticker, 'sector')
                cached_metrics = redis_first_data_service._load_from_cache(ticker, 'metrics')
                
                logger.info(f"     • cached_prices loaded: {cached_prices is not None}")
                logger.info(f"     • cached_sector loaded: {cached_sector is not None}")
                logger.info(f"     • cached_metrics loaded: {cached_metrics is not None}")
                
                if cached_prices is not None:
                    logger.info(f"     • cached_prices type: {type(cached_prices)}")
                    logger.info(f"     • cached_prices length: {len(cached_prices) if hasattr(cached_prices, '__len__') else 'N/A'}")
                
                if cached_sector is not None:
                    logger.info(f"     • cached_sector type: {type(cached_sector)}")
                    logger.info(f"     • cached_sector keys: {list(cached_sector.keys()) if isinstance(cached_sector, dict) else 'N/A'}")
                
            except Exception as e:
                logger.error(f"     • ❌ Error loading data: {e}")
                continue
            
            # Step 4: Check the second condition
            logger.info(f"   Step 4: Checking second condition (cached_prices and cached_sector)...")
            second_condition = cached_prices is not None and cached_sector is not None
            logger.info(f"     • (cached_prices and cached_sector) = {second_condition}")
            
            if not second_condition:
                logger.warning(f"     • ❌ Second condition failed - ticker will be skipped")
                continue
            
            # Step 5: Try to create stock data
            logger.info(f"   Step 5: Creating stock data...")
            try:
                # Calculate basic metrics from cached data
                if cached_prices is not None and len(cached_prices) > 1:
                    price_changes = cached_prices.pct_change().dropna()
                    volatility = price_changes.std() * (252 ** 0.5)
                    
                    if len(cached_prices) > 12:
                        annual_return = ((cached_prices.iloc[-1] / cached_prices.iloc[-12]) - 1)
                    else:
                        annual_return = ((cached_prices.iloc[-1] / cached_prices.iloc[0]) - 1) * (12 / len(cached_prices))
                else:
                    volatility = 0.2
                    annual_return = 0.1
                
                # Use cached metrics if available
                if cached_metrics:
                    volatility = cached_metrics.get('risk', volatility)
                    annual_return = cached_metrics.get('annualized_return', annual_return)
                
                stock_data = {
                    'symbol': ticker,
                    'ticker': ticker,
                    'company_name': cached_sector.get('companyName', ticker),
                    'sector': cached_sector.get('sector', 'Unknown'),
                    'industry': cached_sector.get('industry', 'Unknown'),
                    'volatility': volatility,
                    'expected_return': annual_return,
                    'current_price': cached_prices.iloc[-1] if not cached_prices.empty else 0,
                    'data_quality': 'cached',
                    'cached': True
                }
                
                logger.info(f"     • ✅ Stock data created successfully!")
                logger.info(f"     •   - Sector: {stock_data['sector']}")
                logger.info(f"     •   - Volatility: {stock_data['volatility']:.4f}")
                logger.info(f"     •   - Expected Return: {stock_data['expected_return']:.4f}")
                logger.info(f"     •   - Current Price: {stock_data['current_price']:.2f}")
                
            except Exception as e:
                logger.error(f"     • ❌ Error creating stock data: {e}")
                continue
        
        # Now test the actual method
        logger.info(f"\n🔍 Testing the actual _get_stocks_from_redis_only method...")
        try:
            stocks = optimizer._get_stocks_from_redis_only()
            logger.info(f"   • Method returned {len(stocks)} stocks")
            
            if len(stocks) > 0:
                logger.info(f"   • First stock: {stocks[0]['symbol']} - {stocks[0]['sector']}")
            else:
                logger.warning("   • No stocks returned - method is still failing")
                
        except Exception as e:
            logger.error(f"   • ❌ Error in method: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in detailed debugging: {e}")
        return False

def main():
    """Run detailed Redis debugging"""
    logger.info("🚀 Starting Detailed Redis Data Debugging")
    logger.info("=" * 60)
    
    success = debug_detailed_redis_access()
    
    if success:
        logger.info("✅ Detailed Redis debugging completed")
    else:
        logger.error("❌ Detailed Redis debugging failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
