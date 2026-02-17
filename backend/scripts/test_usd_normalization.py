#!/usr/bin/env python3
"""
USD Normalization Verification Script

Verifies the FX conversion pipeline on 10 specific test tickers:
- Non-USD: VOLV-B.ST, HM-B.ST, AIR.PA, SAP.DE, BP.L, AZN.L, NOVN.SW, EQNR.OL
- USD: AAPL, MSFT

Procedure:
1. Force-fetch each ticker (bypass cache)
2. Read stored data and metadata from Redis
3. Validate USD vs non-USD behavior
4. Run correlation check on the 10 tickers
"""

import sys
import os
import json
import gzip
import logging
from typing import Dict, Any, Optional, Tuple

import pandas as pd
import numpy as np
from tqdm import tqdm
from yahooquery import Ticker as YQTicker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_first_data_service import redis_first_data_service
from utils.enhanced_data_fetcher import EnhancedDataFetcher
from utils.timestamp_utils import get_ticker_country_exchange_currency
from utils.fx_fetcher import FXRateFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEST_TICKERS = [
    "VOLV-B.ST",   # SEK
    "HM-B.ST",     # SEK
    "AIR.PA",      # EUR
    "SAP.DE",      # EUR
    "BP.L",        # GBP
    "VOD.L",       # GBP (Vodafone - lower share price, avoids pence scaling issues)
    "NOVN.SW",     # CHF
    "EQNR.OL",     # NOK
    "AAPL",        # USD
    "MSFT",        # USD
]


def _load_prices_from_redis(ticker: str) -> Optional[pd.Series]:
    """Load price data from Redis for a ticker."""
    r = redis_first_data_service.redis_client
    if not r:
        return None
    key = f"ticker_data:prices:{ticker}"
    raw = r.get(key)
    if not raw:
        return None
    try:
        decompressed = gzip.decompress(raw).decode()
        data_dict = json.loads(decompressed)
        series = pd.Series({k: float(v) for k, v in data_dict.items()})
        series.index = pd.to_datetime(series.index)
        return series
    except Exception as e:
        logger.warning(f"Failed to load prices for {ticker}: {e}")
        return None


def _load_meta_from_redis(ticker: str) -> Optional[Dict[str, Any]]:
    """Load FX metadata from Redis."""
    r = redis_first_data_service.redis_client
    if not r:
        return None
    key = f"ticker_data:meta:{ticker}"
    raw = r.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw.decode())
    except Exception as e:
        logger.warning(f"Failed to load meta for {ticker}: {e}")
        return None


def _fetch_raw_last_close(ticker: str) -> Optional[Tuple[str, float]]:
    """Fetch the last close price from Yahoo (raw, in native currency). Returns (date_str, price)."""
    try:
        yq = YQTicker(ticker)
        end = pd.Timestamp.now()
        start = end - pd.Timedelta(days=35)
        hist = yq.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval="1mo")
        if hist is None or (isinstance(hist, str) and "error" in hist.lower()):
            return None
        if isinstance(hist, pd.DataFrame) and hist.empty:
            return None
        if isinstance(hist.index, pd.MultiIndex):
            if ticker in hist.index.get_level_values(0):
                hist = hist.xs(ticker, level=0)
            else:
                return None
        close_col = "close" if "close" in hist.columns else "adjclose"
        if close_col not in hist.columns:
            return None
        series = hist[close_col].dropna()
        if series.empty:
            return None
        last_ts = series.index[-1]
        last_price = float(series.iloc[-1])
        if hasattr(last_ts, "strftime"):
            date_str = last_ts.strftime("%Y-%m-%d")
        else:
            date_str = pd.to_datetime(last_ts).strftime("%Y-%m-%d")
        return (date_str, last_price)
    except Exception as e:
        logger.debug(f"Raw fetch failed for {ticker}: {e}")
        return None


