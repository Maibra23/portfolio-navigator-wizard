import os
import json
from datetime import datetime

# Ensure backend on path when run from repo root
import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.redis_first_data_service import redis_first_data_service


def export_markdown(output_path: str) -> None:
    manager = RedisPortfolioManager(redis_first_data_service.redis_client)
    profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']

    caps = {
        'very-conservative': 0.12,
        'conservative': 0.15,
        'moderate': 0.25,
        'aggressive': 0.60,
        'very-aggressive': 1.00,
    }

    lines = []
    lines.append(f"# Portfolios in Redis\n")
    lines.append(f"Generated: {datetime.now().isoformat()}\n")

    total = 0
    for rp in profiles:
        try:
            count = manager.get_portfolio_count(rp)
        except Exception:
            count = 0
        lines.append(f"\n## {rp} ({count} portfolios)\n")

        try:
            portfolios = manager.get_portfolio_recommendations(rp, count=count or 12)
        except Exception:
            portfolios = []

        cap = caps.get(rp)
        for idx, p in enumerate(portfolios):
            total += 1
            name = p.get('name', f'Portfolio {idx+1}')
            exp = p.get('expectedReturn')
            risk = p.get('risk')
            div = p.get('diversificationScore')
            over = cap is not None and isinstance(exp, (int, float)) and exp > cap
            badge = " ⚠️ Above cap" if over else ""
            exp_disp = f"{exp:.2f}" if isinstance(exp, (int, float)) else f"{exp}"
            lines.append(f"\n### {idx+1}. {name}{badge}\n")
            lines.append(f"- expectedReturn: {exp_disp}\n")
            lines.append(f"- risk: {risk}\n")
            lines.append(f"- diversificationScore: {div}\n")
            lines.append(f"- variation_id: {p.get('variation_id')}\n")
            lines.append(f"- data_dependency_hash: {p.get('data_dependency_hash')}\n")
            lines.append(f"- generated_at: {p.get('generated_at')}\n")
            lines.append(f"- risk_profile: {p.get('risk_profile', rp)}\n")
            lines.append(f"\nAllocations:\n")
            lines.append(f"\n| Symbol | Allocation | Sector | Name |\n|---|---:|---|---|\n")
            for a in p.get('allocations', []):
                lines.append(f"| {a.get('symbol')} | {a.get('allocation')}% | {a.get('sector', a.get('Sector', 'Unknown'))} | {a.get('name','')} |\n")

    lines.append(f"\n\nTotal portfolios exported: {total}\n")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


if __name__ == '__main__':
    out = os.path.abspath(os.path.join(repo_root, '..', 'PORTFOLIOS_IN_REDIS.md'))
    export_markdown(out)
    print(f"Exported to {out}")


