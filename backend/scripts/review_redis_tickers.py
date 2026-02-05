#!/usr/bin/env python3
"""
Review Redis ticker cache: TTL status, missing-from-master, and metrics coverage.
Read-only; does not modify Redis.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.redis_first_data_service import redis_first_data_service

# Expected metric keys for "all metrics in place"
EXPECTED_METRIC_KEYS = frozenset(['expected_return', 'volatility', 'risk', 'sharpe_ratio', 'data_points'])


def _decode_key(key):
    if isinstance(key, bytes):
        return key.decode('utf-8', errors='replace')
    return str(key)


def _ticker_from_key(key, prefix):
    s = _decode_key(key)
    if s.startswith(prefix):
        return s[len(prefix):].strip()
    return None


def run_review():
    r = redis_first_data_service.redis_client
    if not r:
        print("Redis unavailable. Cannot review.")
        return

    # Master list
    try:
        master_list = redis_first_data_service.all_tickers or []
    except Exception as e:
        master_list = []
        print(f"Warning: could not load master list: {e}")
    master_set = {t.upper() for t in master_list}
    total_master = len(master_set)

    # Redis keys (bytes when decode_responses=False)
    price_keys = r.keys("ticker_data:prices:*")
    sector_keys = r.keys("ticker_data:sector:*")
    metrics_keys = r.keys("ticker_data:metrics:*")

    tickers_with_prices = {_ticker_from_key(k, "ticker_data:prices:") for k in price_keys if _ticker_from_key(k, "ticker_data:prices:")}
    tickers_with_sector = {_ticker_from_key(k, "ticker_data:sector:") for k in sector_keys if _ticker_from_key(k, "ticker_data:sector:")}
    tickers_with_metrics_key = {_ticker_from_key(k, "ticker_data:metrics:") for k in metrics_keys if _ticker_from_key(k, "ticker_data:metrics:")}

    # Joined = have both prices and sector (canonical "cached" ticker)
    joined = tickers_with_prices & tickers_with_sector
    total_joined = len(joined)

    # Missing from master: in master but not in Redis (no full cache)
    missing_from_master = sorted(master_set - joined)
    missing_count = len(missing_from_master)

    # TTL and metrics per joined ticker
    ttl_buckets = {'expired': [], 'lt_24h': [], 'lt_7d': [], 'lt_30d': [], 'gte_30d': []}
    missing_metrics = []
    invalid_metrics = []

    for ticker in sorted(joined):
        pk = f"ticker_data:prices:{ticker}"
        sk = f"ticker_data:sector:{ticker}"
        mk = f"ticker_data:metrics:{ticker}"

        ttl_p = r.ttl(pk) if r.exists(pk) else -2
        ttl_s = r.ttl(sk) if r.exists(sk) else -2
        ttl_m = r.ttl(mk) if r.exists(mk) else -2

        # Effective TTL = min of prices/sector (both required)
        if ttl_p >= 0 and ttl_s >= 0:
            min_ttl = min(ttl_p, ttl_s)
        elif ttl_p >= 0:
            min_ttl = ttl_p
        elif ttl_s >= 0:
            min_ttl = ttl_s
        else:
            min_ttl = max(ttl_p, ttl_s)

        days_left = min_ttl / 86400.0 if min_ttl > 0 else 0
        if min_ttl <= 0:
            ttl_buckets['expired'].append((ticker, min_ttl, days_left))
        elif min_ttl < 86400:
            ttl_buckets['lt_24h'].append((ticker, min_ttl, days_left))
        elif min_ttl < 7 * 86400:
            ttl_buckets['lt_7d'].append((ticker, min_ttl, days_left))
        elif min_ttl < 30 * 86400:
            ttl_buckets['lt_30d'].append((ticker, min_ttl, days_left))
        else:
            ttl_buckets['gte_30d'].append((ticker, min_ttl, days_left))

        # Metrics: present and valid?
        if ticker not in tickers_with_metrics_key:
            missing_metrics.append(ticker)
        else:
            try:
                raw = r.get(mk)
                if not raw:
                    missing_metrics.append(ticker)
                else:
                    try:
                        data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
                    except Exception:
                        data = None
                    if not isinstance(data, dict):
                        invalid_metrics.append(ticker)
                    elif not EXPECTED_METRIC_KEYS.intersection(data.keys()):
                        invalid_metrics.append(ticker)
            except Exception:
                missing_metrics.append(ticker)

    # Report
    print("=" * 60)
    print("REDIS TICKER CACHE REVIEW (read-only)")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    print("--- COUNTS ---")
    print(f"Master list size:              {total_master}")
    print(f"Redis: prices keys              {len(price_keys)}")
    print(f"Redis: sector keys              {len(sector_keys)}")
    print(f"Redis: metrics keys             {len(metrics_keys)}")
    print(f"Tickers with both prices+sector: {total_joined}")
    print(f"Missing from master (not fetched): {missing_count}")
    print()
    print("--- TTL (time left until expiry) ---")
    print(f"Expired (<=0):     {len(ttl_buckets['expired'])} tickers")
    print(f"< 24 hours left:   {len(ttl_buckets['lt_24h'])} tickers")
    print(f"< 7 days left:     {len(ttl_buckets['lt_7d'])} tickers")
    print(f"< 30 days left:    {len(ttl_buckets['lt_30d'])} tickers")
    print(f">= 30 days left:   {len(ttl_buckets['gte_30d'])} tickers")
    if ttl_buckets['gte_30d']:
        sample = ttl_buckets['gte_30d'][:3]
        days_vals = [x[2] for x in sample]
        print(f"  (sample days left: {[round(d, 1) for d in days_vals]})")
    print()
    print("--- MISSING FROM MASTER (in master list but not in Redis with full data) ---")
    print(f"Count: {missing_count}")
    if missing_from_master:
        sample = missing_from_master[:25]
        print(f"Sample (up to 25): {', '.join(sample)}")
    print()
    print("--- METRICS ---")
    print(f"Tickers with prices+sector but no metrics key: {len(missing_metrics)}")
    print(f"Tickers with invalid/empty metrics:            {len(invalid_metrics)}")
    if missing_metrics:
        print(f"Sample missing metrics (up to 15): {', '.join(missing_metrics[:15])}")
    if invalid_metrics:
        print(f"Sample invalid metrics (up to 15): {', '.join(invalid_metrics[:15])}")
    print()
    metrics_ok = total_joined - len(missing_metrics) - len(invalid_metrics)
    print(f"Tickers with prices+sector+valid metrics: {metrics_ok} / {total_joined}")
    print("=" * 60)


if __name__ == "__main__":
    run_review()
