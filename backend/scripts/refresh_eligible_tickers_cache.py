#!/usr/bin/env python3
"""
Refresh eligible tickers cache with latest overlap calculation logic
This script invalidates existing cache and recomputes with the new dynamic overlap approach
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import hashlib
import time
from routers.portfolio import _compute_eligible_tickers_internal, _invalidate_eligible_tickers_cache
from utils.redis_first_data_service import redis_first_data_service

def refresh_eligible_tickers_cache():
    """Refresh eligible tickers cache with latest logic"""
    
    print("="*80)
    print("REFRESHING ELIGIBLE TICKERS CACHE")
    print("="*80)
    
    # Step 1: Invalidate existing cache
    print("\n1️⃣  Invalidating existing cache...")
    _invalidate_eligible_tickers_cache()
    print("   ✅ Existing cache invalidated")
    
    # Step 2: Get all tickers
    print("\n2️⃣  Getting all tickers...")
    all_tickers = redis_first_data_service.all_tickers or redis_first_data_service.list_cached_tickers()
    if not all_tickers:
        print("   ❌ No tickers available!")
        return False
    
    print(f"   ✅ Found {len(all_tickers)} tickers")
    
    # Step 3: Compute eligible tickers with default parameters
    print("\n3️⃣  Computing eligible tickers with latest overlap logic...")
    print("   Parameters:")
    print("     - min_data_points: 30")
    print("     - filter_negative_returns: True")
    print("     - max_volatility: 5.0")
    print("     - max_return: 10.0")
    print("   Processing with optimized parallel processing (8 workers, 4 batches)...")
    
    start_time = time.time()
    
    eligible_tickers, filtered_stats = _compute_eligible_tickers_internal(
        all_tickers,
        min_data_points=30,
        filter_negative_returns=True,
        min_volatility=None,
        max_volatility=5.0,
        min_return=None,
        max_return=10.0,
        sectors_list=None,
        exclude_list=None,
        sort_by='ticker',
        max_workers=8,
        batch_workers=4,
        batch_size=100
    )
    
    elapsed = time.time() - start_time
    
    # Step 4: Calculate statistics
    print("\n4️⃣  Calculating statistics...")
    total_eligible = len(eligible_tickers)
    overlap_groups = {'full': 0, 'partial': 0}
    data_quality_dist = {'Good': 0, 'Fair': 0, 'Limited': 0}
    
    for ticker_info in eligible_tickers:
        overlap_groups[ticker_info.get('overlap_group', 'partial')] += 1
        data_quality_dist[ticker_info.get('data_quality', 'Unknown')] += 1
    
    summary = {
        "total_eligible": total_eligible,
        "filtered_by_negative_returns": filtered_stats['negative_returns'],
        "filtered_by_insufficient_data": filtered_stats['insufficient_data'],
        "filtered_by_data_quality": filtered_stats['data_quality'],
        "filtered_by_missing_metrics": filtered_stats['missing_metrics'],
        "filtered_by_volatility": filtered_stats['volatility'],
        "filtered_by_return": filtered_stats['return'],
        "filtered_by_sector": filtered_stats['sector'],
        "filtered_by_exclude": filtered_stats['exclude'],
        "overlap_groups": overlap_groups,
        "data_quality_distribution": data_quality_dist
    }
    
    print(f"   ✅ Statistics calculated:")
    print(f"      - Total Eligible: {total_eligible}")
    print(f"      - Full Overlap: {overlap_groups['full']} ({overlap_groups['full']/total_eligible*100:.1f}%)")
    print(f"      - Partial Overlap: {overlap_groups['partial']} ({overlap_groups['partial']/total_eligible*100:.1f}%)")
    
    # Step 5: Cache the result
    print("\n5️⃣  Caching results in Redis...")
    cache_params = {
        'min_data_points': 30,
        'filter_negative_returns': True,
        'min_volatility': None,
        'max_volatility': 5.0,
        'min_return': None,
        'max_return': 10.0,
        'sectors': None
    }
    cache_key_str = json.dumps(cache_params, sort_keys=True)
    cache_hash = hashlib.md5(cache_key_str.encode()).hexdigest()
    cache_key = f"optimization:eligible_tickers:{cache_hash}"
    
    result_to_cache = {
        "eligible_tickers": eligible_tickers,
        "summary": summary
    }
    
    if redis_first_data_service.redis_client:
        try:
            redis_first_data_service.redis_client.setex(
                cache_key,
                604800,  # 7 days TTL - background regeneration handles refresh before expiry
                json.dumps(result_to_cache)
            )
            print(f"   ✅ Cache stored successfully!")
            print(f"      - Cache Key: {cache_key}")
            print(f"      - TTL: 7 days (604800 seconds)")
        except Exception as e:
            print(f"   ❌ Failed to store cache: {e}")
            return False
    else:
        print("   ❌ Redis client not available!")
        return False
    
    # Step 6: Summary
    print("\n" + "="*80)
    print("✅ ELIGIBLE TICKERS CACHE REFRESHED SUCCESSFULLY!")
    print("="*80)
    print(f"   ⏱️  Processing Time: {elapsed:.2f}s")
    print(f"   📊 Total Eligible: {total_eligible} tickers")
    print(f"   🔗 Full Overlap: {overlap_groups['full']} tickers ({overlap_groups['full']/total_eligible*100:.1f}%)")
    print(f"   🔗 Partial Overlap: {overlap_groups['partial']} tickers ({overlap_groups['partial']/total_eligible*100:.1f}%)")
    print(f"   ⚡ Performance: {len(all_tickers)/elapsed:.2f} tickers/sec")
    print(f"   💾 Cache Key: {cache_key}")
    print("="*80)
    
    return True

if __name__ == "__main__":
    success = refresh_eligible_tickers_cache()
    sys.exit(0 if success else 1)

