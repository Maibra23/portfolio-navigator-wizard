#!/usr/bin/env python3
"""
Redis-First Data Service
Provides Redis-first data access with lazy initialization of EnhancedDataFetcher
"""

import logging
import os
import random
import redis
import json
import gzip
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from functools import lru_cache
from .timestamp_utils import normalize_timestamp
from .logging_utils import get_job_logger

try:
    from redis.asyncio import Redis as AsyncRedis
    _ASYNC_REDIS_AVAILABLE = True
except ImportError:
    AsyncRedis = None
    _ASYNC_REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)
smart_refresh_logger = get_job_logger("smart_refresh")
full_refresh_logger = get_job_logger("full_refresh")

class RedisFirstDataService:
    """
    Redis-first data service that prioritizes cached data and only initializes
    EnhancedDataFetcher when external data is actually needed
    """
    
    # --- Memory & Connection Configuration ---
    MAX_MEMORY = "256mb"
    MAX_MEMORY_POLICY = "volatile-lru"   # Evict least-recently-used keys that have a TTL
    MAX_CONNECTIONS = 50                 # Connection pool ceiling
    TTL_JITTER_PERCENT = 15             # +/- 15% random jitter on TTLs to prevent stampede

    def __init__(self, redis_url: str = None):
        """
        Initialize Redis-First Data Service

        Args:
            redis_url: Redis connection URL (redis://host:port or rediss://host:port for TLS)
                      If not provided, uses REDIS_URL env var or defaults to localhost
        """
        import os

        # Get Redis URL from parameter or environment
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

        self.redis_client = self._init_redis_from_url(redis_url)
        self._async_client: Optional[Any] = self._init_async_redis_from_url(redis_url)
        self._enhanced_data_fetcher = None  # Lazy initialization
        self._ticker_list = None  # Cached ticker list

        # Cache configuration
        self.CACHE_TTL_DAYS = 28
        self.CACHE_TTL_HOURS = self.CACHE_TTL_DAYS * 24

        # Apply maxmemory and eviction policy on the connected Redis server
        self._configure_redis_memory()

        logger.info("Redis-First Data Service initialized")

    # ------------------------------------------------------------------ #
    #  Memory & eviction policy configuration                            #
    # ------------------------------------------------------------------ #
    def _configure_redis_memory(self):
        """
        Set maxmemory (256 MB) and volatile-lru eviction policy on the
        Redis server.  This runs once at startup so the limits are always
        enforced even if the server was restarted without a config file.
        """
        if self.redis_client is None:
            return
        try:
            self.redis_client.config_set("maxmemory", self.MAX_MEMORY)
            self.redis_client.config_set("maxmemory-policy", self.MAX_MEMORY_POLICY)
            logger.info(
                f"✅ Redis memory configured: maxmemory={self.MAX_MEMORY}, "
                f"policy={self.MAX_MEMORY_POLICY}"
            )
        except redis.ResponseError as e:
            # Some managed Redis providers (e.g. Railway) may disallow CONFIG SET.
            # In that case, rely on the provider's dashboard settings.
            logger.warning(
                f"⚠️  Could not set Redis memory config (managed provider may "
                f"block CONFIG SET): {e}"
            )
        except Exception as e:
            logger.warning(f"⚠️  Redis memory configuration failed: {e}")

    # ------------------------------------------------------------------ #
    #  TTL jitter helper                                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def jittered_ttl(base_seconds: int) -> int:
        """
        Return *base_seconds* with +/- TTL_JITTER_PERCENT random jitter.
        Prevents cache stampede when many keys are written at the same time.
        """
        jitter_range = base_seconds * RedisFirstDataService.TTL_JITTER_PERCENT / 100
        return int(base_seconds + random.uniform(-jitter_range, jitter_range))

    def _init_redis_from_url(self, redis_url: str) -> Optional[redis.Redis]:
        """Initialize Redis connection from URL (supports TLS) with connection pool."""
        try:
            import ssl
            from urllib.parse import urlparse

            # Parse the URL
            parsed = urlparse(redis_url)

            # Check if TLS is required (rediss:// scheme)
            use_ssl = parsed.scheme == 'rediss'

            # Common connection kwargs (includes pool ceiling)
            conn_kwargs = dict(
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                max_connections=self.MAX_CONNECTIONS,
                retry_on_timeout=True,
            )

            if use_ssl:
                conn_kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED

            r = redis.from_url(redis_url, **conn_kwargs)

            # Test connection
            r.ping()
            connection_type = 'TLS' if use_ssl else 'standard'
            logger.info(
                f"✅ Redis connection established ({connection_type}, "
                f"pool max_connections={self.MAX_CONNECTIONS})"
            )
            return r

        except redis.ConnectionError as e:
            logger.warning("Redis connection failed: %s", e)
            return None
        except Exception as e:
            logger.warning("Redis unavailable: %s", e)
            return None

    def _init_async_redis_from_url(self, redis_url: str) -> Optional[Any]:
        """Initialize async Redis connection from URL (for non-blocking I/O in async handlers)."""
        if not _ASYNC_REDIS_AVAILABLE:
            return None
        try:
            import ssl
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            use_ssl = parsed.scheme == "rediss"

            conn_kwargs = dict(
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                max_connections=self.MAX_CONNECTIONS,
            )
            if use_ssl:
                conn_kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED

            client = AsyncRedis.from_url(redis_url, **conn_kwargs)
            return client
        except Exception as e:
            logger.warning("Async Redis init failed: %s", e)
            return None

    async def ping_async(self) -> bool:
        """Async Redis ping for health checks."""
        if self._async_client is None:
            return False
        try:
            await self._async_client.ping()
            return True
        except Exception:
            return False

    async def get_cache_status_async(self) -> Optional[Dict[str, Any]]:
        """Async cache status for use in async route handlers."""
        if self._async_client is None:
            return None
        try:
            info = await self._async_client.info("memory")
            keys = await self._async_client.dbsize()
            return {
                "redis_connected": True,
                "used_memory": info.get("used_memory_human", "?"),
                "keys": keys,
            }
        except Exception as e:
            logger.debug("get_cache_status_async failed: %s", e)
            return None

    @property
    def enhanced_data_fetcher(self):
        """Lazy initialization of EnhancedDataFetcher"""
        if self._enhanced_data_fetcher is None:
            try:
                from .enhanced_data_fetcher import EnhancedDataFetcher
                logger.info("🔄 Lazy initializing EnhancedDataFetcher...")
                self._enhanced_data_fetcher = EnhancedDataFetcher()
                logger.info("✅ EnhancedDataFetcher initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize EnhancedDataFetcher: {e}")
                return None
        return self._enhanced_data_fetcher
    
    @property
    def all_tickers(self) -> List[str]:
        """Get all tickers (cached)"""
        if self._ticker_list is None:
            if self.redis_client:
                # Try multiple Redis keys in order of preference
                ticker_keys = [
                    "master_ticker_list",           # Primary key
                    "master_ticker_list_validated", # Validated list (fallback)
                    "ticker_list:master"            # Alternative key (fallback)
                ]
                
                for ticker_key in ticker_keys:
                    cached_tickers = self.redis_client.get(ticker_key)
                    if cached_tickers:
                        try:
                            # Try decompression first (new format)
                            try:
                                import gzip
                                decompressed = gzip.decompress(cached_tickers)
                                self._ticker_list = json.loads(decompressed.decode())
                                logger.debug(f"✅ Loaded {len(self._ticker_list)} tickers from Redis cache ({ticker_key}, compressed)")
                                return self._ticker_list
                            except Exception:
                                # Fallback to uncompressed (old format)
                                self._ticker_list = json.loads(cached_tickers.decode())
                                logger.debug(f"✅ Loaded {len(self._ticker_list)} tickers from Redis cache ({ticker_key}, uncompressed)")
                                return self._ticker_list
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to load cached tickers from {ticker_key}: {e}")
                            continue
                
                # If no Redis key found, try to get from cached tickers in Redis
                try:
                    cached_tickers_list = self.list_cached_tickers()
                    if cached_tickers_list and len(cached_tickers_list) > 0:
                        self._ticker_list = cached_tickers_list
                        logger.debug(f"✅ Loaded {len(self._ticker_list)} tickers from cached ticker data")
                        return self._ticker_list
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load from cached tickers: {e}")

                # Fallback to CSV backup (permanent source when Redis master list empty)
                csv_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "scripts", "reports", "fetchable_master_list_validated_latest.csv"
                )
                try:
                    if os.path.isfile(csv_path):
                        import csv as csv_module
                        tickers_from_csv = []
                        with open(csv_path, "r", newline="", encoding="utf-8") as f:
                            reader = csv_module.reader(f)
                            next(reader, None)  # skip header
                            for row in reader:
                                if row and row[0].strip():
                                    tickers_from_csv.append(row[0].strip())
                        if tickers_from_csv:
                            self._ticker_list = tickers_from_csv
                            logger.info(f"✅ Loaded {len(self._ticker_list)} tickers from CSV backup ({csv_path})")
                            # Seed Redis so next load uses Redis
                            if self.redis_client:
                                try:
                                    import gzip
                                    compressed = gzip.compress(json.dumps(self._ticker_list).encode())
                                    self.redis_client.setex(
                                        "master_ticker_list_validated",
                                        365 * 24 * 3600,
                                        compressed
                                    )
                                    logger.info("✅ Seeded master_ticker_list_validated in Redis from CSV")
                                except Exception as seed_err:
                                    logger.warning(f"⚠️ Failed to seed Redis from CSV: {seed_err}")
                            return self._ticker_list
                except Exception as e:
                    logger.debug(f"Could not load from CSV backup: {e}")

                # Fallback to EnhancedDataFetcher (S&P 500 + NASDAQ + ETFs)
                if self.enhanced_data_fetcher:
                    self._ticker_list = self.enhanced_data_fetcher.all_tickers
                    # Cache the ticker list
                    if self.redis_client and self._ticker_list:
                        try:
                            self.redis_client.setex(
                                "master_ticker_list", 
                                timedelta(hours=24),  # Cache for 24 hours
                                json.dumps(self._ticker_list).encode()
                            )
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to cache ticker list: {e}")
                else:
                    self._ticker_list = []
        
        return self._ticker_list
    
    def invalidate_ticker_list_cache(self):
        """Invalidate the cached ticker list to force reload"""
        self._ticker_list = None
        logger.info("🗑️ Ticker list cache invalidated")
    
    def _get_cache_key(self, ticker: str, data_type: str = 'prices') -> str:
        """Generate cache key for ticker data"""
        return f"ticker_data:{data_type}:{ticker}"
    
    def _is_cached(self, ticker: str, data_type: str = 'prices') -> bool:
        """Check if ticker data is cached in Redis"""
        if not self.redis_client:
            return False
        key = self._get_cache_key(ticker, data_type)
        return self.redis_client.exists(key)
    
    def _load_from_cache(self, ticker: str, data_type: str = 'prices') -> Optional[Any]:
        """Load ticker data from Redis cache"""
        if not self.redis_client:
            return None
        
        try:
            key = self._get_cache_key(ticker, data_type)
            if self.redis_client.exists(key):
                raw = self.redis_client.get(key)
                
                if data_type == 'prices':
                    # ENHANCED: Robust gzip decompression with fallback handling
                    try:
                        # First try to decompress as gzipped data
                        decompressed_data = gzip.decompress(raw).decode()
                        data_dict = json.loads(decompressed_data)
                        logger.debug(f"✅ {ticker}: Successfully decompressed gzipped price data")
                    except (gzip.BadGzipFile, OSError) as gzip_error:
                        # If gzip fails, try direct JSON parsing (for non-gzipped data)
                        logger.debug(f"⚠️ {ticker}: Gzip decompression failed ({gzip_error}), trying direct JSON parsing")
                        try:
                            # Try direct JSON parsing for non-gzipped data
                            data_dict = json.loads(raw.decode())
                            logger.debug(f"✅ {ticker}: Successfully parsed non-gzipped price data")
                        except json.JSONDecodeError as json_error:
                            # If both fail, try parsing as double-encoded JSON (some cached data might be double-encoded)
                            logger.debug(f"⚠️ {ticker}: Direct JSON parsing failed ({json_error}), trying double-encoded JSON")
                            try:
                                inner_json = json.loads(raw.decode())
                                data_dict = json.loads(inner_json)
                                logger.debug(f"✅ {ticker}: Successfully parsed double-encoded JSON price data")
                            except Exception as double_error:
                                logger.error(f"❌ Failed to load {ticker} prices from cache: All parsing methods failed - gzip: {gzip_error}, json: {json_error}, double-json: {double_error}")
                                return None
                    except Exception as e:
                        logger.error(f"❌ Failed to load {ticker} prices from cache: {e}")
                        return None
                    
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
                    try:
                        decoded = json.loads(raw.decode())
                        # Handle case where value is just a string like "Unknown" instead of a dict
                        if isinstance(decoded, str):
                            # Convert simple string values to dict
                            if data_type == 'sector':
                                return {'sector': decoded, 'industry': 'Unknown', 'country': 'Unknown', 'companyName': ticker}
                            return decoded
                        return decoded
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to load {ticker} {data_type} from cache: JSON decode error - {e}")
                        return None
        except Exception as e:
            logger.error(f"❌ Failed to load {ticker} {data_type} from cache: {e}")
        return None
    
    def _has_cached_monthly_data(self, ticker: str) -> bool:
        """
        Check if ticker has complete monthly data in cache (prices + sector)
        Returns: True if both prices and sector are cached, False otherwise
        """
        ticker = ticker.upper()
        has_prices = self._is_cached(ticker, 'prices')
        has_sector = self._is_cached(ticker, 'sector')
        return bool(has_prices and has_sector)
    
    def get_monthly_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get monthly data for a ticker - Redis first approach
        Returns: Dict with prices, dates, sector, industry, company name
        """
        ticker = ticker.upper()
        
        # Step 1: Check Redis cache first
        cached_prices = self._load_from_cache(ticker, 'prices')
        cached_sector = self._load_from_cache(ticker, 'sector')
        
        if cached_prices is not None and cached_sector is not None:
            logger.debug(f"✅ {ticker}: Served from Redis cache")
            return {
                'prices': cached_prices.tolist(),
                'dates': [d.strftime('%Y-%m-%d') for d in cached_prices.index],
                'ticker': ticker,
                'sector': cached_sector.get('sector', 'Unknown'),
                'industry': cached_sector.get('industry', 'Unknown'),
                'company_name': cached_sector.get('companyName', ticker),
                'country': cached_sector.get('country', 'Unknown'),
                'exchange': cached_sector.get('exchange', 'Unknown'),
                'cached': True
            }
        
        # Step 2: If not in cache, use EnhancedDataFetcher
        logger.info(f"📥 {ticker}: Not in Redis cache, fetching from EnhancedDataFetcher...")
        if self.enhanced_data_fetcher:
            return self.enhanced_data_fetcher.get_monthly_data(ticker)
        else:
            logger.error(f"❌ {ticker}: EnhancedDataFetcher unavailable")
            return None
    
    def get_ticker_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive ticker information - Redis first approach
        Returns: Dict with comprehensive ticker information
        """
        ticker = ticker.upper()
        
        # Step 1: Check Redis cache first
        cached_prices = self._load_from_cache(ticker, 'prices')
        cached_sector = self._load_from_cache(ticker, 'sector')
        cached_metrics = self._load_from_cache(ticker, 'metrics')
        
        if cached_prices is not None and cached_sector is not None:
            logger.debug(f"✅ {ticker}: Info served from Redis cache")
            
            # Calculate basic price metrics from cached data
            current_price = cached_prices.iloc[-1] if not cached_prices.empty else 0
            price_change = cached_prices.iloc[-1] - cached_prices.iloc[-2] if len(cached_prices) > 1 else 0
            price_change_pct = (price_change / cached_prices.iloc[-2] * 100) if len(cached_prices) > 1 and cached_prices.iloc[-2] != 0 else 0
            
            ticker_info = {
                'ticker': ticker,
                'company_name': cached_sector.get('companyName', ticker),
                'sector': cached_sector.get('sector', 'Unknown'),
                'industry': cached_sector.get('industry', 'Unknown'),
                'country': cached_sector.get('country', 'Unknown'),
                'exchange': cached_sector.get('exchange', 'Unknown'),
                'current_price': round(current_price, 2),
                'price_change': round(price_change, 2),
                'price_change_pct': round(price_change_pct, 2),
                'last_updated': cached_prices.index[-1].strftime('%Y-%m-%d') if not cached_prices.empty else None,
                'data_points': len(cached_prices),
                'cached': True,
                'prices': cached_prices.tolist()[-30:],  # Last 30 data points
                'dates': [d.strftime('%Y-%m-%d') for d in cached_prices.index[-30:]]
            }
            
            # Add cached metrics if available
            if cached_metrics:
                ticker_info.update({
                    'annualized_return': cached_metrics.get('annualized_return'),
                    'risk': cached_metrics.get('risk'),
                    'max_drawdown': cached_metrics.get('max_drawdown'),
                    'data_quality': cached_metrics.get('data_quality')
                })
            
            return ticker_info
        
        # Step 2: If not in cache, use EnhancedDataFetcher
        logger.info(f"📥 {ticker}: Info not in Redis cache, fetching from EnhancedDataFetcher...")
        if self.enhanced_data_fetcher:
            return self.enhanced_data_fetcher.get_ticker_info(ticker)
        else:
            logger.error(f"❌ {ticker}: EnhancedDataFetcher unavailable")
            return None

    # FAST helper for mini-lessons and UI: read only cached info without heavy parsing
    def _get_cached_ticker_info_fast(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            ticker = ticker.upper()
            prices = self._load_from_cache(ticker, 'prices')
            sector = self._load_from_cache(ticker, 'sector')
            if prices is None or sector is None:
                return None
            # prices is a pandas Series
            current_price = float(prices.iloc[-1]) if hasattr(prices, 'iloc') and len(prices) > 0 else 0.0
            data_points = int(len(prices)) if hasattr(prices, '__len__') else 0
            return {
                'ticker': ticker,
                'current_price': round(current_price, 4),
                'data_points': data_points,
                'company_name': sector.get('companyName', ticker),
                'sector': sector.get('sector', 'Unknown'),
                'industry': sector.get('industry', 'Unknown'),
            }
        except Exception as e:
            logger.debug(f"_get_cached_ticker_info_fast failed for {ticker}: {e}")
            return None
    
    def get_cached_metrics(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get pre-calculated metrics for a ticker - Redis first"""
        # Check Redis cache first
        cached_metrics = self._load_from_cache(ticker, 'metrics')
        if cached_metrics:
            return cached_metrics
        
        # Fallback to EnhancedDataFetcher
        if self.enhanced_data_fetcher:
            return self.enhanced_data_fetcher.get_cached_metrics(ticker)
        return None
    
    def search_tickers(self, query: str, limit: int = 10, filters: Dict = None) -> List[Dict[str, Any]]:
        """
        Comprehensive search through ONLY cached tickers with smart pre-filtering
        Returns: List of matching tickers with comprehensive information and relevance scores
        NOTE: Only returns tickers that have complete data in Redis cache
        """
        q = query.strip().lower()
        if not q:
            return []
        
        q_upper = q.upper()
        sector_filter = filters.get('sector', None) if filters else None
        risk_filter = filters.get('risk_profile', None) if filters else None

        # Fast path: query looks like a single ticker (e.g. AAPL, MTRS.ST) - direct Redis lookup
        if len(q) <= 10 and q.replace(".", "").replace("-", "").isalnum():
            all_tickers = self.all_tickers
            cached_tickers = [t for t in all_tickers if self._is_cached(t, 'prices') and self._is_cached(t, 'sector')]
            if q_upper in cached_tickers:
                ticker_info = self.get_ticker_info(q_upper)
                if ticker_info:
                    if sector_filter and ticker_info.get('sector', '').lower() != sector_filter.lower():
                        pass  # fall through to full search
                    elif risk_filter and not self._is_suitable_for_risk_profile(ticker_info, risk_filter):
                        pass
                    else:
                        score = self._calculate_enhanced_relevance_score(q, ticker_info)
                        if score > 0:
                            result = [{
                                'ticker': q_upper,
                                'company_name': ticker_info.get('company_name', ''),
                                'sector': ticker_info.get('sector', ''),
                                'industry': ticker_info.get('industry', ''),
                                'relevance_score': score,
                                'cached': self._is_cached(q_upper, 'prices'),
                                'risk_level': self._calculate_risk_level(ticker_info),
                                'market_cap': ticker_info.get('market_cap', 'Unknown'),
                                'last_price': ticker_info.get('current_price', 0),
                                'data_quality': ticker_info.get('data_quality', 'Unknown')
                            }]
                            logger.debug("Single-ticker fast path: %s", q_upper)
                            return result[:limit]

        results = []
        all_tickers = self.all_tickers
        cached_tickers = [t for t in all_tickers if self._is_cached(t, 'prices') and self._is_cached(t, 'sector')]
        
        logger.debug("Searching '%s' through %s cached tickers (out of %s total)", query, len(cached_tickers), len(all_tickers))
        
        # SMART PRE-FILTERING: Only check tickers that might match AND are cached
        candidate_tickers = []
        
        # Phase 1: Quick ticker symbol matching (CACHED ONLY)
        for ticker in cached_tickers:
            if q_upper in ticker or ticker.startswith(q_upper):
                candidate_tickers.append(ticker)
        
        # Phase 2: Company name matching (only if we need more candidates)
        if len(candidate_tickers) < 20:
            for ticker in cached_tickers:
                if ticker in candidate_tickers:
                    continue
                # Quick check using cached sector data
                sector_data = self._load_from_cache(ticker, 'sector')
                if sector_data:
                    company_name = sector_data.get('companyName', '').lower()
                    if q in company_name:
                        candidate_tickers.append(ticker)
        
        logger.debug("Pre-filter found %s cached candidates", len(candidate_tickers))
        
        # Process only the candidate tickers (not all 809)
        for ticker in candidate_tickers:
            try:
                # Get comprehensive ticker info
                ticker_info = self.get_ticker_info(ticker)
                if not ticker_info:
                    continue
                
                # Apply filters
                if sector_filter and ticker_info.get('sector', '').lower() != sector_filter.lower():
                    continue
                    
                if risk_filter and not self._is_suitable_for_risk_profile(ticker_info, risk_filter):
                    continue
                
                # Calculate relevance score
                score = self._calculate_enhanced_relevance_score(q, ticker_info)
                
                if score > 0:
                    results.append({
                        'ticker': ticker,
                        'company_name': ticker_info.get('company_name', ''),
                        'sector': ticker_info.get('sector', ''),
                        'industry': ticker_info.get('industry', ''),
                        'relevance_score': score,
                        'cached': self._is_cached(ticker, 'prices'),
                        'risk_level': self._calculate_risk_level(ticker_info),
                        'market_cap': ticker_info.get('market_cap', 'Unknown'),
                        'last_price': ticker_info.get('current_price', 0),
                        'data_quality': ticker_info.get('data_quality', 'Unknown')
                    })
            except Exception as e:
                logger.debug(f"Error processing {ticker}: {e}")
                continue
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        logger.debug("Search completed: %s results found", len(results))
        return results[:limit]
    
    def _calculate_enhanced_relevance_score(self, query: str, ticker_info: Dict) -> int:
        """Calculate enhanced relevance score (0-100) based on multiple factors"""
        score = 0
        
        # Exact ticker match (highest priority)
        if query.upper() == ticker_info['ticker']:
            score += 50
        
        # Ticker prefix match
        if ticker_info['ticker'].startswith(query.upper()):
            score += 40
        
        # Company name match (with word boundaries)
        company_name = ticker_info.get('company_name', '').lower()
        if query in company_name:
            score += 30
            # Bonus for exact word match
            if query in company_name.split():
                score += 10
        
        # Sector/industry match
        sector = ticker_info.get('sector', '').lower()
        industry = ticker_info.get('industry', '').lower()
        if query in sector or query in industry:
            score += 20
        
        # Fuzzy matching for typos (using Levenshtein distance)
        if self._fuzzy_match(query, ticker_info['ticker']):
            score += 15
        
        # Popularity bonus (higher volume stocks get slight boost)
        if ticker_info.get('volume', 0) > 1000000:  # 1M+ volume
            score += 5
        
        return min(score, 100)
    
    def _fuzzy_match(self, query: str, ticker: str, threshold: float = 0.8) -> bool:
        """Fuzzy matching using Levenshtein distance for typos"""
        try:
            from difflib import SequenceMatcher
            
            # Check ticker similarity
            ticker_similarity = SequenceMatcher(None, query.upper(), ticker).ratio()
            
            # Check company name similarity if available
            company_name = self.get_ticker_info(ticker).get('company_name', '')
            if company_name:
                company_similarity = SequenceMatcher(None, query.lower(), company_name.lower()).ratio()
                return max(ticker_similarity, company_similarity) >= threshold
            
            return ticker_similarity >= threshold
        except ImportError:
            # Fallback to simple similarity if difflib not available
            return self._simple_similarity(query, ticker) >= threshold
    
    def _simple_similarity(self, query: str, ticker: str) -> float:
        """Simple similarity calculation as fallback"""
        query_upper = query.upper()
        ticker_upper = ticker.upper()
        
        # Check if query is contained in ticker
        if query_upper in ticker_upper:
            return 0.9
        
        # Check character overlap
        common_chars = sum(1 for c in query_upper if c in ticker_upper)
        return common_chars / max(len(query_upper), len(ticker_upper))
    
    def _is_suitable_for_risk_profile(self, ticker_info: Dict, risk_profile: str) -> bool:
        """Check if ticker is suitable for given risk profile"""
        try:
            volatility = ticker_info.get('annualized_volatility', 0)
            
            risk_constraints = {
                'very-conservative': 0.15,  # Max 15% volatility
                'conservative': 0.20,       # Max 20% volatility
                'moderate': 0.25,           # Max 25% volatility
                'aggressive': 0.35,         # Max 35% volatility
                'very-aggressive': 0.50     # Max 50% volatility
            }
            
            max_volatility = risk_constraints.get(risk_profile, 0.25)
            return volatility <= max_volatility
        except:
            return True  # Default to True if can't determine
    
    def _calculate_risk_level(self, ticker_info: Dict) -> str:
        """Calculate risk level based on volatility"""
        try:
            volatility = ticker_info.get('annualized_volatility', 0)
            
            if volatility <= 0.15:
                return 'Low Risk'
            elif volatility <= 0.25:
                return 'Medium Risk'
            elif volatility <= 0.35:
                return 'High Risk'
            else:
                return 'Very High Risk'
        except:
            return 'Unknown'
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status from Redis"""
        if not self.redis_client:
            return {'redis': 'unavailable'}
        
        try:
            price_keys = self.redis_client.keys("ticker_data:prices:*")
            sector_keys = self.redis_client.keys("ticker_data:sector:*")
            metrics_keys = self.redis_client.keys("ticker_data:metrics:*")
            
            all_tickers = self.all_tickers
            
            return {
                'redis': 'available',
                'cached_tickers_prices': len(price_keys),
                'cached_tickers_sectors': len(sector_keys),
                'cached_tickers_metrics': len(metrics_keys),
                'total_tickers': len(all_tickers),
                'price_cache_coverage': len(price_keys) / len(all_tickers) * 100 if all_tickers else 0,
                'sector_cache_coverage': len(sector_keys) / len(all_tickers) * 100 if all_tickers else 0,
                'metrics_cache_coverage': len(metrics_keys) / len(all_tickers) * 100 if all_tickers else 0,
                'ttl_days': self.CACHE_TTL_DAYS,
                'enhanced_data_fetcher_initialized': self._enhanced_data_fetcher is not None
            }
        except Exception as e:
            return {'redis': 'error', 'error': str(e)}
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics"""
        try:
            health_metrics = {
                'system_status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'redis_status': 'connected' if self.redis_client else 'unavailable',
                'enhanced_data_fetcher_status': 'initialized' if self._enhanced_data_fetcher else 'lazy',
                'cache_coverage': self.get_cache_status()
            }
            
            # Determine overall health status
            if (health_metrics['redis_status'] == 'connected' and 
                health_metrics['cache_coverage'].get('price_cache_coverage', 0) > 50):
                health_metrics['system_status'] = 'healthy'
            elif health_metrics['redis_status'] == 'connected':
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
    
    def list_cached_tickers(self) -> List[str]:
        """List tickers that have both prices and sector cached (canonical, fast)."""
        if not self.redis_client:
            return []
        try:
            price_keys = self.redis_client.keys("ticker_data:prices:*")
            sector_keys = set(self.redis_client.keys("ticker_data:sector:*"))
            tickers: List[str] = []
            for k in price_keys:
                try:
                    t = k.decode().split(":")[-1]
                except Exception:
                    t = str(k).split(":")[-1]
                sector_key = f"ticker_data:sector:{t}".encode()
                if sector_key in sector_keys:
                    tickers.append(t)
            return tickers
        except Exception as e:
            logger.error(f"list_cached_tickers failed: {e}")
            return []

    def get_cache_inventory(self) -> Dict[str, Any]:
        """Canonical Redis cache inventory and summary for startup-time checks."""
        if not self.redis_client:
            return {'redis': 'unavailable'}
        try:
            price_keys = self.redis_client.keys("ticker_data:prices:*")
            sector_keys = self.redis_client.keys("ticker_data:sector:*")
            metrics_keys = self.redis_client.keys("ticker_data:metrics:*")

            tickers = self.list_cached_tickers()
            n_prices = len(price_keys)
            n_sector = len(sector_keys)
            n_metrics = len(metrics_keys)
            n_joined = len(tickers)
            coverage = {
                'prices': n_prices,
                'sector': n_sector,
                'metrics': n_metrics,
                'joined_tickers': n_joined,
            }

            # TTL sampling: seconds and human-readable days (expected TTL = CACHE_TTL_DAYS)
            sample = tickers[:5]
            ttl_sample = []
            expected_ttl_s = self.CACHE_TTL_DAYS * 24 * 3600
            for t in sample:
                pk = f"ticker_data:prices:{t}"
                sk = f"ticker_data:sector:{t}"
                pt = self.redis_client.ttl(pk)
                st = self.redis_client.ttl(sk)
                # Redis TTL: seconds until expiry; -1 = no expire; -2 = key missing
                pt_days = round(pt / 86400.0, 1) if pt > 0 else (None if pt == -1 else 0)
                st_days = round(st / 86400.0, 1) if st > 0 else (None if st == -1 else 0)
                ttl_sample.append({
                    'ticker': t,
                    'prices_ttl_s': pt,
                    'sector_ttl_s': st,
                    'prices_ttl_days': pt_days,
                    'sector_ttl_days': st_days,
                })

            # One-line summary for display (expected TTL = 28 days)
            missing_metrics = max(0, n_joined - n_metrics)
            def _ttl_str(d):
                return f"{d}d" if d is not None else "n/a"
            ttl_summary = (
                f"TTL sample (expected {self.CACHE_TTL_DAYS}d): "
                + ", ".join(
                    f"{s['ticker']} p={_ttl_str(s['prices_ttl_days'])} s={_ttl_str(s['sector_ttl_days'])}"
                    for s in ttl_sample[:3]
                )
            )
            return {
                'redis': 'available',
                'coverage': coverage,
                'ttl_sample': ttl_sample,
                'expected_ttl_days': self.CACHE_TTL_DAYS,
                'missing_metrics': missing_metrics,
                'ttl_summary': ttl_summary,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"get_cache_inventory failed: {e}")
            return {'redis': 'error', 'error': str(e)}
    
    def warm_cache(self) -> Dict[str, Any]:
        """Warm cache using EnhancedDataFetcher if available"""
        if not self.enhanced_data_fetcher:
            return {
                'success': False,
                'error': 'EnhancedDataFetcher not available',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            logger.info("🔥 Warming cache via EnhancedDataFetcher...")
            results = self.enhanced_data_fetcher.warm_cache()
            results['timestamp'] = datetime.now().isoformat()
            return results
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def clear_cache(self) -> None:
        """Clear all cached data from Redis"""
        if not self.redis_client:
            logger.info("Redis unavailable - no cache to clear")
            return
            
        try:
            price_keys = self.redis_client.keys("ticker_data:prices:*")
            sector_keys = self.redis_client.keys("ticker_data:sector:*")
            metrics_keys = self.redis_client.keys("ticker_data:metrics:*")
            
            if price_keys:
                self.redis_client.delete(*price_keys)
            if sector_keys:
                self.redis_client.delete(*sector_keys)
            if metrics_keys:
                self.redis_client.delete(*metrics_keys)
                
            logger.info(f"Cleared {len(price_keys)} price entries, {len(sector_keys)} sector entries, and {len(metrics_keys)} metrics entries")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    

    def preview_expired_data(self):
        """Return a preview of how many tickers are expired/incomplete without refreshing."""
        if not self.enhanced_data_fetcher:
            return { 'expired_count': 0, 'tickers': [] }
        try:
            return self.enhanced_data_fetcher.preview_expired_data()
        except Exception as e:
            logger.error(f"Error previewing expired data: {e}")
            return { 'expired_count': 0, 'tickers': [], 'error': str(e) }

    def force_refresh_expired_data(self):
        """Force refresh of expired data using EnhancedDataFetcher"""
        if not self.enhanced_data_fetcher:
            logger.warning("EnhancedDataFetcher not available - cannot refresh data")
            full_refresh_logger.error("Full refresh requested but EnhancedDataFetcher unavailable")
            return {
                'expired_before': 0,
                'expired_after': 0,
                'refreshed_count': 0,
                'success': False
            }
        
        try:
            full_refresh_logger.info("Full refresh initiated via UI")
            result = self.enhanced_data_fetcher.force_refresh_expired_data(job_logger=full_refresh_logger)
            full_refresh_logger.info("Full refresh completed: %s", result)
            return result
        except Exception as e:
            logger.error(f"Error refreshing expired data: {e}")
            full_refresh_logger.error("Full refresh failed: %s", e)
            return {
                'expired_before': 0,
                'expired_after': 0,
                'refreshed_count': 0,
                'success': False,
                'error': str(e)
            }
    
    def smart_monthly_refresh(self):
        """Smart monthly refresh using EnhancedDataFetcher"""
        if not self.enhanced_data_fetcher:
            logger.warning("EnhancedDataFetcher not available - cannot perform monthly refresh")
            smart_refresh_logger.error("Smart refresh requested but EnhancedDataFetcher unavailable")
            return
        
        try:
            smart_refresh_logger.info("Smart monthly refresh initiated for all tickers")
            result = self.enhanced_data_fetcher.smart_monthly_refresh(job_logger=smart_refresh_logger)
            smart_refresh_logger.info("Smart monthly refresh completed: %s", result)
            
            # Invalidate eligible tickers cache when ticker data is refreshed
            if result and isinstance(result, dict) and result.get('success_count', 0) > 0:
                try:
                    # Lazy import to avoid circular dependencies
                    from routers.portfolio import _invalidate_eligible_tickers_cache, _trigger_eligible_tickers_refresh
                    _invalidate_eligible_tickers_cache()
                    _trigger_eligible_tickers_refresh()
                    logger.info("🔄 Eligible tickers cache invalidated and refresh triggered after monthly ticker data update")
                except Exception as e:
                    logger.debug(f"⚠️ Could not invalidate eligible tickers cache: {e}")
            
            return result
        except Exception as e:
            logger.error(f"Error performing monthly refresh: {e}")
            smart_refresh_logger.error("Smart monthly refresh failed: %s", e)
            return None
    
    def tickers_needing_refresh(self, tickers: List[str]) -> List[str]:
        """Return which tickers are missing or stale (data older than 30 days). Call this before smart_refresh_tickers to avoid triggering refresh when all are fresh."""
        result = []
        for ticker in tickers:
            try:
                cached_data = self.get_monthly_data(ticker)
                if cached_data is None:
                    result.append(ticker)
                elif isinstance(cached_data, pd.Series) and not cached_data.empty:
                    last_date = cached_data.index[-1]
                    if hasattr(last_date, 'to_pydatetime'):
                        last_date_dt = last_date.to_pydatetime()
                    elif isinstance(last_date, pd.Timestamp):
                        last_date_dt = last_date.to_pydatetime()
                    else:
                        last_date_dt = pd.to_datetime(last_date).to_pydatetime()
                    days_old = (datetime.now() - last_date_dt).days
                    if days_old > 30:
                        result.append(ticker)
            except Exception as e:
                logger.debug("Error checking cache freshness for %s: %s", ticker, e)
                result.append(ticker)
        return result

    def smart_refresh_tickers(self, tickers: List[str]):
        """Smart refresh for specific tickers using EnhancedDataFetcher"""
        if not self.enhanced_data_fetcher:
            logger.warning("EnhancedDataFetcher not available - cannot perform ticker refresh")
            smart_refresh_logger.error("Smart refresh requested but EnhancedDataFetcher unavailable")
            return None
        
        try:
            tickers_needing_refresh = self.tickers_needing_refresh(tickers)
            if not tickers_needing_refresh:
                logger.info(f"✅ All {len(tickers)} tickers are fresh, no refresh needed")
                smart_refresh_logger.info("All tickers are fresh, no refresh needed")
                return {
                    "changed_count": 0,
                    "tickers": tickers,
                    "result": {"success_count": 0, "error_count": 0, "total_processed": 0}
                }
            
            logger.info(f"🔄 {len(tickers_needing_refresh)}/{len(tickers)} tickers need refresh: {tickers_needing_refresh}")
            smart_refresh_logger.info("Refreshing %s tickers that need update", len(tickers_needing_refresh))
            
            # Use the enhanced data fetcher to refresh specific tickers
            result = self.enhanced_data_fetcher.refresh_specific_tickers(tickers_needing_refresh, job_logger=smart_refresh_logger)
            smart_refresh_logger.info("Smart refresh finished with summary: %s", result)
            
            # Only invalidate eligible tickers cache when data was actually refreshed
            if result and result.get('success_count', 0) > 0:
                try:
                    # Lazy import to avoid circular dependencies
                    from routers.portfolio import _invalidate_eligible_tickers_cache, _trigger_eligible_tickers_refresh
                    _invalidate_eligible_tickers_cache()
                    _trigger_eligible_tickers_refresh()
                    logger.info("🔄 Eligible tickers cache invalidated and refresh triggered after ticker data update")
                except Exception as e:
                    logger.debug(f"⚠️ Could not invalidate eligible tickers cache: {e}")
            else:
                logger.debug("ℹ️ No data was refreshed, eligible tickers cache remains valid")
            
            return {
                "changed_count": len(tickers_needing_refresh),
                "tickers": tickers,
                "result": result
            }
        except Exception as e:
            logger.error(f"Error refreshing specific tickers: {e}")
            smart_refresh_logger.error("Smart refresh failed: %s", e)
            return None
    
    def check_ticker_status(self) -> Optional[Dict[str, Any]]:
        """
        Check ticker data status in Redis without fetching anything.
        Returns statistics about ticker data health, including comparison with master list.
        """
        if not self.redis_client:
            return None
        
        try:
            import redis
            from datetime import datetime
            
            # Get master ticker list for comparison
            master_tickers = set()
            try:
                master_list = self.all_tickers
                if master_list:
                    master_tickers = set(master_list)
            except Exception as e:
                logger.debug(f"Could not load master ticker list: {e}")
            
            # Get all ticker keys - Use correct key pattern matching actual storage format
            price_keys = self.redis_client.keys("ticker_data:prices:*")
            sector_keys = self.redis_client.keys("ticker_data:sector:*")
            
            # Get unique tickers with data in Redis
            tickers_with_data = set()
            for key in price_keys:
                if isinstance(key, bytes):
                    key = key.decode()
                # Extract ticker from "ticker_data:prices:{ticker}"
                ticker = key.replace("ticker_data:prices:", "")
                tickers_with_data.add(ticker)
            
            for key in sector_keys:
                if isinstance(key, bytes):
                    key = key.decode()
                # Extract ticker from "ticker_data:sector:{ticker}"
                ticker = key.replace("ticker_data:sector:", "")
                tickers_with_data.add(ticker)
            
            tickers_with_data = sorted(list(tickers_with_data))
            total_tickers_in_redis = len(tickers_with_data)
            
            # Find missing tickers (in master list but not in Redis)
            missing_from_master = []
            if master_tickers:
                tickers_with_data_set = set(tickers_with_data)
                missing_from_master = sorted(list(master_tickers - tickers_with_data_set))
            
            # Analyze TTL status for existing tickers
            expired = []
            expiring_soon = []  # Within 24 hours
            missing_prices = []
            missing_sector = []
            missing_both = []
            
            for ticker in tickers_with_data:
                # Use _get_cache_key() method to ensure correct key format
                price_key = self._get_cache_key(ticker, 'prices')
                sector_key = self._get_cache_key(ticker, 'sector')
                
                price_ttl = self.redis_client.ttl(price_key)
                sector_ttl = self.redis_client.ttl(sector_key)
                
                # Check if keys exist
                has_prices = self.redis_client.exists(price_key)
                has_sector = self.redis_client.exists(sector_key)
                
                if not has_prices and not has_sector:
                    missing_both.append(ticker)
                elif not has_prices:
                    missing_prices.append(ticker)
                elif not has_sector:
                    missing_sector.append(ticker)
                
                # Use the minimum TTL (most critical)
                min_ttl = min(price_ttl, sector_ttl) if price_ttl > 0 and sector_ttl > 0 else (price_ttl if price_ttl > 0 else sector_ttl)
                
                if min_ttl == -2:  # Key doesn't exist
                    expired.append(ticker)
                elif min_ttl == 0:
                    expired.append(ticker)
                elif min_ttl > 0 and min_ttl < 86400:  # Less than 24 hours
                    expiring_soon.append(ticker)
            
            # Total needing fetch = missing from master + expired + missing data
            needs_fetch = len(missing_from_master) + len(expired) + len(missing_both) + len(missing_prices) + len(missing_sector)
            
            return {
                'total_tickers_in_redis': total_tickers_in_redis,
                'total_tickers_in_master': len(master_tickers) if master_tickers else 0,
                'missing_from_master_count': len(missing_from_master),
                'expired_count': len(expired),
                'expiring_soon_count': len(expiring_soon),
                'missing_data_count': len(missing_both) + len(missing_prices) + len(missing_sector),
                'missing_both_count': len(missing_both),
                'missing_prices_count': len(missing_prices),
                'missing_sector_count': len(missing_sector),
                'needs_fetch_count': needs_fetch,
                'missing_from_master_sample': missing_from_master[:20],  # Sample
                'expired_tickers': expired[:20],  # Sample
                'expiring_soon_tickers': expiring_soon[:20],  # Sample
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking ticker status: {e}")
            import traceback
            traceback.print_exc()
            return None

# Global instance for lazy initialization
redis_first_data_service = RedisFirstDataService()
