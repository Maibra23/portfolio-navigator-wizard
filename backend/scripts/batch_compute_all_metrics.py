#!/usr/bin/env python3
"""
Batch compute metrics for all tickers

This script:
1. Identifies all tickers with prices+sector but missing or expired metrics
2. Computes metrics in batches with progress tracking
3. Provides summary of results
"""

import sys
import os
import logging
from typing import List, Dict
from tqdm import tqdm
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_first_data_service import RedisFirstDataService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_metrics_for_ticker(data_service: RedisFirstDataService, ticker: str) -> Dict[str, any]:
    """Calculate and store metrics for a ticker - returns result dict"""
    result = {
        'ticker': ticker,
        'success': False,
        'error': None,
        'metrics': None
    }
    
    try:
        import pandas as pd
        import numpy as np
        import json
        
        # Get price data from cache
        prices = data_service._load_from_cache(ticker, 'prices')
        if prices is None or len(prices) < 2:
            result['error'] = "Insufficient price data"
            return result
        
        # Calculate returns
        returns = prices.pct_change().dropna()
        if len(returns) < 2:
            result['error'] = "Insufficient returns data"
            return result
        
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
        
        result['success'] = True
        result['metrics'] = metrics
        return result
        
    except Exception as e:
        result['error'] = str(e)
        return result

def get_tickers_needing_metrics(data_service: RedisFirstDataService) -> List[str]:
    """Get all tickers that need metrics computed"""
    if not data_service.redis_client:
        return []
    
    try:
        # Get all tickers with both prices and sector
        tickers_with_data = data_service.list_cached_tickers()
        
        # Check which ones are missing metrics
        tickers_needing_metrics = []
        
        for ticker in tickers_with_data:
            metrics_key = data_service._get_cache_key(ticker, 'metrics')
            if not data_service.redis_client.exists(metrics_key):
                tickers_needing_metrics.append(ticker)
        
        return sorted(tickers_needing_metrics)
    
    except Exception as e:
        logger.error(f"Error getting tickers needing metrics: {e}")
        return []

def main():
    """Main function"""
    try:
        logger.info("=" * 80)
        logger.info("🚀 Batch Metrics Computation System")
        logger.info("=" * 80)
        
        # Initialize services
        logger.info("\n📋 Step 1: Initializing services...")
        data_service = RedisFirstDataService()
        
        if not data_service.redis_client:
            logger.error("❌ Redis client not available")
            return
        
        # Step 2: Get tickers needing metrics
        logger.info("\n📋 Step 2: Identifying tickers needing metrics...")
        tickers_needing_metrics = get_tickers_needing_metrics(data_service)
        
        if not tickers_needing_metrics:
            logger.info("✅ All tickers already have metrics! No computation needed.")
            return
        
        logger.info(f"✅ Found {len(tickers_needing_metrics)} tickers needing metrics computation")
        
        # Step 3: Compute metrics in batches
        logger.info(f"\n📋 Step 3: Computing metrics for {len(tickers_needing_metrics)} tickers...")
        
        successful = 0
        failed = 0
        results = []
        
        for ticker in tqdm(tickers_needing_metrics, desc="Computing metrics"):
            result = calculate_metrics_for_ticker(data_service, ticker)
            results.append(result)
            
            if result['success']:
                successful += 1
                logger.debug(f"  ✅ {ticker}: Metrics computed")
            else:
                failed += 1
                logger.warning(f"  ⚠️  {ticker}: {result.get('error', 'Unknown error')}")
        
        # Step 4: Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 BATCH METRICS COMPUTATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tickers Processed: {len(tickers_needing_metrics)}")
        logger.info(f"✅ Successful: {successful}")
        logger.info(f"❌ Failed: {failed}")
        
        if len(tickers_needing_metrics) > 0:
            logger.info(f"Success Rate: {(successful/len(tickers_needing_metrics)*100):.1f}%")
        
        if failed > 0:
            logger.info("\n⚠️  Failed Tickers:")
            for result in results:
                if not result['success']:
                    logger.info(f"   - {result['ticker']}: {result.get('error', 'Unknown error')}")
        
        # Verify final state
        logger.info("\n📋 Step 4: Verifying final metrics coverage...")
        final_tickers_needing = get_tickers_needing_metrics(data_service)
        total_tickers = len(data_service.list_cached_tickers())
        metrics_coverage = ((total_tickers - len(final_tickers_needing)) / total_tickers * 100) if total_tickers > 0 else 0
        
        logger.info(f"Final Metrics Coverage: {total_tickers - len(final_tickers_needing)}/{total_tickers} ({metrics_coverage:.1f}%)")
        
        if len(final_tickers_needing) == 0:
            logger.info("✅ All tickers now have metrics!")
        else:
            logger.warning(f"⚠️  Still missing metrics for {len(final_tickers_needing)} tickers")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Batch metrics computation completed")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Error in main process: {e}", exc_info=True)

if __name__ == "__main__":
    main()

