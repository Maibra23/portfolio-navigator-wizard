#!/usr/bin/env python3
"""
Redis-First Data Service
Provides Redis-first data access with lazy initialization of EnhancedDataFetcher
"""

import logging
import redis
import json
import gzip
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from functools import lru_cache
from .timestamp_utils import normalize_timestamp

logger = logging.getLogger(__name__)

class RedisFirstDataService:
    """
    Redis-first data service that prioritizes cached data and only initializes
    EnhancedDataFetcher when external data is actually needed
    """
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        self.redis_client = self._init_redis(redis_host, redis_port)
        self._enhanced_data_fetcher = None  # Lazy initialization
        self._ticker_list = None  # Cached ticker list
        
        # Cache configuration
        self.CACHE_TTL_DAYS = 28
        self.CACHE_TTL_HOURS = self.CACHE_TTL_DAYS * 24
        
        logger.info("✅ Redis-First Data Service initialized")
    
    def _init_redis(self, host: str, port: int) -> Optional[redis.Redis]:
        """Initialize Redis connection"""
        try:
            r = redis.Redis(host=host, port=port, decode_responses=False)
            r.ping()
            logger.info("✅ Redis connection established")
            return r
        except redis.ConnectionError as e:
            logger.warning(f"❌ Redis connection failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"❌ Redis unavailable: {e}")
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
                
                # Fallback to EnhancedDataFetcher
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
        
        results = []
        
        # Apply filters if provided
        sector_filter = filters.get('sector', None) if filters else None
        risk_filter = filters.get('risk_profile', None) if filters else None
        
        # Search through ALL cached tickers (complete data in Redis)
        all_tickers = self.all_tickers
        cached_tickers = [t for t in all_tickers if self._is_cached(t, 'prices') and self._is_cached(t, 'sector')]
        
        logger.info(f"🔍 Searching '{query}' through {len(cached_tickers)} cached tickers (out of {len(all_tickers)} total)")
        
        # SMART PRE-FILTERING: Only check tickers that might match AND are cached
        candidate_tickers = []
        q_upper = q.upper()
        
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
        
        logger.info(f"📋 Pre-filter found {len(candidate_tickers)} cached candidates")
        
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
        logger.info(f"✅ Search completed: {len(results)} results found")
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
            coverage = {
                'prices': len(price_keys),
                'sector': len(sector_keys),
                'metrics': len(metrics_keys),
                'joined_tickers': len(tickers)
            }

            # TTL sampling for quick freshness view (sample 5 symbols if available)
            sample = tickers[:5]
            ttl_sample = []
            for t in sample:
                pk = f"ticker_data:prices:{t}"
                sk = f"ticker_data:sector:{t}"
                pt = self.redis_client.ttl(pk)
                st = self.redis_client.ttl(sk)
                ttl_sample.append({'ticker': t, 'prices_ttl_s': pt, 'sector_ttl_s': st})

            return {
                'redis': 'available',
                'coverage': coverage,
                'ttl_sample': ttl_sample,
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
            return {
                'expired_before': 0,
                'expired_after': 0,
                'refreshed_count': 0,
                'success': False
            }
        
        try:
            return self.enhanced_data_fetcher.force_refresh_expired_data()
        except Exception as e:
            logger.error(f"Error refreshing expired data: {e}")
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
            return
        
        try:
            return self.enhanced_data_fetcher.smart_monthly_refresh()
        except Exception as e:
            logger.error(f"Error performing monthly refresh: {e}")
            return None
    
    def smart_refresh_tickers(self, tickers: List[str]):
        """Smart refresh for specific tickers using EnhancedDataFetcher"""
        if not self.enhanced_data_fetcher:
            logger.warning("EnhancedDataFetcher not available - cannot perform ticker refresh")
            return None
        
        try:
            logger.info(f"Smart refreshing {len(tickers)} specific tickers")
            # Use the enhanced data fetcher to refresh specific tickers
            result = self.enhanced_data_fetcher.refresh_specific_tickers(tickers)
            return {
                "changed_count": len(tickers),
                "tickers": tickers,
                "result": result
            }
        except Exception as e:
            logger.error(f"Error refreshing specific tickers: {e}")
            return None

# Global instance for lazy initialization
redis_first_data_service = RedisFirstDataService()
