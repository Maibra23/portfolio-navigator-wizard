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

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')  # Reduced logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Keep INFO for this script only

# Suppress noisy loggers
logging.getLogger('utils.strategy_portfolio_optimizer').setLevel(logging.WARNING)
logging.getLogger('utils.redis_first_data_service').setLevel(logging.WARNING)
logging.getLogger('utils.port_analytics').setLevel(logging.WARNING)

def verify_changes(optimizer, redis_service):
    """Comprehensive verification of generated portfolios"""
    import json
    from collections import defaultdict
    from utils.port_analytics import PortfolioAnalytics
    
    print("\n" + "=" * 80)
    print("VERIFICATION OF STRATEGY PORTFOLIO CHANGES")
    print("=" * 80)
    
    analytics = PortfolioAnalytics()
    redis_client = redis_service.redis_client
    strategy_keys = redis_client.keys("strategy_portfolios:*")
    
    if not strategy_keys:
        print("⚠️  No portfolios to verify")
        return
    
    print(f"\nAnalyzing {len(strategy_keys)} portfolio bundles...")
    
    # Collect all portfolios by strategy
    all_portfolios = {'diversification': [], 'risk': [], 'return': []}
    
    for key in strategy_keys:
        try:
            data = json.loads(redis_client.get(key))
            strategy = data.get('strategy')
            portfolios = data.get('portfolios', [])
            if strategy in all_portfolios and portfolios:
                all_portfolios[strategy].extend(portfolios)
        except:
            continue
    
    # Get stock pool for allocation verification
    stock_pool = optimizer._stock_pool_cache or optimizer._get_available_stocks()
    stock_map = {s.get('symbol', s.get('ticker')): s for s in stock_pool if s.get('symbol') or s.get('ticker')}
    
    print("\n" + "-" * 80)
    print("1. STRATEGY-SPECIFIC ALLOCATION VERIFICATION")
    print("-" * 80)
    
    for strategy in ['diversification', 'risk', 'return']:
        portfolios = all_portfolios[strategy]
        if not portfolios:
            print(f"\n{strategy.upper()}: No portfolios found")
            continue
        
        sample = portfolios[0]
        allocations = sample.get('allocations', [])
        metrics = sample.get('metrics', {})
        
        print(f"\n{strategy.upper()} ({len(portfolios)} portfolios):")
        print(f"  Return: {metrics.get('expected_return', 0):.2%}, Risk: {metrics.get('risk', 0):.2%}")
        
        # Top allocations
        sorted_alloc = sorted(allocations, key=lambda x: x.get('allocation', 0), reverse=True)
        print(f"  Top 3 allocations:")
        for i, alloc in enumerate(sorted_alloc[:3], 1):
            symbol = alloc.get('symbol')
            weight = alloc.get('allocation', 0)
            stock = stock_map.get(symbol, {})
            vol = stock.get('volatility', 0)
            ret = stock.get('expected_return', 0)
            print(f"    {i}. {symbol}: {weight:.1%} (vol={vol:.2%}, ret={ret:.2%})")
        
        # Strategy-specific checks
        if strategy == 'risk':
            vol_weights = [(stock_map.get(a.get('symbol'), {}).get('volatility', 0.2), a.get('allocation', 0)) 
                          for a in allocations if stock_map.get(a.get('symbol'))]
            if vol_weights:
                vol_weights.sort(key=lambda x: x[0])
                if vol_weights[0][1] > vol_weights[-1][1]:
                    print(f"  ✅ PASSED: Inverse-volatility weighting")
                else:
                    print(f"  ❌ FAILED: Not using inverse-volatility")
        
        elif strategy == 'return':
            ret_weights = [(stock_map.get(a.get('symbol'), {}).get('expected_return', 0.1), a.get('allocation', 0)) 
                          for a in allocations if stock_map.get(a.get('symbol'))]
            if ret_weights:
                ret_weights.sort(key=lambda x: x[0], reverse=True)
                if ret_weights[0][1] > ret_weights[-1][1]:
                    print(f"  ✅ PASSED: Return-proportional weighting")
                else:
                    print(f"  ❌ FAILED: Not return-proportional")
        
        elif strategy == 'diversification':
            sector_weights = defaultdict(float)
            for alloc in allocations:
                sector_weights[alloc.get('sector', 'Unknown')] += alloc.get('allocation', 0)
            max_sector = max(sector_weights.values()) if sector_weights else 0
            min_sector = min(sector_weights.values()) if sector_weights else 0
            print(f"  Sectors: {len(sector_weights)}, Max: {max_sector:.1%}, Min: {min_sector:.1%}")
            if max_sector - min_sector < 0.30:
                print(f"  ✅ PASSED: Sector-balanced allocations")
            else:
                print(f"  ⚠️  WARNING: Sectors may be imbalanced")
    
    print("\n" + "-" * 80)
    print("2. RETURN STRATEGY CAP (90%) VERIFICATION")
    print("-" * 80)
    
    return_portfolios = all_portfolios['return']
    if return_portfolios:
        returns = [p.get('metrics', {}).get('expected_return', 0) for p in return_portfolios]
        max_ret = max(returns) if returns else 0
        exceeded = [r for r in returns if r > 0.90]
        
        print(f"\n  Total return portfolios: {len(returns)}")
        print(f"  Return range: {min(returns):.2%} - {max_ret:.2%}")
        
        if exceeded:
            print(f"  ❌ FAILED: {len(exceeded)} portfolios exceed 90%")
        else:
            print(f"  ✅ PASSED: All portfolios within 90% cap")
    
    print("\n" + "-" * 80)
    print("3. DIVERSIFICATION SCORE METHOD VERIFICATION")
    print("-" * 80)
    
    for strategy in ['diversification', 'risk', 'return']:
        if not all_portfolios[strategy]:
            continue
        
        sample = all_portfolios[strategy][0]
        allocations = sample.get('allocations', [])
        actual_score = sample.get('metrics', {}).get('diversification_score', 0)
        
        try:
            analytics_allocations = [
                {'symbol': a.get('symbol'), 'allocation': float(a.get('allocation', 0)) * 100, 'sector': a.get('sector', 'Unknown')}
                for a in allocations
            ]
            sophisticated_score = analytics._calculate_sophisticated_diversification_score(analytics_allocations)
            diff = abs(actual_score - sophisticated_score)
            
            print(f"\n  {strategy}: actual={actual_score:.1f}, sophisticated={sophisticated_score:.1f}, diff={diff:.1f}")
            if diff < 5.0:
                print(f"  ✅ PASSED: Using sophisticated method")
            else:
                print(f"  ⚠️  WARNING: Scores differ")
        except Exception as e:
            print(f"\n  {strategy}: ⚠️  Could not verify - {e}")
    
    print("\n" + "-" * 80)
    print("4. RISK-FREE RATE VERIFICATION")
    print("-" * 80)
    
    rfr_analytics = analytics.risk_free_rate
    rfr_optimizer = getattr(optimizer.portfolio_analytics, 'risk_free_rate', None)
    
    print(f"\n  PortfolioAnalytics RFR: {rfr_analytics:.2%}")
    print(f"  StrategyOptimizer RFR: {rfr_optimizer:.2%}" if rfr_optimizer else "  StrategyOptimizer RFR: N/A")
    
    if rfr_optimizer and abs(rfr_optimizer - rfr_analytics) < 0.001:
        print(f"  ✅ PASSED: Risk-free rates match")
    else:
        print(f"  ⚠️  WARNING: Risk-free rates differ")
    
    # Verify Sharpe ratio calculation
    sample = all_portfolios['diversification'][0] if all_portfolios['diversification'] else None
    if sample:
        m = sample.get('metrics', {})
        ret, risk, sharpe = m.get('expected_return', 0), m.get('risk', 0), m.get('sharpe_ratio', 0)
        if risk > 0:
            implied_rfr = ret - (sharpe * risk)
            print(f"  Implied RFR from Sharpe: {implied_rfr:.2%}")
            if abs(implied_rfr - rfr_analytics) < 0.01:
                print(f"  ✅ PASSED: Sharpe uses correct RFR")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

