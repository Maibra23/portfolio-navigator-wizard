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
                # Try to get from Redis first
                ticker_key = "master_ticker_list"
                cached_tickers = self.redis_client.get(ticker_key)
                if cached_tickers:
                    try:
                        self._ticker_list = json.loads(cached_tickers.decode())
                        logger.debug(f"✅ Loaded {len(self._ticker_list)} tickers from Redis cache")
                        return self._ticker_list
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load cached tickers: {e}")
                
            # Fallback to EnhancedDataFetcher
            if self.enhanced_data_fetcher:
                self._ticker_list = self.enhanced_data_fetcher.all_tickers
                # Cache the ticker list
                if self.redis_client and self._ticker_list:
                    try:
                        self.redis_client.setex(
                            ticker_key, 
                            timedelta(hours=24),  # Cache for 24 hours
                            json.dumps(self._ticker_list).encode()
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to cache ticker list: {e}")
            else:
                self._ticker_list = []
        
        return self._ticker_list
    
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
        Enhanced fuzzy search with smart relevance scoring and filters
        Returns: List of matching tickers with comprehensive information and relevance scores
        """
        q = query.strip().lower()
        results = []
        
        # Apply filters if provided
        sector_filter = filters.get('sector', None) if filters else None
        risk_filter = filters.get('risk_profile', None) if filters else None
        
        # Get ticker list (cached)
        all_tickers = self.all_tickers
        
        for ticker in all_tickers:
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
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
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
    
    def force_refresh_expired_data(self):
        """Force refresh of expired data using EnhancedDataFetcher"""
        if not self.enhanced_data_fetcher:
            logger.warning("EnhancedDataFetcher not available - cannot refresh data")
            return
        
        try:
            self.enhanced_data_fetcher.force_refresh_expired_data()
        except Exception as e:
            logger.error(f"Error refreshing expired data: {e}")
    
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
