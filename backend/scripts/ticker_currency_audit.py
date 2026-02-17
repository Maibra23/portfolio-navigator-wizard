#!/usr/bin/env python3
"""
Ticker master list revision and currency standardization audit.

Produces:
- Ticker -> Country -> Exchange -> Native Currency classification
- Currency handling behavior and conversion gap analysis
- Data integrity summary and recommendations
"""

import sys
import os
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.timestamp_utils import get_ticker_country_exchange_currency, detect_ticker_exchange
from utils.redis_first_data_service import redis_first_data_service

# Progress bar helper
def _progress(current: int, total: int, width: int = 40, prefix: str = ""):
    if total <= 0:
        return
    pct = current / total
    filled = int(width * pct)
    bar = "=" * filled + "-" * (width - filled)
    sys.stderr.write(f"\r{prefix}[{bar}] {current}/{total} ({100*pct:.0f}%)")
    sys.stderr.flush()


def load_master_tickers():
    """Load master ticker list from Redis or cached tickers."""
    try:
        master = redis_first_data_service.all_tickers
        if master and len(master) > 0:
            return list(master)
    except Exception as e:
        sys.stderr.write(f"Warning: could not load master from all_tickers: {e}\n")
    try:
        cached = redis_first_data_service.list_cached_tickers()
        if cached and len(cached) > 0:
            return list(cached)
    except Exception as e:
        sys.stderr.write(f"Warning: could not load from list_cached_tickers: {e}\n")
    return []


def classify_all_tickers(tickers: list) -> tuple:
    """Classify each ticker: country, exchange, native currency. Returns (rows, by_currency, by_country, ambiguous)."""
    rows = []
    by_currency = defaultdict(list)
    by_country = defaultdict(list)
    base_to_tickers = defaultdict(list)  # base symbol -> [full tickers] for ambiguity check
    total = len(tickers)
    for i, t in enumerate(tickers):
        _progress(i + 1, total, prefix="Classifying ")
        country, exchange, currency = get_ticker_country_exchange_currency(t)
        rows.append({
            "ticker": t,
            "country": country or "Unknown",
            "exchange": exchange or "Unknown",
            "native_currency": currency,
        })
        by_currency[currency].append(t)
        by_country[country or "Unknown"].append(t)
        base = t.split(".")[0] if "." in t else t
        base_to_tickers[base].append(t)
    sys.stderr.write("\n")
    ambiguous = {b: lst for b, lst in base_to_tickers.items() if len(lst) > 1}
    return rows, dict(by_currency), dict(by_country), ambiguous


