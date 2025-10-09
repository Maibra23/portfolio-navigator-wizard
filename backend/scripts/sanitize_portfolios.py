import os
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime

import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from utils.redis_first_data_service import redis_first_data_service
from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.port_analytics import PortfolioAnalytics
from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator


RISK_PROFILES = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']


def round2(x: float) -> float:
    try:
        return round(float(x), 2)
    except Exception:
        return 0.0


def main():
    r = redis_first_data_service.redis_client
    mgr = RedisPortfolioManager(r)
    pa = PortfolioAnalytics()
    gen = EnhancedPortfolioGenerator(redis_first_data_service, pa)

    updated: List[Dict[str, Any]] = []
    regenerated: List[Dict[str, Any]] = []

    for rp in RISK_PROFILES:
        bucket_prefix = f"portfolio_bucket:{rp}:"
        # Load all existing slots
        slots: List[Tuple[int, Dict[str, Any]]] = []
        for i in range(mgr.PORTFOLIOS_PER_PROFILE):
            raw = r.get(f"{bucket_prefix}{i}")
            if not raw:
                continue
            try:
                p = json.loads(raw)
                slots.append((i, p))
            except Exception:
                continue

        # Regenerate any invalid/negative-return portfolios, reuse a single generated bucket per profile
        gen_bucket: List[Dict[str, Any]] = []
        for idx, p in slots:
            allocs = p.get('allocations', [])
            met = pa.calculate_real_portfolio_metrics({
                'allocations': [{'symbol': a.get('symbol'), 'allocation': a.get('allocation')} for a in allocs]
            })
            e = met.get('expected_return')
            rsk = met.get('risk')
            div = met.get('diversification_score')

            # Determine validity
            invalid = (
                e is None or rsk is None or div is None or
                not isinstance(e, (int, float)) or not isinstance(rsk, (int, float)) or not isinstance(div, (int, float)) or
                e != e or rsk != rsk or div != div or  # NaN checks
                e <= 0
            )

            if invalid:
                if not gen_bucket:
                    gen_bucket = gen.generate_portfolio_bucket(rp, use_parallel=False)
                replacement = next((c for c in gen_bucket if isinstance(c.get('expectedReturn'), (int, float)) and c.get('expectedReturn') > 0), None)
                if not replacement:
                    continue
                try:
                    r.setex(f"{bucket_prefix}{idx}", mgr.PORTFOLIO_TTL_SECONDS, json.dumps(replacement, default=str))
                    regenerated.append({'risk_profile': rp, 'slot': idx, 'old_expectedReturn': p.get('expectedReturn'), 'new_expectedReturn': replacement.get('expectedReturn')})
                    continue
                except Exception:
                    continue

            # Valid: update metrics and round expectedReturn to 2 decimals
            new_exp = round2(e)
            needs_store = False
            if p.get('expectedReturn') != new_exp:
                p['expectedReturn'] = new_exp
                needs_store = True
            # Keep risk and diversificationScore in sync
            if p.get('risk') != rsk or p.get('diversificationScore') != div:
                p['risk'] = rsk
                p['diversificationScore'] = div
                needs_store = True

            if needs_store:
                try:
                    r.setex(f"{bucket_prefix}{idx}", mgr.PORTFOLIO_TTL_SECONDS, json.dumps(p, default=str))
                    updated.append({'risk_profile': rp, 'slot': idx, 'new_expectedReturn': p['expectedReturn']})
                except Exception:
                    continue

    summary = {
        'updated_count': len(updated),
        'regenerated_count': len(regenerated),
        'updated': updated,
        'regenerated': regenerated,
        'timestamp': datetime.now().isoformat(),
    }
    out = os.path.abspath(os.path.join(repo_root, '..', 'SANITIZE_PORTFOLIOS_SUMMARY.json'))
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {out}")


if __name__ == '__main__':
    main()


