#!/usr/bin/env python3
"""
Debug Script for StrategyPortfolioOptimizer
Investigates why the optimizer returns 0 stocks when Redis data is available
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_strategy_optimizer():
    """Debug the StrategyPortfolioOptimizer to see why it returns 0 stocks"""
    logger.info("🔍 Debugging StrategyPortfolioOptimizer")
    logger.info("=" * 60)
    
    try:
        # Create optimizer
        optimizer = StrategyPortfolioOptimizer(
            data_service=redis_first_data_service,
            redis_manager=RedisPortfolioManager(redis_first_data_service.redis_client)
        )
        
        logger.info("✅ StrategyPortfolioOptimizer created successfully")
        
        # Check Redis data sufficiency
        logger.info("\n📊 Checking Redis data sufficiency...")
        data_status = optimizer.check_redis_data_sufficiency()
        
        for key, value in data_status.items():
            logger.info(f"   • {key}: {value}")
        
        # Test individual ticker access
        logger.info("\n🔍 Testing individual ticker access...")
        sample_tickers = ['AAPL', 'MSFT', 'GOOGL']
        
        for ticker in sample_tickers:
            logger.info(f"\n   • Checking {ticker}:")
            
            # Check cache existence
            has_prices = redis_first_data_service._is_cached(ticker, 'prices')
            has_sector = redis_first_data_service._is_cached(ticker, 'sector')
            has_metrics = redis_first_data_service._is_cached(ticker, 'metrics')
            
            logger.info(f"     - Prices cached: {has_prices}")
            logger.info(f"     - Sector cached: {has_sector}")
            logger.info(f"     - Metrics cached: {has_metrics}")
            
            # Try to load data
            if has_prices and has_sector:
                try:
                    cached_prices = redis_first_data_service._load_from_cache(ticker, 'prices')
                    cached_sector = redis_first_data_service._load_from_cache(ticker, 'sector')
                    cached_metrics = redis_first_data_service._load_from_cache(ticker, 'metrics')
                    
                    if cached_prices is not None and cached_sector is not None:
                        # Calculate basic metrics from cached data
                        if len(cached_prices) > 1:
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
                        
                        logger.info(f"     - Stock data created successfully")
                        logger.info(f"     - Sector: {stock_data['sector']}")
                        logger.info(f"     - Volatility: {stock_data['volatility']:.4f}")
                        logger.info(f"     - Expected Return: {stock_data['expected_return']:.4f}")
                        logger.info(f"     - Current Price: {stock_data['current_price']:.2f}")
                        
                    else:
                        logger.warning(f"     - Failed to load cached data")
                        
                except Exception as e:
                    logger.error(f"     - Error processing {ticker}: {e}")
        
        # Test the optimizer's stock loading method
        logger.info("\n🔍 Testing optimizer's _get_stocks_from_redis_only method...")
        try:
            stocks = optimizer._get_stocks_from_redis_only()
            logger.info(f"   • Method returned {len(stocks)} stocks")
            
            if len(stocks) > 0:
                logger.info(f"   • First stock: {stocks[0]['symbol']} - {stocks[0]['sector']}")
                logger.info(f"   • Sample stocks: {[s['symbol'] for s in stocks[:5]]}")
            else:
                logger.warning("   • No stocks returned - investigating further...")
                
                # Check what's happening in the method
                all_tickers = redis_first_data_service.all_tickers
                logger.info(f"   • Total tickers available: {len(all_tickers)}")
                
                # Check first few tickers
                for i, ticker in enumerate(all_tickers[:5]):
                    logger.info(f"     - Ticker {i+1}: {ticker}")
                    
                    has_prices = redis_first_data_service._is_cached(ticker, 'prices')
                    has_sector = redis_first_data_service._is_cached(ticker, 'sector')
                    
                    logger.info(f"       • Has prices: {has_prices}")
                    logger.info(f"       • Has sector: {has_sector}")
                    
                    if has_prices and has_sector:
                        try:
                            cached_prices = redis_first_data_service._load_from_cache(ticker, 'prices')
                            cached_sector = redis_first_data_service._load_from_cache(ticker, 'sector')
                            
                            if cached_prices is not None and cached_sector is not None:
                                logger.info(f"       • Data loaded successfully")
                            else:
                                logger.warning(f"       • Data loading failed")
                        except Exception as e:
                            logger.error(f"       • Error loading data: {e}")
                    else:
                        logger.warning(f"       • Missing required data")
                
        except Exception as e:
            logger.error(f"   • Error in _get_stocks_from_redis_only: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error debugging strategy optimizer: {e}")
        return False

def main():
    """Run strategy optimizer debugging"""
    logger.info("🚀 Starting StrategyPortfolioOptimizer Debugging")
    logger.info("=" * 60)
    
    success = debug_strategy_optimizer()
    
    if success:
        logger.info("✅ Strategy optimizer debugging completed")
    else:
        logger.error("❌ Strategy optimizer debugging failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
