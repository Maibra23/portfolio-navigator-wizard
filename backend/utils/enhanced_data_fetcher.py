import redis
import json
import yfinance as yf
from datetime import timedelta
import logging
from typing import Optional, Dict, List, Any
import pandas as pd # Added for MultiIndex handling

# Import our custom modules
from .ticker_store import ticker_store

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDataFetcher:
    """
    Simple data fetcher for monthly adjusted close prices with Redis caching
    - Focuses only on monthly adjusted close prices
    - Uses Redis for fast caching with 24-hour TTL
    - Validates tickers against S&P 500 + Nasdaq 100 master list
    """
    
    def __init__(self):
        # Connect to local Redis server
        self.r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.master_tickers = ticker_store.get_all_tickers()
        logger.info(f"Initialized with {len(self.master_tickers)} master tickers")
    
    def cache_monthly_data(self, ticker: str, ttl_hours: int = 24) -> bool:
        """
        Cache monthly data for a single ticker
        Returns: True if successful, False otherwise
        """
        key = f"monthly:{ticker}"
        
        if self.r.exists(key):
            logger.info(f"{ticker} already cached.")
            return True

        try:
            data = yf.download(ticker, period="15y", interval="1mo", auto_adjust=True)
            
            # Handle tuple column names when auto_adjust=True
            if isinstance(data.columns, pd.MultiIndex):
                # When auto_adjust=True, columns are tuples like ('Close', 'AAPL')
                monthly_prices = data[('Close', ticker)].dropna().to_dict()
            else:
                # Regular column names
                monthly_prices = data["Adj Close"].dropna().to_dict()

            # Convert Timestamp keys to strings for JSON serialization
            monthly_prices_str = {str(k): v for k, v in monthly_prices.items()}

            self.r.setex(key, timedelta(hours=ttl_hours), json.dumps(monthly_prices_str))
            logger.info(f"{ticker} cached successfully.")
            return True

        except Exception as e:
            logger.error(f"Error caching {ticker}: {e}")
            return False
    
    def warm_cache(self) -> Dict[str, Any]:
        """
        Perform one-time bulk download of monthly data for all tickers
        Returns: Summary of cache warming results
        """
        logger.info(f"Starting cache warming for {len(self.master_tickers)} tickers...")
        
        cached_count = 0
        failed_tickers = []
        
        for ticker in self.master_tickers:
            if self.cache_monthly_data(ticker):
                cached_count += 1
            else:
                failed_tickers.append(ticker)
        
        result = {
            'status': 'success',
            'total_tickers': len(self.master_tickers),
            'cached_tickers': cached_count,
            'failed_tickers': len(failed_tickers),
            'failed_list': failed_tickers
        }
        
        logger.info(f"Cache warming complete: {cached_count} cached, {len(failed_tickers)} failed")
        return result
    
    def get_monthly_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get monthly data for a ticker
        Returns: Dict with dates and prices, or None if not found
        """
        # Validate ticker
        if not ticker_store.validate_ticker(ticker):
            logger.warning(f"Invalid ticker: {ticker}")
            return None
        
        ticker = ticker.upper()
        key = f"monthly:{ticker}"
        
        # Try Redis cache first
        if self.r.exists(key):
            try:
                cached_data = json.loads(self.r.get(key))
                dates = list(cached_data.keys())
                prices = list(cached_data.values())
                
                logger.info(f"Cache hit for {ticker}: {len(prices)} monthly points")
                
                return {
                    'ticker': ticker,
                    'dates': dates,
                    'prices': prices,
                    'data_points': len(prices),
                    'source': 'cache'
                }
            except Exception as e:
                logger.error(f"Error retrieving cached data for {ticker}: {e}")
        
        # Fallback to yfinance for individual ticker
        logger.info(f"Cache miss for {ticker}, fetching from yfinance...")
        try:
            data = yf.download(ticker, period="15y", interval="1mo", auto_adjust=True)
            
            # Handle tuple column names when auto_adjust=True
            if isinstance(data.columns, pd.MultiIndex):
                # When auto_adjust=True, columns are tuples like ('Close', 'AAPL')
                monthly_prices = data[('Close', ticker)].dropna().to_dict()
            else:
                # Regular column names
                monthly_prices = data["Adj Close"].dropna().to_dict()
            
            if not monthly_prices:
                logger.warning(f"No data returned for {ticker}")
                return None
            
            # Convert Timestamp keys to strings for JSON serialization
            monthly_prices_str = {str(k): v for k, v in monthly_prices.items()}
            
            dates = list(monthly_prices_str.keys())
            prices = list(monthly_prices_str.values())
            
            # Cache the fresh data
            self.r.setex(key, timedelta(hours=24), json.dumps(monthly_prices_str))
            
            logger.info(f"Fetched and cached {ticker}: {len(prices)} monthly points")
            
            return {
                'ticker': ticker,
                'dates': dates,
                'prices': prices,
                'data_points': len(prices),
                'source': 'yfinance'
            }
            
        except Exception as e:
            logger.error(f"Error fetching monthly data for {ticker}: {e}")
            return None
    
    def search_tickers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search tickers by query string
        Returns: List of matching tickers with cache status
        """
        matches = ticker_store.search_tickers(query, limit)
        
        results = []
        for ticker in matches:
            cache_exists = self.r.exists(f"monthly:{ticker}")
            results.append({
                'ticker': ticker,
                'cached': cache_exists
            })
        
        return results
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status"""
        cached_tickers = []
        total_cached = 0
        
        # Count cached tickers
        for ticker in self.master_tickers:
            if self.r.exists(f"monthly:{ticker}"):
                cached_tickers.append(ticker)
                total_cached += 1
        
        return {
            'master_tickers_count': len(self.master_tickers),
            'cached_tickers_count': total_cached,
            'sample_cached_tickers': cached_tickers[:10]  # First 10 for display
        }
    
    def clear_cache(self) -> Dict[str, Any]:
        """Clear all cached data"""
        try:
            # Delete all monthly:* keys
            pattern = "monthly:*"
            keys = self.r.keys(pattern)
            if keys:
                self.r.delete(*keys)
                logger.info(f"Cleared {len(keys)} cached entries")
                return {'status': 'success', 'cleared_count': len(keys)}
            else:
                return {'status': 'success', 'cleared_count': 0}
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {'status': 'error', 'error': str(e)}

# Global instance
enhanced_data_fetcher = EnhancedDataFetcher() 