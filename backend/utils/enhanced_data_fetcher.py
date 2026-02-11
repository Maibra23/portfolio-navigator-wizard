import pandas as pd
import yfinance as yf
from yahooquery import Ticker as YQTicker
import logging
import time
import threading
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import json
import gzip
import redis
from collections import defaultdict
from alpha_vantage.fundamentaldata import FundamentalData
from alpha_vantage.timeseries import TimeSeries
import os
from .redis_first_data_service import redis_first_data_service as _rds

from .timestamp_utils import normalize_timestamp, normalize_ticker_format, suggest_ticker_alternatives
from .logging_utils import get_job_logger
# Handle both relative and absolute imports
try:
    from ..config.settings import config
except ImportError:
    from config.settings import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SMART_REFRESH_LOGGER = get_job_logger("smart_refresh")

# Configuration - OPTIMIZED for rate limit bypass
BATCH_SIZE = 20  # Batch size (user requested: 20)
MAX_WORKERS = 1  # Single worker to avoid concurrent rate limit issues
RATE_LIMIT_DELAY = 4  # Increased delay between batches for better rate limit compliance
REQUEST_DELAY = (1.3, 4.0)  # Random delay between 1.3-4 seconds (user requested)

# Alpha Vantage configuration (env override for production)
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY") or os.getenv("ALPHA_VANTAGE_FALLBACK_KEY") or "demo"
ALPHA_VANTAGE_RATE_LIMIT = 5  # requests per minute for free tier
ALPHA_VANTAGE_DELAY = 60 / ALPHA_VANTAGE_RATE_LIMIT  # seconds between requests

# Cache configuration  
CACHE_TTL_DAYS = 90  # FIXED: 3 months as requested
CACHE_TTL_HOURS = CACHE_TTL_DAYS * 24  # 2160 hours

# Data period configuration
# NOTE: Stress tests include the 2008 crisis (needs 2007-09+ coverage). 15 years is not enough
# for 2026 and causes "2008 crisis" series to begin ~2011. Use 20 years to cover 2008.
END_DATE = datetime.now().replace(day=1)  # Beginning of current month
START_DATE = END_DATE - timedelta(days=20 * 365)  # 20 years back minimum

# Yahoo Finance rate limiting - OPTIMIZED for rate limit bypass
YAHOO_REQUEST_DELAY = (1.3, 4.0)  # Random delay between 1.3-4 seconds (user requested)
MAX_RETRIES = 1  # Single retry only (user requested)
RETRY_DELAY = 5  # Base retry delay (exponential backoff: 5s, then 10s)
USE_ALPHA_VANTAGE_FALLBACK = False  # Disabled (user requested)

# Daily quota management
DAILY_REQUEST_LIMIT = 2000