def show_progress(current, total, prefix='Progress'):
    """Simple progress indicator"""
    percent = int(100 * current / total) if total > 0 else 0
    bar_len = 40
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f'\r{prefix}: [{bar}] {percent}% ({current}/{total})', end='', flush=True)
    if current >= total:
        print()

def regenerate_all_strategy_portfolios():
    """Regenerate all strategy portfolios with refactored logic - OPTIMIZED"""
    import time
    
    try:
        print("=" * 80)
        print("FAST STRATEGY PORTFOLIO REGENERATION")
        print("=" * 80)
        
        # Initialize services
        print("\n1. Initializing services...")
        start_time = time.time()
        
        redis_service = RedisFirstDataService()
        if not redis_service or not redis_service.redis_client:
            raise ConnectionError("Cannot connect to Redis")
        
        redis_manager = RedisPortfolioManager(redis_service.redis_client)
        optimizer = StrategyPortfolioOptimizer(redis_service, redis_manager)
        
        init_time = time.time() - start_time
        print(f"   ✅ Services initialized ({init_time:.1f}s)")
        
        # Clear existing
        print("\n2. Clearing existing portfolios...")
        clear_start = time.time()
        clear_result = optimizer.clear_all_strategy_caches()
        clear_time = time.time() - clear_start
        print(f"   ✅ Cleared {clear_result.get('deleted_count', 0)} keys ({clear_time:.1f}s)")
        
        # Pre-load stock pool
        print("\n3. Pre-loading stock pool (optimized batch)...")
        pool_start = time.time()
        stock_pool = optimizer._get_available_stocks()
        pool_time = time.time() - pool_start
        print(f"   ✅ Loaded {len(stock_pool)} stocks ({pool_time:.1f}s)")
        
        # Generate portfolios
        print("\n4. Generating portfolios...")
        print("   Target: 18 pure + 90 personalized = 108 total")
        
        gen_start = time.time()
        summary = optimizer.pre_generate_all_strategy_portfolios()
        gen_time = time.time() - gen_start
        
        if summary.get('success'):
            print(f"\n   ✅ Generated {summary['total_portfolios_generated']} portfolios ({gen_time:.1f}s)")
            print(f"   ✅ Stored {summary['total_portfolios_stored']} portfolios")
            
            # Per-strategy breakdown
            print("\n   Strategy breakdown:")
            for strategy, result in summary['strategies'].items():
                pure = result.get('pure_count', 0)
                pers = result.get('personalized_count', 0)
                stime = result.get('elapsed_seconds', 0)
                print(f"     {strategy}: {pure} pure + {pers} personalized ({stime:.1f}s)")
            
            # Total time
            total_time = time.time() - start_time
            print(f"\n   Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
            print(f"   Average per portfolio: {gen_time/summary['total_portfolios_generated']:.2f}s")
            
            # Verify changes
            verify_changes(optimizer, redis_service)
            
            return True
        else:
            print("\n   ❌ Generation failed")
            if summary.get('errors'):
                for error in summary['errors']:
                    print(f"      Error: {error}")
            return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        success = regenerate_all_strategy_portfolios()
        if success:
            print("\n" + "=" * 80)
            print("✅ REGENERATION AND VERIFICATION COMPLETE!")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n❌ Regeneration failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Regeneration failed: {e}")
        sys.exit(1)

