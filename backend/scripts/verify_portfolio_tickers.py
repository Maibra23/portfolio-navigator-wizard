#!/usr/bin/env python3
"""
Verify and fetch missing tickers from cached portfolios

This script:
1. Checks all tickers in cached portfolios
2. Verifies if they exist in Redis
3. Fetches missing tickers using the data fetching system
4. Reports status
"""

import sys
import os
import json
import logging
from typing import List, Dict, Set
from math import isnan, isfinite

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_first_data_service import RedisFirstDataService
from utils.redis_portfolio_manager import RedisPortfolioManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_all_portfolio_tickers(redis_manager: RedisPortfolioManager) -> Dict[str, Set[str]]:
    """Get all tickers from all cached portfolios"""
    risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
    all_tickers_by_profile: Dict[str, Set[str]] = {}
    
    for risk_profile in risk_profiles:
        tickers = set()
        try:
            portfolios = redis_manager.get_portfolio_recommendations(risk_profile, count=12)
            for portfolio in portfolios:
                allocations = portfolio.get('allocations', [])
                for alloc in allocations:
                    symbol = alloc.get('symbol', '').upper().strip()
                    if symbol:
                        tickers.add(symbol)
            
            all_tickers_by_profile[risk_profile] = tickers
            logger.info(f"✅ {risk_profile}: Found {len(tickers)} unique tickers in {len(portfolios)} portfolios")
        except Exception as e:
            logger.error(f"❌ Error getting tickers for {risk_profile}: {e}")
            all_tickers_by_profile[risk_profile] = set()
    
    return all_tickers_by_profile

def check_tickers_in_redis(data_service: RedisFirstDataService, tickers: Set[str]) -> Dict[str, Dict[str, bool]]:
    """Check which tickers exist in Redis with complete data (prices, sector, metrics)"""
    ticker_status = {}
    
    for ticker in tickers:
        try:
            # Check if price data exists
            price_key = data_service._get_cache_key(ticker, 'prices')
            has_prices = data_service.redis_client.exists(price_key) > 0
            
            # Check if sector data exists
            sector_key = data_service._get_cache_key(ticker, 'sector')
            has_sector = data_service.redis_client.exists(sector_key) > 0
            
            # Check if metrics data exists
            metrics_key = data_service._get_cache_key(ticker, 'metrics')
            has_metrics = data_service.redis_client.exists(metrics_key) > 0
            
            # Check if metrics are valid (visualization uses risk + annualized_return/expected_return)
            metrics_valid = False
            if has_metrics:
                try:
                    metrics_data = data_service._load_from_cache(ticker, 'metrics')
                    if metrics_data and isinstance(metrics_data, dict):
                        ret = metrics_data.get('expected_return') or metrics_data.get('annualized_return') or metrics_data.get('annual_return')
                        risk = metrics_data.get('volatility') or metrics_data.get('risk') or metrics_data.get('annualized_risk')
                        metrics_valid = (
                            ret is not None and risk is not None and
                            isinstance(ret, (int, float)) and isinstance(risk, (int, float)) and
                            not (isinstance(ret, float) and (isnan(ret) or not isfinite(ret))) and
                            not (isinstance(risk, float) and (isnan(risk) or not isfinite(risk)))
                        )
                except Exception as e:
                    logger.debug(f"Error validating metrics for {ticker}: {e}")
            
            ticker_status[ticker] = {
                'has_prices': has_prices,
                'has_sector': has_sector,
                'has_metrics': has_metrics,
                'metrics_valid': metrics_valid,
                'complete': has_prices and has_sector and has_metrics and metrics_valid
            }
        except Exception as e:
            logger.warning(f"⚠️ Error checking {ticker}: {e}")
            ticker_status[ticker] = {
                'has_prices': False,
                'has_sector': False,
                'has_metrics': False,
                'metrics_valid': False,
                'complete': False
            }
    
    return ticker_status

def fetch_missing_tickers(data_service: RedisFirstDataService, missing_tickers: List[str]) -> Dict[str, bool]:
    """Fetch missing tickers using the data fetching system"""
    from utils.enhanced_data_fetcher import EnhancedDataFetcher
    
    results = {}
    
    logger.info(f"📥 Fetching {len(missing_tickers)} missing tickers...")
    
    # Initialize data fetcher
    data_fetcher = EnhancedDataFetcher()
    
    for ticker in missing_tickers:
        try:
            logger.info(f"  Fetching {ticker}...")
            # Use the data fetcher to get ticker data
            ticker_data = data_fetcher.get_ticker_data(ticker)
            
            success = ticker_data is not None and 'prices' in ticker_data and len(ticker_data.get('prices', [])) > 0
            results[ticker] = success
            
            if success:
                logger.info(f"  ✅ Successfully fetched {ticker}")
            else:
                logger.warning(f"  ⚠️ Failed to fetch {ticker}")
        except Exception as e:
            logger.error(f"  ❌ Error fetching {ticker}: {e}")
            results[ticker] = False
    
    return results