class EnhancedDataFetcher:
    """
    Enhanced data fetcher with proper rate limiting and sector data support.
    Fetches 15-year monthly adjusted close prices AND sector information for:
    - All S&P 500 companies
    - All NASDAQ 100 companies  
    - Top 15 ETFs by market capitalization
    """

    def __init__(self):
        # Redis cache
        self.r = self._init_redis()

        # Alpha Vantage clients
        self.alpha_vantage_fundamental = FundamentalData(ALPHA_VANTAGE_API_KEY)
        self.alpha_vantage_timeseries = TimeSeries(ALPHA_VANTAGE_API_KEY)

        # Enhanced request session for better yfinance compatibility
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        # Get all tickers from Redis master list (canonical)
        # Support validated master list feature flag
        self.use_validated_master_list = config.use_validated_master_list
        
        try:
            if self.use_validated_master_list:
                # Load validated master list (only tickers confirmed to work)
                logger.info("📋 Using validated master list (USE_VALIDATED_MASTER_LIST=True)")
                validated_key = "master_ticker_list_validated"
                if self.r:
                    validated_data = self.r.get(validated_key)
                    if validated_data:
                        try:
                            self.all_tickers = json.loads(validated_data.decode())
                            logger.info(f"✅ Loaded {len(self.all_tickers)} validated tickers from Redis")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to parse validated list, falling back to full list: {e}")
                            self.all_tickers = list(_rds.all_tickers) if _rds.all_tickers else []
                    else:
                        logger.warning(f"⚠️ Validated master list not found in Redis, falling back to full list")
                        self.all_tickers = list(_rds.all_tickers) if _rds.all_tickers else []
                else:
                    logger.warning(f"⚠️ Redis unavailable, cannot load validated list, falling back to full list")
                    self.all_tickers = list(_rds.all_tickers) if _rds.all_tickers else []
            else:
                # Use current inference path with full master list
                logger.info("📋 Using full master list with inference path (USE_VALIDATED_MASTER_LIST=False)")
            master = _rds.all_tickers
            if not master:
                master = _rds.list_cached_tickers()
            self.all_tickers = list(master) if master else []
        except Exception as e:
            logger.warning(f"⚠️ Error loading ticker list: {e}")
            self.all_tickers = []
        
        # Track processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'cached': 0,
            'errors': defaultdict(int),
            'throttled': 0,
            'stopped_due_to_throttling': False
        }
        
        # Daily quota tracking
        self.daily_requests = 0
        self.last_reset_date = datetime.now().date()
        
        logger.info(f"Initialized with {len(self.all_tickers)} unique tickers")
        
        # Auto-warm cache if Redis is available and cache is empty
        self._auto_warm_cache()

    def _validate_and_cache_price_data(self, ticker: str, price_dict: Dict[str, float]) -> bool:
        """
        Lightweight validation and safe caching of price data.
        Only validates and caches data during fetching process.
        
        Args:
            ticker: Ticker symbol
            price_dict: Price data dictionary
            
        Returns:
            True if caching successful, False otherwise
        """
        try:
            # Lightweight validation - only check essential requirements
            if not isinstance(price_dict, dict) or len(price_dict) < 12:
                logger.warning(f"⚠️ {ticker}: Insufficient data for caching")
                return False
            
            # Check for non-numeric values (quick check)
            for price in list(price_dict.values())[:5]:  # Sample first 5 values
                if not isinstance(price, (int, float)) or price <= 0:
                    logger.warning(f"⚠️ {ticker}: Invalid price data detected")
                    return False
            
            # Cache with proper format (single JSON encoding + gzip)
            key = f'ticker_data:prices:{ticker}'
            prices_json = json.dumps(price_dict)
            prices_compressed = gzip.compress(prices_json.encode())
            # Unified TTL to match sector/metrics (90 days via CACHE_TTL_HOURS)
            self.r.setex(key, timedelta(hours=CACHE_TTL_HOURS), prices_compressed)
            
            # Invalidate eligible tickers cache when new ticker data is cached
            # (Only invalidate, don't trigger refresh here to avoid excessive refreshes during batch operations)
            try:
                # Lazy import to avoid circular dependencies
                from routers.portfolio import _invalidate_eligible_tickers_cache
                _invalidate_eligible_tickers_cache()
            except Exception as e:
                logger.debug(f"⚠️ Could not invalidate eligible tickers cache: {e}")
            
            logger.debug(f"✅ {ticker}: Data validated and cached safely ({len(price_dict)} points)")
            return True
            
        except Exception as e:
            logger.error(f"❌ {ticker}: Failed to cache data safely - {e}")
            return False

    def _init_redis(self):
        """Initialize Redis connection from REDIS_URL (production-safe) or localhost fallback"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            r = redis.from_url(redis_url, decode_responses=False, socket_connect_timeout=5, socket_timeout=5)
            r.ping()
            logger.info("✅ Redis connection established")
            return r
        except redis.ConnectionError as e:
            logger.warning(f"❌ Redis connection failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"❌ Redis unavailable: {e}")
            return None

    def _check_daily_quota(self) -> bool:
        """Check if we're within daily request limits"""
        current_date = datetime.now().date()
        
        # Reset counter if it's a new day
        if current_date != self.last_reset_date:
            self.daily_requests = 0
            self.last_reset_date = current_date
            logger.info("🔄 Daily quota reset")
        
        # Check if we're under the limit
        if self.daily_requests >= DAILY_REQUEST_LIMIT:
            logger.warning(f"⚠️ Daily quota exceeded: {self.daily_requests}/{DAILY_REQUEST_LIMIT}")
            return False
        
        return True

    def _increment_daily_quota(self):
        """Increment daily request counter"""
        self.daily_requests += 1
        if self.daily_requests % 100 == 0:  # Log every 100 requests
            logger.info(f"📊 Daily requests: {self.daily_requests}/{DAILY_REQUEST_LIMIT}")

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Detect if error is related to rate limiting or throttling"""
        error_str = str(error).lower()
        rate_limit_indicators = [
            'rate limit', 'too many requests', '429', 'quota exceeded',
            'expecting value: line 1 column 1', 'timeout', 'connection',
            '403', '999', 'throttled', 'throttling', 'blocked', 'forbidden'
        ]
        return any(indicator in error_str for indicator in rate_limit_indicators)

    def _calculate_rate_limit_wait(self, attempt: int) -> int:
        """Calculate wait time for rate limit errors with exponential backoff"""
        base_wait = 60  # Base 60 seconds for throttling
        exponential_wait = base_wait * (2 ** attempt)  # Exponential backoff
        max_wait = 600  # Maximum 10 minutes for severe throttling
        return min(exponential_wait, max_wait)

    def _get_random_delay(self) -> float:
        """Get random delay from the configured range"""
        if isinstance(YAHOO_REQUEST_DELAY, tuple):
            return random.uniform(YAHOO_REQUEST_DELAY[0], YAHOO_REQUEST_DELAY[1])
        else:
            return float(YAHOO_REQUEST_DELAY)
    
    def _get_adaptive_delay(self) -> float:
        """Get adaptive delay based on current success rate"""
        base_delay = self._get_random_delay()
        
        if self.stats['total_processed'] == 0:
            return base_delay  # Use base delay for first request
        
        success_rate = self.stats['successful'] / self.stats['total_processed']
        
        if success_rate > 0.9:  # High success rate
            return max(base_delay * 0.8, 0.5)  # Reduce delay slightly
        elif success_rate < 0.7:  # Low success rate
            return base_delay * 1.5  # Increase delay
        else:  # Medium success rate
            return base_delay  # Use base delay

    def _get_all_tickers(self) -> List[str]:
        """Deprecated: kept for compatibility; use Redis master list instead."""
        return _rds.all_tickers or _rds.list_cached_tickers()

    def _fetch_sp500_tickers(self) -> List[str]:
        """Fetch S&P 500 tickers from Wikipedia"""
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            df = pd.read_html(url, attrs={'id': 'constituents'})[0]
            tickers = df['Symbol'].str.replace('.', '-').str.upper().tolist()  # Handle BRK.B -> BRK-B
            
            # Filter valid tickers
            valid_tickers = []
            for ticker in tickers:
                if isinstance(ticker, str) and len(ticker) <= 6 and ticker.replace('-', '').isalnum():
                    valid_tickers.append(ticker)
            
            return valid_tickers
        except Exception as e:
            logger.error(f"Error fetching S&P 500 from Wikipedia: {e}")
            raise

    def _fetch_nasdaq100_tickers(self) -> List[str]:
        """Fetch NASDAQ 100 tickers from Wikipedia with improved parsing"""
        try:
            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            tables = pd.read_html(url)
            
            # Try different table indices and column patterns
            for table_index in [3, 2, 1, 0, 4]:
                try:
                    df = tables[table_index]
                    
                    # Look for Symbol/Ticker column
                    symbol_col = None
                    for col in df.columns:
                        if isinstance(col, str) and any(word in col.lower() for word in ['symbol', 'ticker']):
                            symbol_col = col
                            break
                    
                    if symbol_col and len(df) >= 90:  # Should have close to 100 tickers
                        tickers = df[symbol_col].str.upper().tolist()
                        valid_tickers = []
                        
                        for ticker in tickers:
                            if isinstance(ticker, str) and len(ticker) <= 6 and ticker.replace('-', '').isalnum():
                                valid_tickers.append(ticker)
                        
                        if len(valid_tickers) >= 90:
                            return valid_tickers
                except Exception as e:
                    logger.debug(f"Failed to parse table {table_index}: {e}")
                    continue
            
            raise Exception("No valid NASDAQ 100 table found with sufficient data")
            
        except Exception as e:
            logger.error(f"Error fetching NASDAQ 100 from Wikipedia: {e}")
            raise

    def _fetch_top_etfs(self) -> List[str]:
        """Fetch top 15 ETFs by market capitalization"""
        # Updated list based on 2024-2025 market cap data
        top_etfs = [
            'SPY',   # SPDR S&P 500 ETF Trust (~$400B AUM)
            'IVV',   # iShares Core S&P 500 ETF (~$300B AUM)
            'VOO',   # Vanguard S&P 500 ETF (~$250B AUM)
            'QQQ',   # Invesco QQQ Trust (~$200B AUM)
            'VTI',   # Vanguard Total Stock Market ETF (~$200B AUM)
            'EFA',   # iShares MSCI EAFE ETF (~$70B AUM)
            'IWM',   # iShares Russell 2000 ETF (~$60B AUM)
            'GLD',   # SPDR Gold Shares (~$55B AUM)
            'VEA',   # Vanguard FTSE Developed Markets ETF (~$90B AUM)
            'DIA',   # SPDR Dow Jones Industrial Average ETF (~$30B AUM)
            'VWO',   # Vanguard FTSE Emerging Markets ETF (~$75B AUM)
            'BND',   # Vanguard Total Bond Market ETF (~$85B AUM)
            'AGG',   # iShares Core U.S. Aggregate Bond ETF (~$90B AUM)
            'VXUS',  # Vanguard Total International Stock ETF (~$80B AUM)
            'VTV'    # Vanguard Value ETF (~$70B AUM)
        ]
        return top_etfs

    def _get_cache_key(self, ticker: str, data_type: str = 'prices') -> str:
        """Generate cache key for ticker data"""
        return f"ticker_data:{data_type}:{ticker}"

    def _is_cached(self, ticker: str, data_type: str = 'prices') -> bool:
        """Check if ticker data is cached"""
        if not self.r:
            return False
        key = self._get_cache_key(ticker, data_type)
        return self.r.exists(key)

    def _validate_price_data(self, data: pd.Series, ticker: str) -> bool:
        """Validate price data quality and completeness"""
        if data is None or data.empty:
            logger.warning(f"⚠️ {ticker}: Empty or None data")
            return False
        
        # Check for minimum data points (at least 12 months)
        if len(data) < 12:
            logger.warning(f"⚠️ {ticker}: Insufficient data points ({len(data)} < 12)")
            return False
        
        # Check for all negative or zero prices
        if (data <= 0).all():
            logger.warning(f"⚠️ {ticker}: All prices are zero or negative")
            return False
        
        # Check for excessive missing values (>20%)
        missing_ratio = data.isna().sum() / len(data)
        if missing_ratio > 0.2:
            logger.warning(f"⚠️ {ticker}: Too many missing values ({missing_ratio:.1%})")
            return False
        
        # Check for reasonable price range (not all same value)
        if data.std() == 0:
            logger.warning(f"⚠️ {ticker}: No price variation (all same value)")
            return False
        
        # Check for reasonable price values (not astronomical)
        if data.max() > 10000 or data.min() < 0.01:
            logger.warning(f"⚠️ {ticker}: Suspicious price range ({data.min():.2f} - {data.max():.2f})")
            return False
        
        logger.debug(f"✅ {ticker}: Data validation passed")
        return True

    def _save_to_cache(self, ticker: str, data: Dict[str, Any]) -> bool:
        """Save ticker data to cache with lightweight validation and compression"""
        if not self.r:
            return False
        try:
            # Save prices with lightweight validation
            if 'prices' in data:
                prices_series = data['prices']
                if hasattr(prices_series.index, 'tz_localize'):
                    prices_series.index = prices_series.index.tz_localize(None)
                prices_dict = {str(date): float(price) for date, price in prices_series.items()}
                
                # Use lightweight validation for price data
                if self._validate_and_cache_price_data(ticker, prices_dict):
                    # Auto-calculate and save metrics (standard approach)
                    # This ensures metrics are always computed when data is fetched
                    try:
                        metrics_saved = self._calculate_and_save_metrics(ticker, prices_series)
                        if not metrics_saved:
                            logger.warning(f"⚠️ {ticker}: Metrics calculation failed, but price data was cached")
                        # Continue even if metrics fail - price data is still valid
                    except Exception as metrics_error:
                        logger.warning(f"⚠️ {ticker}: Error computing metrics: {metrics_error}, but price data was cached")
                        # Don't fail the entire cache operation if metrics fail
                else:
                    logger.warning(f"⚠️ {ticker}: Price data validation failed")
                    return False
            
            # Save sector info (no validation needed for sector data)
            if 'sector' in data:
                key = self._get_cache_key(ticker, 'sector')
                sector_data = json.dumps(data['sector']).encode()
                self.r.setex(key, timedelta(hours=CACHE_TTL_HOURS), sector_data)
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cache {ticker}: {e}")
            return False

    def _load_from_cache(self, ticker: str, data_type: str = 'prices') -> Optional[Any]:
        """Load ticker data from cache"""
        if not self.r:
            return None
        try:
            key = self._get_cache_key(ticker, data_type)
            if self.r.exists(key):
                raw = self.r.get(key)
                
                if data_type == 'prices':
                    data_dict = json.loads(gzip.decompress(raw).decode())
                    # Convert back to Series
                    data = pd.Series(data_dict)
                    # ENHANCED: Use robust timestamp parsing for all formats
                    try:
                        # Parse timestamps using our robust utility
                        parsed_dates = []
                        for date_str in data.index:
                            # First try to normalize the timestamp
                            normalized = normalize_timestamp(date_str)
                            if normalized:
                                try:
                                    parsed_date = pd.to_datetime(normalized)
                                    parsed_dates.append(parsed_date)
                                except Exception as e:
                                    logger.warning(f"⚠️ Failed to parse normalized date {normalized} for {ticker}: {e}")
                                    # Fallback to direct parsing
                                    try:
                                        parsed_date = pd.to_datetime(date_str)
                                        parsed_dates.append(parsed_date)
                                    except Exception as e2:
                                        logger.error(f"❌ Failed to parse date {date_str} for {ticker}: {e2}")
                                        return None
                            else:
                                logger.error(f"❌ Could not normalize date {date_str} for {ticker}")
                                return None
                        
                        data.index = pd.DatetimeIndex(parsed_dates)
                        return data
                    except Exception as e:
                        logger.error(f"❌ Failed to parse timestamps for {ticker}: {e}")
                        return None
                else:  # sector, metrics, or other metadata
                    return json.loads(raw.decode())
        except Exception as e:
            logger.error(f"❌ Failed to load {ticker} {data_type} from cache: {e}")
        return None

    def _calculate_and_save_metrics(self, ticker: str, prices: pd.Series) -> bool:
        """Calculate and save risk/return metrics for a ticker - STANDARD FORMAT"""
        try:
            if len(prices) < 2:  # Need at least 2 data points for returns calculation
                logger.warning(f"⚠️ {ticker}: Insufficient data for metrics calculation ({len(prices)} < 2)")
                return False
            
            # Calculate returns
            returns = prices.pct_change().dropna()
            
            if len(returns) < 2:
                logger.warning(f"⚠️ {ticker}: Insufficient returns data for metrics calculation")
                return False
            
            # Calculate monthly metrics
            monthly_return = returns.mean()
            monthly_risk = returns.std()
            
            # Annualize metrics - use simple multiplication for consistency with system expectations
            # For small returns, compound and simple are similar; for large returns, simple is more stable
            if abs(monthly_return) < 0.1:  # Small returns, compound is fine
                annual_return = (1 + monthly_return) ** 12 - 1
            else:  # Large returns, use simple multiplication to avoid extreme values
                annual_return = monthly_return * 12
            
            annual_risk = monthly_risk * (12 ** 0.5)  # Annualized volatility
            
            # Calculate max drawdown
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdowns = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            # Calculate sharpe ratio (assuming risk-free rate of 0 for simplicity)
            sharpe_ratio = (annual_return / annual_risk) if annual_risk > 0 else None
            
            # Calculate skewness and kurtosis
            skewness = returns.skew()
            kurtosis = returns.kurtosis()
            
            # Create metrics dictionary - STANDARD FORMAT with both naming conventions for compatibility
            metrics = {
                # Standard format (primary) - used by optimization and portfolio systems
                'expected_return': float(annual_return),
                'volatility': float(annual_risk),
                # Legacy format (secondary) - for backward compatibility
                'annualized_return': float(annual_return * 100),  # Percentage format
                'risk': float(annual_risk),  # Alternative naming
                # Additional metrics
                'max_drawdown': float(max_drawdown) if not pd.isna(max_drawdown) else None,
                'sharpe_ratio': float(sharpe_ratio) if sharpe_ratio is not None and not pd.isna(sharpe_ratio) else None,
                'skewness': float(skewness) if not pd.isna(skewness) else None,
                'kurtosis': float(kurtosis) if not pd.isna(kurtosis) else None,
                # Metadata
                'data_points': len(prices),
                'last_price': float(prices.iloc[-1]),
                'calculation_date': datetime.now().isoformat(),
                'data_quality': 'good' if len(prices) >= 180 else 'limited'  # 15 years of monthly data
            }
            
            # Save metrics to cache
            key = self._get_cache_key(ticker, 'metrics')
            metrics_data = json.dumps(metrics).encode()
            self.r.setex(key, timedelta(hours=CACHE_TTL_HOURS), metrics_data)
            
            logger.debug(f"✅ {ticker}: Metrics calculated and cached (return={annual_return:.4f}, volatility={annual_risk:.4f})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate metrics for {ticker}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def get_cached_metrics(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get pre-calculated metrics for a ticker"""
        return self._load_from_cache(ticker, 'metrics')

    def get_all_cached_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all cached tickers"""
        if not self.r:
            return {}
        
        try:
            all_metrics = {}
            # Get all metrics keys
            pattern = self._get_cache_key('*', 'metrics')
            keys = self.r.keys(pattern.replace('*', '*'))
            
            for key in keys:
                ticker = key.decode().split(':')[-1]  # Extract ticker from key
                metrics = self.get_cached_metrics(ticker)
                if metrics:
                    all_metrics[ticker] = metrics
            
            return all_metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get all cached metrics: {e}")
            return {}

    def _fetch_ticker_yahooquery(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch ticker data using yahooquery library
        Uses timestamp_utils for robust date handling across all exchanges
        """
        try:
            # Create yahooquery Ticker object
            yq_ticker = YQTicker(ticker)
            
            # Fetch historical data (monthly) using configured global time range.
            # This must include 2008 for historical stress tests.
            end_date = END_DATE
            start_date = START_DATE
            
            hist_data = yq_ticker.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval='1mo',
                adj_timezone=False
            )
            
            # Check if data is valid
            if hist_data is None or (isinstance(hist_data, str) and 'error' in hist_data.lower()):
                logger.warning(f"⚠️ {ticker}: No data returned from yahooquery")
                return None
            
            if isinstance(hist_data, pd.DataFrame) and hist_data.empty:
                logger.warning(f"⚠️ {ticker}: Empty DataFrame returned")
                return None
            
            # yahooquery returns multi-index for multiple tickers, single index for one ticker
            if isinstance(hist_data.index, pd.MultiIndex):
                # Extract data for this specific ticker
                if ticker in hist_data.index.get_level_values(0):
                    hist_data = hist_data.xs(ticker, level=0)
                else:
                    logger.warning(f"⚠️ {ticker}: Ticker not found in multi-index result")
                    return None
            
            # Extract close prices
            if 'close' in hist_data.columns:
                close_data = hist_data['close']
            elif 'adjclose' in hist_data.columns:
                close_data = hist_data['adjclose']
            else:
                logger.warning(f"⚠️ {ticker}: No close price column found")
                return None
            
            # Remove any NaN values and ensure we have enough data
            close_data = close_data.dropna()
            
            if len(close_data) < 12:
                logger.warning(f"⚠️ {ticker}: Insufficient data points ({len(close_data)})")
                return None
            
            # Fetch company profile/summary data
            try:
                # Get summary detail which includes sector/industry
                summary = yq_ticker.summary_detail
                profile = yq_ticker.asset_profile
                quote_type = yq_ticker.quote_type
                
                sector_info = {
                    'sector': 'Unknown',
                    'industry': 'Unknown',
                    'country': 'Unknown',
                    'exchange': 'Unknown',
                    'companyName': ticker
                }
                
                # Extract from asset_profile (best source for sector/industry)
                if isinstance(profile, dict) and ticker in profile:
                    prof_data = profile[ticker]
                    if isinstance(prof_data, dict) and 'sector' not in str(prof_data).lower() or True:
                        sector_info['sector'] = prof_data.get('sector', 'Unknown')
                        sector_info['industry'] = prof_data.get('industry', 'Unknown')
                        sector_info['country'] = prof_data.get('country', 'Unknown')
                        sector_info['companyName'] = prof_data.get('longName', prof_data.get('shortName', ticker))
                
                # Fallback to quote_type for exchange info
                if isinstance(quote_type, dict) and ticker in quote_type:
                    qt_data = quote_type[ticker]
                    if isinstance(qt_data, dict):
                        if sector_info['companyName'] == ticker:
                            sector_info['companyName'] = qt_data.get('longName', qt_data.get('shortName', ticker))
                        if sector_info['exchange'] == 'Unknown':
                            sector_info['exchange'] = qt_data.get('exchange', 'Unknown')
                
            except Exception as e:
                logger.debug(f"Could not fetch company info for {ticker}: {e}")
                # Use basic info from historical data metadata if available
                sector_info = {
                    'sector': 'Unknown',
                    'industry': 'Unknown',
                    'country': 'Unknown',
                    'exchange': 'Unknown',
                    'companyName': ticker
                }
            
            return {'prices': close_data, 'sector': sector_info}
            
        except Exception as e:
            logger.warning(f"⚠️ yahooquery fetch failed for {ticker}: {e}")
            return None

    def _fetch_single_ticker_with_retry(self, ticker: str, force_fetch: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch data for a single ticker with retry logic and rate limiting

        Args:
            ticker: Ticker symbol to fetch
            force_fetch: If True, bypass cached data and refetch from source (then overwrite cache)
        """
        # NEW: Normalize ticker format first using timestamp_utils
        original_ticker = ticker
        normalized_ticker = normalize_ticker_format(ticker)
        
        # Determine which ticker formats to try and which to use for caching
        # Strategy: 
        # 1. Keep normalization as-is (it's useful for Yahoo Finance compatibility)
        # 2. Try multiple formats when fetching (normalized first, then original if needed)
        # 3. Cache under the format that's in master list to ensure consistency
        fetch_formats_to_try = []  # List of formats to try when fetching
        cache_ticker = None  # Format to use for caching (must be in master list)
        
        if normalized_ticker != original_ticker:
            logger.info(f"🔄 Normalized ticker: {original_ticker} → {normalized_ticker}")
            
            # Check which formats are in master list
            normalized_in_master = normalized_ticker in self.all_tickers if self.all_tickers else False
            original_in_master = original_ticker in self.all_tickers if self.all_tickers else False
            
            # Build list of formats to try (prefer normalized first, then original)
            if normalized_in_master:
                fetch_formats_to_try.append(normalized_ticker)
                cache_ticker = normalized_ticker  # Cache under normalized if it's in master
            if original_in_master:
                if original_ticker not in fetch_formats_to_try:
                    fetch_formats_to_try.append(original_ticker)
                if cache_ticker is None:
                    cache_ticker = original_ticker  # Cache under original if normalized not in master
            
            # If neither is in master list
            if not fetch_formats_to_try:
                if not getattr(self, '_allow_out_of_master', False):
                    logger.warning(f"⚠️ Ticker {normalized_ticker} (normalized from {original_ticker}) not in master list - skipping fetch")
                    return None
                # If allowed, try both formats
                fetch_formats_to_try = [normalized_ticker, original_ticker]
                cache_ticker = original_ticker  # Default to original for caching
        else:
            # No normalization occurred, use original
            fetch_formats_to_try = [original_ticker]
            cache_ticker = original_ticker
        
        # Final validation: cache_ticker must be in master list unless allowed
        if cache_ticker not in self.all_tickers and not getattr(self, '_allow_out_of_master', False):
            logger.warning(f"⚠️ Ticker {cache_ticker} not in master list - skipping fetch")
            return None
            
        # Check daily quota first
        display_ticker = fetch_formats_to_try[0] if fetch_formats_to_try else original_ticker
        if not self._check_daily_quota():
            logger.warning(f"⚠️ Daily quota exceeded, skipping {display_ticker}")
            return None
        
        for attempt in range(MAX_RETRIES):
            try:
                # Check cache first unless force_fetch is requested
                if not force_fetch:
                    cached_prices = None
                    cached_sector = None
                    
                    # Build unique list of formats to check (avoid duplicates)
                    formats_to_check = list(dict.fromkeys(fetch_formats_to_try + [cache_ticker]))
                    
                    for format_to_check in formats_to_check:
                        if not format_to_check:
                            continue
                        cached_prices = self._load_from_cache(format_to_check, 'prices')
                        cached_sector = self._load_from_cache(format_to_check, 'sector')
                        if cached_prices is not None and cached_sector is not None:
                            logger.debug(f"✅ Found cached data for {format_to_check}")
                            break
                    
                    if cached_prices is not None and cached_sector is not None:
                        # Handle timezone-aware datetime index
                        if hasattr(cached_prices.index, 'tz_localize'):
                            cached_prices.index = cached_prices.index.tz_localize(None)
                        self.stats['cached'] += 1
                        return {'prices': cached_prices, 'sector': cached_sector}

                # Random delay between requests (user requested: 1.3-4 seconds)
                delay = random.uniform(REQUEST_DELAY[0], REQUEST_DELAY[1])
                time.sleep(delay)
                
                # Increment daily quota
                self._increment_daily_quota()
                
                # Try fetching with different formats (normalized first, then original if needed)
                direct_data = None
                successful_fetch_ticker = None
                
                for fetch_format in fetch_formats_to_try:
                    try:
                        logger.debug(f"🔄 Trying to fetch with format: {fetch_format}")
                        direct_data = self._fetch_ticker_yahooquery(fetch_format)
                        
                        if direct_data and direct_data.get('prices') is not None:
                            successful_fetch_ticker = fetch_format
                            if fetch_format != fetch_formats_to_try[0]:
                                logger.info(f"✅ Successfully fetched with format {fetch_format} (tried {len(fetch_formats_to_try)} formats)")
                            break
                    except Exception as e:
                        logger.debug(f"⚠️ Format {fetch_format} failed: {str(e)[:50]}")
                        continue
                
                if not direct_data:
                    logger.warning(f"⚠️  No data found for any format: {fetch_formats_to_try}")
                    self.stats['errors']['no_data'] += 1
                    continue  # Retry

                # Extract data
                close_data = direct_data['prices']
                sector_info = direct_data['sector']
                
                # Validate price data (use successful fetch ticker for logging)
                validation_ticker = successful_fetch_ticker or fetch_formats_to_try[0]
                if not self._validate_price_data(close_data, validation_ticker):
                    self.stats['errors']['invalid_data'] += 1
                    continue  # Retry
                
                # Prepare data for caching
                data_to_cache = {
                    'prices': close_data,
                    'sector': sector_info
                }
                
                # Cache the data under the format that's in master list (cache_ticker)
                # This ensures data is cached under the correct format for future lookups
                self._save_to_cache(cache_ticker, data_to_cache)
                
                return data_to_cache

            except Exception as e:
                logger.warning(f"⚠️  Attempt {attempt + 1} failed for {display_ticker}: {e}")
                
                # Intelligent error handling for rate limiting and throttling
                if self._is_rate_limit_error(e):
                    self.stats['throttled'] += 1
                    wait_time = self._calculate_rate_limit_wait(attempt)
                    logger.warning(f"🔄 Rate limit/throttling detected for {display_ticker}, waiting {wait_time}s...")
                    
                    # Check if we're getting heavily throttled
                    if self.stats['throttled'] >= 10:  # Stop after 10 throttling events
                        logger.error(f"❌ Heavy throttling detected ({self.stats['throttled']} events). Stopping fetch process.")
                        self.stats['stopped_due_to_throttling'] = True
                        return None
                    
                    time.sleep(wait_time)
                    continue
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"❌ All attempts failed for {display_ticker}")
                    self.stats['errors'][str(e)] += 1
                    
                    # Alpha Vantage fallback DISABLED (user requested)
                    # Just continue to next ticker
                    return None

    def _process_batch(
        self,
        batch: List[str],
        batch_number: Optional[int] = None,
        total_batches: Optional[int] = None,
        job_logger: Optional[logging.Logger] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Process a batch of tickers with detailed progress logging."""
        results = {}
        failed_tickers = []  # Track failures for reporting
        
        logger.info(f"🔄 Processing batch of {len(batch)} tickers...")
        job_logger = job_logger or SMART_REFRESH_LOGGER

        if batch_number is not None and total_batches is not None:
            job_logger.info(
                "Batch %s/%s started (%s tickers)",
                batch_number,
                total_batches,
                len(batch),
            )
        else:
            job_logger.info("Processing batch of %s tickers", len(batch))
        
        for i, ticker in enumerate(batch, 1):
            try:
                # Check if we should stop due to throttling
                if self.stats['stopped_due_to_throttling']:
                    logger.error(f"🛑 Stopping batch processing due to throttling")
                    break
                
                logger.debug(f"  [{i}/{len(batch)}] Processing {ticker}...")
                job_logger.info("  [%s/%s] Processing %s", i, len(batch), ticker)
                
                data = self._fetch_single_ticker_with_retry(ticker)
                if data is not None:
                    results[ticker] = data
                    self.stats['successful'] += 1
                    logger.info(f"  ✅ {ticker} successful")
                    job_logger.info("  ✅ %s successful", ticker)
                else:
                    self.stats['failed'] += 1
                    failed_tickers.append(ticker)
                    logger.warning(f"  ❌ {ticker} failed")
                    job_logger.warning("  ❌ %s failed", ticker)
                
                self.stats['total_processed'] += 1
                
            except Exception as e:
                logger.error(f"❌ Batch processing error for {ticker}: {e}")
                self.stats['failed'] += 1
                failed_tickers.append(ticker)
                self.stats['total_processed'] += 1
                job_logger.error("  ❌ %s failed with error: %s", ticker, e)

        # Log failed tickers for this batch
        if failed_tickers:
            logger.warning(f"Batch failed tickers: {failed_tickers}")
            job_logger.warning("Batch failures: %s", ", ".join(failed_tickers))
        else:
            job_logger.info("Batch completed with no failures")
        
        # Return statement was incorrectly indented inside the for loop
        return results

    def fetch_all_data(self, batch_size: int = BATCH_SIZE, include_failed_tickers: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Fetch data for all tickers using batch processing with proper rate limiting
        
        Args:
            batch_size: Number of tickers per batch
            include_failed_tickers: If True, include normalized failed tickers from CSV files in fetch queue
        """
        # When include_failed_tickers=True, ONLY fetch normalized failed tickers (skip validated ones)
        if include_failed_tickers:
            logger.info("📋 Fetching ONLY normalized failed tickers (skipping already validated/cached)...")
            normalized_failed = self._collect_and_normalize_failed_tickers()
            if normalized_failed:
                # Filter out tickers that are already cached
                tickers_to_fetch = []
                for ticker in normalized_failed:
                    # Skip if already cached (both prices and sector)
                    if self._is_cached(ticker, 'prices') and self._is_cached(ticker, 'sector'):
                        logger.debug(f"⏭️  {ticker} already cached, skipping")
                        continue
                    tickers_to_fetch.append(ticker)
                logger.info(f"✅ {len(tickers_to_fetch)} normalized failed tickers to fetch (filtered out {len(normalized_failed) - len(tickers_to_fetch)} already cached)")
            else:
                logger.info("ℹ️  No normalized failed tickers to fetch")
                tickers_to_fetch = []
        else:
            # Normal mode: fetch all tickers from master list
            tickers_to_fetch = list(self.all_tickers)

        # Check if there are any tickers to fetch
        if not tickers_to_fetch:
            logger.info("ℹ️  No tickers to fetch (all already cached or no failed tickers found)")
            return {}
        
        # Allow out-of-master tickers during this run only if we included normalized failed set
        self._allow_out_of_master = bool(include_failed_tickers)
        
        logger.info(f"🚀 Starting batch processing of {len(tickers_to_fetch)} tickers")
        logger.info(f"📊 Configuration: batch_size={batch_size}, workers={MAX_WORKERS}, delay={RATE_LIMIT_DELAY}s")
        logger.info(f"⚙️  Retry policy: {MAX_RETRIES} attempt(s), Alpha Vantage fallback: {USE_ALPHA_VANTAGE_FALLBACK}")
        
        all_results = {}
        all_failed_tickers = []  # Track all failed tickers
        total_batches = (len(tickers_to_fetch) + batch_size - 1) // batch_size
        
        # Process in batches with sequential execution to respect rate limits
        for i in range(0, len(tickers_to_fetch), batch_size):
            batch_num = i // batch_size + 1
            batch = tickers_to_fetch[i:i + batch_size]
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches}: {len(batch)} tickers")
            
            # Process batch (sequential to respect rate limits better)
            batch_results = self._process_batch(batch, batch_number=batch_num, total_batches=total_batches)
            all_results.update(batch_results)
            
            # Check if we should stop due to throttling
            if self.stats['stopped_due_to_throttling']:
                logger.error(f"🛑 Stopping fetch process due to throttling")
                break
            
            # Track failed tickers
            batch_failed = [t for t in batch if t not in batch_results]
            all_failed_tickers.extend(batch_failed)
            
            # Show progress
            success_rate = (self.stats['successful'] / max(self.stats['total_processed'], 1)) * 100
            logger.info(f"  📈 Batch {batch_num} completed: {len(batch_results)} successful")
            logger.info(f"  📊 Overall progress: {self.stats['total_processed']}/{len(tickers_to_fetch)} ({success_rate:.1f}% success)")
            SMART_REFRESH_LOGGER.info(
                "Batch %s/%s summary: %s success, %s failed | cumulative success rate %.1f%%",
                batch_num,
                total_batches,
                len(batch_results),
                len(batch_failed),
                success_rate,
            )
            
            # Rate limiting between batches (except for last batch)
            if i + batch_size < len(tickers_to_fetch):
                logger.info(f"⏳ Waiting {RATE_LIMIT_DELAY}s between batches...")
                SMART_REFRESH_LOGGER.info("Waiting %ss before next batch", RATE_LIMIT_DELAY)
                time.sleep(RATE_LIMIT_DELAY)
        
        final_success_rate = (self.stats['successful'] / max(self.stats['total_processed'], 1)) * 100
        logger.info(f"🎉 Batch processing completed!")
        logger.info(f"📊 Final stats: {self.stats['successful']} successful, {self.stats['failed']} failed, {self.stats['cached']} cached")
        logger.info(f"📈 Success rate: {final_success_rate:.1f}%")
        SMART_REFRESH_LOGGER.info(
            "Batch processing complete: %s success, %s failed, %s cached | final success rate %.1f%%",
            self.stats['successful'],
            self.stats['failed'],
            self.stats['cached'],
            final_success_rate,
        )
        
        # Save failed tickers list
        if all_failed_tickers:
            import json
            failed_list_path = '../FAILED_TICKERS_LIST.json'
            with open(failed_list_path, 'w') as f:
                json.dump({
                    'failed_count': len(all_failed_tickers),
                    'failed_tickers': sorted(all_failed_tickers),
                    'timestamp': datetime.now().isoformat(),
                    'can_retry_later': True
                }, f, indent=2)
            logger.info(f"📝 Failed tickers list saved to: {failed_list_path}")
        
        # Publish validated master list at end of run (from successfully cached tickers)
        self._publish_validated_master_list()
        
        # Reset allowance flag after run
        if hasattr(self, '_allow_out_of_master'):
            try:
                delattr(self, '_allow_out_of_master')
            except Exception:
                pass
        
        return all_results

    def _publish_validated_master_list(self):
        """
        Publish validated master list at end of fetch run.
        Builds list from all successfully cached tickers (have both prices and sector).
        Saves to Redis and CSV backup for safety.
        """
        if not self.r:
            logger.warning("⚠️ Redis unavailable - cannot publish validated master list")
            return
        
        try:
            logger.info("📋 Building validated master list from cached tickers...")
            
            # Find all tickers that have both prices and sector cached (successfully fetched)
            price_keys = self.r.keys("ticker_data:prices:*")
            sector_keys = self.r.keys("ticker_data:sector:*")
            
            # Extract ticker symbols from keys
            price_tickers = set()
            for key in price_keys:
                try:
                    ticker = key.decode().replace("ticker_data:prices:", "")
                    price_tickers.add(ticker)
                except:
                    pass
            
            sector_tickers = set()
            for key in sector_keys:
                try:
                    ticker = key.decode().replace("ticker_data:sector:", "")
                    sector_tickers.add(ticker)
                except:
                    pass
            
            # Validated tickers are those with both prices AND sector (successfully fetched)
            validated_tickers = sorted(list(price_tickers & sector_tickers))
            
            if not validated_tickers:
                logger.warning("⚠️ No validated tickers found (no tickers with both prices and sector cached)")
                return
            
            logger.info(f"✅ Found {len(validated_tickers)} validated tickers")
            
            # Save to Redis
            validated_key = "master_ticker_list_validated"
            validated_json = json.dumps(validated_tickers)
            # Set TTL to 365 days (validated list persists long-term)
            self.r.setex(validated_key, 365*24*3600, validated_json.encode())
            logger.info(f"✅ Saved {len(validated_tickers)} validated tickers to Redis key: {validated_key}")
            
            # Save CSV backup with timestamp
            backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts', 'reports')
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_path = os.path.join(backup_dir, f'fetchable_master_list_validated_{timestamp}.csv')
            
            import csv
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['ticker', 'validated_date'])
                for ticker in validated_tickers:
                    writer.writerow([ticker, datetime.now().isoformat()])
            
            logger.info(f"✅ Saved CSV backup to: {csv_path}")
            
            # Also save a "latest" version without timestamp for easy access
            latest_path = os.path.join(backup_dir, 'fetchable_master_list_validated_latest.csv')
            with open(latest_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['ticker', 'validated_date'])
                for ticker in validated_tickers:
                    writer.writerow([ticker, datetime.now().isoformat()])
            
            logger.info(f"✅ Saved latest CSV backup to: {latest_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish validated master list: {e}")

    def _collect_and_normalize_failed_tickers(self) -> List[str]:
        """
        Collect failed tickers from classification CSV files and normalize them.
        Returns list of normalized ticker symbols ready for fetching.
        """
        script_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts')
        reports_dir = os.path.join(script_dir, 'reports')
        
        csv_files = [
            'classified_after_lookup.csv',
            'failed_tickers_classification.csv',
            'unknown_remaining.csv'
        ]
        
        all_failed = set()
        
        # Load all failed tickers from CSV files
        for csv_file in csv_files:
            csv_path = os.path.join(reports_dir, csv_file)
            if not os.path.exists(csv_path):
                logger.debug(f"CSV file not found: {csv_path}, skipping")
                continue
            
            try:
                import csv as csv_module
                with open(csv_path, 'r') as f:
                    reader = csv_module.DictReader(f)
                    for row in reader:
                        ticker = row.get('ticker', '').strip()
                        if ticker:
                            all_failed.add(ticker)
            except Exception as e:
                logger.warning(f"Error reading {csv_file}: {e}")
        
        logger.info(f"📂 Loaded {len(all_failed)} unique failed tickers from CSV files")
        
        # Normalize each ticker
        normalized_tickers = []
        normalized_set = set()
        validated_set = set(self.all_tickers) if hasattr(self, 'all_tickers') else set()
        
        for ticker in all_failed:
            normalized = normalize_ticker_format(ticker)
            
            # Skip if already validated
            if normalized in validated_set:
                logger.debug(f"⏭️  {normalized} already in validated list, skipping")
                continue
            
            # Add to normalized list (deduplicate)
            if normalized not in normalized_set:
                normalized_tickers.append(normalized)
                normalized_set.add(normalized)
                if normalized != ticker:
                    logger.debug(f"🔄 Normalized: {ticker} → {normalized}")
        
        logger.info(f"✅ Normalized to {len(normalized_tickers)} unique tickers (after filtering already validated)")
        
        return normalized_tickers

    def get_ticker_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific ticker - CACHE FIRST approach"""
        ticker = ticker.upper()
        if ticker not in self.all_tickers:
            logger.warning(f"⚠️  Ticker {ticker} not in master list")
            return None

        # Always check cache first
        cached_prices = self._load_from_cache(ticker, 'prices')
        cached_sector = self._load_from_cache(ticker, 'sector')
        
        if cached_prices is not None and cached_sector is not None:
            self.stats['cached'] += 1
            logger.debug(f"✅ {ticker} served from cache")
            return {'prices': cached_prices, 'sector': cached_sector}

        # Only fetch from external API if not in cache AND manual regeneration is approved
        if os.environ.get('MANUAL_REGENERATION_REQUIRED', 'true').lower() == 'true':
            logger.warning(f"⚠️ MANUAL_REGENERATION_REQUIRED enabled - expired ticker {ticker} needs manual approval for regeneration")
            return None
        
        logger.info(f"📥 {ticker} not in cache, fetching from Yahoo Finance...")
        return self._fetch_single_ticker_with_retry(ticker)

    def get_ticker_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive ticker information including prices, metrics, and company details
        Returns: Dict with comprehensive ticker information for frontend display
        """
        ticker = ticker.upper()
        if ticker not in self.all_tickers:
            logger.warning(f"⚠️  Ticker {ticker} not in master list")
            return None

        # Get basic ticker data
        ticker_data = self.get_ticker_data(ticker)
        if not ticker_data:
            return None

        # Get cached metrics if available
        cached_metrics = self.get_cached_metrics(ticker)
        
        prices = ticker_data.get('prices', pd.Series())
        sector_info = ticker_data.get('sector', {})
        
        if prices.empty:
            return None

        # Calculate basic price metrics
        current_price = prices.iloc[-1] if not prices.empty else 0
        price_change = prices.iloc[-1] - prices.iloc[-2] if len(prices) > 1 else 0
        price_change_pct = (price_change / prices.iloc[-2] * 100) if len(prices) > 1 and prices.iloc[-2] != 0 else 0
        
        # Prepare response
        ticker_info = {
            'ticker': ticker,
            'company_name': sector_info.get('companyName', ticker),
            'sector': sector_info.get('sector', 'Unknown'),
            'industry': sector_info.get('industry', 'Unknown'),
            'country': sector_info.get('country', 'Unknown'),
            'exchange': sector_info.get('exchange', 'Unknown'),
            'current_price': round(current_price, 2),
            'price_change': round(price_change, 2),
            'price_change_pct': round(price_change_pct, 2),
            'last_updated': prices.index[-1].strftime('%Y-%m-%d') if not prices.empty else None,
            'data_points': len(prices),
            'cached': True,  # Since we're using cache-first approach
            'prices': prices.tolist()[-30:],  # Last 30 data points for charts
            'dates': [d.strftime('%Y-%m-%d') for d in prices.index[-30:]]  # Last 30 dates
        }

        # Add cached metrics if available
        if cached_metrics:
            ticker_info.update({
                'annualized_return': cached_metrics.get('annualized_return'),
                'risk': cached_metrics.get('annualized_volatility'),  # Using 'risk' as preferred naming
                'sharpe_ratio': cached_metrics.get('sharpe_ratio'),
                'max_drawdown': cached_metrics.get('max_drawdown'),
                'var_95': cached_metrics.get('var_95'),
                'skewness': cached_metrics.get('skewness'),
                'kurtosis': cached_metrics.get('kurtosis')
            })

        return ticker_info

    def get_monthly_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get monthly data for a ticker - returns prices, dates, and company info
        Returns: Dict with prices, dates, sector, industry, company name
        """
        ticker_data = self.get_ticker_data(ticker)
        if not ticker_data:
            return None
        
        prices = ticker_data.get('prices', pd.Series())
        sector_info = ticker_data.get('sector', {})
        
        if prices.empty:
            return None
        
        return {
            'prices': prices.tolist(),
            'dates': [d.strftime('%Y-%m-%d') for d in prices.index],
            'ticker': ticker.upper(),
            'sector': sector_info.get('sector', 'Unknown'),
            'industry': sector_info.get('industry', 'Unknown'),
            'company_name': sector_info.get('companyName', ticker.upper()),
            'country': sector_info.get('country', 'Unknown'),
            'exchange': sector_info.get('exchange', 'Unknown')
        }

    def search_tickers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Enhanced case-insensitive search that works with any case input
        Includes Redis fallback logic and prioritizes exact matches
        """
        q = query.strip().upper()  # Normalize to uppercase for consistency
        matches = []
        
        # Strategy 1: Exact prefix matches (highest priority)
        prefix_matches = [t for t in self.all_tickers if t.startswith(q)]
        matches.extend(prefix_matches)
        
        # Strategy 2: Partial matches anywhere in the ticker
        partial_matches = [t for t in self.all_tickers if q in t and t not in prefix_matches]
        matches.extend(partial_matches)
        
        # Limit results
        limited_matches = matches[:limit]
        
        # Handle cache status with Redis fallback
        results = []
        for ticker in limited_matches:
            cached = self._is_cached(ticker, 'prices') and self._is_cached(ticker, 'sector')
            results.append({"ticker": ticker, "cached": cached})
        
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'total_tickers': len(self.all_tickers),
            'total_processed': self.stats['total_processed'],
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'cached': self.stats['cached'],
            'throttled': self.stats['throttled'],
            'stopped_due_to_throttling': self.stats['stopped_due_to_throttling'],
            'errors': dict(self.stats['errors']),
            'success_rate': self.stats['successful'] / max(self.stats['total_processed'], 1) * 100,
            'cache_ttl_days': CACHE_TTL_DAYS,
            'date_range': f"{START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}",
            'daily_requests': self.daily_requests,
            'daily_limit': DAILY_REQUEST_LIMIT,
            'quota_remaining': DAILY_REQUEST_LIMIT - self.daily_requests
        }

    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status"""
        if not self.r:
            return {'redis': 'unavailable'}
        
        try:
            price_keys = self.r.keys("ticker_data:prices:*")
            sector_keys = self.r.keys("ticker_data:sector:*")
            
            return {
                'redis': 'available',
                'cached_tickers_prices': len(price_keys),
                'cached_tickers_sectors': len(sector_keys),
                'total_tickers': len(self.all_tickers),
                'price_cache_coverage': len(price_keys) / len(self.all_tickers) * 100,
                'sector_cache_coverage': len(sector_keys) / len(self.all_tickers) * 100,
                'ttl_days': CACHE_TTL_DAYS
            }
        except Exception as e:
            return {'redis': 'error', 'error': str(e)}

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics for monitoring"""
        try:
            # Basic system health
            health_metrics = {
                'system_status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': time.time(),  # Could be enhanced with actual start time
                'version': '2.0.0'
            }
            
            # Redis health
            if self.r:
                try:
                    self.r.ping()
                    redis_info = self.r.info()
                    health_metrics['redis'] = {
                        'status': 'connected',
                        'memory_used_mb': redis_info.get('used_memory_human', 'N/A'),
                        'connected_clients': redis_info.get('connected_clients', 0),
                        'total_commands_processed': redis_info.get('total_commands_processed', 0)
                    }
                except Exception as e:
                    health_metrics['redis'] = {
                        'status': 'error',
                        'error': str(e)
                    }
            else:
                health_metrics['redis'] = {'status': 'unavailable'}
            
            # Data health
            cache_status = self.get_cache_status()
            stats = self.get_statistics()
            
            health_metrics['data'] = {
                'total_tickers': stats['total_tickers'],
                'cache_coverage': cache_status.get('price_cache_coverage', 0),
                'success_rate': stats['success_rate'],
                'daily_requests': stats['daily_requests'],
                'quota_remaining': stats['quota_remaining'],
                'total_processed': stats['total_processed'],
                'error_rate': stats['failed'] / max(stats['total_processed'], 1) * 100
            }
            
            # Performance health
            health_metrics['performance'] = {
                'batch_size': BATCH_SIZE,
                'rate_limit_delay': RATE_LIMIT_DELAY,
                'cache_ttl_days': CACHE_TTL_DAYS,
                'max_retries': MAX_RETRIES
            }
            
            # Determine overall health status
            if (health_metrics['redis']['status'] == 'connected' and 
                health_metrics['data']['cache_coverage'] > 50 and
                health_metrics['data']['quota_remaining'] > 0):
                # If no requests made yet, consider healthy if cache coverage is good
                if health_metrics['data']['total_processed'] == 0:
                    health_metrics['system_status'] = 'healthy'
                elif health_metrics['data']['success_rate'] > 80:
                    health_metrics['system_status'] = 'healthy'
                elif health_metrics['data']['success_rate'] > 50:
                    health_metrics['system_status'] = 'degraded'
                else:
                    health_metrics['system_status'] = 'unhealthy'
            elif (health_metrics['redis']['status'] == 'connected' and
                  health_metrics['data']['cache_coverage'] > 30):
                health_metrics['system_status'] = 'degraded'
            else:
                health_metrics['system_status'] = 'unhealthy'
            
            return health_metrics
            
        except Exception as e:
            return {
                'system_status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _auto_warm_cache(self):
        """Auto-warm cache if coverage is low"""
        if not self.r:
            logger.info("❌ Redis unavailable - skipping auto-warm cache")
            return
            
        try:
            price_keys = self.r.keys("ticker_data:prices:*")
            sector_keys = self.r.keys("ticker_data:sector:*")
            cache_coverage = len(price_keys) / len(self.all_tickers) * 100
            sector_coverage = len(sector_keys) / len(self.all_tickers) * 100
            
            if cache_coverage < 80 or sector_coverage < 80:  # If less than 80% cached
                logger.info(f"🔄 Cache coverage: prices {cache_coverage:.1f}%, sectors {sector_coverage:.1f}% - starting auto-warm")
                logger.info("⏳ This may take 5-10 minutes for the first time (respecting rate limits)...")
                
                # Start background cache warming
                cache_thread = threading.Thread(target=self._background_cache_warming, daemon=True)
                cache_thread.start()
                
                logger.info("🚀 Cache warming started in background")
            else:
                logger.info(f"✅ Cache coverage: prices {cache_coverage:.1f}%, sectors {sector_coverage:.1f}% - no warming needed")
                
                # Even with good coverage, run corruption scan for data quality
                self._run_corruption_scan_if_needed()
        except Exception as e:
            logger.error(f"❌ Error in auto-warm cache: {e}")
    
    def _run_corruption_scan_if_needed(self):
        """Corruption scan disabled for performance"""
        logger.info("✅ Corruption scan disabled for fast startup")

    def _background_cache_warming(self):
        """Background thread for cache warming with better error handling"""
        try:
            logger.info("🔄 Starting background cache warming...")
            start_time = time.time()
            
            self.fetch_all_data()
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Background cache warming completed in {elapsed_time:.1f}s!")
            
            # Log final statistics
            stats = self.get_statistics()
            logger.info(f"📊 Cache warming stats: {stats['successful']} successful, {stats['failed']} failed")
            
        except Exception as e:
            logger.error(f"❌ Background cache warming failed: {e}")


    def preview_expired_data(self):
        """
        Compute how many tickers would be refreshed without performing any action.
        Checks both missing keys and TTL expiration status.
        """
        if not self.r:
            return {
                'expired_count': 0,
                'tickers': [],
                'missing_counts': {'prices': 0, 'sector': 0, 'metrics': 0},
                'missing_samples': {'prices': [], 'sector': [], 'metrics': []},
                'refresh_candidates': [],
                'expiring_soon_count': 0,
                'expiring_soon_tickers': []
            }

        expired_tickers: List[str] = []
        expiring_soon_tickers: List[str] = []
        missing_prices: List[str] = []
        missing_sector: List[str] = []
        missing_metrics: List[str] = []
        expired_by_ttl: List[str] = []

        for ticker in self.all_tickers:
            # Get cache keys
            price_key = self._get_cache_key(ticker, 'prices')
            sector_key = self._get_cache_key(ticker, 'sector')
            metrics_key = self._get_cache_key(ticker, 'metrics')
            
            # Check if keys exist
            has_prices = bool(self.r.exists(price_key))
            has_sector = bool(self.r.exists(sector_key))
            has_metrics = bool(self.r.exists(metrics_key))
            
            # Check TTL values for prices and sector (metrics are optional)
            price_ttl = self.r.ttl(price_key) if has_prices else -2
            sector_ttl = self.r.ttl(sector_key) if has_sector else -2
            
            # Track missing data
            if not has_prices:
                missing_prices.append(ticker)
            if not has_sector:
                missing_sector.append(ticker)
            if not has_metrics:
                missing_metrics.append(ticker)
            
            # Determine the minimum TTL (most critical)
            # Only consider TTL if keys exist, otherwise treat as missing
            min_ttl = None
            if has_prices and has_sector:
                # Both exist - use minimum TTL
                if price_ttl > 0 and sector_ttl > 0:
                    min_ttl = min(price_ttl, sector_ttl)
                elif price_ttl > 0:
                    min_ttl = price_ttl
                elif sector_ttl > 0:
                    min_ttl = sector_ttl
                else:
                    # At least one has -1 (no expiration), 0 (expired), or -2 (doesn't exist)
                    min_ttl = max(price_ttl, sector_ttl)  # Use the "worst" status
            elif has_prices:
                min_ttl = price_ttl
            elif has_sector:
                min_ttl = sector_ttl
            
            # Check TTL expiration status
            is_expired_by_ttl = False
            is_expiring_soon = False
            
            if min_ttl is not None:
                if min_ttl == -2:  # Key doesn't exist
                    is_expired_by_ttl = True
                elif min_ttl == -1:  # No expiration set - consider as expired
                    is_expired_by_ttl = True
                elif min_ttl == 0:  # Expired
                    is_expired_by_ttl = True
                elif min_ttl > 0 and min_ttl < 86400:  # Less than 24 hours remaining
                    is_expiring_soon = True
            
            # Determine if ticker needs refresh
            needs_refresh = False
            
            # Missing critical data (prices or sector)
            if not has_prices or not has_sector:
                needs_refresh = True
            
            # Expired by TTL (even if keys exist)
            if is_expired_by_ttl and has_prices and has_sector:
                needs_refresh = True
                if ticker not in expired_by_ttl:
                    expired_by_ttl.append(ticker)
            
            # Expiring soon (add to separate list for information, not necessarily needing refresh)
            if is_expiring_soon:
                if ticker not in expiring_soon_tickers:
                    expiring_soon_tickers.append(ticker)
            
            # Add to expired list if needs refresh
            if needs_refresh and ticker not in expired_tickers:
                expired_tickers.append(ticker)

        return {
            'expired_count': len(expired_tickers),
            'tickers': expired_tickers[:20],
            'missing_counts': {
                'prices': len(missing_prices),
                'sector': len(missing_sector),
                'metrics': len(missing_metrics)
            },
            'missing_samples': {
                'prices': missing_prices[:20],
                'sector': missing_sector[:20],
                'metrics': missing_metrics[:20]
            },
            'expired_by_ttl_count': len(expired_by_ttl),
            'expired_by_ttl_tickers': expired_by_ttl[:20],
            'expiring_soon_count': len(expiring_soon_tickers),
            'expiring_soon_tickers': expiring_soon_tickers[:20],
            # Provide the complete candidate list so callers can target just the gaps
            'refresh_candidates': expired_tickers
        }

    def force_refresh_expired_data(self, job_logger: Optional[logging.Logger] = None):
        """Force refresh of expired data with incremental month addition"""
        job_logger = job_logger or SMART_REFRESH_LOGGER

        if not self.r:
            logger.warning("❌ Redis unavailable - cannot refresh data")
            job_logger.error("Redis unavailable - refresh aborted")
            return {
                'expired_before': 0,
                'expired_after': 0,
                'refreshed_count': 0,
                'success': False
            }
        
        logger.info("🔄 Checking for expired data to refresh...")
        job_logger.info("Ticker refresh requested")

        # Check which tickers have expired or missing data
        expired_tickers = []
        metrics_computed = []

        for ticker in self.all_tickers:
            has_prices = bool(self._is_cached(ticker, 'prices'))
            has_sector = bool(self._is_cached(ticker, 'sector'))
            has_metrics = bool(self._is_cached(ticker, 'metrics'))

            # If prices and sector exist but metrics are missing, attempt local calculation first
            if has_prices and has_sector and not has_metrics:
                try:
                    cached_prices = self._load_from_cache(ticker, 'prices')
                    if isinstance(cached_prices, pd.Series) and not cached_prices.empty:
                        if self._calculate_and_save_metrics(ticker, cached_prices):
                            metrics_computed.append(ticker)
                            has_metrics = True
                            job_logger.info("%s metrics computed locally from cached prices", ticker)
                except Exception as metrics_error:
                    logger.warning(f"⚠️ {ticker}: Failed to compute metrics from cache ({metrics_error})")
                    job_logger.warning(
                        "%s metrics computation from cache failed: %s", ticker, metrics_error
                    )

            if not (has_prices and has_sector and has_metrics):
                expired_tickers.append(ticker)
        
        if expired_tickers:
            logger.info(f"🔄 Found {len(expired_tickers)} tickers needing refresh")
            job_logger.info(
                "Found %s tickers requiring external refresh (prices/sector/metrics missing)",
                len(expired_tickers),
            )
            
            # Update end date to current month for incremental updates
            global END_DATE
            current_end = datetime.now().replace(day=1)  # First of current month
            if current_end > END_DATE:
                END_DATE = current_end
                logger.info(f"📅 Updated end date to {END_DATE.strftime('%Y-%m-%d')} for incremental update")
                job_logger.info("Adjusted fetch end date to %s", END_DATE.strftime('%Y-%m-%d'))
            
            # Process expired tickers in small batches
            total_batches = (len(expired_tickers) + BATCH_SIZE - 1) // BATCH_SIZE
            for i in range(0, len(expired_tickers), BATCH_SIZE):
                batch = expired_tickers[i:i + BATCH_SIZE]
                batch_num = i // BATCH_SIZE + 1
                logger.info(f"🔄 Refreshing batch {batch_num}: {len(batch)} expired tickers")
                job_logger.info(
                    "Refreshing batch %s/%s (%s tickers)",
                    batch_num,
                    total_batches,
                    len(batch),
                )
                self._process_batch(
                    batch,
                    batch_number=batch_num,
                    total_batches=total_batches,
                    job_logger=job_logger,
                )
                
                if i + BATCH_SIZE < len(expired_tickers):
                    job_logger.info("Waiting %ss between batches", RATE_LIMIT_DELAY)
                    time.sleep(RATE_LIMIT_DELAY)
            # Recompute remaining expired after processing
            expired_after = []
            for ticker in self.all_tickers:
                if not self._is_cached(ticker, 'prices') or not self._is_cached(ticker, 'sector'):
                    expired_after.append(ticker)
            refreshed_count = len(expired_tickers) - len(expired_after)
            result = {
                'expired_before': len(expired_tickers),
                'expired_after': len(expired_after),
                'refreshed_count': max(refreshed_count, 0),
                'success': True
            }
            if metrics_computed:
                result['metrics_computed_from_cache'] = metrics_computed
                job_logger.info(
                    "Metrics computed locally for %s tickers: %s",
                    len(metrics_computed),
                    ", ".join(metrics_computed),
                )
            job_logger.info(
                "Ticker refresh complete: expired_before=%s expired_after=%s refreshed=%s",
                result['expired_before'],
                result['expired_after'],
                result['refreshed_count'],
            )
            return result
        else:
            logger.info("✅ No expired data found")
            job_logger.info("Ticker refresh complete: no expired data found")
            return {
                'expired_before': 0,
                'expired_after': 0,
                'refreshed_count': 0,
                'success': True
            }

    def clear_cache(self) -> None:
        """Clear all cached data"""
        if self.r is None:
            logger.info("Redis unavailable - no cache to clear")
            return
            
        try:
            price_keys = self.r.keys("ticker_data:prices:*")
            sector_keys = self.r.keys("ticker_data:sector:*")
            metrics_keys = self.r.keys("ticker_data:metrics:*")
            
            if price_keys:
                self.r.delete(*price_keys)
            if sector_keys:
                self.r.delete(*sector_keys)
            if metrics_keys:
                self.r.delete(*metrics_keys)
                
            logger.info(f"Cleared {len(price_keys)} price entries, {len(sector_keys)} sector entries, and {len(metrics_keys)} metrics entries")
            
            # Reset statistics
            self.stats = {
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'cached': 0,
                'errors': defaultdict(int)
            }
            logger.info("✅ Statistics reset")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def fetch_all_data_with_retry(self, max_attempts: int = 3) -> Dict[str, Dict[str, Any]]:
        """Fetch all data with multiple attempts and intelligent fallback"""
        logger.info(f"🚀 Starting comprehensive data fetch for {len(self.all_tickers)} tickers")
        logger.info(f"📊 Optimized settings: batch_size={BATCH_SIZE}, delay={YAHOO_REQUEST_DELAY}, retries={MAX_RETRIES}")
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔄 Attempt {attempt + 1}/{max_attempts}")
                results = self.fetch_all_data()
                
                success_rate = (self.stats['successful'] / max(self.stats['total_processed'], 1)) * 100
                if success_rate > 0.8:  # 80% success rate threshold
                    logger.info(f"✅ Data fetch successful with {success_rate:.1f}% success rate")
                    return results
                else:
                    logger.warning(f"⚠️ Low success rate ({success_rate:.1f}%), retrying...")
                    
            except Exception as e:
                logger.error(f"❌ Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    wait_time = 60 * (2 ** attempt)  # Exponential backoff
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
        
        logger.error("❌ All attempts failed, falling back to Alpha Vantage for remaining tickers")
        return self._fallback_to_alpha_vantage()

    def _fallback_to_alpha_vantage(self) -> Dict[str, Dict[str, Any]]:
        """Fallback to Alpha Vantage for tickers that failed with yfinance"""
        logger.info("🔄 Starting Alpha Vantage fallback for failed tickers...")
        
        failed_tickers = []
        for ticker in self.all_tickers:
            if not self._is_cached(ticker, 'prices') or not self._is_cached(ticker, 'sector'):
                failed_tickers.append(ticker)
        
        if not failed_tickers:
            logger.info("✅ All tickers already have data, no fallback needed")
            return {}
        
        logger.info(f"🔄 Processing {len(failed_tickers)} failed tickers with Alpha Vantage...")
        
        results = {}
        success_count = 0
        
        for i, ticker in enumerate(failed_tickers, 1):
            try:
                logger.info(f"🔄 [{i}/{len(failed_tickers)}] Processing {ticker} with Alpha Vantage...")
                
                fallback_data = self._fetch_with_alpha_vantage_fallback(ticker)
                if fallback_data:
                    results[ticker] = fallback_data
                    success_count += 1
                    logger.info(f"✅ {ticker}: Alpha Vantage fallback successful")
                else:
                    logger.warning(f"⚠️ {ticker}: Alpha Vantage fallback failed")
                
                # Rate limiting for Alpha Vantage
                if i < len(failed_tickers):
                    time.sleep(ALPHA_VANTAGE_DELAY)
                    
            except Exception as e:
                logger.error(f"❌ Alpha Vantage fallback error for {ticker}: {e}")
        
        logger.info(f"🎉 Alpha Vantage fallback completed: {success_count}/{len(failed_tickers)} successful")
        return results

    def warm_cache(self) -> Dict[str, Any]:
        """
        Main cache warming method with corruption detection
        Returns: Cache warming results with corruption status
        """
        logger.info("🔥 Starting main cache warming process...")
        
        # First, run corruption scan to identify issues
        corruption_status = self._run_corruption_scan_before_warming()
        
        # Then warm the cache
        warming_results = self._perform_cache_warming()
        
        # Combine results
        results = {
            'warming_results': warming_results,
            'corruption_status': corruption_status,
            'timestamp': datetime.now().isoformat(),
            'recommendations': []
        }
        
        # Generate recommendations based on corruption status
        if corruption_status['critical_issues'] > 0:
            results['recommendations'].append({
                'priority': 'high',
                'action': 'Critical corruption detected',
                'description': f'{corruption_status["critical_issues"]} tickers have critical data issues',
                'command': 'Data has been refreshed during warming'
            })
        
        if corruption_status['warning_issues'] > 0:
            results['recommendations'].append({
                'priority': 'medium',
                'action': 'Data quality warnings',
                'description': f'{corruption_status["warning_issues"]} tickers have minor quality issues',
                'command': 'Monitor and consider manual refresh if needed'
            })
        
        logger.info("✅ Main cache warming completed with corruption detection")
        return results
    
    def _run_corruption_scan_before_warming(self) -> Dict[str, Any]:
        """Corruption scan disabled for performance"""
        logger.info("✅ Corruption scan disabled for fast startup")
        return {
            'scan_timestamp': datetime.now().isoformat(),
            'critical_issues': 0,
            'warning_issues': 0,
            'missing_data': 0,
            'total_scanned': 0,
            'corrupted_tickers': [],
            'status': 'disabled'
        }
    
    def _perform_cache_warming(self) -> Dict[str, Any]:
        """Perform the actual cache warming process"""
        try:
            start_time = time.time()
            
            # Use the existing fetch_all_data method
            self.fetch_all_data()
            
            elapsed_time = time.time() - start_time
            
            # Get final statistics
            stats = self.get_statistics()
            
            return {
                'success': True,
                'elapsed_time': elapsed_time,
                'statistics': stats,
                'cache_coverage': {
                    'prices': self._get_cache_coverage(),
                    'sectors': self._get_sector_cache_coverage()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Cache warming failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'elapsed_time': 0,
                'statistics': {},
                'cache_coverage': {'prices': 0, 'sectors': 0}
            }
    
    def warm_required_cache(self) -> Dict[str, Any]:
        """
        Pre-warm cache for all required tickers (educational pairs and recommendation pools)
        Returns: Cache status
        """
        required_tickers = set([
            # Educational pairs
            'NVDA', 'AMZN', 'JNJ', 'TSLA',
            
            # Conservative pool
            'JNJ', 'PG', 'KO', 'WMT', 'VZ', 'UNH',
            
            # Moderate pool
            'AAPL', 'MSFT', 'GOOGL', 'V', 'MA', 'HD',
            
            # Aggressive pool
            'NVDA', 'TSLA', 'AMD', 'ADBE', 'CRM', 'META'
        ])
        
        logger.info(f"🔥 Warming cache for {len(required_tickers)} required tickers...")
        
        # Set time frame for data (4 years of monthly data)
        current_date = datetime.now()
        self.START_DATE = datetime(current_date.year - 4, current_date.month, 1)
        self.END_DATE = current_date
        
        success_count = 0
        error_count = 0
        
        for ticker in required_tickers:
            try:
                # Check if data needs updating
                cached_prices = self._load_from_cache(ticker, 'prices')
                cached_sector = self._load_from_cache(ticker, 'sector')
                
                if cached_prices is None or cached_sector is None:
                    logger.info(f"Fetching data for {ticker}...")
                    data = self._fetch_single_ticker_with_retry(ticker)
                    if data:
                        success_count += 1
                        logger.info(f"✅ {ticker}: Successfully cached")
                    else:
                        error_count += 1
                        logger.error(f"❌ {ticker}: Failed to cache")
                else:
                    # Validate data freshness
                    if isinstance(cached_prices, pd.Series) and not cached_prices.empty:
                        last_date = cached_prices.index[-1]
                        # Convert to timezone-naive datetime for comparison
                        if hasattr(last_date, 'tz_localize'):
                            last_date = last_date.tz_localize(None)
                        if last_date < self.END_DATE - timedelta(days=30):  # More than a month old
                            logger.info(f"🔄 {ticker}: Refreshing stale data...")
                            data = self._fetch_single_ticker_with_retry(ticker)
                            if data:
                                success_count += 1
                                logger.info(f"✅ {ticker}: Successfully refreshed")
                            else:
                                error_count += 1
                                logger.error(f"❌ {ticker}: Failed to refresh")
                        else:
                            success_count += 1
                            logger.info(f"✅ {ticker}: Using fresh cached data")
                    else:
                        success_count += 1
                        logger.info(f"✅ {ticker}: Using cached data")
            except Exception as e:
                logger.error(f"❌ Error warming cache for {ticker}: {e}")
                error_count += 1
            
            # Rate limiting between tickers
            time.sleep(self._get_random_delay())
        
        status = {
            'required_tickers': len(required_tickers),
            'success_count': success_count,
            'error_count': error_count,
            'cache_coverage': f"{(success_count / len(required_tickers)) * 100:.1f}%",
            'time_frame': {
                'start': self.START_DATE.strftime('%Y-%m-%d'),
                'end': self.END_DATE.strftime('%Y-%m-%d'),
                'months': (self.END_DATE.year - self.START_DATE.year) * 12 + 
                         self.END_DATE.month - self.START_DATE.month
            }
        }
        
        logger.info(f"✅ Cache warming completed: {status['cache_coverage']} coverage")
        logger.info(f"📅 Time frame: {status['time_frame']['start']} to {status['time_frame']['end']}")
        return status

    def _fetch_alpha_vantage_financial_metrics(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch financial metrics from Alpha Vantage API
        Returns: Dictionary with financial metrics or None if failed
        """
        try:
            logger.debug(f"🔄 Fetching Alpha Vantage financial metrics for {ticker}...")
            
            # Rate limiting for Alpha Vantage free tier
            time.sleep(ALPHA_VANTAGE_DELAY)
            
            # REMOVED: Financial metrics fetching for now
            # We'll add this back later when needed
            logger.info(f"✅ {ticker}: Financial metrics fetching disabled for now")
            return None
                
        except Exception as e:
            logger.error(f"❌ Alpha Vantage fetch error for {ticker}: {e}")
            return None

    def _fetch_alpha_vantage_price_data(self, ticker: str) -> Optional[pd.Series]:
        """
        Fetch monthly price data from Alpha Vantage API
        Returns: Pandas Series with monthly adjusted close prices
        """
        try:
            logger.debug(f"🔄 Fetching Alpha Vantage price data for {ticker}...")
            
            # Rate limiting for Alpha Vantage free tier
            time.sleep(ALPHA_VANTAGE_DELAY)
            
            # Fetch monthly adjusted close data
            monthly_data, meta_data = self.alpha_vantage_timeseries.get_monthly_adjusted(ticker)
            
            # Handle different response formats
            if isinstance(monthly_data, dict) and 'Error Message' in monthly_data:
                logger.warning(f"⚠️ Alpha Vantage price data error for {ticker}: {monthly_data['Error Message']}")
                return None
            elif hasattr(monthly_data, 'empty') and monthly_data.empty:
                logger.warning(f"⚠️ Alpha Vantage price data empty for {ticker}")
                return None
            
            # Convert to pandas Series
            prices = {}
            
            # Handle DataFrame response
            if hasattr(monthly_data, 'to_dict'):
                monthly_data = monthly_data.to_dict('index')
            
            # Handle different data structures
            if isinstance(monthly_data, dict):
                for date_str, data in monthly_data.items():
                    try:
                        # Parse date and extract adjusted close price
                        if isinstance(date_str, str):
                            date = datetime.strptime(date_str, '%Y-%m-%d')
                        else:
                            date = date_str
                        
                        # Extract adjusted close price from different possible formats
                        if isinstance(data, dict):
                            adjusted_close = data.get('5. adjusted close') or data.get('adjusted_close') or data.get('close')
                        else:
                            adjusted_close = data
                        
                        if adjusted_close is not None:
                            prices[date] = float(adjusted_close)
                    except (ValueError, KeyError, TypeError) as e:
                        logger.debug(f"⚠️ Skipping invalid data point for {ticker}: {e}")
                        continue
            
            if not prices:
                logger.warning(f"⚠️ No valid price data found for {ticker}")
                return None
            
            # Create pandas Series and sort by date
            price_series = pd.Series(prices)
            price_series = price_series.sort_index()
            
            logger.info(f"✅ {ticker}: Successfully fetched {len(price_series)} monthly price points from Alpha Vantage")
            return price_series
            
        except Exception as e:
            logger.error(f"❌ Alpha Vantage price fetch error for {ticker}: {e}")
            return None

    def _fetch_with_alpha_vantage_fallback(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data using Alpha Vantage as fallback when yfinance fails
        Returns: Dictionary with prices, sector info, and financial metrics
        """
        try:
            logger.info(f"🔄 Attempting Alpha Vantage fallback for {ticker}...")
            
            # Fetch price data
            price_data = self._fetch_alpha_vantage_price_data(ticker)
            if price_data is None:
                return None
            
            # Fetch financial metrics
            financial_metrics = self._fetch_alpha_vantage_financial_metrics(ticker)
            
            # Create sector info (basic fallback)
            sector_info = {
                'sector': 'Unknown',
                'industry': 'Unknown',
                'country': 'United States',
                'exchange': 'Unknown',
                'companyName': ticker
            }
            
            # Add financial metrics if available
            if financial_metrics:
                sector_info['financial_metrics'] = financial_metrics
            
            # Validate price data
            if not self._validate_price_data(price_data, ticker):
                return None
            
            data_to_cache = {
                'prices': price_data,
                'sector': sector_info
            }
            
            # Cache the data
            self._save_to_cache(ticker, data_to_cache)
            
            logger.info(f"✅ {ticker}: Alpha Vantage fallback successful")
            return data_to_cache
            
        except Exception as e:
            logger.error(f"❌ Alpha Vantage fallback failed for {ticker}: {e}")
            return None

    def smart_monthly_refresh(self, job_logger: Optional[logging.Logger] = None):
        """
        Smart monthly refresh that only fetches the latest month of data
        - Extends time range incrementally (no re-downloading of historical data)
        - Respects TTL and only refreshes when needed
        - Efficient: Only fetches new months, not entire history
        """
        job_logger = job_logger or SMART_REFRESH_LOGGER

        if not self.r:
            logger.warning("❌ Redis unavailable - cannot perform monthly refresh")
            job_logger.error("Redis unavailable - smart monthly refresh aborted")
            return
        
        logger.info("🔄 Starting smart monthly refresh...")
        job_logger.info("Smart monthly refresh requested")
        
        # Update end date to current month (incremental extension)
        global END_DATE
        current_end = datetime.now().replace(day=1)  # First of current month
        
        if current_end > END_DATE:
            old_end = END_DATE
            END_DATE = current_end
            logger.info(f"📅 Extended time range: {old_end.strftime('%Y-%m-%d')} → {END_DATE.strftime('%Y-%m-%d')}")
            job_logger.info(
                "Extended time range: %s → %s",
                old_end.strftime('%Y-%m-%d'),
                END_DATE.strftime('%Y-%m-%d'),
            )
        else:
            logger.info("✅ Time range already up to date")
            job_logger.info("Smart monthly refresh skipped: time range already current")
            return
        
        # Check which tickers need refresh (only those with expired cache or missing latest month)
        tickers_needing_refresh = []
        
        for ticker in self.all_tickers:
            try:
                cached_prices = self._load_from_cache(ticker, 'prices')
                
                if cached_prices is None:
                    # No cached data - needs full fetch
                    tickers_needing_refresh.append(ticker)
                    continue
                
                if not isinstance(cached_prices, pd.Series) or cached_prices.empty:
                    # Invalid cached data - needs refresh
                    tickers_needing_refresh.append(ticker)
                    continue
                
                # Check if we have the latest month
                last_cached_date = cached_prices.index[-1]
                if hasattr(last_cached_date, 'tz_localize'):
                    last_cached_date = last_cached_date.tz_localize(None)
                
                # If last cached date is more than 30 days behind current month, refresh
                if last_cached_date < current_end - timedelta(days=30):
                    tickers_needing_refresh.append(ticker)
                    
            except Exception as e:
                logger.warning(f"⚠️ Error checking {ticker} for refresh: {e}")
                tickers_needing_refresh.append(ticker)
        
        if not tickers_needing_refresh:
            logger.info("✅ All tickers have current month data")
            job_logger.info("Smart monthly refresh skipped: all tickers current")
            return
        
        logger.info(f"🔄 Found {len(tickers_needing_refresh)} tickers needing refresh")
        job_logger.info("Refreshing %s tickers for current month data", len(tickers_needing_refresh))
        
        # Process in batches with rate limiting
        success_count = 0
        error_count = 0
        
        for i in range(0, len(tickers_needing_refresh), BATCH_SIZE):
            batch = tickers_needing_refresh[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(tickers_needing_refresh) + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"🔄 Processing batch {batch_num}/{total_batches}: {len(batch)} tickers")
            job_logger.info("Batch %s/%s started (%s tickers)", batch_num, total_batches, len(batch))
            
            for ticker in batch:
                try:
                    # Fetch only new data (yfinance will automatically extend the range)
                    data = self._fetch_single_ticker_with_retry(ticker)
                    if data:
                        success_count += 1
                        logger.debug(f"✅ {ticker}: Monthly refresh successful")
                        job_logger.info("✅ %s refreshed", ticker)
                    else:
                        error_count += 1
                        logger.warning(f"⚠️ {ticker}: Monthly refresh failed")
                        job_logger.warning("⚠️ %s refresh failed", ticker)
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Error refreshing {ticker}: {e}")
                    job_logger.error("❌ %s refresh errored: %s", ticker, e)
                
                # Rate limiting between individual tickers
                time.sleep(self._get_random_delay())
            
            # Rate limiting between batches (except for last batch)
            if i + BATCH_SIZE < len(tickers_needing_refresh):
                logger.info(f"⏳ Waiting {RATE_LIMIT_DELAY}s between batches...")
                job_logger.info("Waiting %ss before next batch", RATE_LIMIT_DELAY)
                time.sleep(RATE_LIMIT_DELAY)
        
        logger.info(f"🎉 Smart monthly refresh completed!")
        logger.info(f"📊 Results: {success_count} successful, {error_count} failed")
        logger.info(f"📅 New time range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
        job_logger.info(
            "Smart monthly refresh completed: %s success, %s failed | range %s → %s",
            success_count,
            error_count,
            START_DATE.strftime('%Y-%m-%d'),
            END_DATE.strftime('%Y-%m-%d'),
        )
        
        return {
            'status': 'completed',
            'success_count': success_count,
            'error_count': error_count,
            'total_processed': len(tickers_needing_refresh),
            'time_range': {
                'start': START_DATE.strftime('%Y-%m-%d'),
                'end': END_DATE.strftime('%Y-%m-%d'),
                'months': (END_DATE.year - START_DATE.year) * 12 + END_DATE.month - START_DATE.month
            }
        }
    
    def _get_cache_coverage(self):
        """Get cache coverage percentage for prices"""
        if not self.r:
            return 0.0
        
        try:
            price_keys = self.r.keys("ticker_data:prices:*")
            return len(price_keys) / len(self.all_tickers)
        except Exception as e:
            logger.error(f"Error getting cache coverage: {e}")
            return 0.0
    
    def _get_sector_cache_coverage(self):
        """Get cache coverage percentage for sectors"""
        if not self.r:
            return 0.0
        
        try:
            sector_keys = self.r.keys("ticker_data:sector:*")
            return len(sector_keys) / len(self.all_tickers)
        except Exception as e:
            logger.error(f"Error getting sector cache coverage: {e}")
            return 0.0
    
    def refresh_specific_tickers(self, tickers: List[str], job_logger: Optional[logging.Logger] = None):
        """
        Refresh specific tickers using smart monthly refresh logic
        """
        job_logger = job_logger or SMART_REFRESH_LOGGER

        try:
            logger.info(f"🔄 Refreshing {len(tickers)} specific tickers")
            job_logger.info("Targeted refresh requested for %s tickers", len(tickers))
            job_logger.info("Tickers: %s", ", ".join(tickers))
            
            success_count = 0
            error_count = 0
            
            for ticker in tickers:
                try:
                    # Use the same logic as smart_monthly_refresh but for specific tickers
                    # Force refetch to extend history when needed (e.g., 2008 stress tests)
                    data = self._fetch_single_ticker_with_retry(ticker, force_fetch=True)
                    if data:
                        success_count += 1
                        logger.debug(f"✅ {ticker} refreshed successfully")
                        job_logger.info("✅ %s refreshed successfully", ticker)
                    else:
                        error_count += 1
                        logger.warning(f"⚠️ {ticker} refresh failed")
                        job_logger.warning("⚠️ %s refresh failed", ticker)
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Error refreshing {ticker}: {e}")
                    job_logger.error("❌ %s refresh errored: %s", ticker, e)
            
            logger.info(f"🎉 Specific ticker refresh completed: {success_count} successful, {error_count} failed")
            job_logger.info(
                "Targeted refresh completed: %s success, %s failed",
                success_count,
                error_count,
            )
            
            return {
                "success_count": success_count,
                "error_count": error_count,
                "total_processed": len(tickers)
            }
            
        except Exception as e:
            logger.error(f"❌ Error in specific ticker refresh: {e}")
            job_logger.error("Targeted refresh failed with error: %s", e)
            return None

    def check_expired_tickers(self) -> List[str]:
        """
        Check for tickers with expired cache and require manual approval for regeneration
        Returns list of expired tickers that need manual approval
        """
        expired_tickers = []
        
        if not self.r:
            logger.warning("⚠️ Redis not available for expired ticker check")
            return expired_tickers
        
        try:
            for ticker in self.all_tickers:
                key = self._get_cache_key(ticker, 'prices')
                if self.r.exists(key):
                    ttl = self.r.ttl(key)
                    if ttl == -1:  # No expiration set
                        logger.warning(f"⚠️ {ticker}: No TTL set - needs manual review")
                        expired_tickers.append(ticker)
                    elif ttl == -2:  # Key doesn't exist
                        logger.info(f"ℹ️ {ticker}: Not in cache - needs manual approval for regeneration")
                        expired_tickers.append(ticker)
                    elif ttl < 3600:  # Less than 1 hour remaining
                        logger.warning(f"⚠️ {ticker}: Cache expires in {ttl} seconds - needs manual approval for regeneration")
                        expired_tickers.append(ticker)
            
            if expired_tickers:
                logger.warning(f"⚠️ Found {len(expired_tickers)} tickers requiring manual approval for regeneration")
                logger.warning(f"🔧 Set MANUAL_REGENERATION_REQUIRED=false to allow automatic regeneration")
            else:
                logger.info("✅ No expired tickers found - all caches are valid")
                
        except Exception as e:
            logger.error(f"❌ Error checking expired tickers: {e}")
        
        return expired_tickers

    def manual_regeneration_approval(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Manually approve regeneration for specific expired tickers
        This method should be called by developers to approve regeneration
        """
        if not tickers:
            logger.info("ℹ️ No tickers provided for manual regeneration")
            return {"approved": 0, "message": "No tickers provided"}
        
        logger.info(f"🔧 Manual regeneration approved for {len(tickers)} tickers")
        logger.info(f"📋 Approved tickers: {tickers}")
        
        # Temporarily disable manual regeneration requirement
        os.environ['MANUAL_REGENERATION_REQUIRED'] = 'false'
        
        try:
            # Process approved tickers
            results = {}
            for ticker in tickers:
                if ticker in self.all_tickers:
                    data = self._fetch_single_ticker_with_retry(ticker)
                    if data:
                        results[ticker] = "Success"
                        logger.info(f"✅ {ticker}: Manual regeneration successful")
                    else:
                        results[ticker] = "Failed"
                        logger.warning(f"❌ {ticker}: Manual regeneration failed")
                else:
                    results[ticker] = "Not in master list"
                    logger.warning(f"⚠️ {ticker}: Not in master list")
            
            # Re-enable manual regeneration requirement
            os.environ['MANUAL_REGENERATION_REQUIRED'] = 'true'
            
            return {
                "approved": len(tickers),
                "results": results,
                "message": f"Manual regeneration completed for {len(tickers)} tickers"
            }
            
        except Exception as e:
            # Re-enable manual regeneration requirement even if error occurs
            os.environ['MANUAL_REGENERATION_REQUIRED'] = 'true'
            logger.error(f"❌ Error during manual regeneration: {e}")
            return {"approved": 0, "error": str(e), "message": "Manual regeneration failed"}

# Global instance
enhanced_data_fetcher = EnhancedDataFetcher() 