#!/usr/bin/env python3
"""
Refetch failed tickers (master - cached) with FX normalization.
- Loads master list from CSV or Redis
- Loads cached tickers via list_cached_tickers()
- Computes failed = set(master) - set(cached)
- Retries each failed ticker with _fetch_single_ticker_with_retry(force_fetch=True)
- Optionally refetches non-normalized tickers (stored_currency != USD or no meta)
- Progress bar and rate limiting
- Saves still-failed tickers to reports/refetch_failed_tickers_YYYYMMDD.json
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm

from utils.redis_first_data_service import redis_first_data_service
from utils.enhanced_data_fetcher import EnhancedDataFetcher
from utils.enhanced_data_fetcher import BATCH_SIZE, RATE_LIMIT_DELAY

REPORTS_DIR = Path(__file__).parent / "reports"


def _load_master_list():
    """Load master ticker list (same logic as verify_redis_content)."""
    tickers = []
    csv_latest = REPORTS_DIR / "fetchable_master_list_validated_latest.csv"
    if csv_latest.is_file():
        try:
            import csv
            with open(csv_latest, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if row and row[0].strip():
                        tickers.append(row[0].strip())
        except Exception:
            pass
    if not tickers or len(tickers) < 100:
        for p in sorted(REPORTS_DIR.glob("fetchable_master_list_validated_*.csv"), reverse=True):
            if "latest" in p.name:
                continue
            try:
                import csv
                cand = []
                with open(p, "r", newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    for row in reader:
                        if row and row[0].strip():
                            cand.append(row[0].strip())
                if len(cand) > len(tickers):
                    tickers = cand
            except Exception:
                pass
    if not tickers and redis_first_data_service.redis_client:
        try:
            raw = redis_first_data_service.redis_client.get("master_ticker_list_validated")
            if raw:
                try:
                    tickers = json.loads(raw.decode())
                except Exception:
                    try:
                        import gzip
                        tickers = json.loads(gzip.decompress(raw).decode())
                    except Exception:
                        tickers = []
        except Exception:
            pass
    if not tickers:
        try:
            tickers = list(redis_first_data_service.all_tickers or [])
        except Exception:
            pass
    return tickers


def _load_non_normalized_tickers():
    """Load tickers that need normalization (no meta or stored_currency != USD)."""
    r = redis_first_data_service.redis_client
    if not r:
        return []
    cached = redis_first_data_service.list_cached_tickers()
    need_refetch = []
    for t in cached:
        key = f"ticker_data:meta:{t}"
        raw = r.get(key)
        if raw is None:
            need_refetch.append(t)
        else:
            try:
                meta = json.loads(raw.decode())
                if meta.get("stored_currency") != "USD":
                    need_refetch.append(t)
            except Exception:
                need_refetch.append(t)
    return need_refetch


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Refetch failed or non-normalized tickers")
    parser.add_argument(
        "--non-normalized",
        action="store_true",
        help="Also refetch tickers with no meta or stored_currency != USD",
    )
    args = parser.parse_args()

    for name in ("utils.enhanced_data_fetcher", "utils.pdf_report_generator", "routers.portfolio"):
        logging.getLogger(name).setLevel(logging.WARNING)

    master_list = _load_master_list()
    if not master_list:
        print("Master list empty. Cannot refetch.")
        sys.exit(1)

    cached_set = set(redis_first_data_service.list_cached_tickers())
    failed = sorted(set(master_list) - cached_set)

    if args.non_normalized:
        non_norm = _load_non_normalized_tickers()
        failed = sorted(set(failed) | set(non_norm))
        print(f"Including {len(non_norm)} non-normalized tickers")

    if not failed:
        print("No failed tickers to refetch.")
        return

    print(f"Refetching {len(failed)} tickers...")
    fetcher = EnhancedDataFetcher()
    fetcher.all_tickers = master_list

    still_failed = []
    success_count = 0

    with tqdm(total=len(failed), desc="Refetch", unit="ticker", file=sys.stdout) as pbar:
        for i, ticker in enumerate(failed):
            data = fetcher._fetch_single_ticker_with_retry(ticker, force_fetch=True)
            if data is not None:
                success_count += 1
                pbar.set_postfix_str(f"{ticker} OK")
            else:
                still_failed.append(ticker)
                pbar.set_postfix_str(f"{ticker} FAIL")
            pbar.update(1)
            if (i + 1) % BATCH_SIZE == 0 and i + 1 < len(failed):
                time.sleep(RATE_LIMIT_DELAY)

    print()
    print(f"Successful: {success_count}/{len(failed)}")
    print(f"Still failed: {len(still_failed)}")

    if still_failed:
        out_path = REPORTS_DIR / f"refetch_failed_tickers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        REPORTS_DIR.mkdir(exist_ok=True)
        with open(out_path, "w") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_attempted": len(failed),
                "success_count": success_count,
                "still_failed": still_failed,
            }, f, indent=2)
        print(f"Still-failed list saved to {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
