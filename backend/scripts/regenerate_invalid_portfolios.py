import os
import json
import math
from datetime import datetime
from typing import Dict, Any

import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from utils.redis_first_data_service import redis_first_data_service
from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.port_analytics import PortfolioAnalytics
from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator


RISK_PROFILES = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']


def is_invalid(metrics: Dict[str, Any]) -> bool:
    e = metrics.get('expected_return')
    r = metrics.get('risk')
    d = metrics.get('diversification_score')
    vals = [e, r, d]
    if any(v is None for v in vals):
        return True
    if any(isinstance(v, float) and (math.isnan(v) or math.isinf(v)) for v in vals):
        return True
    return False


def main():
    r = redis_first_data_service.redis_client
    mgr = RedisPortfolioManager(r)
    pa = PortfolioAnalytics()
    gen = EnhancedPortfolioGenerator(redis_first_data_service, pa)

    replaced = []
    checked = 0
    for rp in RISK_PROFILES:
        bucket_prefix = f"portfolio_bucket:{rp}:"
        for i in range(mgr.PORTFOLIOS_PER_PROFILE):
            key = f"{bucket_prefix}{i}"
            raw = r.get(key)
            if not raw:
                continue
            try:
                p = json.loads(raw)
            except Exception:
                continue
            checked += 1

            allocs = p.get('allocations', [])
            metrics = pa.calculate_real_portfolio_metrics({
                'allocations': [{'symbol': a.get('symbol'), 'allocation': a.get('allocation')} for a in allocs]
            })
            if not is_invalid(metrics):
                continue

            # Regenerate a replacement portfolio and store into the same slot
            new_bucket = gen.generate_portfolio_bucket(rp, use_parallel=False)
            # Pick the best by expectedReturn
            best = max(new_bucket, key=lambda x: x.get('expectedReturn', 0.0)) if new_bucket else None
            if not best:
                continue
            try:
                r.setex(key, mgr.PORTFOLIO_TTL_SECONDS, json.dumps(best, default=str))
                replaced.append({'risk_profile': rp, 'slot': i, 'name': best.get('name')})
            except Exception:
                continue

    summary = {
        'checked': checked,
        'replaced': replaced,
        'replaced_count': len(replaced),
        'timestamp': datetime.now().isoformat()
    }
    out = os.path.abspath(os.path.join(repo_root, '..', 'INVALID_PORTFOLIO_REGEN_SUMMARY.json'))
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {out}")


if __name__ == '__main__':
    main()


