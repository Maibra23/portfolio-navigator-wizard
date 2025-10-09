#!/usr/bin/env python3
"""
Quick component verification (skip warming):
- Limits to a single risk profile and 4 variations for speed
- Verifies seeds, uniqueness/signature, volatility in signature,
  pool validation, overlap matrix (4x4), metadata presence, fallback count
"""
import os
import sys
import json

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

os.environ.setdefault("PORTFOLIO_DEDUP_TOLERANCE", "0.1")
os.environ.setdefault("PORTFOLIO_DEDUP_INCLUDE_VARIATION", "1")

from backend.utils.redis_first_data_service import redis_first_data_service
from backend.utils.port_analytics import PortfolioAnalytics
from backend.utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
from backend.utils.portfolio_stock_selector import PortfolioStockSelector


def main():
    out = {}
    risk = "aggressive"
    max_vars = 4

    pa = PortfolioAnalytics()
    gen = EnhancedPortfolioGenerator(redis_first_data_service, pa)
    selector = PortfolioStockSelector(redis_first_data_service)

    # 2) Seed enrichment dispersion (first 4)
    seeds = [gen._generate_variation_seed(risk, i) for i in range(max_vars)]
    out['seed_unique_count'] = len(set(seeds))
    out['seeds'] = seeds

    # Prefetch stocks once
    stocks = selector._get_available_stocks_with_metrics()

    # 4) Pre-flight pool validation
    try:
        ok, stats = gen._validate_stock_pool_sufficiency(selector, stocks, risk)
        out['pool_ok'] = ok
        out['pool_stats'] = stats
    except Exception as e:
        out['pool_validation_error'] = str(e)

    # Generate 4 deterministic portfolios using pre-fetched stocks
    portfolios = []
    for vid in range(max_vars):
        seed = gen._generate_variation_seed(risk, vid)
        p = gen._generate_single_portfolio_deterministic(
            risk_profile=risk,
            variation_seed=seed,
            variation_id=vid,
            stock_selector=selector,
            available_stocks=stocks
        )
        portfolios.append(p)

    out['generated_count'] = len(portfolios)

    # 1 & 3) Signature/volatility checks
    sig = portfolios[0].get('allocation_signature')
    out['has_var_in_sig'] = ('|var:' in sig) if isinstance(sig, str) else False
    out['sig_has_vol'] = any(seg.count(':') >= 3 for seg in sig.split('|')[1:]) if isinstance(sig, str) else False

    # 5) Overlap matrix (build locally for 4 portfolios)
    symbols_list = [set(p.get('symbol_set') or [a['symbol'] for a in p['allocations']]) for p in portfolios]
    n = len(symbols_list)
    matrix = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            matrix[i][j] = len(symbols_list[i] & symbols_list[j])
    out['overlap_matrix_shape'] = (n, n)
    out['overlap_diag'] = [matrix[i][i] for i in range(n)]

    # 6) Metadata presence
    out['metadata_on_generated'] = all(('allocation_signature' in p and 'symbol_set' in p) for p in portfolios)

    # 7) Fallback usage count among the 4
    out['fallback_count'] = sum(1 for p in portfolios if p.get('data_dependency_hash') == 'fallback_hash')

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()


