#!/usr/bin/env python3
"""
Run full generation for the 'very-aggressive' risk profile and print all 12 portfolios.
"""

import os
import sys
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from backend.utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
from backend.utils.port_analytics import PortfolioAnalytics
from backend.utils.redis_first_data_service import redis_first_data_service


def main():
    # Optional: set regime flag and TTL for this run
    os.environ.setdefault('REGIME_FLAG', 'neutral')
    os.environ.setdefault('SECTOR_WEIGHTS_TTL_SECONDS', '3600')

    analytics = PortfolioAnalytics()
    generator = EnhancedPortfolioGenerator(redis_first_data_service, analytics)
    portfolios = generator.generate_portfolio_bucket('very-aggressive', use_parallel=True)
    # Print concise breakdown with sectors and a small stats block
    summary = []
    sector_counts = {}
    ticker_counts = {}
    for idx, p in enumerate(portfolios, start=1):
        allocs = []
        for a in p.get('allocations', []):
            allocs.append({
                'symbol': a['symbol'],
                'allocation_pct': a['allocation'],
                'sector': a.get('sector', 'Unknown')
            })
            sector = a.get('sector', 'Unknown')
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            ticker_counts[a['symbol']] = ticker_counts.get(a['symbol'], 0) + 1
        summary.append({
            'portfolio': idx,
            'name': p.get('name'),
            'allocations': allocs
        })
    output = {
        'portfolios': summary,
        'stats': {
            'num_portfolios': len(summary),
            'unique_tickers': len(ticker_counts),
            'sector_counts': sector_counts
        }
    }
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()


