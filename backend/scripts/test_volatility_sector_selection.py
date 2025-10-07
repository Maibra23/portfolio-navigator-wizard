#!/usr/bin/env python3
"""
Generate 4 portfolios each for 'moderate' and 'very-aggressive' using the
volatility-weighted sector prioritization integrated into PortfolioStockSelector.
"""

import os
import sys
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from backend.utils.portfolio_stock_selector import PortfolioStockSelector
from backend.utils.redis_first_data_service import redis_first_data_service
import os


def generate_portfolios(profile: str, count: int = 4):
    selector = PortfolioStockSelector(redis_first_data_service)
    portfolios = []
    for i in range(count):
        allocations = selector.select_stocks_for_risk_profile(profile)
        portfolios.append({
            'variation': i + 1,
            'allocations': allocations,
            'sectorBreakdown': selector._calculate_sector_breakdown(allocations)
        })
    return portfolios


def main():
    # Set regime flag for this test if provided
    os.environ.setdefault('REGIME_FLAG', 'neutral')
    os.environ.setdefault('SECTOR_WEIGHTS_TTL_SECONDS', '1800')  # 30 min
    results = {}
    for profile in ['very-conservative', 'very-aggressive']:
        portfolios = generate_portfolios(profile, count=4)
        results[profile] = portfolios

    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()


