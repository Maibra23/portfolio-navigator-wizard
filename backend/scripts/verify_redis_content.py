#!/usr/bin/env python3
"""
Verify Redis content and FX normalization status.
Read-only: no Redis writes or deletions.
- Loads master list from CSV or Redis
- Loads cached tickers via list_cached_tickers()
- Computes missing = master - cached (failed tickers)
- Checks meta for each cached ticker: stored_currency, converted
- Reports totals and normalization status
"""

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.redis_first_data_service import redis_first_data_service
from utils.timestamp_utils import get_ticker_country_exchange_currency

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

REPORTS_DIR = Path(__file__).parent / "reports"


def _load_tickers_from_csv(path: Path):
    """Load tickers from a CSV file (ticker in first column)."""
    tickers = []
    try:
        import csv
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if row and row[0].strip():
                    tickers.append(row[0].strip())
    except Exception:
        pass
    return tickers


def _load_master_list():
    """Load master ticker list from CSV or Redis. Uses fullest available list."""
    tickers = []
    csv_latest = REPORTS_DIR / "fetchable_master_list_validated_latest.csv"
    if csv_latest.is_file():
        tickers = _load_tickers_from_csv(csv_latest)
    if not tickers or len(tickers) < 100:
        for p in sorted(REPORTS_DIR.glob("fetchable_master_list_validated_*.csv"), reverse=True):
            if p.name == "fetchable_master_list_validated_latest.csv":
                continue
            cand = _load_tickers_from_csv(p)
            if len(cand) > len(tickers):
                tickers = cand
            if tickers and len(tickers) >= 100:
                break
    if tickers:
        return tickers
    if redis_first_data_service.redis_client:
        try:
            validated = redis_first_data_service.redis_client.get("master_ticker_list_validated")
            if validated:
                try:
                    lst = json.loads(validated.decode())
                except Exception:
                    try:
                        import gzip
                        lst = json.loads(gzip.decompress(validated).decode())
                    except Exception:
                        lst = []
                if lst:
                    return list(lst)
        except Exception as e:
            sys.stderr.write(f"Warning: Redis validated list read failed: {e}\n")
        try:
            master = redis_first_data_service.all_tickers
            if master:
                return list(master)
        except Exception as e:
            sys.stderr.write(f"Warning: all_tickers failed: {e}\n")
    return tickers


def _load_meta(r, ticker: str):
    if not r:
        return None
    key = f"ticker_data:meta:{ticker}"
    raw = r.get(key)
    if raw:
        try:
            return json.loads(raw.decode())
        except Exception:
            pass
    return None


def main():
    logging.getLogger("utils.enhanced_data_fetcher").setLevel(logging.WARNING)
    logging.getLogger("utils.redis_first_data_service").setLevel(logging.WARNING)

    r = redis_first_data_service.redis_client
    if not r:
        print("Redis unavailable. Ensure Redis is running.")
        sys.exit(1)

    print("=" * 70)
    print("REDIS CONTENT VERIFICATION (read-only)")
    print("=" * 70)

    master_list = _load_master_list()
    if not master_list:
        print("Master list empty. No CSV or Redis validated list found.")
        sys.exit(1)
    print(f"Master list: {len(master_list)} tickers")

    cached_tickers = redis_first_data_service.list_cached_tickers()
    print(f"Cached tickers (prices + sector): {len(cached_tickers)}")

    master_set = set(master_list)
    cached_set = set(cached_tickers)
    missing = sorted(master_set - cached_set)
    print(f"Missing (failed): {len(missing)} tickers")
    if missing:
        print("Missing tickers:")
        for t in missing:
            print(f"  {t}")

    print()
    print("Normalization status (cached tickers):")
    print("-" * 50)

    with_meta = 0
    without_meta = 0
    fully_normalized = 0
    needs_check = []
    by_stored_currency = defaultdict(int)
    non_usd_not_converted = []

    it = tqdm(cached_tickers, desc="Checking meta", unit="ticker") if HAS_TQDM else cached_tickers
    for ticker in it:
        meta = _load_meta(r, ticker)
        if meta is None:
            without_meta += 1
            needs_check.append(ticker)
        else:
            with_meta += 1
            sc = meta.get("stored_currency", "?")
            by_stored_currency[sc] += 1
            _, _, native = get_ticker_country_exchange_currency(ticker)
            if sc == "USD":
                if native in ("USD", "Unknown"):
                    fully_normalized += 1
                else:
                    if meta.get("converted") is True:
                        fully_normalized += 1
                    else:
                        non_usd_not_converted.append(ticker)
            else:
                non_usd_not_converted.append(ticker)

    print(f"  With meta: {with_meta}")
    print(f"  Without meta (legacy): {without_meta}")
    print(f"  Fully normalized (stored_currency=USD, converted where needed): {fully_normalized}")
    print(f"  Needs normalization check: {len(needs_check)}")
    print(f"  Non-USD not converted: {len(non_usd_not_converted)}")
    print(f"  By stored_currency: {dict(by_stored_currency)}")
    if non_usd_not_converted:
        print("  Non-USD not converted tickers (sample):")
        for t in non_usd_not_converted[:10]:
            print(f"    {t}")
        if len(non_usd_not_converted) > 10:
            print(f"    ... and {len(non_usd_not_converted) - 10} more")

    payload = {
        "generated_at": datetime.now().isoformat(),
        "master_count": len(master_list),
        "cached_count": len(cached_tickers),
        "missing_tickers": missing,
        "with_meta": with_meta,
        "without_meta": without_meta,
        "fully_normalized": fully_normalized,
        "needs_check": needs_check,
        "non_usd_not_converted": non_usd_not_converted,
        "by_stored_currency": dict(by_stored_currency),
    }
    REPORTS_DIR.mkdir(exist_ok=True)
    out_path = REPORTS_DIR / f"verify_redis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print()
    print(f"Report saved to {out_path}")

    print()
    print("=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    return payload


if __name__ == "__main__":
    main()
