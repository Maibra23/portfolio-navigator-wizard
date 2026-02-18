#!/usr/bin/env python3
"""
Remove the 15 tickers that have no meta (legacy cache) by deleting their
Redis keys (prices, sector, metrics, meta). After running this, run
refetch_failed_tickers.py to refetch them with the updated USD/meta system.

Usage: python backend/scripts/remove_legacy_tickers_without_meta.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from utils.redis_first_data_service import redis_first_data_service

# 15 tickers without meta from verify_redis_content report
TICKERS_WITHOUT_META = [
    "BGEO.L",
    "IPG",
    "ROO.L",
    "TKWY.AS",
    "HELN.SW",
    "SYDB.CO",
    "SPT.L",
    "ALPH.L",
    "COLOB.CO",
    "AGRP.L",
    "FI",
    "SXS.L",
    "KURN.SW",
    "BALN.SW",
    "K",
]

KEY_TYPES = ("prices", "sector", "metrics", "meta")


def main():
    print("=" * 70)
    print("Remove legacy tickers (no meta) from Redis")
    print("=" * 70)

    redis_client = redis_first_data_service.redis_client
    if not redis_client:
        print("Redis client not available. Ensure Redis is running.")
        sys.exit(1)

    deleted_keys = 0
    it = tqdm(TICKERS_WITHOUT_META, desc="Removing tickers", unit="ticker") if HAS_TQDM else TICKERS_WITHOUT_META
    for ticker in it:
        for data_type in KEY_TYPES:
            key = f"ticker_data:{data_type}:{ticker}"
            if redis_client.delete(key):
                deleted_keys += 1
        if HAS_TQDM:
            it.set_postfix_str(ticker)

    print(f"Deleted keys for {len(TICKERS_WITHOUT_META)} tickers (total keys removed: {deleted_keys}).")
    print()
    print("Next step: run refetch_failed_tickers.py to refetch these tickers with USD/meta.")
    print("Done.")


if __name__ == "__main__":
    main()
