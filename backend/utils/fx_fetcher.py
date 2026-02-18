#!/usr/bin/env python3
"""
FX Rate Fetcher - USD Price Normalization

Fetches historical FX rates from Yahoo Finance (via yahooquery) and caches in Redis.
Used to convert non-USD ticker prices to USD at storage time.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from yahooquery import Ticker as YQTicker

logger = logging.getLogger(__name__)

# Supported currency -> Yahoo FX ticker (XXXUSD=X means 1 XXX = rate USD)
CURRENCY_TO_YAHOO_TICKER = {
    "EUR": "EURUSD=X",
    "GBP": "GBPUSD=X",
    "SEK": "SEKUSD=X",
    "CHF": "CHFUSD=X",
    "NOK": "NOKUSD=X",
    "DKK": "DKKUSD=X",
    "PLN": "PLNUSD=X",
}

FX_CACHE_TTL_SECONDS = 86400  # 24 hours
FX_CACHE_KEY_PREFIX = "fx_rates"


class FXRateFetcher:
    """
    Fetches and caches FX rates from Yahoo Finance.
    Converts price series from local currency to USD using historical rates.
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client

    def _get_cache_key(self, from_currency: str) -> str:
        return f"{FX_CACHE_KEY_PREFIX}:{from_currency}:USD"

    def _load_from_cache(self, from_currency: str) -> Optional[Dict[str, float]]:
        """Load cached FX rates from Redis."""
        if not self.redis:
            return None
        try:
            key = self._get_cache_key(from_currency)
            raw = self.redis.get(key)
            if raw:
                data = json.loads(raw.decode())
                return {k: float(v) for k, v in data.items()}
        except Exception as e:
            logger.debug(f"FX cache read failed for {from_currency}: {e}")
        return None

    def _save_to_cache(self, from_currency: str, rates: Dict[str, float]) -> None:
        """Cache FX rates in Redis with 24h TTL."""
        if not self.redis:
            return
        try:
            key = self._get_cache_key(from_currency)
            self.redis.setex(key, FX_CACHE_TTL_SECONDS, json.dumps(rates).encode())
            logger.debug(f"FX rates cached for {from_currency}: {len(rates)} dates")
        except Exception as e:
            logger.warning(f"FX cache write failed for {from_currency}: {e}")

    def get_fx_rates(self, from_currency: str, start_date: str, end_date: str) -> Dict[str, float]:
        """
        Fetch historical daily FX rates from Yahoo.

        Args:
            from_currency: 3-letter currency code (e.g., SEK, EUR)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dict mapping date strings (YYYY-MM-DD) to rate (float).
            Rate means: 1 unit of from_currency = rate USD.
            Missing dates (e.g. holidays) are forward-filled from last known rate.
        """
        from_currency = from_currency.upper()
        if from_currency == "USD":
            return {}

        yahoo_ticker = CURRENCY_TO_YAHOO_TICKER.get(from_currency)
        if not yahoo_ticker:
            logger.warning(f"FX: Unsupported currency {from_currency}, no conversion")
            return {}

        cache_key = self._get_cache_key(from_currency)
        cached = self._load_from_cache(from_currency)
        if cached:
            cached_dates = sorted(cached.keys())
            if cached_dates:
                c_start_s = cached_dates[0]
                c_end_s = cached_dates[-1]
                req_start_s = pd.to_datetime(start_date).strftime("%Y-%m-%d") if start_date else ""
                req_end_s = pd.to_datetime(end_date).strftime("%Y-%m-%d") if end_date else ""
                if req_start_s and req_end_s and c_start_s <= req_start_s and c_end_s >= req_end_s:
                    subset = {d: cached[d] for d in cached_dates}
                    return self._forward_fill_rates(subset, start_date, end_date)

        try:
            yq = YQTicker(yahoo_ticker)
            hist = yq.history(
                start=start_date,
                end=end_date,
                interval="1d",
                adj_timezone=False,
            )
            if hist is None or (isinstance(hist, str) and "error" in hist.lower()):
                logger.warning(f"FX: No data for {yahoo_ticker}")
                return {}
            if isinstance(hist, pd.DataFrame) and hist.empty:
                return {}

            if isinstance(hist.index, pd.MultiIndex):
                if yahoo_ticker in hist.index.get_level_values(0):
                    hist = hist.xs(yahoo_ticker, level=0)
                else:
                    return {}

            close_col = "close" if "close" in hist.columns else "adjclose"
            if close_col not in hist.columns:
                return {}

            series = hist[close_col].dropna()
            rates = {}
            for ts, val in series.items():
                if hasattr(ts, "strftime"):
                    dt = ts
                else:
                    dt = pd.to_datetime(ts)
                if hasattr(dt, "tz_localize") and dt.tzinfo is not None:
                    dt = dt.tz_localize(None)
                date_str = dt.strftime("%Y-%m-%d")
                rates[date_str] = float(val)

            if rates:
                rates = self._forward_fill_rates(rates, start_date, end_date)
                self._save_to_cache(from_currency, rates)
            return rates
        except Exception as e:
            logger.warning(f"FX: Failed to fetch {yahoo_ticker}: {e}")
            return {}

    def _forward_fill_rates(
        self, rates: Dict[str, float], start_date: str, end_date: str
    ) -> Dict[str, float]:
        """Forward-fill missing dates (e.g. weekends/holidays) from last known rate."""
        if not rates:
            return {}
        sorted_dates = sorted(rates.keys())
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        result = {}
        last_rate = None
        rate_idx = 0
        for d in date_range:
            ds = d.strftime("%Y-%m-%d")
            while rate_idx < len(sorted_dates) and sorted_dates[rate_idx] <= ds:
                last_rate = rates[sorted_dates[rate_idx]]
                rate_idx += 1
            if last_rate is not None:
                result[ds] = last_rate
        if not result and sorted_dates:
            for ds in sorted_dates:
                if start_date <= ds <= end_date:
                    result[ds] = rates[ds]
        return result

    def _to_date_str(self, val) -> str:
        """Normalize any date-like value to YYYY-MM-DD string. Avoids datetime vs date comparison."""
        if val is None:
            return ""
        try:
            ts = pd.to_datetime(val)
            return ts.strftime("%Y-%m-%d")
        except Exception:
            return str(val)[:10] if val else ""

    def convert_series(self, prices: pd.Series, from_currency: str) -> pd.Series:
        """
        Convert a price series from local currency to USD.

        Handles mixed tz-aware/tz-naive and datetime/date index types by normalizing
        to naive DatetimeIndex before conversion. Uses string date comparisons to
        avoid datetime.datetime vs datetime.date comparison errors.

        Args:
            prices: Series of prices (index = datetime/date/Period)
            from_currency: 3-letter currency code of the prices

        Returns:
            New Series with USD prices (price_usd = price_local * fx_rate).
            Dates are aligned; missing FX dates use forward-filled rates.
        """
        from_currency = from_currency.upper()
        if from_currency == "USD" or from_currency == "UNKNOWN":
            return prices.copy()

        if prices is None or prices.empty:
            return prices

        idx = prices.index
        try:
            vals = []
            for t in idx:
                ts = pd.Timestamp(t)
                if ts.tz is not None:
                    ts = pd.Timestamp(ts.strftime("%Y-%m-%d %H:%M:%S"))
                vals.append(ts)
            idx = pd.DatetimeIndex(vals)
        except Exception as e:
            try:
                vals = [pd.Timestamp(str(pd.Timestamp(t))[:10]) for t in idx]
                idx = pd.DatetimeIndex(vals)
            except Exception as e2:
                logger.warning(f"FX: Could not normalize price index: {e}, {e2}")
                return prices.copy()
        min_date = self._to_date_str(idx.min())
        max_date = self._to_date_str(idx.max())
        if not min_date or not max_date:
            return prices.copy()

        rates = self.get_fx_rates(from_currency, min_date, max_date)
        if not rates:
            logger.warning(f"FX: No rates for {from_currency}, returning original prices")
            return prices.copy()

        sorted_rate_dates = sorted(rates.keys())
        usd_prices = []
        for i, ts in enumerate(idx):
            ds = self._to_date_str(ts)
            rate = rates.get(ds)
            if rate is None:
                for d in reversed(sorted_rate_dates):
                    if d <= ds:
                        rate = rates[d]
                        break
            if rate is None:
                rate = 1.0
                logger.debug(f"FX: No rate for {ds}, using 1.0")
            orig = float(prices.iloc[i])
            usd_prices.append(orig * rate)

        return pd.Series(usd_prices, index=idx)