def main():
    sys.stderr.write("Ticker master list and currency audit\n")
    sys.stderr.write("Loading master ticker list...\n")
    tickers = load_master_tickers()
    if not tickers:
        sys.stderr.write("No tickers loaded. Ensure Redis is available and master list is populated.\n")
        sys.exit(1)
    sys.stderr.write(f"Loaded {len(tickers)} tickers.\n")
    rows, by_currency, by_country, ambiguous = classify_all_tickers(tickers)

    # Build report
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("TICKER MASTER LIST AND CURRENCY STANDARDIZATION DIAGNOSTIC REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    report_lines.append("1. TICKER CLASSIFICATION SUMMARY")
    report_lines.append("-" * 80)
    report_lines.append("By native currency:")
    for curr in sorted(by_currency.keys(), key=lambda c: (-len(by_currency[c]), c)):
        report_lines.append(f"  {curr}: {len(by_currency[curr])} tickers")
    report_lines.append("")
    report_lines.append("By country:")
    for country in sorted(by_country.keys(), key=lambda c: (-len(by_country[c]), c)):
        report_lines.append(f"  {country}: {len(by_country[country])} tickers")
    report_lines.append("")

    report_lines.append("2. CURRENCY HANDLING BEHAVIOR")
    report_lines.append("-" * 80)
    report_lines.append("USD standardization: NOT ENFORCED.")
    report_lines.append("  - Prices are fetched from Yahoo (yahooquery) in listing currency.")
    report_lines.append("  - No FX conversion to USD is performed anywhere in:")
    report_lines.append("    enhanced_data_fetcher (fetch/cache), redis_first_data_service,")
    report_lines.append("    portfolio metrics (get_ticker_metrics_batch), optimization (MVO),")
    report_lines.append("    or analytics (returns/covariance).")
    report_lines.append("  - Returns are computed as pct_change() on raw prices (local currency).")
    report_lines.append("  - Covariance matrix and expected returns are in mixed currencies when")
    report_lines.append("    the portfolio contains non-USD assets.")
    report_lines.append("  - Portfolio value and risk in a single numeraire (e.g. USD) are not")
    report_lines.append("    correct for mixed-currency portfolios.")
    report_lines.append("")
    report_lines.append("Conversion timing: N/A (no conversion implemented).")
    report_lines.append("FX rate integration: NONE (no FX rates fetched or applied).")
    report_lines.append("")

    report_lines.append("3. IDENTIFIED WEAKNESSES AND CONVERSION GAPS")
    report_lines.append("-" * 80)
    report_lines.append("  - Mixed-currency contamination: Portfolios mixing USD and non-USD assets")
    report_lines.append("    combine returns and volatilities in different units; portfolio risk")
    report_lines.append("    and expected return are not in a single currency.")
    report_lines.append("  - Implicit assumption: All metrics (return, volatility, covariance) are")
    report_lines.append("    treated as if in one currency; true only for USD-only portfolios.")
    report_lines.append("  - No native currency detection at fetch time: Stored prices have no")
    report_lines.append("    currency metadata; classification is by symbol suffix only.")
    report_lines.append("  - Analytics/optimization layer: No conversion before covariance or")
    report_lines.append("    before optimization; frontier and weights are currency-inconsistent")
    report_lines.append("    for mixed portfolios.")
    report_lines.append("")

    report_lines.append("4. AMBIGUOUS SYMBOLS (SAME BASE TICKER ACROSS EXCHANGES)")
    report_lines.append("-" * 80)
    if ambiguous:
        for base in sorted(ambiguous.keys())[:30]:
            report_lines.append(f"  {base}: {', '.join(ambiguous[base])}")
        if len(ambiguous) > 30:
            report_lines.append(f"  ... and {len(ambiguous) - 30} more base symbols with multiple listings.")
    else:
        report_lines.append("  None (each base symbol has at most one listing in the list).")
    report_lines.append("")

    report_lines.append("5. RECOMMENDED ARCHITECTURAL CORRECTIONS")
    report_lines.append("-" * 80)
    report_lines.append("  a) Add currency metadata: Store native currency per ticker (from suffix or")
    report_lines.append("     Yahoo quote) in sector/metrics cache.")
    report_lines.append("  b) FX conversion layer: Fetch or cache FX rates (e.g. SEK/USD, EUR/USD)")
    report_lines.append("     and convert all stored prices to USD at cache time, or convert at read")
    report_lines.append("     time when building returns for optimization.")
    report_lines.append("  c) Single numeraire: Ensure get_ticker_metrics_batch and MVO use")
    report_lines.append("     USD-denominated returns and covariance for all tickers.")
    report_lines.append("  d) Tests: Run portfolios with USD-only, mixed, and non-USD-only assets")
    report_lines.append("     and compare risk/return and frontier consistency after FX is added.")
    report_lines.append("")

    report_lines.append("6. SAMPLE CLASSIFICATION TABLE (FIRST 50 TICKERS)")
    report_lines.append("-" * 80)
    report_lines.append(f"{'Ticker':<20} {'Country':<25} {'Exchange':<30} {'Currency':<8}")
    report_lines.append("-" * 80)
    for r in rows[:50]:
        report_lines.append(f"{r['ticker']:<20} {(r['country'] or '')[:24]:<25} {(r['exchange'] or '')[:29]:<30} {r['native_currency']:<8}")
    report_lines.append("")

    full_report = "\n".join(report_lines)
    print(full_report)

    # Write structured output for programmatic use
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir / f"ticker_currency_audit_{ts}.json"
    payload = {
        "generated_at": datetime.now().isoformat(),
        "total_tickers": len(rows),
        "by_currency": {k: len(v) for k, v in by_currency.items()},
        "by_country": {k: len(v) for k, v in by_country.items()},
        "ambiguous_base_count": len(ambiguous),
        "classification_table": rows,
        "summary": {
            "usd_tickers": len(by_currency.get("USD", [])),
            "non_usd_tickers": len(tickers) - len(by_currency.get("USD", [])),
            "currencies_present": list(by_currency.keys()),
        },
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    sys.stderr.write(f"Structured report written to {out_path}\n")


if __name__ == "__main__":
    main()
