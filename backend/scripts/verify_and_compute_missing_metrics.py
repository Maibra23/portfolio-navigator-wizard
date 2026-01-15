#!/usr/bin/env python3
"""
Verify metrics status and compute missing metrics

This script:
1. Verifies the actual state of metrics in Redis
2. Identifies tickers with missing metrics
3. Computes metrics for missing tickers only
"""

import sys
import os
import logging
from typing import List, Dict
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_first_data_service import RedisFirstDataService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_redis_state(data_service: RedisFirstDataService) -> Dict[str, int]:
    """Verify actual state of Redis keys"""
    if not data_service.redis_client:
        return {}
    
    try:
        price_keys = data_service.redis_client.keys("ticker_data:prices:*")
        sector_keys = data_service.redis_client.keys("ticker_data:sector:*")
        metrics_keys = data_service.redis_client.keys("ticker_data:metrics:*")
        
        # Get joined tickers (have both prices and sector)
        tickers_with_both = set()
        price_tickers = set()
        sector_tickers = set()
        
        for key in price_keys:
            if isinstance(key, bytes):
                key = key.decode()
            ticker = key.replace("ticker_data:prices:", "")
            price_tickers.add(ticker)
        
        for key in sector_keys:
            if isinstance(key, bytes):
                key = key.decode()
            ticker = key.replace("ticker_data:sector:", "")
            sector_tickers.add(ticker)
            if ticker in price_tickers:
                tickers_with_both.add(ticker)
        
        metrics_tickers = set()
        for key in metrics_keys:
            if isinstance(key, bytes):
                key = key.decode()
            ticker = key.replace("ticker_data:metrics:", "")
            metrics_tickers.add(ticker)
        
        return {
            'joined_tickers': len(tickers_with_both),
            'prices_keys': len(price_keys),
            'sector_keys': len(sector_keys),
            'metrics_keys': len(metrics_keys),
            'tickers_with_both': tickers_with_both,
            'tickers_with_metrics': metrics_tickers
        }
    except Exception as e:
        logger.error(f"Error verifying Redis state: {e}")
        return {}

def get_tickers_missing_metrics(data_service: RedisFirstDataService) -> List[str]:
    """Get list of tickers that have prices+sector but no metrics"""
    state = verify_redis_state(data_service)
    
    if not state:
        return []
    
    tickers_with_both = state['tickers_with_both']
    tickers_with_metrics = state['tickers_with_metrics']
    
    # Find tickers with both prices and sector but no metrics
    missing_metrics = []
    for ticker in tickers_with_both:
        if ticker not in tickers_with_metrics:
            missing_metrics.append(ticker)
    
    return sorted(missing_metrics)

