#!/usr/bin/env python3
"""
Full Refetch with First-Batch Gate

Option B: Refetch all tickers with FX normalization.
- CSV (fetchable_master_list_validated_latest.csv) as primary source when Redis empty
- Progress bar for fetch+normalization per batch
- Resume: continue from last fetched ticker if interrupted
- Gate: stop if first batch success/normalization < 95%
"""

import gzip
import json
import logging
import os
import sys
import time
from typing import Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tqdm import tqdm

from utils.redis_first_data_service import redis_first_data_service
from utils.enhanced_data_fetcher import EnhancedDataFetcher
from utils.timestamp_utils import get_ticker_country_exchange_currency, normalize_ticker_format
from utils.enhanced_data_fetcher import BATCH_SIZE, RATE_LIMIT_DELAY

_FLUSH = {"flush": True}
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "reports", "full_refetch_progress.json")
CSV_BACKUP_DIR = os.path.join(os.path.dirname(__file__), "reports")

GATE_SUCCESS_THRESHOLD = 95.0
GATE_NORMALIZED_THRESHOLD = 95.0


def _load_meta(ticker: str) -> Optional[dict]:
    r = redis_first_data_service.redis_client
    if not r:
        return None
    for t in (ticker, normalize_ticker_format(ticker)):
        key = f"ticker_data:meta:{t}"
        raw = r.get(key)
        if raw:
            try:
                return json.loads(raw.decode())
            except Exception:
                pass
    return None


def _check_first_batch_gate(batch: list, results: dict) -> Tuple[bool, str]:
    total = len(batch)
    successful = len(results)
    success_rate = (successful / total * 100) if total else 0

    non_usd_tickers = [
        t for t in batch
        if get_ticker_country_exchange_currency(t)[2] not in ("USD", "Unknown")
    ]
    if not non_usd_tickers:
        normalized_rate = 100.0
        msg = "No non-USD in first batch; normalization N/A"
    else:
        non_usd_success = [t for t in non_usd_tickers if t in results]
        non_usd_normalized = sum(
            1 for t in non_usd_success
            if _load_meta(t) and _load_meta(t).get("converted") is True
        )
        normalized_rate = (non_usd_normalized / len(non_usd_success) * 100) if non_usd_success else 0
        msg = f"Non-USD: {non_usd_normalized}/{len(non_usd_success)} normalized"

    pass_gate = success_rate >= GATE_SUCCESS_THRESHOLD and normalized_rate >= GATE_NORMALIZED_THRESHOLD
    return pass_gate, f"Success: {success_rate:.1f}% ({successful}/{total}) | {msg} | Normalized: {normalized_rate:.1f}%"


def _load_progress() -> Set[str]:
    if not os.path.isfile(PROGRESS_FILE):
        return set()
    try:
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
        return set(data.get("completed_tickers", []))
    except Exception:
        return set()


def _save_progress(completed: Set[str], tickers: list) -> None:
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "completed_tickers": list(completed),
            "total_tickers": len(tickers),
            "progress_pct": len(completed) / len(tickers) * 100 if tickers else 0,
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, f, indent=2)


def _clear_progress() -> None:
    if os.path.isfile(PROGRESS_FILE):
        try:
            os.remove(PROGRESS_FILE)
        except Exception:
            pass


