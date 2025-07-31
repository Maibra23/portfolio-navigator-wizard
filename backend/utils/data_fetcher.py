import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import time
import logging
from config.settings import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self):
        self.cache = {}
        self.cache_timestamps = {}
        self.alpha_vantage_requests_today = 0
        self.last_request_date = None
    
    def _is_cache_valid(self, ticker: str) -> bool:
        """Check if cached data is still valid"""
        if ticker not in self.cache_timestamps:
            return False
        
        cache_age = datetime.now() - self.cache_timestamps[ticker]
        return cache_age.total_seconds() < (config.cache_duration_hours * 3600)
    
    def _update_cache(self, ticker: str, data: Dict):
        """Update cache with new data"""
        self.cache[ticker] = data
        self.cache_timestamps[ticker] = datetime.now()
    
    def _fetch_from_yahoo_finance(self, ticker: str) -> Optional[Dict]:
        """
        Fetch stock data from Yahoo Finance
        Returns None if failed
        """
        try:
            logger.info(f"Fetching data for {ticker} from Yahoo Finance")
            
            # Create ticker object
            stock = yf.Ticker(ticker)
            
            # Fetch historical data for 15 years
            hist = stock.history(
                start=config.start_date.strftime('%Y-%m-%d'),
                end=config.end_date.strftime('%Y-%m-%d'),
                interval='1d'
            )
            
            if hist.empty:
                logger.warning(f"No data returned from Yahoo Finance for {ticker}")
                return None
            
            # Extract required data
            prices = hist['Close'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            last_price = prices[-1] if prices else 0
            
            # Check if we have sufficient data (at least 10 years worth)
            min_required_days = 10 * 252  # 10 years minimum
            if len(prices) < min_required_days:
                logger.warning(f"Insufficient data for {ticker}: {len(prices)} days (need at least {min_required_days})")
                return None
            
            return {
                'prices': prices,
                'dates': dates,
                'last_price': last_price,
                'data_source': 'yahoo_finance',
                'data_points': len(prices),
                'start_date': dates[0],
                'end_date': dates[-1]
            }
            
        except Exception as e:
            logger.error(f"Error fetching from Yahoo Finance for {ticker}: {str(e)}")
            return None
    
    def _fetch_from_alpha_vantage(self, ticker: str) -> Optional[Dict]:
        """
        Fetch stock data from Alpha Vantage as fallback
        Returns None if failed
        """
        try:
            # Check rate limits
            current_date = datetime.now().date()
            if self.last_request_date != current_date:
                self.alpha_vantage_requests_today = 0
                self.last_request_date = current_date
            
            if self.alpha_vantage_requests_today >= config.alpha_vantage_rate_limit:
                logger.error("Alpha Vantage rate limit exceeded")
                return None
            
            logger.info(f"Fetching data for {ticker} from Alpha Vantage")
            
            # Alpha Vantage API call for daily prices (free tier)
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': ticker,
                'apikey': config.alpha_vantage_key,
                'outputsize': 'full'  # Get full history
            }
            
            response = requests.get(config.alpha_vantage_base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                logger.error(f"Alpha Vantage API error for {ticker}: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                logger.error(f"Alpha Vantage rate limit message: {data['Note']}")
                return None
            
            # Extract time series data
            time_series = data.get('Time Series (Daily)', {})
            if not time_series:
                logger.error(f"No time series data found for {ticker}")
                return None
            
            # Convert to sorted list of (date, price) tuples
            price_data = []
            for date_str, values in time_series.items():
                try:
                    price = float(values['4. close'])  # Use close price instead of adjusted close
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # Only include data within our 15-year window
                    if config.start_date <= date_obj <= config.end_date:
                        price_data.append((date_obj, price))
                except (ValueError, KeyError):
                    continue
            
            # Sort by date and extract prices
            price_data.sort(key=lambda x: x[0])
            
            if len(price_data) < 10 * 252:  # At least 10 years
                logger.warning(f"Insufficient Alpha Vantage data for {ticker}: {len(price_data)} days")
                return None
            
            prices = [price for _, price in price_data]
            dates = [date.strftime('%Y-%m-%d') for date, _ in price_data]
            last_price = prices[-1] if prices else 0
            
            # Update request counter
            self.alpha_vantage_requests_today += 1
            
            return {
                'prices': prices,
                'dates': dates,
                'last_price': last_price,
                'data_source': 'alpha_vantage',
                'data_points': len(prices),
                'start_date': dates[0],
                'end_date': dates[-1]
            }
            
        except Exception as e:
            logger.error(f"Error fetching from Alpha Vantage for {ticker}: {str(e)}")
            return None
    
    def fetch_stock_data(self, ticker: str) -> Optional[Dict]:
        """
        Fetch 15-year stock data with fallback from yfinance to Alpha Vantage
        Returns: {
            'prices': List[float],
            'dates': List[str],
            'last_price': float,
            'data_source': str,
            'data_points': int,
            'start_date': str,
            'end_date': str
        }
        """
        # Check cache first
        if ticker in self.cache and self._is_cache_valid(ticker):
            logger.info(f"Returning cached data for {ticker}")
            return self.cache[ticker]
        
        # Try Yahoo Finance first (up to 2 attempts)
        for attempt in range(config.yahoo_finance_retry_attempts):
            data = self._fetch_from_yahoo_finance(ticker)
            if data:
                self._update_cache(ticker, data)
                return data
            
            if attempt < config.yahoo_finance_retry_attempts - 1:
                logger.info(f"Yahoo Finance attempt {attempt + 1} failed for {ticker}, retrying...")
                time.sleep(1)  # Brief delay before retry
        
        # Fallback to Alpha Vantage
        logger.info(f"Yahoo Finance failed for {ticker}, trying Alpha Vantage")
        data = self._fetch_from_alpha_vantage(ticker)
        
        if data:
            self._update_cache(ticker, data)
            return data
        
        logger.error(f"All data sources failed for {ticker}")
        return None
    
    def fetch_batch_data(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Fetch data for multiple tickers efficiently
        Returns: {ticker: data_dict}
        """
        results = {}
        
        for ticker in tickers:
            try:
                data = self.fetch_stock_data(ticker)
                if data:
                    results[ticker] = data
                else:
                    logger.warning(f"Failed to fetch data for {ticker}")
            except Exception as e:
                logger.error(f"Error processing {ticker}: {str(e)}")
                continue
        
        return results
    
    def get_cache_status(self) -> Dict:
        """Get cache status for debugging"""
        return {
            'cached_tickers': list(self.cache.keys()),
            'cache_size': len(self.cache),
            'alpha_vantage_requests_today': self.alpha_vantage_requests_today,
            'last_request_date': self.last_request_date.isoformat() if self.last_request_date else None
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Cache cleared") 