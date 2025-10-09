import os
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple

import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from utils.redis_first_data_service import redis_first_data_service
from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.port_analytics import PortfolioAnalytics
from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator


EXPECTED_CAPS = {
    'very-conservative': 0.12,
    'conservative': 0.15,
    'moderate': 0.25,
    'aggressive': 0.60,
    'very-aggressive': 1.00,
}


def choose_replacement(candidates: List[Dict], cap: float) -> Dict:
    under_cap = [c for c in candidates if c.get('expectedReturn', 0.0) <= cap]
    if under_cap:
        # pick best under cap
        return max(under_cap, key=lambda x: x.get('expectedReturn', 0.0))
    # fallback: pick min above cap if none under
    if candidates:
        return min(candidates, key=lambda x: x.get('expectedReturn', 9e9))
    return {}


def main():
    r = redis_first_data_service.redis_client
    mgr = RedisPortfolioManager(r)
    pa = PortfolioAnalytics()
    gen = EnhancedPortfolioGenerator(redis_first_data_service, pa)

    replaced = []
    scanned = 0

    for rp, cap in EXPECTED_CAPS.items():
        # Load entire bucket once
        bucket_key_prefix = f"portfolio_bucket:{rp}:"
        existing: List[Tuple[int, Dict]] = []
        for i in range(mgr.PORTFOLIOS_PER_PROFILE):
            raw = r.get(f"{bucket_key_prefix}{i}")
            if not raw:
                continue
            try:
                p = json.loads(raw)
                existing.append((i, p))
            except Exception:
                continue
        scanned += len(existing)

        offenders = [(i, p) for i, p in existing if (p.get('expectedReturn') or 0) > cap]
        if not offenders:
            continue

        # Candidates: under-cap from existing bucket
        candidates = [p for _, p in existing if (p.get('expectedReturn') or 0) <= cap]

        # If insufficient, generate one new bucket and extend candidates (single heavy call per profile)
        if len(candidates) < len(offenders):
            gen_bucket = gen.generate_portfolio_bucket(rp, use_parallel=False)
            gen_under = [p for p in gen_bucket if (p.get('expectedReturn') or 0) <= cap]
            candidates.extend(gen_under)

        # Sort candidates by expectedReturn desc (best under cap first)
        candidates.sort(key=lambda x: x.get('expectedReturn', 0.0), reverse=True)

        ci = 0
        for slot_idx, old_p in offenders:
            if ci >= len(candidates):
                break
            replacement = candidates[ci]
            ci += 1
            try:
                r.setex(f"{bucket_key_prefix}{slot_idx}", mgr.PORTFOLIO_TTL_SECONDS, json.dumps(replacement, default=str))
                replaced.append({'risk_profile': rp, 'slot': slot_idx, 'old_expectedReturn': old_p.get('expectedReturn'), 'new_expectedReturn': replacement.get('expectedReturn')})
            except Exception:
                continue

    summary = {
        'scanned': scanned,
        'replaced_count': len(replaced),
        'replaced': replaced,
        'timestamp': datetime.now().isoformat(),
    }
    out = os.path.abspath(os.path.join(repo_root, '..', 'RETURN_CAP_ENFORCEMENT_SUMMARY.json'))
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {out}")


if __name__ == '__main__':
    main()


