#!/usr/bin/env python3
"""
Generate portfolios for all risk profiles WITHOUT storing them in Redis.

Purpose:
- Preview portfolios and their compositions
- Analyze returns, risks, diversification, and ticker usage
- Verify that conservative + Strategy 5 setup works end-to-end without side effects

This script reuses the internal generation logic but:
- Applies the conservative config where appropriate
- Uses the configured diversification strategy (Strategy 5 when conservative is on)
- Calls the internal `_generate_portfolios_with_ticker_exclusion` method directly
- DOES NOT store portfolios in Redis
"""

import os
import sys
from datetime import datetime
from typing import Dict, List

from tqdm import tqdm

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(__file__))

from utils.redis_first_data_service import redis_first_data_service as _rds
from utils.port_analytics import PortfolioAnalytics
from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
from utils.enhanced_stock_selector import EnhancedStockSelector

PROFILES = [
    "very-conservative",
    "conservative",
    "moderate",
    "aggressive",
    "very-aggressive",
]


def get_stats(portfolios: List[Dict]) -> Dict:
    if not portfolios:
        return {
            "count": 0,
            "returns": {},
            "risks": {},
            "diversification": {},
            "stock_counts": {},
            "unique_tickers": 0,
        }

    rets = []
    risks = []
    divs = []
    counts = []
    tickers = set()

    for p in portfolios:
        r = p.get("expectedReturn", 0)
        if r > 1.0:
            r = r / 100.0
        rets.append(r * 100.0)

        risk = p.get("risk", 0)
        if risk > 1.0:
            risk = risk / 100.0
        risks.append(risk * 100.0)

        d = p.get("diversificationScore", p.get("diversification_score", 0.0))
        divs.append(d)

        allocs = p.get("allocations", [])
        counts.append(len(allocs))
        for a in allocs:
            sym = a.get("symbol")
            if sym:
                tickers.add(sym)

    def _mm(x: List[float]):
        xs = sorted(x)
        return {
            "min": xs[0],
            "max": xs[-1],
            "mean": sum(xs) / len(xs),
            "median": xs[len(xs) // 2],
        }

    return {
        "count": len(portfolios),
        "returns": _mm(rets),
        "risks": _mm(risks),
        "diversification": {
            "min": min(divs),
            "max": max(divs),
            "mean": sum(divs) / len(divs),
        }
        if divs
        else {},
        "stock_counts": {
            "min": min(counts),
            "max": max(counts),
            "mean": sum(counts) / len(counts),
        }
        if counts
        else {},
        "unique_tickers": len(tickers),
    }


def main():
    print("=" * 80)
    print("PORTFOLIO PREVIEW (NO REDIS STORAGE)")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    pa = PortfolioAnalytics()
    gen = EnhancedPortfolioGenerator(_rds, pa, use_conservative_approach=True)

    results: Dict[str, List[Dict]] = {}

    print("Generating portfolios (preview only)...")
    for profile in tqdm(PROFILES, desc="Profiles", unit="profile"):
        print()
        print(f"Profile: {profile}")
        print("-" * 40)

        # Apply conservative config if enabled for this profile (mimic generate_portfolio_bucket)
        original_config = None
        if getattr(gen, "conservative_generator", None) and gen.conservative_generator.should_use_conservative(profile):
            original_config = gen.conservative_generator.apply_conservative_config(profile)
            print(f"  Using conservative config for {profile}")

        try:
            # Set diversification stage for generation if strategy supports it
            if gen.diversification_strategy and hasattr(gen.diversification_strategy, "set_stage"):
                gen.diversification_strategy.set_stage("generation")

            # Stock selector and available stocks (same as generate_portfolio_bucket)
            selector = EnhancedStockSelector(_rds)
            print("  Fetching stock universe with metrics...")
            available_stocks = selector._get_available_stocks_with_metrics()
            print(f"  Stocks available: {len(available_stocks)}")

            # Use the same internal bucket-generation logic but do NOT store in Redis
            portfolios = gen._generate_portfolios_with_ticker_exclusion(  # type: ignore[attr-defined]
                profile, selector, available_stocks
            )

            results[profile] = portfolios
            stats = get_stats(portfolios)

            print(f"  Portfolios: {stats['count']}/12")
            if stats["count"] > 0:
                r = stats["returns"]
                k = stats["risks"]
                d = stats["diversification"]
                c = stats["stock_counts"]
                print(
                    f"  Returns mean: {r['mean']:.2f}%  range: {r['min']:.2f}% - {r['max']:.2f}%"
                )
                print(
                    f"  Risk    mean: {k['mean']:.2f}%  range: {k['min']:.2f}% - {k['max']:.2f}%"
                )
                if d:
                    print(
                        f"  Diversification mean: {d['mean']:.1f}%  range: {d['min']:.1f}% - {d['max']:.1f}%"
                    )
                if c:
                    print(
                        f"  Stock count mean: {c['mean']:.1f}  range: {c['min']} - {c['max']}"
                    )
                print(f"  Unique tickers: {stats['unique_tickers']}")
        finally:
            # Restore original configuration if conservative was applied
            if original_config and getattr(gen, "conservative_generator", None):
                gen.conservative_generator.restore_original_config(profile)
                print(f"  Restored original config for {profile}")

    print()
    print("=" * 80)
    print("NOTE")
    print("=" * 80)
    print("- These portfolios were generated using the same logic as regeneration (conservative + Strategy 5).")
    print("- They were NOT stored in Redis; only printed here for analysis.")
    print("- Use this preview to verify behavior and decide if configuration changes are needed.")
    print()


if __name__ == "__main__":
    main()
