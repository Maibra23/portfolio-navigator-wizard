import redis
import json
import gzip
import yfinance as yf
import pandas as pd
import logging
import time

from datetime import timedelta
from typing import Optional, Dict, List, Any

from .ticker_store import ticker_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDataFetcher:
    """
    Data fetcher for monthly adjusted close prices with Redis caching,
    batch downloading, gzip compression, and in-memory ticker validation.
    Supports S&P 500, Nasdaq 100, Dow 30, and key ETFs for benchmarking.
    """

    def __init__(self):
        # Initialize Redis with retry logic
        self.r = self._init_redis_with_retry()
        # Load our combined index tickers and append ETFs
        self.master_tickers = ticker_store.get_all_tickers()

        # Append selected ETFs for passive benchmark inclusion
        etf_list = ["VOO", "SPY", "IVV", "VTI", "VTS", "QQQ", "VUG", "VEA", "IEFA", "VTV", "BND"]
        for etf in etf_list:
            if etf not in self.master_tickers:
                self.master_tickers.append(etf)

        logger.info(f"Initialized with {len(self.master_tickers)} master tickers including ETFs")

    def _init_redis_with_retry(self, max_retries: int = 2) -> Optional[redis.Redis]:
        """
        Initialize Redis connection with retry logic
        Returns: Redis connection or None if failed after retries
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting Redis connection (attempt {attempt + 1}/{max_retries})")
                r = redis.Redis(host='localhost', port=6379, decode_responses=False, socket_timeout=5)
                # Test connection
                r.ping()
                logger.info("✅ Redis connection established successfully")
                return r
            except Exception as e:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info("Retrying Redis connection in 2 seconds...")
                    time.sleep(2)
                else:
                    logger.error(f"❌ Redis connection failed after {max_retries} attempts. Running without caching.")
                    return None

    def _compress_data(self, data: Dict[str, Any]) -> bytes:
        json_str = json.dumps(data)
        return gzip.compress(json_str.encode('utf-8'))

    def _decompress_data(self, compressed_data: bytes) -> Dict[str, Any]:
        json_str = gzip.decompress(compressed_data).decode('utf-8')
        return json.loads(json_str)

    def _redis_operation_with_fallback(self, operation, fallback_value=None):
        """
        Execute Redis operation with fallback if Redis is unavailable
        """
        if self.r is None:
            return fallback_value
        
        try:
            return operation()
        except Exception as e:
            logger.warning(f"Redis operation failed: {e}")
            return fallback_value

    def cache_monthly_data(self, ticker: str, ttl_hours: int = 24) -> bool:
        if self.r is None:
            logger.info(f"Redis unavailable - skipping cache for {ticker}")
            return True  # Return True to continue processing
            
        key = f"monthly:{ticker}"
        if self.r.exists(key):
            return True
        try:
            df = yf.download(ticker, period="15y", interval="1mo", auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                series = df[('Close', ticker)].dropna()
            else:
                series = df["Adj Close"].dropna()
            payload = {str(idx.date()): float(val) for idx, val in series.items()}
            compressed = self._compress_data(payload)
            self.r.setex(key, timedelta(hours=ttl_hours), compressed)
            return True
        except Exception as e:
            logger.error(f"Error caching {ticker}: {e}")
            return False

    def _download_batch(self, tickers: List[str]) -> Dict[str, Dict[str, float]]:
        try:
            df = yf.download(tickers, period="15y", interval="1mo", auto_adjust=True, progress=False)
            results: Dict[str, Dict[str, float]] = {}
            if isinstance(df.columns, pd.MultiIndex):
                for field, ticker in df.columns:
                    if field in ("Close", "Adj Close"):
                        series = df[(field, ticker)].dropna()
                        results.setdefault(ticker, {}).update({str(idx.date()): float(val) for idx, val in series.items()})
            else:
                for ticker in tickers:
                    if ticker in df.columns:
                        series = df[ticker].dropna()
                        results[ticker] = {str(idx.date()): float(val) for idx, val in series.items()}
            return results
        except Exception as e:
            logger.error(f"Error downloading batch: {e}")
            return {}

    def warm_cache(self) -> Dict[str, Any]:
        if self.r is None:
            logger.warning("Redis unavailable - cache warming skipped")
            return {
                "status": "skipped",
                "reason": "Redis unavailable",
                "total_tickers": len(self.master_tickers),
                "cached_tickers": 0,
                "failed_tickers": 0,
                "failed_list": [],
                "total_time_s": 0
            }
            
        logger.info(f"Starting batch cache warming for {len(self.master_tickers)} tickers")
        batch_size = 50
        batches = [self.master_tickers[i:i+batch_size] for i in range(0, len(self.master_tickers), batch_size)]
        start = time.time()
        total_cached = 0
        failed: List[str] = []

        for i, batch in enumerate(batches, 1):
            logger.info(f"Batch {i}/{len(batches)}: downloading {len(batch)} tickers")
            data = self._download_batch(batch)
            for ticker in batch:
                if ticker in data and data[ticker]:
                    if self.cache_monthly_data(ticker):
                        total_cached += 1
                    else:
                        failed.append(ticker)
                else:
                    failed.append(ticker)
            elapsed = time.time() - start
            logger.info(f"Completed batch {i}: elapsed {elapsed:.1f}s")

        total_time = time.time() - start
        result = {
            "status": "success",
            "total_tickers": len(self.master_tickers),
            "cached_tickers": total_cached,
            "failed_tickers": len(failed),
            "failed_list": failed,
            "total_time_s": total_time
        }
        logger.info(f"Cache warming done in {total_time:.1f}s: {total_cached} cached, {len(failed)} failed")
        return result

    def get_monthly_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        # Validate ticker against our master list (includes ETFs)
        if ticker.upper() not in self.master_tickers:
            logger.warning(f"Invalid ticker: {ticker}")
            return None
        key = f"monthly:{ticker.upper()}"
        
        # Try Redis cache first (if available)
        if self.r is not None:
            if self.r.exists(key):
                try:
                    compressed = self.r.get(key)
                    data = self._decompress_data(compressed)
                    dates, prices = list(data.keys()), list(data.values())
                    return {
                        "ticker": ticker.upper(),
                        "dates": dates,
                        "prices": prices,
                        "data_points": len(prices),
                        "source": "cache"
                    }
                except Exception as e:
                    logger.error(f"Error reading cache for {ticker}: {e}")
        
        # Fallback to live fetch
        logger.info(f"Cache miss for {ticker}, fetching live")
        success = self.cache_monthly_data(ticker.upper())
        if success:
            return self.get_monthly_data(ticker)
        return None

    def search_tickers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Enhanced case-insensitive search that works with any case input
        Includes Redis fallback logic and prioritizes exact matches
        """
        q = query.strip().upper()  # Normalize to uppercase for consistency
        matches = []
        
        # Strategy 1: Exact prefix matches (highest priority)
        prefix_matches = [t for t in self.master_tickers if t.startswith(q)]
        matches.extend(prefix_matches)
        
        # Strategy 2: Partial matches anywhere in the ticker
        partial_matches = [t for t in self.master_tickers if q in t and t not in prefix_matches]
        matches.extend(partial_matches)
        
        # Limit results
        limited_matches = matches[:limit]
        
        # Handle cache status with Redis fallback
        results = []
        for ticker in limited_matches:
            cached = self._redis_operation_with_fallback(
                lambda: self.r.exists(f"monthly:{ticker}"),
                fallback_value=False
            )
            results.append({"ticker": ticker, "cached": cached})
        
        return results

    def get_cache_status(self) -> Dict[str, Any]:
        if self.r is None:
            return {
                "master_count": len(self.master_tickers),
                "cached_count": 0,
                "sample_cached": [],
                "redis_status": "unavailable"
            }
        
        cached = [t for t in self.master_tickers if self.r.exists(f"monthly:{t}")]
        return {
            "master_count": len(self.master_tickers),
            "cached_count": len(cached),
            "sample_cached": cached[:10],
            "redis_status": "available"
        }

    def clear_cache(self) -> None:
        if self.r is None:
            logger.info("Redis unavailable - no cache to clear")
            return
            
        keys = self.r.keys("monthly:*")
        if keys:
            self.r.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache entries")
        else:
            logger.info("Cache already empty")

# Instantiate for use
enhanced_data_fetcher = EnhancedDataFetcher() 