def main():
    """Main function"""
    try:
        # Initialize services
        logger.info("🚀 Initializing services...")
        data_service = RedisFirstDataService()
        redis_manager = RedisPortfolioManager(data_service.redis_client)
        
        if not data_service.redis_client:
            logger.error("❌ Redis client not available")
            return
        
        # Step 1: Get all tickers from portfolios
        logger.info("\n📊 Step 1: Collecting tickers from cached portfolios...")
        all_tickers_by_profile = get_all_portfolio_tickers(redis_manager)
        
        # Combine all tickers
        all_unique_tickers = set()
        for tickers in all_tickers_by_profile.values():
            all_unique_tickers.update(tickers)
        
        logger.info(f"\n📈 Total unique tickers across all portfolios: {len(all_unique_tickers)}")
        
        # Step 2: Check which tickers are in Redis with complete data
        logger.info("\n🔍 Step 2: Checking ticker availability and data completeness in Redis...")
        ticker_status = check_tickers_in_redis(data_service, all_unique_tickers)
        
        # Analyze results
        complete_tickers = [t for t, status in ticker_status.items() if status.get('complete', False)]
        missing_tickers = [t for t, status in ticker_status.items() if not status.get('complete', False)]
        
        # Detailed breakdown
        missing_prices = [t for t, status in ticker_status.items() if not status.get('has_prices', False)]
        missing_sector = [t for t, status in ticker_status.items() if not status.get('has_sector', False)]
        missing_metrics = [t for t, status in ticker_status.items() if not status.get('has_metrics', False)]
        invalid_metrics = [t for t, status in ticker_status.items() if status.get('has_metrics', False) and not status.get('metrics_valid', False)]
        
        logger.info(f"\n✅ Tickers with complete data (prices + sector + valid metrics): {len(complete_tickers)}")
        logger.info(f"❌ Tickers missing or incomplete: {len(missing_tickers)}")
        
        if missing_prices:
            logger.info(f"\n  📉 Missing price data: {len(missing_prices)} tickers")
            logger.info(f"     {', '.join(sorted(missing_prices))}")
        
        if missing_sector:
            logger.info(f"\n  🏢 Missing sector data: {len(missing_sector)} tickers")
            logger.info(f"     {', '.join(sorted(missing_sector))}")
        
        if missing_metrics:
            logger.info(f"\n  📊 Missing metrics data: {len(missing_metrics)} tickers")
            logger.info(f"     {', '.join(sorted(missing_metrics))}")
        
        if invalid_metrics:
            logger.info(f"\n  ⚠️ Invalid metrics data: {len(invalid_metrics)} tickers")
            logger.info(f"     {', '.join(sorted(invalid_metrics))}")
        
        if missing_tickers:
            logger.info(f"\n📋 Incomplete tickers: {', '.join(sorted(missing_tickers))}")
            
            # Step 3: Fetch missing tickers
            logger.info("\n📥 Step 3: Fetching missing tickers...")
            fetch_results = fetch_missing_tickers(data_service, missing_tickers)
            
            # Step 4: Verify after fetching
            logger.info("\n🔍 Step 4: Verifying fetched tickers...")
            updated_status = check_tickers_in_redis(data_service, set(missing_tickers))
            
            newly_present = [t for t, status in updated_status.items() if status]
            still_missing = [t for t, status in updated_status.items() if not status]
            
            logger.info(f"\n✅ Successfully fetched: {len(newly_present)}")
            if newly_present:
                logger.info(f"   {', '.join(sorted(newly_present))}")
            
            if still_missing:
                logger.warning(f"\n⚠️ Still missing: {len(still_missing)}")
                logger.warning(f"   {', '.join(sorted(still_missing))}")
        else:
            logger.info("\n✅ All tickers are present in Redis!")
        
        # Summary by risk profile
        logger.info("\n📊 Summary by Risk Profile:")
        for risk_profile, tickers in all_tickers_by_profile.items():
            profile_status = {t: ticker_status.get(t, {'complete': False}) for t in tickers}
            complete_count = sum(1 for status in profile_status.values() if status.get('complete', False))
            missing_count = len(profile_status) - complete_count
            
            logger.info(f"  {risk_profile}: {complete_count}/{len(tickers)} complete, {missing_count} incomplete")
            
            # Show incomplete tickers for this profile
            incomplete = [t for t, status in profile_status.items() if not status.get('complete', False)]
            if incomplete:
                logger.info(f"    Incomplete: {', '.join(sorted(incomplete))}")
        
        logger.info("\n✅ Verification complete!")
        
    except Exception as e:
        logger.error(f"❌ Error in verification script: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

