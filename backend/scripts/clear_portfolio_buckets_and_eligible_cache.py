#!/usr/bin/env python3
"""
Clear all portfolio buckets (all risk profiles) and invalidate the
eligible-tickers cache. Does not delete any ticker_data:* keys.

Usage: python backend/scripts/clear_portfolio_buckets_and_eligible_cache.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from utils.redis_first_data_service import redis_first_data_service
from utils.redis_portfolio_manager import RedisPortfolioManager

RISK_PROFILES = [
    "very-conservative",
    "conservative",
    "moderate",
    "aggressive",
    "very-aggressive",
]

ELIGIBLE_CACHE_PATTERN = "optimization:eligible_tickers:*"


def main():
    print("=" * 70)
    print("Clear portfolio buckets and eligible-tickers cache")
    print("=" * 70)

    redis_client = redis_first_data_service.redis_client
    if not redis_client:
        print("Redis client not available. Ensure Redis is running.")
        sys.exit(1)

    manager = RedisPortfolioManager(redis_client)
    cleared = 0
    it = tqdm(RISK_PROFILES, desc="Clearing buckets", unit="profile") if HAS_TQDM else RISK_PROFILES
    for risk_profile in it:
        if manager.clear_portfolio_bucket(risk_profile):
            cleared += 1
        if HAS_TQDM:
            it.set_postfix_str(risk_profile)

    print(f"Cleared {cleared}/{len(RISK_PROFILES)} portfolio buckets.")

    # Invalidate eligible-tickers cache
    try:
        keys = redis_client.keys(ELIGIBLE_CACHE_PATTERN)
        if keys:
            redis_client.delete(*keys)
            print(f"Invalidated {len(keys)} eligible-tickers cache key(s).")
        else:
            print("No eligible-tickers cache keys found.")
    except Exception as e:
        print(f"Error invalidating eligible-tickers cache: {e}")
        sys.exit(1)

    print()
    print("Done.")


if __name__ == "__main__":
    main()
