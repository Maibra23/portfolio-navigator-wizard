#!/usr/bin/env python3
"""
One-time helper to:
1) Warm Redis cache via RedisFirstDataService (if EnhancedDataFetcher available)
2) Ensure import paths so nested `from utils...` imports resolve
3) Re-run component-level checks for the enhanced portfolio generator

Outputs a compact JSON with results suitable for quick verification.
"""
import os
import sys
import json

# Ensure both project root and backend are importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

# Set stricter de-dup defaults for verification
os.environ.setdefault("PORTFOLIO_DEDUP_TOLERANCE", "0.1")
os.environ.setdefault("PORTFOLIO_DEDUP_INCLUDE_VARIATION", "1")

from backend.utils.redis_first_data_service import redis_first_data_service
from backend.utils.port_analytics import PortfolioAnalytics
from backend.utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator


def warm_cache_once():
    """Attempt to warm the Redis cache if the EnhancedDataFetcher is available."""
    try:
        result = redis_first_data_service.warm_cache()
        return {
            'attempted': True,
            'success': bool(result and result.get('success', False)),
            'details': result
        }
    except Exception as e:
        return {'attempted': True, 'success': False, 'error': str(e)}


def run_component_checks(risk_profile: str = "aggressive"):
    results = {}

    pa = PortfolioAnalytics()
    gen = EnhancedPortfolioGenerator(redis_first_data_service, pa)

    # 2) Seed enrichment dispersion
    seeds = [gen._generate_variation_seed(risk_profile, i) for i in range(12)]
    results['seed_unique_count'] = len(set(seeds))

    # Generate portfolio bucket
    try:
        portfolios = gen.generate_portfolio_bucket(risk_profile)
        results['generated_count'] = len(portfolios)
    except Exception as e:
        portfolios = []
        results['generation_error'] = str(e)

    # 1 & 3) Signature checks
    if portfolios:
        sig = portfolios[0].get('allocation_signature')
        results['has_var_in_sig'] = ('|var:' in sig) if isinstance(sig, str) else False
        results['sig_has_vol'] = any(seg.count(':') >= 3 for seg in sig.split('|')[1:]) if isinstance(sig, str) else False

    # 5) Overlap matrix presence
    try:
        import redis
        r = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        if portfolios:
            dh = portfolios[0].get('data_dependency_hash', 'unknown')
            key = f"portfolio:overlap:{risk_profile}:{dh}"
            raw = r.get(key)
            results['overlap_key_exists'] = raw is not None
            if raw:
                payload = json.loads(raw)
                m = payload.get('matrix')
                results['overlap_matrix_shape'] = (len(m), len(m[0]) if m else 0) if m else (0, 0)
    except Exception as e:
        results['overlap_error'] = str(e)

    # 6) Allocation metadata present
    if portfolios:
        results['metadata_on_generated'] = all(('allocation_signature' in p and 'symbol_set' in p) for p in portfolios)

    # 7) Fallback usage
    if portfolios:
        results['fallback_count'] = sum(1 for p in portfolios if p.get('data_dependency_hash') == 'fallback_hash')

    return results


def main():
    out = {}

    # Step 1: Warm cache
    out['warm_cache'] = warm_cache_once()

    # Step 2: Component checks
    out['component_checks'] = run_component_checks('aggressive')

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()