def compute_metrics_for_ticker(data_service: RedisFirstDataService, ticker: str) -> bool:
    """Compute and cache metrics for a ticker"""
    try:
        import pandas as pd
        import numpy as np
        import json
        from datetime import datetime
        
        # Get price data from cache
        prices = data_service._load_from_cache(ticker, 'prices')
        if prices is None or len(prices) < 2:
            logger.warning(f"  ⚠️  {ticker}: Insufficient price data")
            return False
        
        # Calculate returns
        returns = prices.pct_change().dropna()
        if len(returns) < 2:
            logger.warning(f"  ⚠️  {ticker}: Insufficient returns data")
            return False
        
        # Calculate annualized return (assuming monthly data)
        mean_return = returns.mean()
        annual_return = mean_return * 12
        
        # Calculate annualized volatility (risk)
        std_return = returns.std()
        annual_risk = std_return * (12 ** 0.5)
        
        # Calculate max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = drawdowns.min()
        
        # Calculate sharpe ratio (assuming risk-free rate of 0 for simplicity)
        sharpe_ratio = (annual_return / annual_risk) if annual_risk > 0 else None
        
        # Calculate skewness and kurtosis
        skewness = returns.skew()
        kurtosis = returns.kurtosis()
        
        # Create metrics dictionary
        metrics = {
            'expected_return': float(annual_return),
            'volatility': float(annual_risk),
            'annualized_return': float(annual_return * 100),  # Percentage
            'risk': float(annual_risk),  # Decimal
            'max_drawdown': float(max_drawdown) if not np.isnan(max_drawdown) else None,
            'sharpe_ratio': float(sharpe_ratio) if sharpe_ratio is not None and not np.isnan(sharpe_ratio) else None,
            'skewness': float(skewness) if not np.isnan(skewness) else None,
            'kurtosis': float(kurtosis) if not np.isnan(kurtosis) else None,
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
        
        logger.info(f"  ✅ {ticker}: Calculated metrics (return={annual_return:.4f}, risk={annual_risk:.4f})")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ {ticker}: Error computing metrics - {e}")
        return False

def main():
    """Main function"""
    try:
        logger.info("=" * 80)
        logger.info("🔍 Verifying Redis state and computing missing metrics")
        logger.info("=" * 80)
        
        # Initialize services
        logger.info("\n📋 Step 1: Initializing services...")
        data_service = RedisFirstDataService()
        
        if not data_service.redis_client:
            logger.error("❌ Redis client not available")
            return
        
        # Step 2: Verify Redis state
        logger.info("\n📋 Step 2: Verifying Redis state...")
        state = verify_redis_state(data_service)
        
        if not state:
            logger.error("❌ Could not verify Redis state")
            return
        
        logger.info(f"📊 Redis State Verification:")
        logger.info(f"   Joined tickers (prices + sector): {state['joined_tickers']}")
        logger.info(f"   Prices keys: {state['prices_keys']}")
        logger.info(f"   Sector keys: {state['sector_keys']}")
        logger.info(f"   Metrics keys: {state['metrics_keys']}")
        
        # Compare with expected
        expected_metrics = state['joined_tickers'] - (state['joined_tickers'] - state['metrics_keys'])
        missing_count = state['joined_tickers'] - state['metrics_keys']
        
        logger.info(f"\n📊 Metrics Status:")
        logger.info(f"   Tickers with complete data: {state['joined_tickers']}")
        logger.info(f"   Tickers with metrics: {state['metrics_keys']}")
        logger.info(f"   Missing metrics: {missing_count}")
        
        if missing_count == 0:
            logger.info("✅ All tickers have metrics! No computation needed.")
            return
        
        # Step 3: Get tickers missing metrics
        logger.info(f"\n📋 Step 3: Identifying tickers with missing metrics...")
        missing_metrics_tickers = get_tickers_missing_metrics(data_service)
        
        if not missing_metrics_tickers:
            logger.info("✅ No tickers found with missing metrics")
            return
        
        logger.info(f"✅ Found {len(missing_metrics_tickers)} tickers with missing metrics")
        
        # Step 4: Compute metrics for missing tickers
        logger.info(f"\n📋 Step 4: Computing metrics for {len(missing_metrics_tickers)} tickers...")
        
        successful = 0
        failed = 0
        
        for ticker in tqdm(missing_metrics_tickers, desc="Computing metrics"):
            if compute_metrics_for_ticker(data_service, ticker):
                successful += 1
            else:
                failed += 1
        
        # Step 5: Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 METRICS COMPUTATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Tickers Processed: {len(missing_metrics_tickers)}")
        logger.info(f"✅ Successful: {successful}")
        logger.info(f"❌ Failed: {failed}")
        
        if successful > 0:
            logger.info(f"Success Rate: {(successful/len(missing_metrics_tickers)*100):.1f}%")
        
        # Verify final state
        logger.info("\n📋 Step 5: Verifying final state...")
        final_state = verify_redis_state(data_service)
        if final_state:
            final_missing = final_state['joined_tickers'] - final_state['metrics_keys']
            logger.info(f"Final Metrics Coverage: {final_state['metrics_keys']}/{final_state['joined_tickers']} ({(final_state['metrics_keys']/final_state['joined_tickers']*100):.1f}%)")
            if final_missing > 0:
                logger.warning(f"⚠️  Still missing metrics for {final_missing} tickers")
            else:
                logger.info("✅ All tickers now have metrics!")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Process completed")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Error in main process: {e}", exc_info=True)

if __name__ == "__main__":
    main()

