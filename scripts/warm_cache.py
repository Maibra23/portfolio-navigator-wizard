#!/usr/bin/env python3
"""
Warm Redis cache with common tickers (top 50-100 stocks).

Connects to Redis using REDIS_URL from environment and populates ticker data
by calling the backend data service (run from project root with backend on PYTHONPATH)
or by calling the backend warm-cache API if BACKEND_URL is set.

Usage:
  # Using backend code (from repo root, backend venv active):
  export REDIS_URL=redis://localhost:6379
  python scripts/warm_cache.py

  python scripts/warm_cache.py --batch-size 10
  python scripts/warm_cache.py --ticker-list path/to/tickers.txt

  # Using backend API (backend must be running):
  export BACKEND_URL=http://localhost:8000
  python scripts/warm_cache.py

Options:
  --ticker-list FILE   One ticker per line (default: built-in top ~100)
  --batch-size N       Process N tickers per batch (default: 20)
"""

import argparse
import os
import sys
import time

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
except ImportError:
    Fore = type("Fore", (), {"GREEN": "", "RED": "", "YELLOW": "", "CYAN": ""})()
    Style = type("Style", (), {"RESET_ALL": ""})()

# Default top tickers (top ~50-100 by market cap / liquidity)
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK.B", "TSLA", "JPM", "V",
    "JNJ", "WMT", "PG", "UNH", "MA", "HD", "DIS", "PYPL", "BAC", "ADBE",
    "XOM", "CRM", "NFLX", "CSCO", "PEP", "KO", "AVGO", "COST", "ABT", "ACN",
    "NKE", "TMO", "DHR", "MCD", "ABBV", "TXN", "CVX", "NEE", "PM", "WFC",
    "BMY", "INTC", "AMD", "ORCL", "UPS", "RTX", "HON", "AMGN", "QCOM", "INTU",
    "LOW", "AMAT", "SPGI", "AXP", "LMT", "SBUX", "DE", "CAT", "BKNG", "ADI",
    "MDT", "GILD", "CVS", "SYK", "TJX", "C", "BLK", "PLD", "SO", "DUK",
    "ISRG", "BDX", "ZTS", "BSX", "REGN", "EOG", "SLB", "MMC", "CI", "CMCSA",
    "APD", "APTV", "KLAC", "SNPS", "CDNS", "MAR", "ITW", "WM", "ETN", "ECL",
]

def load_tickers(path: str | None) -> list[str]:
    if not path or not os.path.isfile(path):
        return []
    with open(path) as f:
        return [line.strip().upper() for line in f if line.strip()]


def progress_bar(current: int, total: int, width: int = 40) -> str:
    if total <= 0:
        return "[" + "=" * width + "] 100%"
    pct = current / total
    filled = int(width * pct)
    bar = "=" * filled + " " * (width - filled)
    return f"[{bar}] {pct*100:.1f}%"


def warm_via_backend_api(base_url: str, tickers: list[str], batch_size: int) -> dict:
    import urllib.request
    import json
    base_url = base_url.rstrip("/")
    # Endpoint that triggers cache for a ticker (e.g. search or a minimal endpoint)
    # We use search-tickers which will load data for matching tickers
    done = 0
    failed = 0
    start = time.time()
    total = len(tickers)
    for i in range(0, total, batch_size):
        batch = tickers[i : i + batch_size]
        for ticker in batch:
            try:
                url = f"{base_url}/api/v1/portfolio/search-tickers?q={ticker}&limit=1"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=30) as r:
                    r.read()
                done += 1
            except Exception:
                failed += 1
            print(f"\r  {progress_bar(done + failed, total)} done={done} fail={failed}", end="")
        time.sleep(0.5)
    elapsed = time.time() - start
    return {"cached": done, "failures": failed, "time_seconds": round(elapsed, 2)}


def warm_via_redis(tickers: list[str], batch_size: int) -> dict:
    # Add backend to path so we can use RedisFirstDataService
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend = os.path.join(repo, "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    if repo not in sys.path:
        sys.path.insert(0, repo)
    os.chdir(backend)
    from utils.redis_first_data_service import RedisFirstDataService
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    service = RedisFirstDataService(redis_url=redis_url)
    if not service.redis_client:
        raise RuntimeError("Redis connection failed. Check REDIS_URL.")
    done = 0
    failed = 0
    start = time.time()
    total = len(tickers)
    for i, ticker in enumerate(tickers):
        try:
            data = service.get_monthly_data(ticker)
            if data:
                done += 1
            else:
                failed += 1
        except Exception:
            failed += 1
        print(f"\r  {progress_bar(i + 1, total)} done={done} fail={failed}", end="")
    print()
    elapsed = time.time() - start
    return {"cached": done, "failures": failed, "time_seconds": round(elapsed, 2)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Warm Redis cache with common tickers")
    parser.add_argument("--ticker-list", type=str, help="Path to file with one ticker per line")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size (default 20)")
    args = parser.parse_args()

    if args.ticker_list:
        tickers = load_tickers(args.ticker_list)
        if not tickers:
            print(f"{Fore.RED}Ticker list file empty or not found: {args.ticker_list}{Style.RESET_ALL}")
            return 1
    else:
        tickers = DEFAULT_TICKERS

    print(f"{Fore.CYAN}Warming cache for {len(tickers)} tickers{Style.RESET_ALL}")
    backend_url = os.getenv("BACKEND_URL")
    try:
        if backend_url:
            result = warm_via_backend_api(backend_url, tickers, args.batch_size)
        else:
            result = warm_via_redis(tickers, args.batch_size)
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        return 1

    print(f"{Fore.GREEN}Summary:{Style.RESET_ALL}")
    print(f"  Items cached: {result['cached']}, Failures: {result['failures']}, Time taken: {result['time_seconds']}s")
    return 0 if result["failures"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
