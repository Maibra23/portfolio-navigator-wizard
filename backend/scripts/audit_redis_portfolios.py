import os
import json
from datetime import datetime
from typing import Dict, List

import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.redis_first_data_service import redis_first_data_service
from utils.port_analytics import PortfolioAnalytics


EXPECTED_RANGES = {
    'very-conservative': {'return_max': 0.12, 'risk_max': 0.20},
    'conservative': {'return_max': 0.15, 'risk_max': 0.25},
    'moderate': {'return_max': 0.25, 'risk_max': 0.35},
    'aggressive': {'return_max': 0.60, 'risk_max': 0.50},
    'very-aggressive': {'return_max': 1.00, 'risk_max': 0.80},
}


def audit() -> Dict:
    manager = RedisPortfolioManager(redis_first_data_service.redis_client)
    analytics = PortfolioAnalytics()
    profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']

    report: Dict[str, Dict] = {}
    for rp in profiles:
        items: List[Dict] = manager.get_portfolio_recommendations(rp, count=manager.PORTFOLIOS_PER_PROFILE)
        rp_report = {"count": len(items), "issues": [], "ok": 0}
        rng = EXPECTED_RANGES.get(rp, {})

        for idx, p in enumerate(items):
            allocs = p.get('allocations', [])
            # recompute metrics to assert consistency
            computed = analytics.calculate_real_portfolio_metrics({
                'allocations': [{'symbol': a.get('symbol'), 'allocation': a.get('allocation')} for a in allocs]
            })
            e = computed.get('expected_return')
            r = computed.get('risk')
            d = computed.get('diversification_score')
            ok = True
            # sanity checks
            if e is None or r is None or d is None:
                rp_report["issues"].append({"idx": idx, "reason": "missing_metrics", "name": p.get('name')})
                ok = False
            # expected profile ranges (soft caps)
            if rng:
                if e is not None and e < 0:
                    rp_report["issues"].append({"idx": idx, "reason": "negative_return", "value": e, "name": p.get('name')})
                    ok = False
                if r is not None and r < 0:
                    rp_report["issues"].append({"idx": idx, "reason": "negative_risk", "value": r, "name": p.get('name')})
                    ok = False
                if e is not None and e > rng.get('return_max', 9e9):
                    rp_report["issues"].append({"idx": idx, "reason": "return_exceeds_profile_cap", "value": e, "cap": rng.get('return_max'), "name": p.get('name')})
                    ok = False
                if r is not None and r > rng.get('risk_max', 9e9):
                    rp_report["issues"].append({"idx": idx, "reason": "risk_exceeds_profile_cap", "value": r, "cap": rng.get('risk_max'), "name": p.get('name')})
                    ok = False
            if ok:
                rp_report["ok"] += 1

        report[rp] = rp_report
    return report


def write_markdown(report: Dict, out_path: str):
    lines = []
    lines.append(f"# Redis Portfolio Audit\n\nGenerated: {datetime.now().isoformat()}\n\n")
    for rp, rp_report in report.items():
        lines.append(f"## {rp}\n")
        lines.append(f"- count: {rp_report['count']}\n")
        lines.append(f"- ok: {rp_report['ok']}\n")
        lines.append(f"- issues: {len(rp_report['issues'])}\n")
        if rp_report['issues']:
            lines.append("\n### Issues\n")
            for issue in rp_report['issues']:
                lines.append(f"- {issue}\n")
        lines.append("\n")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


if __name__ == '__main__':
    rep = audit()
    out = os.path.abspath(os.path.join(repo_root, '..', 'REDIS_PORTFOLIO_AUDIT.md'))
    write_markdown(rep, out)
    print(json.dumps(rep, indent=2))
    print(f"\nWrote {out}")


