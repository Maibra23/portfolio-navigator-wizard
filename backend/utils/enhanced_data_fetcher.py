import pandas as pd
import yfinance as yf
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import json
import gzip
import redis
from collections import defaultdict

from .ticker_store import ticker_store

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BATCH_SIZE = 20  # Reduced for better rate limiting
MAX_WORKERS = 2  # Reduced to respect free tier limits
RATE_LIMIT_DELAY = 2  # Increased delay between batches

# Cache configuration  
CACHE_TTL_DAYS = 28  # FIXED: 4 weeks as requested
CACHE_TTL_HOURS = CACHE_TTL_DAYS * 24  # 672 hours

# Data period configuration - FIXED: 15 years minimum
END_DATE = datetime.now()  # Current date
START_DATE = END_DATE - timedelta(days=15 * 365)  # 15 years back minimum

# Yahoo Finance rate limiting
YAHOO_REQUEST_DELAY = 0.1  # 100ms between individual requests
MAX_RETRIES = 3
RETRY_DELAY = 1

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

        # Get all tickers from multiple sources
        self.all_tickers = self._get_all_tickers()
        
        # Track processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'cached': 0,
            'errors': defaultdict(int)
        }
        
        # Daily quota tracking
        self.daily_requests = 0
        self.last_reset_date = datetime.now().date()
        
        logger.info(f"Initialized with {len(self.all_tickers)} unique tickers")
        
        # Auto-warm cache if Redis is available and cache is empty
        self._auto_warm_cache()

    def _init_redis(self):
        """Initialize Redis connection with better error handling"""
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=False)
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

    def _get_all_tickers(self) -> List[str]:
        """Get all tickers from multiple sources with deduplication"""
        tickers = set()
        
        # Get S&P 500 tickers
        try:
            sp500_tickers = self._fetch_sp500_tickers()
            tickers.update(sp500_tickers)
            logger.info(f"✅ Added {len(sp500_tickers)} S&P 500 tickers")
        except Exception as e:
            logger.error(f"❌ Failed to fetch S&P 500 tickers: {e}")
            # Use fallback from ticker_store
            sp500_fallback = getattr(ticker_store, 'sp500_tickers', [])
            tickers.update(sp500_fallback)
            logger.info(f"📦 Used fallback S&P 500 tickers: {len(sp500_fallback)}")

        # Get NASDAQ 100 tickers
        try:
            nasdaq_tickers = self._fetch_nasdaq100_tickers()
            tickers.update(nasdaq_tickers)
            logger.info(f"✅ Added {len(nasdaq_tickers)} NASDAQ 100 tickers")
        except Exception as e:
            logger.error(f"❌ Failed to fetch NASDAQ 100 tickers: {e}")
            # Use fallback from ticker_store
            nasdaq_fallback = getattr(ticker_store, 'nasdaq100_tickers', [])
            tickers.update(nasdaq_fallback)
            logger.info(f"📦 Used fallback NASDAQ 100 tickers: {len(nasdaq_fallback)}")

        # Get top 15 ETFs by market cap
        try:
            etf_tickers = self._fetch_top_etfs()
            tickers.update(etf_tickers)
            logger.info(f"✅ Added {len(etf_tickers)} top ETFs")
        except Exception as e:
            logger.error(f"❌ Failed to fetch top ETFs: {e}")
            # Use comprehensive ETF fallback
            etf_fallback = [
                'SPY', 'IVV', 'VOO', 'QQQ', 'VTI', 'DIA', 'EFA', 'IWM', 'GLD', 'VWO',
                'VEA', 'VTV', 'BND', 'AGG', 'VXUS'
            ]
            tickers.update(etf_fallback)
            logger.info(f"📦 Used fallback ETFs: {len(etf_fallback)}")

        # Convert to sorted list
        all_tickers = sorted(list(tickers))
        logger.info(f"🎯 Total unique tickers: {len(all_tickers)}")
        
        return all_tickers

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
        """Save ticker data to cache with compression"""
        if not self.r:
            return False
        try:
            # Save prices
            if 'prices' in data:
                key = self._get_cache_key(ticker, 'prices')
                prices_dict = {str(date): float(price) for date, price in data['prices'].items()}
                compressed = gzip.compress(json.dumps(prices_dict).encode())
                self.r.setex(key, timedelta(hours=CACHE_TTL_HOURS), compressed)
            
            # Save sector info
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
                    data.index = pd.to_datetime(data.index)
                    return data
                else:  # sector or other metadata
                    return json.loads(raw.decode())
        except Exception as e:
            logger.error(f"❌ Failed to load {ticker} {data_type} from cache: {e}")
        return None

    def _fetch_single_ticker_with_retry(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch data for a single ticker with retry logic and rate limiting"""
        # Check daily quota first
        if not self._check_daily_quota():
            logger.warning(f"⚠️ Daily quota exceeded, skipping {ticker}")
            return None
        
        for attempt in range(MAX_RETRIES):
            try:
                # Check cache first
                cached_prices = self._load_from_cache(ticker, 'prices')
                cached_sector = self._load_from_cache(ticker, 'sector')
                
                if cached_prices is not None and cached_sector is not None:
                    self.stats['cached'] += 1
                    return {'prices': cached_prices, 'sector': cached_sector}

                # Rate limiting before Yahoo Finance API call
                time.sleep(YAHOO_REQUEST_DELAY)
                
                # Increment daily quota
                self._increment_daily_quota()
                
                # Fetch from yfinance
                ticker_obj = yf.Ticker(ticker)
                
                # Get historical data
                hist_data = ticker_obj.history(
                    start=START_DATE, 
                    end=END_DATE + timedelta(days=1),  # Include end date
                    interval='1mo', 
                    auto_adjust=True,
                    timeout=10
                )
                
                if hist_data.empty:
                    logger.warning(f"⚠️  No price data found for {ticker}")
                    self.stats['errors']['no_data'] += 1
                    return None

                # Extract adjusted close prices
                close_data = hist_data['Close']
                
                # Validate price data
                if not self._validate_price_data(close_data, ticker):
                    self.stats['errors']['invalid_data'] += 1
                    return None
                
                # Get sector information with company name
                try:
                    info = ticker_obj.info
                    sector_info = {
                        'sector': info.get('sector', 'Unknown'),
                        'industry': info.get('industry', 'Unknown'),
                        'country': info.get('country', 'Unknown'),
                        'exchange': info.get('exchange', 'Unknown'),
                        'companyName': info.get('longName', ticker)  # Real company name
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Failed to fetch company info for {ticker}: {e}")
                    # Fallback for ETFs or failed info fetch
                    sector_info = {
                        'sector': 'ETF' if ticker in self._fetch_top_etfs() else 'Unknown',
                        'industry': 'Exchange Traded Fund' if ticker in self._fetch_top_etfs() else 'Unknown',
                        'country': 'US',
                        'exchange': 'NASDAQ' if ticker in self._fetch_top_etfs() else 'Unknown',
                        'companyName': ticker  # Use ticker as fallback name
                    }
                
                # Prepare data for caching
                data_to_cache = {
                    'prices': close_data,
                    'sector': sector_info
                }
                
                # Cache the data
                self._save_to_cache(ticker, data_to_cache)
                
                return data_to_cache

            except Exception as e:
                logger.warning(f"⚠️  Attempt {attempt + 1} failed for {ticker}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"❌ All attempts failed for {ticker}")
                    self.stats['errors'][str(e)] += 1
                    return None

        return None

    def _process_batch(self, batch: List[str]) -> Dict[str, Dict[str, Any]]:
        """Process a batch of tickers - return statement was incorrectly indented"""
        results = {}
        
        logger.info(f"🔄 Processing batch of {len(batch)} tickers...")
        
        for i, ticker in enumerate(batch, 1):
            try:
                logger.debug(f"  [{i}/{len(batch)}] Processing {ticker}...")
                
                data = self._fetch_single_ticker_with_retry(ticker)
                if data is not None:
                    results[ticker] = data
                    self.stats['successful'] += 1
                    logger.debug(f"  ✅ {ticker} successful")
                else:
                    self.stats['failed'] += 1
                    logger.debug(f"  ❌ {ticker} failed")
                
                self.stats['total_processed'] += 1
                
            except Exception as e:
                logger.error(f"❌ Batch processing error for {ticker}: {e}")
                self.stats['failed'] += 1
                self.stats['total_processed'] += 1

        # Return statement was incorrectly indented inside the for loop
        return results

    def fetch_all_data(self, batch_size: int = BATCH_SIZE) -> Dict[str, Dict[str, Any]]:
        """Fetch data for all tickers using batch processing with proper rate limiting"""
        logger.info(f"🚀 Starting batch processing of {len(self.all_tickers)} tickers")
        logger.info(f"📊 Configuration: batch_size={batch_size}, workers={MAX_WORKERS}, delay={RATE_LIMIT_DELAY}s")
        
        all_results = {}
        total_batches = (len(self.all_tickers) + batch_size - 1) // batch_size
        
        # Process in batches with sequential execution to respect rate limits
        for i in range(0, len(self.all_tickers), batch_size):
            batch_num = i // batch_size + 1
            batch = self.all_tickers[i:i + batch_size]
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches}: {len(batch)} tickers")
            
            # Process batch (sequential to respect rate limits better)
            batch_results = self._process_batch(batch)
            all_results.update(batch_results)
            
            # Show progress
            success_rate = (self.stats['successful'] / max(self.stats['total_processed'], 1)) * 100
            logger.info(f"  📈 Batch {batch_num} completed: {len(batch_results)} successful")
            logger.info(f"  📊 Overall progress: {self.stats['total_processed']}/{len(self.all_tickers)} ({success_rate:.1f}% success)")
            
            # Rate limiting between batches (except for last batch)
            if i + batch_size < len(self.all_tickers):
                logger.info(f"⏳ Waiting {RATE_LIMIT_DELAY}s between batches...")
                time.sleep(RATE_LIMIT_DELAY)
        
        final_success_rate = (self.stats['successful'] / max(self.stats['total_processed'], 1)) * 100
        logger.info(f"🎉 Batch processing completed!")
        logger.info(f"📊 Final stats: {self.stats['successful']} successful, {self.stats['failed']} failed, {self.stats['cached']} cached")
        logger.info(f"📈 Success rate: {final_success_rate:.1f}%")
        
        return all_results

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

        # Only fetch from external API if not in cache
        logger.info(f"📥 {ticker} not in cache, fetching from Yahoo Finance...")
        return self._fetch_single_ticker_with_retry(ticker)

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
        except Exception as e:
            logger.error(f"❌ Error in auto-warm cache: {e}")

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

    def force_refresh_expired_data(self):
        """Force refresh of expired data with incremental month addition"""
        if not self.r:
            logger.warning("❌ Redis unavailable - cannot refresh data")
            return
        
        logger.info("🔄 Checking for expired data to refresh...")
        
        # Check which tickers have expired or missing data
        expired_tickers = []
        for ticker in self.all_tickers:
            if not self._is_cached(ticker, 'prices') or not self._is_cached(ticker, 'sector'):
                expired_tickers.append(ticker)
        
        if expired_tickers:
            logger.info(f"🔄 Found {len(expired_tickers)} tickers needing refresh")
            
            # Update end date to current month for incremental updates
            global END_DATE
            current_end = datetime.now().replace(day=1)  # First of current month
            if current_end > END_DATE:
                END_DATE = current_end
                logger.info(f"📅 Updated end date to {END_DATE.strftime('%Y-%m-%d')} for incremental update")
            
            # Process expired tickers in small batches
            for i in range(0, len(expired_tickers), BATCH_SIZE):
                batch = expired_tickers[i:i + BATCH_SIZE]
                logger.info(f"🔄 Refreshing batch {i//BATCH_SIZE + 1}: {len(batch)} expired tickers")
                self._process_batch(batch)
                
                if i + BATCH_SIZE < len(expired_tickers):
                    time.sleep(RATE_LIMIT_DELAY)
        else:
            logger.info("✅ No expired data found")

    def clear_cache(self) -> None:
        """Clear all cached data"""
        if self.r is None:
            logger.info("Redis unavailable - no cache to clear")
            return
            
        try:
            price_keys = self.r.keys("ticker_data:prices:*")
            sector_keys = self.r.keys("ticker_data:sector:*")
            
            if price_keys:
                self.r.delete(*price_keys)
            if sector_keys:
                self.r.delete(*sector_keys)
                
            logger.info(f"Cleared {len(price_keys)} price entries and {len(sector_keys)} sector entries")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

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
            time.sleep(YAHOO_REQUEST_DELAY)
        
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

# Global instance
enhanced_data_fetcher = EnhancedDataFetcher() 