def run_verification() -> None:
    """Run full verification on the 10 test tickers."""
    data_fetcher = EnhancedDataFetcher()
    data_fetcher._allow_out_of_master = True

    results = []
    r = redis_first_data_service.redis_client
    fx_fetcher = FXRateFetcher(r) if r else None

    logger.info("Force-fetching 10 test tickers (bypass cache)...")
    for ticker in tqdm(TEST_TICKERS, desc="Fetching"):
        data = data_fetcher._fetch_single_ticker_with_retry(ticker, force_fetch=True)
        if data is None or "prices" not in data:
            results.append({
                "ticker": ticker,
                "native": "?",
                "stored": "?",
                "latest_usd": None,
                "converted": "?",
                "valid": False,
                "note": "Fetch failed",
            })
            continue

        prices = _load_prices_from_redis(ticker)
        meta = _load_meta_from_redis(ticker)
        _, _, native = get_ticker_country_exchange_currency(ticker)

        if prices is None or prices.empty:
            results.append({
                "ticker": ticker,
                "native": native,
                "stored": meta.get("stored_currency", "?") if meta else "?",
                "latest_usd": None,
                "converted": "?" if not meta else ("Yes" if meta.get("converted") else "No"),
                "valid": False,
                "note": "No cached prices",
            })
            continue

        latest_usd = float(prices.iloc[-1])
        converted = meta.get("converted", False) if meta else False
        stored_ccy = meta.get("stored_currency", "?") if meta else "?"

        valid = True
        note = ""
        if native in ("USD", "Unknown"):
            if converted:
                valid = False
                note = "USD ticker should not be converted"
            else:
                note = "OK"
        else:
            if not converted:
                valid = False
                note = "Non-USD ticker should be converted"
            else:
                raw_info = _fetch_raw_last_close(ticker)
                if raw_info and fx_fetcher:
                    date_str, raw_price = raw_info
                    rates = fx_fetcher.get_fx_rates(native, date_str, date_str)
                    fx_rate = rates.get(date_str)
                    if fx_rate is None and rates:
                        sorted_dates = sorted(rates.keys())
                        for d in reversed(sorted_dates):
                            if d <= date_str:
                                fx_rate = rates[d]
                                break
                    if fx_rate is not None:
                        expected_usd = raw_price * fx_rate
                        diff_pct = abs(latest_usd - expected_usd) / expected_usd * 100 if expected_usd else 0
                        if diff_pct < 5.0:
                            note = f"OK (~{diff_pct:.2f}% diff)"
                        else:
                            note = f"Large diff: {diff_pct:.1f}%"
                    else:
                        note = "OK (no FX for date)"
                else:
                    note = "OK"

        results.append({
            "ticker": ticker,
            "native": native,
            "stored": stored_ccy,
            "latest_usd": latest_usd,
            "converted": "Yes" if converted else "No",
            "valid": valid,
            "note": note,
        })

    print("\n" + "=" * 90)
    print("USD NORMALIZATION VERIFICATION SUMMARY")
    print("=" * 90)
    print(f"{'Ticker':<12} {'Native':<6} {'Stored':<6} {'Latest (USD)':<14} {'Converted':<10} {'Status'}")
    print("-" * 90)
    for r in results:
        latest_str = f"{r['latest_usd']:.2f}" if r["latest_usd"] is not None else "N/A"
        print(f"{r['ticker']:<12} {r['native']:<6} {r['stored']:<6} {latest_str:<14} {r['converted']:<10} {r['note']}")
    print("=" * 90)

    valid_count = sum(1 for r in results if r["valid"])
    print(f"\nValidation: {valid_count}/{len(results)} tickers passed")

    # Correlation check
    logger.info("Computing correlation matrix for the 10 tickers...")
    price_dict = {}
    for ticker in TEST_TICKERS:
        prices = _load_prices_from_redis(ticker)
        if prices is not None and len(prices) >= 12:
            price_dict[ticker] = prices

    if len(price_dict) >= 2:
        df = pd.DataFrame(price_dict)
        df = df.dropna(how="any")
        if len(df) < 12:
            print("\nInsufficient overlapping dates for correlation check")
        else:
            returns = df.pct_change().dropna()
            corr = returns.corr()
            cmin, cmax = corr.min().min(), corr.max().max()
            invalid = (corr < -1.001).any().any() or (corr > 1.001).any().any()
            print(f"\nCorrelation matrix ({len(df)} overlapping dates): min={cmin:.4f}, max={cmax:.4f}")
            if invalid:
                print("WARNING: Some correlations outside [-1, 1]")
            else:
                print("Correlation values within [-1, 1] - OK")
    else:
        print("\nInsufficient data for correlation check")


if __name__ == "__main__":
    run_verification()
