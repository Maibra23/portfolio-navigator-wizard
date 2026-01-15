#!/usr/bin/env python3
"""
Scheduled regeneration entrypoint.
- Generates 12 portfolios per risk profile
- Stores run stats (unique tickers, sector counts, timestamp) in Redis
- Intended to be invoked by cron/systemd timer every 7 days
- TTL set to 14 days for Redis storage
"""

import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.redis_first_data_service import redis_first_data_service
from utils.port_analytics import PortfolioAnalytics
from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
from collections import Counter

PROFILES = [
    'very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive'
]

def generate_and_store_stats(profile: str):
    pa = PortfolioAnalytics()
    # Use conservative approach + Strategy 5 for aggressive profiles
    eg = EnhancedPortfolioGenerator(redis_first_data_service, pa, use_conservative_approach=True)
    portfolios = eg.generate_portfolio_bucket(profile, use_parallel=True)

    # Build stats
    sector_counts = Counter()
    unique_tickers = set()
    for p in portfolios:
        for a in p.get('allocations', []):
            sector_counts[a.get('sector', 'Unknown')] += 1
            unique_tickers.add(a.get('symbol'))

    stats = {
        'profile': profile,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'portfolios': len(portfolios),
        'unique_tickers': len(unique_tickers),
        'sector_counts': dict(sector_counts),
    }

    # Store stats in Redis with same TTL as portfolios
    r = redis_first_data_service.redis_client
    key = f"portfolio:stats:{profile}"
    ttl = 14 * 24 * 3600
    r.setex(key, ttl, json.dumps(stats))

    # Compute and store Top Pick by expected return for quick frontend access
    def score(p):
        return float(p.get('expectedReturn', 0.0))
    top = max(portfolios, key=score) if portfolios else None
    if top:
        r.setex(f"portfolio:top_pick:{profile}", ttl, json.dumps(top))
    return portfolios, stats

def main():
    results = {}
    for profile in PROFILES:
        portfolios, stats = generate_and_store_stats(profile)
        results[profile] = {'stats': stats}
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()


