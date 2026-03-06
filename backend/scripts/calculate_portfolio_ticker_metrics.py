#!/usr/bin/env python3
"""
Calculate and store metrics for all tickers used in portfolio recommendations.
This ensures all portfolio tickers have complete data (prices + sector + metrics).
"""

import sys
import os
import json
import logging
from typing import Set, Dict
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_first_data_service import RedisFirstDataService
from utils.redis_portfolio_manager import RedisPortfolioManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_metrics_for_ticker(data_service: RedisFirstDataService, ticker: str) -> bool:
    """Calculate and store metrics for a ticker"""
    try:
        # Get price data
        prices = data_service._load_from_cache(ticker, 'prices')
        if prices is None or len(prices) < 2:
            logger.warning(f"⚠️ {ticker}: Insufficient price data")
            return False
        
        # Calculate returns
        returns = prices.pct_change().dropna()
        if len(returns) < 2:
            logger.warning(f"⚠️ {ticker}: Insufficient returns data")
            return False
        
        # Calculate annualized return (compound, consistent with port_analytics and DATA_SOURCES_AND_METHODOLOGY.md)
        mean_return = returns.mean()
        annual_return = (1 + mean_return) ** 12 - 1
        
        # Calculate annualized volatility (risk)
        std_return = returns.std()
        annual_risk = std_return * (12 ** 0.5)
        
        # Calculate max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = drawdowns.min()
        
        # Create metrics dictionary
        metrics = {
            'expected_return': float(annual_return),
            'volatility': float(annual_risk),
            'annualized_return': float(annual_return * 100),  # Percentage
            'risk': float(annual_risk),  # Decimal
            'max_drawdown': float(max_drawdown),
            'data_points': len(prices),
            'last_price': float(prices.iloc[-1]),
            'calculation_date': datetime.now().isoformat(),
            'data_quality': 'good' if len(prices) >= 180 else 'limited'
        }
        
        # Store metrics in Redis
        metrics_key = data_service._get_cache_key(ticker, 'metrics')
        metrics_json = json.dumps(metrics).encode()
        # Use same TTL as prices (28 days)
        data_service.redis_client.setex(metrics_key, 28 * 24 * 3600, metrics_json)
        
        logger.info(f"✅ {ticker}: Calculated metrics (return={annual_return:.4f}, risk={annual_risk:.4f})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error calculating metrics for {ticker}: {e}")
        return False

def get_all_portfolio_tickers(redis_manager: RedisPortfolioManager) -> Set[str]:
    """Get all unique tickers from all portfolio recommendations"""
    risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
    all_tickers = set()
    
    for risk_profile in risk_profiles:
        try:
            portfolios = redis_manager.get_portfolio_recommendations(risk_profile, count=12)
            for portfolio in portfolios:
                allocations = portfolio.get('allocations', [])
                for alloc in allocations:
                    symbol = alloc.get('symbol', '').upper().strip()
                    if symbol:
                        all_tickers.add(symbol)
        except Exception as e:
            logger.error(f"❌ Error getting tickers for {risk_profile}: {e}")
    
    return all_tickers

def main():
    """Main function"""
    try:
        # Initialize services
        logger.info("🚀 Initializing services...")
        data_service = RedisFirstDataService()
        redis_manager = RedisPortfolioManager(data_service.redis_client)
        
        if not data_service.redis_client:
            logger.error("❌ Redis client not available")
            return 1
        
        # Get all portfolio tickers
        logger.info("\n📊 Collecting tickers from portfolio recommendations...")
        all_tickers = get_all_portfolio_tickers(redis_manager)
        logger.info(f"📈 Found {len(all_tickers)} unique tickers across all portfolios")
        
        # Calculate metrics for each ticker
        logger.info("\n📊 Calculating metrics for portfolio tickers...")
        success_count = 0
        fail_count = 0
        
        for ticker in sorted(all_tickers):
            if calculate_metrics_for_ticker(data_service, ticker):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"\n✅ Successfully calculated metrics for {success_count} tickers")
        if fail_count > 0:
            logger.warning(f"⚠️ Failed to calculate metrics for {fail_count} tickers")
        
        logger.info("\n✅ Metrics calculation complete!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error in metrics calculation script: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