def main():
    def out(msg: str) -> None:
        print(msg, **_FLUSH)

    for name in ("utils.enhanced_data_fetcher", "utils.pdf_report_generator", "routers.portfolio"):
        logging.getLogger(name).setLevel(logging.WARNING)

    out("=" * 70)
    out("FULL REFETCH - FX Normalization + Resume")
    out("=" * 70)
    out("Source: Redis / CSV (fetchable_master_list_validated_latest.csv) when Redis empty")
    out("Resume: Continues from last fetched ticker if interrupted.")
    out("Gate: Stop if first batch success or normalization < 95%")
    out("")

    redis_first_data_service.invalidate_ticker_list_cache()
    fetcher = EnhancedDataFetcher()
    all_tickers = list(fetcher.all_tickers)

    # Bootstrap from CSV if still empty (Redis + list_cached_tickers empty)
    if not all_tickers:
        csv_path = os.path.join(CSV_BACKUP_DIR, "fetchable_master_list_validated_latest.csv")
        if os.path.isfile(csv_path):
            out(f"Master list empty. Loading from CSV: {csv_path}")
            import csv as csv_module
            tickers_from_csv = []
            with open(csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv_module.reader(f)
                next(reader, None)
                for row in reader:
                    if row and row[0].strip():
                        tickers_from_csv.append(row[0].strip())
            if tickers_from_csv:
                all_tickers = tickers_from_csv
                fetcher.all_tickers = all_tickers
                r = redis_first_data_service.redis_client
                if r:
                    r.setex(
                        "master_ticker_list_validated",
                        365 * 24 * 3600,
                        gzip.compress(json.dumps(all_tickers).encode())
                    )
                redis_first_data_service.invalidate_ticker_list_cache()
                out(f"  Loaded {len(all_tickers)} tickers from CSV and seeded Redis.")
        if not all_tickers:
            out("Bootstrapping from S&P 500 + NASDAQ 100 + ETFs...")
            try:
                sp500 = fetcher._fetch_sp500_tickers()
                nasdaq = fetcher._fetch_nasdaq100_tickers()
                etfs = fetcher._fetch_top_etfs()
                all_tickers = list(dict.fromkeys(sp500 + nasdaq + etfs))
                fetcher.all_tickers = all_tickers
                if redis_first_data_service.redis_client and all_tickers:
                    redis_first_data_service.redis_client.setex(
                        "master_ticker_list",
                        24 * 3600,
                        gzip.compress(json.dumps(all_tickers).encode())
                    )
                out(f"  Loaded {len(all_tickers)} tickers.")
            except Exception as e:
                out(f"Bootstrap failed: {e}")
                sys.exit(1)

    completed = _load_progress()
    tickers_to_fetch = [t for t in all_tickers if t not in completed]
    total_tickers = len(all_tickers)
    remaining = len(tickers_to_fetch)

    if completed:
        out(f"Resume: {len(completed)} already done, {remaining} remaining.")
    out(f"Total tickers: {total_tickers} | To fetch: {remaining}")
    out(f"Batch size: {BATCH_SIZE}")
    out("")

    if not tickers_to_fetch:
        out("All tickers already fetched. Run complete.")
        fetcher._publish_validated_master_list()
        _clear_progress()
        return

    total_batches = (remaining + BATCH_SIZE - 1) // BATCH_SIZE
    start_time = time.time()
    all_results = {t: None for t in completed}
    batch_times = []

    with tqdm(total=remaining, desc="Fetch+Normalize", unit="ticker", file=sys.stdout) as pbar:
        for batch_idx in range(total_batches):
            i = batch_idx * BATCH_SIZE
            batch = tickers_to_fetch[i : i + BATCH_SIZE]
            batch_num = batch_idx + 1

            batch_start = time.time()
            pbar.set_postfix_str(f"Batch {batch_num}/{total_batches}")

            for ticker in batch:
                data = fetcher._fetch_single_ticker_with_retry(ticker, force_fetch=True)
                if data is not None:
                    all_results[ticker] = data
                    completed.add(ticker)
                    fetcher.stats["successful"] += 1
                    pbar.set_postfix_str(f"Batch {batch_num}/{total_batches} | {ticker} OK")
                else:
                    fetcher.stats["failed"] += 1
                    pbar.set_postfix_str(f"Batch {batch_num}/{total_batches} | {ticker} FAIL")
                fetcher.stats["total_processed"] += 1
                pbar.update(1)
                _save_progress(completed, all_tickers)

            if fetcher.stats.get("stopped_due_to_throttling"):
                pbar.write("STOP: Throttling detected. Progress saved. Run again to resume.")
                sys.exit(1)

            batch_elapsed = time.time() - batch_start
            batch_times.append(batch_elapsed)
            success_count = sum(1 for t in batch if t in all_results and all_results[t])

            pbar.write(f"Batch {batch_num} done: {success_count}/{len(batch)} in {batch_elapsed:.1f}s")

            if batch_num == 1:
                pass_gate, gate_msg = _check_first_batch_gate(batch, {t: all_results[t] for t in batch if all_results[t]})
                pbar.write("GATE CHECK (first batch):")
                pbar.write(f"  {gate_msg}")
                if not pass_gate:
                    pbar.write("STOP: Gate failed. Progress saved. Fix and run again to resume.")
                    sys.exit(1)
                pbar.write("  Gate PASSED.")

            if batch_idx < total_batches - 1:
                eta_batches = total_batches - batch_num
                avg_batch_time = sum(batch_times) / len(batch_times)
                eta_str = f"{int(eta_batches * avg_batch_time // 60)}m {int(eta_batches * avg_batch_time % 60)}s"
                pbar.write(f"Waiting {RATE_LIMIT_DELAY}s... (ETA: {eta_str})")
                time.sleep(RATE_LIMIT_DELAY)

    total_elapsed = time.time() - start_time
    success_rate = (fetcher.stats["successful"] / total_tickers * 100) if total_tickers else 0

    fetcher._publish_validated_master_list()
    _clear_progress()

    out("")
    out("=" * 70)
    out("FULL REFETCH COMPLETE")
    out("=" * 70)
    out(f"  Successful:  {fetcher.stats['successful']}/{total_tickers}")
    out(f"  Failed:      {fetcher.stats['failed']}")
    out(f"  Success rate: {success_rate:.1f}%")
    out(f"  Total time:  {int(total_elapsed // 60)}m {int(total_elapsed % 60)}s")
    out("  Validated list saved to CSV + Redis.")
    out("=" * 70)


if __name__ == "__main__":
    main()
