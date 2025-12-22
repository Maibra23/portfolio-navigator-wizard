#!/usr/bin/env python3
"""
Portfolio Stock Selection Algorithm
Selects stocks based on sector diversification and volatility matching for risk profiles
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import random
from .redis_first_data_service import redis_first_data_service as _rds
from .volatility_weighted_sector import get_volatility_weighted_sector_weights

logger = logging.getLogger(__name__)

class PortfolioStockSelector:
    """
    Algorithmic stock selector that chooses stocks based on:
    1. Sector diversification (avoid over-concentration)
    2. Volatility matching (align with risk profile)
    3. Portfolio size optimization (3-4 stocks minimum)
    4. Correlation analysis (minimize portfolio risk)
    """
    
    def __init__(self, data_service=None):
        """
        Initialize Portfolio Stock Selector
        Args:
            data_service: RedisFirstDataService or EnhancedDataFetcher instance
        """
        self.data_service = data_service
        if data_service:
            # Handle both RedisFirstDataService and EnhancedDataFetcher
            if hasattr(data_service, 'redis_client'):
                self.redis_client = data_service.redis_client
            else:
                self.redis_client = data_service.r
        else:
            self.redis_client = None
        
        # Enhanced cache for stock data to avoid repeated processing
        self._stock_cache = {}
        self._cache_timestamp = None
        self.CACHE_TTL_HOURS = 24  # Cache for 24 hours
        import threading
        self._cache_lock = threading.Lock()  # Thread-safe cache access
        
        # Enhanced sector categories for better diversification - ALL 11 SECTORS
        self.SECTOR_CATEGORIES = {
            'technology': ['Technology'],
            'communication': ['Communication Services'],
            'healthcare': ['Healthcare', 'Biotechnology', 'Pharmaceuticals'],
            'financial': ['Financial Services', 'Banks', 'Insurance'],
            'consumer_staples': ['Consumer Staples', 'Consumer Defensive'],
            'consumer_discretionary': ['Consumer Discretionary', 'Retail', 'Consumer Cyclical'],
            'industrial': ['Industrials', 'Manufacturing', 'Transportation'],
            'energy': ['Energy', 'Oil & Gas'],
            'utilities': ['Utilities'],
            'materials': ['Materials', 'Mining', 'Chemicals', 'Basic Materials'],
            'real_estate': ['Real Estate']
        }
        
        # Risk profile volatility targets (annualized) - Using centralized config
        # Import from risk_profile_config.py for consistency across the project
        from .risk_profile_config import RISK_PROFILE_VOLATILITY
        self.RISK_PROFILE_VOLATILITY = RISK_PROFILE_VOLATILITY
        
        # Variable stock count ranges by risk profile (replaces fixed sizes)
        self.STOCK_COUNT_RANGES = {
            'very-conservative': (3, 5),    # 3-5 stocks for diversification
            'conservative': (3, 5),         # 3-5 stocks for stability
            'moderate': (3, 5),             # 3-5 stocks for balanced approach
            'aggressive': (3, 4),           # 3-4 stocks for focused growth
            'very-aggressive': (3, 4)       # 3-4 stocks for concentrated growth
        }
        
        # Preferred sectors by risk profile (optional guidance, not strict weights)
        self.PREFERRED_SECTORS = {
            'very-conservative': ['healthcare', 'utilities', 'consumer_staples'],
            'conservative': ['healthcare', 'technology', 'financial'],
            'moderate': ['technology', 'communication', 'healthcare'],
            'aggressive': ['technology', 'communication', 'consumer_discretionary'],
            'very-aggressive': ['technology', 'communication', 'healthcare']
        }
    
    def get_variable_stock_count(self, risk_profile: str, portfolio_index: int) -> int:
        """Get variable stock count within the range for this risk profile"""
        import random
        
        # Use portfolio index as seed for consistent results
        random.seed(portfolio_index + hash(risk_profile))
        
        count_range = self.STOCK_COUNT_RANGES.get(risk_profile, (3, 5))
        count = random.randint(count_range[0], count_range[1])
        
        return count
    
    def select_stocks_for_risk_profile(self, risk_profile: str) -> List[Dict]:
        """
        Select optimal stocks for a given risk profile
        Returns: List of stock allocations with symbols, names, and percentages
        """
        logger.info(f"🔍 Selecting stocks for {risk_profile} risk profile...")
        
        try:
            # Get available stocks with their data
            available_stocks = self._get_available_stocks_with_metrics()
            
            if not available_stocks:
                logger.error("❌ No stocks available for selection")
                return self._get_fallback_portfolio(risk_profile)
            
            # Filter stocks by volatility range for this risk profile
            volatility_range = self.RISK_PROFILE_VOLATILITY[risk_profile]
            filtered_stocks = self._filter_stocks_by_volatility(
                available_stocks, volatility_range
            )
            
            if len(filtered_stocks) < 3:
                logger.warning(f"⚠️ Only {len(filtered_stocks)} stocks meet volatility criteria, using fallback")
                return self._get_fallback_portfolio(risk_profile)
            
            # Select stocks ensuring sector diversification
            selected_stocks = self._select_diversified_stocks(
                filtered_stocks, risk_profile
            )
            
            # Create portfolio allocations
            portfolio_size = self.PORTFOLIO_SIZE[risk_profile]
            allocations = self._create_portfolio_allocations(selected_stocks, portfolio_size)
            
            logger.info(f"✅ Selected {len(allocations)} stocks for {risk_profile} profile")
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error selecting stocks: {e}")
            return self._get_fallback_portfolio(risk_profile)
    
    def select_stocks_for_risk_profile_deterministic_with_data(self, risk_profile: str, variation_seed: int, variation_id: int, available_stocks: List[Dict], fast_mode: bool = False) -> List[Dict]:
        """
        Select optimal stocks for a given risk profile using pre-fetched stock data
        This eliminates redundant data fetching in parallel generation
        """
        logger.info(f"🔍 Selecting stocks deterministically for {risk_profile} risk profile (seed: {variation_seed}) with pre-fetched data...")
        
        try:
            import time
            t0 = time.time()
            if not available_stocks:
                logger.error("❌ No pre-fetched stocks available for selection")
                fallback_portfolio = self._get_fallback_portfolio(risk_profile, variation_id)
                return fallback_portfolio.get('allocations', [])
            
            # Filter stocks by volatility range for this risk profile
            volatility_range = self.RISK_PROFILE_VOLATILITY[risk_profile]
            filtered_stocks = self._filter_stocks_by_volatility(available_stocks, volatility_range)

            # Adaptive widening if pool too small
            min_needed = 60
            if len(filtered_stocks) < min_needed:
                lo, hi = volatility_range
                width = hi - lo
                widen = max(0.01, 0.10 * width)
                lo = max(0.0, lo - widen)
                hi = min(1.5, hi + widen)
                logger.info(f"🪄 Adaptive widen volatility to {lo:.2f}-{hi:.2f} due to small pool ({len(filtered_stocks)})")
                filtered_stocks = self._filter_stocks_by_volatility(available_stocks, (lo, hi))
            t_filter = time.time() - t0
            
            if len(filtered_stocks) < 3:
                logger.warning(f"⚠️ Only {len(filtered_stocks)} stocks meet volatility criteria, using fallback")
                fallback_portfolio = self._get_fallback_portfolio(risk_profile, variation_id)
                return fallback_portfolio.get('allocations', [])
            
            # Select stocks ensuring sector diversification with deterministic algorithm
            t_sel0 = time.time()
            selected_stocks = self._select_diversified_stocks_deterministic(filtered_stocks, risk_profile, variation_seed, fast_mode)
            t_select = time.time() - t_sel0
            
            # Create portfolio allocations
            portfolio_size = self.PORTFOLIO_SIZE[risk_profile]
            allocations = self._create_portfolio_allocations(selected_stocks, portfolio_size, variation_id)
            logger.debug(f"⏱️ filter_t={t_filter:.3f}s select_t={t_select:.3f}s rp={risk_profile} seed={variation_seed}")
            
            logger.info(f"✅ Selected {len(allocations)} stocks deterministically for {risk_profile} profile")
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error selecting stocks deterministically: {e}")
            fallback_portfolio = self._get_fallback_portfolio(risk_profile, variation_id)
            return fallback_portfolio.get('allocations', [])
    
    def select_stocks_for_risk_profile_deterministic(self, risk_profile: str, variation_seed: int, variation_id: int = 0, fast_mode: bool = False) -> List[Dict]:
        """
        Select optimal stocks for a given risk profile using deterministic algorithm
        This method eliminates randomization for consistent portfolio generation
        """
        logger.info(f"🔍 Selecting stocks deterministically for {risk_profile} risk profile (seed: {variation_seed})...")
        
        try:
            import time
            t0 = time.time()
            # Get available stocks with their data
            available_stocks = self._get_available_stocks_with_metrics()
            
            if not available_stocks:
                logger.error("❌ No stocks available for selection")
                fallback_portfolio = self._get_fallback_portfolio(risk_profile, variation_id)
                return fallback_portfolio.get('allocations', [])
            
            # Filter stocks by volatility range for this risk profile
            volatility_range = self.RISK_PROFILE_VOLATILITY[risk_profile]
            filtered_stocks = self._filter_stocks_by_volatility(available_stocks, volatility_range)

            # Adaptive widening if pool too small
            min_needed = 60
            if len(filtered_stocks) < min_needed:
                lo, hi = volatility_range
                width = hi - lo
                widen = max(0.01, 0.10 * width)
                lo = max(0.0, lo - widen)
                hi = min(1.5, hi + widen)
                logger.info(f"🪄 Adaptive widen volatility to {lo:.2f}-{hi:.2f} due to small pool ({len(filtered_stocks)})")
                filtered_stocks = self._filter_stocks_by_volatility(available_stocks, (lo, hi))
            t_filter = time.time() - t0
            
            if len(filtered_stocks) < 3:
                logger.warning(f"⚠️ Only {len(filtered_stocks)} stocks meet volatility criteria, using fallback")
                fallback_portfolio = self._get_fallback_portfolio(risk_profile, variation_id)
                return fallback_portfolio.get('allocations', [])
            
            # Select stocks ensuring sector diversification with deterministic algorithm
            t_sel0 = time.time()
            selected_stocks = self._select_diversified_stocks_deterministic(filtered_stocks, risk_profile, variation_seed, fast_mode)
            t_select = time.time() - t_sel0
            
            # Create portfolio allocations
            portfolio_size = self.PORTFOLIO_SIZE[risk_profile]
            allocations = self._create_portfolio_allocations(selected_stocks, portfolio_size, variation_id)
            logger.debug(f"⏱️ filter_t={t_filter:.3f}s select_t={t_select:.3f}s rp={risk_profile} seed={variation_seed}")
            
            logger.info(f"✅ Selected {len(allocations)} stocks deterministically for {risk_profile} profile")
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error selecting stocks deterministically: {e}")
            fallback_portfolio = self._get_fallback_portfolio(risk_profile, variation_id)
            return fallback_portfolio.get('allocations', [])
    
    def _get_available_stocks_with_metrics(self) -> List[Dict]:
        """Get all available stocks with their metrics from cache - Optimized batch processing."""
        from datetime import datetime
        import concurrent.futures
        import threading
        
        current_time = datetime.now()

        # Cache hit path - improved thread-safe caching
        with self._cache_lock:
            if (self._stock_cache and self._cache_timestamp and 
                (current_time - self._cache_timestamp).total_seconds() < self.CACHE_TTL_HOURS * 3600):
                logger.info(f"⚡ Using cached stock data (cache hit) - {len(self._stock_cache)} stocks")
                return self._stock_cache.copy()  # Return copy to prevent modification

        if not self.data_service or not getattr(self.data_service, 'redis_client', None):
            logger.warning("⚠️ Redis service unavailable; returning empty stock list")
            return []

        try:
            # Canonical, fast enumeration from Redis
            tickers = []
            if hasattr(self.data_service, 'list_cached_tickers'):
                tickers = self.data_service.list_cached_tickers()
            else:
                # Fallback: derive from keys
                price_keys = self.data_service.redis_client.keys("ticker_data:prices:*")
                sector_keys = set(self.data_service.redis_client.keys("ticker_data:sector:*"))
                for k in price_keys:
                    try:
                        t = k.decode().split(":")[-1]
                    except Exception:
                        t = str(k).split(":")[-1]
                    if f"ticker_data:sector:{t}".encode() in sector_keys:
                        tickers.append(t)

            logger.info(f"📊 Redis enumeration found {len(tickers)} tickers with prices+sector")

            # OPTIMIZED: Process all tickers with batch operations and parallel processing
            available_stocks = self._batch_process_tickers_optimized(tickers)

            # Cache the results with thread-safe access
            with self._cache_lock:
                self._stock_cache = available_stocks
                self._cache_timestamp = current_time
            logger.info(f"✅ Prepared {len(available_stocks)} stocks from Redis (optimized batch processing)")
            return available_stocks
        except Exception as e:
            logger.error(f"❌ Error building stock list from Redis: {e}")
            return self._stock_cache or []
    
    def _batch_process_tickers_optimized(self, tickers: List[str]) -> List[Dict]:
        """Optimized batch processing of tickers with parallel Redis operations."""
        import concurrent.futures
        import threading
        from datetime import datetime
        
        start_time = datetime.now()
        logger.info(f"🚀 Starting optimized batch processing of {len(tickers)} tickers")
        
        available_stocks = []
        batch_size = 50  # Process 50 tickers per batch
        max_workers = 8  # Parallel workers for Redis operations
        
        # Split tickers into batches
        ticker_batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
        logger.info(f"📦 Split into {len(ticker_batches)} batches of {batch_size} tickers each")
        
        # Process batches in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._process_ticker_batch_optimized, batch, batch_idx): batch_idx
                for batch_idx, batch in enumerate(ticker_batches)
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_stocks = future.result()
                    available_stocks.extend(batch_stocks)
                    
                    # Progress logging
                    progress = len(available_stocks) / len(tickers) * 100
                    logger.info(f"📊 Batch {batch_idx + 1}/{len(ticker_batches)} complete - {len(batch_stocks)} stocks, Total: {len(available_stocks)} ({progress:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"❌ Batch {batch_idx + 1} failed: {e}")
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"✅ Batch processing complete: {len(available_stocks)} stocks in {processing_time:.2f}s ({len(available_stocks)/processing_time:.1f} stocks/sec)")
        
        return available_stocks
    
    def _process_ticker_batch_optimized(self, ticker_batch: List[str], batch_idx: int) -> List[Dict]:
        """Process a batch of tickers with optimized Redis batch operations."""
        batch_stocks = []
        
        try:
            # OPTIMIZATION 1: Batch Redis operations using mget
            price_keys = [f"ticker_data:prices:{ticker}" for ticker in ticker_batch]
            sector_keys = [f"ticker_data:sector:{ticker}" for ticker in ticker_batch]
            metrics_keys = [f"ticker_data:metrics:{ticker}" for ticker in ticker_batch]
            
            # Batch get all data types at once
            redis_client = self.data_service.redis_client
            
            # Use pipeline for better performance
            with redis_client.pipeline() as pipe:
                for key in price_keys + sector_keys + metrics_keys:
                    pipe.get(key)
                results = pipe.execute()
            
            # Split results by data type
            price_results = results[:len(price_keys)]
            sector_results = results[len(price_keys):len(price_keys) + len(sector_keys)]
            metrics_results = results[len(price_keys) + len(sector_keys):]
            
            # Process each ticker in the batch
            for i, ticker in enumerate(ticker_batch):
                try:
                    # Get data for this ticker
                    price_data = price_results[i]
                    sector_data = sector_results[i]
                    metrics_data = metrics_results[i]
                    
                    # Skip if missing critical data
                    if not price_data or not sector_data:
                        continue
                    
                    # Parse data
                    stock_data = self._parse_ticker_data_optimized(ticker, price_data, sector_data, metrics_data)
                    if stock_data:
                        batch_stocks.append(stock_data)
                        
                except Exception as e:
                    logger.debug(f"Error processing {ticker} in batch {batch_idx}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Batch {batch_idx} processing failed: {e}")
            
        return batch_stocks
    
    def _parse_ticker_data_optimized(self, ticker: str, price_data: bytes, sector_data: bytes, metrics_data: bytes) -> Optional[Dict]:
        """Parse ticker data from Redis batch results - optimized version."""
        import json
        import gzip
        
        try:
            # Parse price data
            if price_data:
                price_dict = json.loads(gzip.decompress(price_data).decode())
                price_series = pd.Series(price_dict)
                
                # Calculate basic metrics
                if len(price_series) >= 12:  # Need at least 1 year of data
                    current_price = price_series.iloc[-1] if not price_series.empty else 0
                    returns = price_series.pct_change().dropna()
                    volatility = returns.std() * np.sqrt(12) if len(returns) > 0 else 0
                    annual_return = returns.mean() * 12 if len(returns) > 0 else 0
                else:
                    return None
            else:
                return None
            
            # Parse sector data with enhanced validation
            sector_info = {}
            if sector_data:
                sector_info = json.loads(sector_data.decode())
            
            # FILTER: Exclude ETFs and Unknown sectors
            sector = sector_info.get('sector', 'Unknown')
            if not sector or sector == 'Unknown':
                # Try inference, but still exclude if remains Unknown
                inferred_sector = self._infer_sector_from_ticker(ticker)
                sector = inferred_sector
                sector_info['sector'] = inferred_sector
                logger.debug(f"✅ {ticker}: Applied sector inference: {inferred_sector}")
            
            # Exclude ETFs and Unknown sectors
            company_name = sector_info.get('companyName', ticker)
            etf_indicators = ['ETF', 'Fund', 'Trust', 'Index', 'Diversified ETF']
            is_etf = any(indicator in str(company_name) for indicator in etf_indicators) or 'ETF' in str(sector)
            
            if is_etf or sector == 'Unknown':
                logger.debug(f"❌ {ticker}: Excluded (ETF={is_etf}, sector={sector})")
                return None
            
            # Parse metrics data
            metrics_info = {}
            if metrics_data:
                metrics_info = json.loads(metrics_data.decode())
            stock_data = {
                'symbol': ticker,  # FIXED: Use 'symbol' instead of 'ticker' for consistency
                'ticker': ticker,  # Keep both for compatibility
                'name': company_name,  # FIXED: Add 'name' key for portfolio allocation
                'company_name': company_name,
                'sector': sector_info.get('sector', 'Unknown'),
                'industry': sector_info.get('industry', 'Unknown'),
                'volatility': metrics_info.get('risk', volatility),  # FIXED: Use 'risk' key from Redis
                'annualized_return': metrics_info.get('annualized_return', annual_return),  # FIXED: Use correct key
                'annual_return': metrics_info.get('annualized_return', annual_return),  # Keep both for compatibility
                'return': metrics_info.get('annualized_return', annual_return),
                'price': current_price,
                'data_quality': metrics_info.get('data_quality', 'cached'),
                'prices': price_series.tolist()[-30:],  # Last 30 data points for correlation
                'returns': returns.tolist() if len(returns) > 0 else []
            }
            
            return stock_data
            
        except Exception as e:
            logger.debug(f"Error parsing data for {ticker}: {e}")
            return None
    
    def _quick_pre_filter_tickers(self, all_tickers: List[str]) -> List[str]:
        """Quick pre-filtering to reduce processing load"""
        pre_filtered = []
        
        # Priority 1: S&P 500 stocks (most liquid)
        sp500_tickers = []  # Classification removed; rely on Redis presence only
        pre_filtered.extend(sp500_tickers[:0])
        
        # Priority 2: NASDAQ 100 stocks (growth focus)
        nasdaq_tickers = []  # Classification removed
        nasdaq_tickers = [t for t in nasdaq_tickers if t not in pre_filtered]
        pre_filtered.extend(nasdaq_tickers[:0])
        
        # Priority 3: Additional diversified stocks
        remaining_tickers = [t for t in all_tickers if t not in pre_filtered]
        pre_filtered.extend(remaining_tickers[:100])  # Top 100 remaining
        
        return pre_filtered[:400]  # Cap at 400 for performance
    
    def _batch_process_stocks(self, tickers: List[str]) -> List[Dict]:
        """Process stocks in batches with progress tracking"""
        available_stocks = []
        batch_size = 50
        total_batches = (len(tickers) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(tickers))
            batch_tickers = tickers[start_idx:end_idx]
            
            logger.info(f"📦 Processing batch {batch_num + 1}/{total_batches} ({start_idx + 1}-{end_idx})")
            
            batch_stocks = self._process_stock_batch(batch_tickers)
            available_stocks.extend(batch_stocks)
            
            # Progress update
            progress = ((batch_num + 1) / total_batches) * 100
            logger.info(f"📊 Progress: {progress:.1f}% - Found {len(available_stocks)} stocks so far")
        
        return available_stocks
    
    def _infer_sector_from_ticker(self, ticker: str) -> str:
        """Infer sector from ticker symbol when Redis data is missing"""
        ticker = ticker.upper()
        
        # Known sector mappings for common tickers (EXPANDED)
        sector_mappings = {
            # Technology
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
            'AMZN': 'Technology', 'META': 'Technology', 'NVDA': 'Technology', 'TSLA': 'Technology',
            'NFLX': 'Technology', 'ADBE': 'Technology', 'CRM': 'Technology', 'ORCL': 'Technology',
            'INTC': 'Technology', 'AMD': 'Technology', 'QCOM': 'Technology', 'AVGO': 'Technology',
            'ADP': 'Technology', 'TRMB': 'Technology',
            
            # Financial Services
            'JPM': 'Financial Services', 'BAC': 'Financial Services', 'WFC': 'Financial Services',
            'GS': 'Financial Services', 'MS': 'Financial Services', 'C': 'Financial Services',
            'AXP': 'Financial Services', 'V': 'Financial Services', 'MA': 'Financial Services',
            
            # Healthcare
            'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare', 'ABBV': 'Healthcare',
            'MRK': 'Healthcare', 'TMO': 'Healthcare', 'ABT': 'Healthcare', 'DHR': 'Healthcare',
            
            # Consumer Discretionary
            'HD': 'Consumer Discretionary', 'MCD': 'Consumer Discretionary', 'NKE': 'Consumer Discretionary',
            'SBUX': 'Consumer Discretionary', 'LOW': 'Consumer Discretionary', 'TJX': 'Consumer Discretionary',
            'RCL': 'Consumer Discretionary', 'MELI': 'Consumer Discretionary', 'APTV': 'Consumer Discretionary',
            'HWDN.L': 'Consumer Discretionary', 'CZR': 'Consumer Discretionary',
            
            # Consumer Staples
            'PG': 'Consumer Staples', 'KO': 'Consumer Staples', 'PEP': 'Consumer Staples',
            'WMT': 'Consumer Staples', 'CL': 'Consumer Staples', 'KMB': 'Consumer Staples',
            
            # Energy
            'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'EOG': 'Energy', 'CTRA': 'Energy',
            
            # Industrials
            'BA': 'Industrials', 'CAT': 'Industrials', 'GE': 'Industrials', 'MMM': 'Industrials',
            'HON': 'Industrials', 'UPS': 'Industrials', 'RTX': 'Industrials', 'ITW': 'Industrials',
            'IR': 'Industrials', 'PCAR': 'Industrials',
            
            # Utilities
            'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities', 'AEP': 'Utilities', 'FE': 'Utilities',
            
            # Communication Services
            'VZ': 'Communication Services', 'T': 'Communication Services', 'CMCSA': 'Communication Services',
            'DIS': 'Communication Services', 'GOOG': 'Communication Services', 'GOOGL': 'Communication Services',
            'CHTR': 'Communication Services', 'ROL': 'Communication Services',
            
            # Materials
            'LIN': 'Materials', 'APD': 'Materials', 'SHW': 'Materials', 'ECL': 'Materials', 'ALB': 'Materials',
            
            # Real Estate
            'AMT': 'Real Estate', 'PLD': 'Real Estate', 'CCI': 'Real Estate', 'EQIX': 'Real Estate',
            
            # ETFs - Map to diversified categories
            'VXUS': 'Diversified ETF', 'ITOT': 'Diversified ETF', 'SPY': 'Diversified ETF', 'QQQ': 'Technology ETF',
            'VTI': 'Diversified ETF', 'VEA': 'Diversified ETF', 'VWO': 'Diversified ETF', 'AGG': 'Fixed Income ETF',
            'BND': 'Fixed Income ETF', 'TLT': 'Fixed Income ETF', 'IEF': 'Fixed Income ETF',
            
            # International tickers - Map to appropriate sectors
            'RBREW.CO': 'Consumer Staples', 'ASML': 'Technology', 'TSM': 'Technology', 'SAP': 'Technology',
            'UL': 'Consumer Staples', 'NVO': 'Healthcare', 'TM': 'Consumer Discretionary',
            
            # Additional common tickers
            'BABA': 'Technology', 'PDD': 'Technology', 'JD': 'Technology', 'NTES': 'Technology',
            'YMMD': 'Technology', 'TME': 'Technology', 'WB': 'Technology', 'VIPS': 'Consumer Discretionary'
        }
        
        # Check direct mapping
        if ticker in sector_mappings:
            return sector_mappings[ticker]
        
        # Try to infer from ticker patterns
        if ticker.endswith('.BR') or ticker.endswith('.AS') or ticker.endswith('.CO'):
            # European tickers - try to get from Redis with different key format
            return 'Unknown'  # Will be handled by enhanced data fetcher
        
        # Default fallback
        return 'Unknown'
    
    def _process_stock_batch(self, batch_tickers: List[str]) -> List[Dict]:
        """Process a batch of tickers efficiently"""
        batch_stocks = []
        
        for ticker in batch_tickers:
            try:
                # Quick cache check
                sector_info = self.data_service._load_from_cache(ticker, 'sector')
                if not sector_info:
                    continue
                
                price_data = self.data_service.get_monthly_data(ticker)
                if not price_data or 'prices' not in price_data:
                    continue
                
                prices = price_data['prices']
                if len(prices) < 12:  # Need at least 1 year of data
                    continue
                
                # Calculate volatility efficiently
                price_series = pd.Series(prices)
                returns = price_series.pct_change().dropna()
                volatility = returns.std() * np.sqrt(12)  # Monthly to annual
                
                # Get company info (sector enhancement already applied in parsing)
                company_name = sector_info.get('company_name', ticker)
                sector = sector_info.get('sector', 'Unknown')
                industry = sector_info.get('industry', 'Unknown')
                
                stock_data = {
                    'symbol': ticker,
                    'name': company_name,
                    'sector': sector,
                    'industry': industry,
                    'volatility': volatility,
                    'prices': prices,
                    'returns': returns
                }
                
                batch_stocks.append(stock_data)
                
            except Exception as e:
                logger.debug(f"Error processing {ticker}: {e}")
                continue
        
        return batch_stocks
    
    def _filter_stocks_by_volatility(self, stocks: List[Dict], volatility_range: Tuple[float, float]) -> List[Dict]:
        """Filter stocks by volatility range"""
        min_vol, max_vol = volatility_range
        
        filtered_stocks = [
            stock for stock in stocks 
            if min_vol <= stock['volatility'] <= max_vol
        ]
        
        # Sort by volatility (closest to target)
        target_vol = (min_vol + max_vol) / 2
        filtered_stocks.sort(key=lambda x: abs(x['volatility'] - target_vol))
        
        logger.info(f"📈 Filtered to {len(filtered_stocks)} stocks within volatility range {min_vol:.1%} - {max_vol:.1%}")
        return filtered_stocks
    
    def _select_diversified_stocks(self, stocks: List[Dict], risk_profile: str) -> List[Dict]:
        """Select stocks ensuring sector diversification with correlation analysis"""
        portfolio_size = self.PORTFOLIO_SIZE[risk_profile]
        selected_stocks = []
        sector_count = defaultdict(int)
        
        # Group stocks by sector
        stocks_by_sector = defaultdict(list)
        for stock in stocks:
            sector = stock['sector']
            if sector != 'Unknown':
                stocks_by_sector[sector].append(stock)
        
        # Get sector weights for this risk profile
        sector_weights = self.SECTOR_WEIGHTS.get(risk_profile, {})
        
        # First pass: select stocks based on sector weights
        for sector_group, weight in sector_weights.items():
            if len(selected_stocks) >= portfolio_size:
                break
                
            # Find stocks from sectors in this group
            available_sectors = [s for s in stocks_by_sector.keys() 
                               if s in self.SECTOR_CATEGORIES.get(sector_group, [])]
            
            for sector in available_sectors:
                if len(selected_stocks) >= portfolio_size:
                    break
                    
                sector_stocks = stocks_by_sector[sector]
                best_stock = self._select_best_stock_from_sector(sector_stocks, risk_profile)
                if best_stock:
                    selected_stocks.append(best_stock)
                    sector_count[sector] += 1
                    break  # Only take one from each sector group initially
        
        # Second pass: fill remaining slots with diversification in mind
        remaining_slots = portfolio_size - len(selected_stocks)
        
        if remaining_slots > 0:
            # Find sectors with lowest representation
            underrepresented_sectors = [
                sector for sector in stocks_by_sector.keys()
                if sector_count[sector] == 0
            ]
            
            # Select from underrepresented sectors
            for sector in underrepresented_sectors[:remaining_slots]:
                if len(selected_stocks) >= portfolio_size:
                    break
                    
                sector_stocks = stocks_by_sector[sector]
                best_stock = self._select_best_stock_from_sector(sector_stocks, risk_profile)
                if best_stock:
                    selected_stocks.append(best_stock)
                    sector_count[sector] += 1
        
        # If we still have slots, fill with best remaining stocks
        if len(selected_stocks) < portfolio_size:
            remaining_stocks = [s for s in stocks if s not in selected_stocks]
            remaining_stocks.sort(key=lambda x: x['volatility'])  # Sort by volatility
            
            for stock in remaining_stocks[:portfolio_size - len(selected_stocks)]:
                selected_stocks.append(stock)
        
        # Final optimization: minimize correlation (DISABLED for maximum speed)
        # if len(selected_stocks) >= 3:  # Only optimize for 3+ stocks
        #     selected_stocks = self._optimize_correlation(selected_stocks)
        
        return selected_stocks[:portfolio_size]
    
    def _select_diversified_stocks_dynamic(self, stocks: List[Dict], risk_profile: str, variation_seed: int, fast_mode: bool = False) -> List[Dict]:
        """DYNAMIC stock selection for maximum diversity - wrapper for the dynamic method"""
        return self._select_diversified_stocks_deterministic(stocks, risk_profile, variation_seed, fast_mode)
    
    def _select_diversified_stocks_deterministic(self, stocks: List[Dict], risk_profile: str, variation_seed: int, fast_mode: bool = False) -> List[Dict]:
        """Select stocks ensuring sector diversification with deterministic algorithm and least-correlation optimization on a small candidate set."""
        portfolio_size = self.PORTFOLIO_SIZE[risk_profile]
        selected_stocks = []
        sector_count = defaultdict(int)
        
        # Group stocks by sector
        stocks_by_sector = defaultdict(list)
        for stock in stocks:
            sector = stock['sector']
            if sector != 'Unknown':
                stocks_by_sector[sector].append(stock)
        
        # MAIN PRIORITIZATION: Volatility-weighted sector system
        # Compute sector weights based on dynamic realized vol alignment with profile band
        try:
            flat_stocks = []
            for sec, lst in stocks_by_sector.items():
                flat_stocks.extend(lst)
            vol_weights = get_volatility_weighted_sector_weights(
                risk_profile,
                flat_stocks,
                min_sectors=max(3, portfolio_size),
                data_service=self.data_service
            )
        except Exception:
            vol_weights = {}

        # Build ordered sector list by weight (fallback to natural order if empty)
        ordered_sectors = []
        if vol_weights:
            ordered_sectors = [sec for sec, _ in sorted(vol_weights.items(), key=lambda kv: kv[1], reverse=True) if sec in stocks_by_sector]
        else:
            ordered_sectors = list(stocks_by_sector.keys())

        # Build a small candidate set per prioritized sector (limit correlation scope)
        import random
        import time
        current_time = int(time.time() * 1000000) % 1000000
        
        candidate_set: List[Dict] = []
        max_candidates_total = 24  # expanded cap for 12-portfolio generation
        per_sector_pick = 3        # take more per sector to enrich pool
        
        # Score stocks within a sector by proximity to desired profile volatility
        def _sector_score(stock: Dict) -> float:
            lo, hi = self.RISK_PROFILE_VOLATILITY[risk_profile]
            target = (lo + hi) / 2
            return abs(stock['volatility'] - target)
        
        for sector in ordered_sectors:
            if sector not in stocks_by_sector:
                continue
            sector_list = stocks_by_sector[sector]
            # Prefer better volatility alignment first
            sector_list_sorted = sorted(sector_list, key=_sector_score)
            # Add small randomized tie-break inside top window
            window = min(len(sector_list_sorted), max(5, per_sector_pick * 3))
            sub = sector_list_sorted[:window]
            random.seed(current_time + variation_seed + hash(sector))
            random.shuffle(sub)
            candidate_set.extend(sub[:per_sector_pick])
            if len(candidate_set) >= max_candidates_total:
                    break
                    
        # Deduplicate candidate_set by symbol
        seen = set()
        dedup_candidates = []
        for c in candidate_set:
            if c['symbol'] in seen:
                continue
            seen.add(c['symbol'])
            dedup_candidates.append(c)
        candidate_set = dedup_candidates[:max_candidates_total]
        
        # Apply least-correlation optimization on the small candidate set with sector cap
        selected_stocks = self._build_least_correlated_portfolio(candidate_set, portfolio_size, risk_profile, sector_cap=1)
        
        # Second pass: fill remaining slots with diversification in mind
        remaining_slots = portfolio_size - len(selected_stocks)
        
        if remaining_slots > 0:
            # Find sectors with lowest representation
            underrepresented_sectors = [
                sector for sector in stocks_by_sector.keys()
                if sector_count[sector] == 0
            ]
            
            # Select from underrepresented sectors
            for sector in underrepresented_sectors[:remaining_slots]:
                if len(selected_stocks) >= portfolio_size:
                    break
                    
                sector_stocks = stocks_by_sector[sector]
                best_stock = self._select_best_stock_from_sector_dynamic(sector_stocks, risk_profile, variation_seed, current_time)
                if best_stock:
                    selected_stocks.append(best_stock)
                    sector_count[sector] += 1
        
        # If we still have slots, fill with best remaining stocks
        if len(selected_stocks) < portfolio_size:
            remaining_stocks = [s for s in stocks if s not in selected_stocks]
            remaining_stocks.sort(key=lambda x: x['volatility'])  # Sort by volatility
            
            for stock in remaining_stocks[:portfolio_size - len(selected_stocks)]:
                selected_stocks.append(stock)
        
        # Final check already uses least-correlation construction above
        
        return selected_stocks[:portfolio_size]

    def _build_least_correlated_portfolio(self, candidates: List[Dict], portfolio_size: int, risk_profile: str, sector_cap: int = 1) -> List[Dict]:
        """Greedy least-correlation selection from a small candidate set using 5y history (60 months)."""
        if not candidates:
            return []
        
        # Require at least 60 monthly returns; drop otherwise
        filtered = []
        for c in candidates:
            rets = c.get('returns')
            if isinstance(rets, (list, np.ndarray)) and len(rets) >= 60:
                # Use last 60 months only
                arr = np.array(rets[-60:])
                # Skip if all zeros or NaNs
                if np.isnan(arr).any() or (np.std(arr) == 0):
                    continue
                cc = dict(c)
                cc['__lc_returns__'] = arr
                filtered.append(cc)
        
        if len(filtered) <= 1:
            return [candidates[0]] if candidates else []
        
        # Start with the candidate with lowest average correlation proxy (vol distance)
        # Seed by best volatility alignment
        lo, hi = self.RISK_PROFILE_VOLATILITY.get(risk_profile, (0.15, 0.30))
        target = (lo + hi) / 2
        filtered.sort(key=lambda x: abs(x['volatility'] - target))
        selected: List[Dict] = []
        sector_counts = defaultdict(int)
        
        # Greedy selection
        def avg_corr_to_selected(cand: Dict) -> float:
            if not selected:
                return 0.0
            vals = []
            for s in selected:
                corr = np.corrcoef(cand['__lc_returns__'], s['__lc_returns__'])[0,1]
                if np.isnan(corr):
                    continue
                vals.append(corr)
            return float(np.mean(vals)) if vals else 0.0
        
        pool = filtered[:]
        while len(selected) < portfolio_size and pool:
            # Respect sector cap
            pool_feasible = [p for p in pool if sector_counts[p.get('sector','Unknown')] < sector_cap]
            if not pool_feasible:
                break
            # Pick the candidate with lowest average correlation to current selected
            best = min(pool_feasible, key=avg_corr_to_selected)
            selected.append(best)
            sector_counts[best.get('sector','Unknown')] += 1
            # Remove chosen from pool
            pool = [p for p in pool if p['symbol'] != best['symbol']]
        
        # Strip helper field
        for s in selected:
            if '__lc_returns__' in s:
                del s['__lc_returns__']
        
        return selected
    
    def _select_best_stock_from_sector(self, sector_stocks: List[Dict], risk_profile: str) -> Optional[Dict]:
        """Select the best stock from a sector based on risk profile with randomization"""
        if not sector_stocks:
            return None
        
        # For conservative profiles, prefer lower volatility
        # For aggressive profiles, prefer higher volatility
        if risk_profile in ['very-conservative', 'conservative']:
            # Sort by volatility (ascending) for conservative profiles
            sector_stocks.sort(key=lambda x: x['volatility'])
        else:
            # Sort by volatility (descending) for aggressive profiles
            sector_stocks.sort(key=lambda x: x['volatility'], reverse=True)
        
        # Add randomization: select from top 3 stocks instead of always the first
        top_stocks = sector_stocks[:min(3, len(sector_stocks))]
        if len(top_stocks) == 1:
            return top_stocks[0]
        else:
            # Randomly select from top stocks to ensure variety
            import random
            return random.choice(top_stocks)
    
    def _select_best_stock_from_sector_deterministic(self, sector_stocks: List[Dict], risk_profile: str, variation_seed: int) -> Optional[Dict]:
        """Select the best stock from a sector using deterministic algorithm with smart sampling"""
        if not sector_stocks:
            return None
        
        # For conservative profiles, prefer lower volatility
        # For aggressive profiles, prefer higher volatility
        if risk_profile in ['very-conservative', 'conservative']:
            # Sort by volatility (ascending) for conservative profiles
            sector_stocks.sort(key=lambda x: x['volatility'])
        else:
            # Sort by volatility (descending) for aggressive profiles
            sector_stocks.sort(key=lambda x: x['volatility'], reverse=True)
        
        # PHASE 2: Smart sampling for maximum diversity
        # Instead of limiting to top 20, use smart sampling for large sectors
        sampled_stocks = self._smart_sector_sampling(sector_stocks, variation_seed)
        
        if len(sampled_stocks) == 1:
            return sampled_stocks[0]
        else:
            # Deterministic selection based on variation seed
            selection_index = variation_seed % len(sampled_stocks)
            return sampled_stocks[selection_index]
    
    def _smart_sector_sampling(self, sector_stocks: List[Dict], variation_seed: int) -> List[Dict]:
        """Smart sampling strategy for maximum portfolio diversity
        
        Uses different sampling strategies based on sector size and variation seed
        to ensure maximum diversity while maintaining performance.
        """
        total_stocks = len(sector_stocks)
        
        if total_stocks <= 50:
            # Small sectors: use all stocks for maximum diversity
            return sector_stocks
        elif total_stocks <= 200:
            # Medium sectors: use every 2nd stock for good diversity
            step = 2
            sampled = sector_stocks[::step]
        else:
            # Large sectors: use every 3rd stock for balanced diversity
            step = 3
            sampled = sector_stocks[::step]
        
        # Ensure we have at least 20 stocks for good variation
        if len(sampled) < 20:
            # If sampling reduced too much, take top 20
            sampled = sector_stocks[:20]
        
        # Cap at 100 stocks for performance (still 5x more than before)
        sampled = sampled[:100]
        
        # Additional diversity enhancement: use variation seed to vary sampling
        # This ensures different portfolios get different stock selections
        if len(sampled) > 20:
            # Use variation seed to create different sampling patterns
            pattern = variation_seed % 4
            
            if pattern == 0:
                # Pattern 0: Use every nth stock (already done above)
                pass
            elif pattern == 1:
                # Pattern 1: Use every 3rd stock starting from middle
                mid_point = len(sampled) // 2
                sampled = sampled[mid_point::3] + sampled[:mid_point:3]
            elif pattern == 2:
                # Pattern 2: Use every 4th stock in reverse order
                sampled = sampled[::-1][::4]
            else:
                # Pattern 3: Use every 5th stock with offset
                offset = (variation_seed % 5) + 1
                sampled = sampled[offset::5]
            
            # Ensure we still have enough stocks after pattern application
            if len(sampled) < 40 and len(sector_stocks) > 100:
                # fallback to a less aggressive sampling for large sectors
                sampled = sector_stocks[::2][:100]
            elif len(sampled) < 10:
                sampled = sector_stocks[:50]  # Fallback to top 50
        
        # Ensure we still have enough stocks
        if len(sampled) < 10:
            sampled = sector_stocks[:50]  # Fallback to top 50
        
        return sampled[:100]  # Final cap at 100
    
    def _select_best_stock_from_sector_dynamic(self, sector_stocks: List[Dict], risk_profile: str, variation_seed: int, current_time: int) -> Optional[Dict]:
        """DYNAMIC stock selection for maximum diversity using multiple entropy sources"""
        if not sector_stocks:
            return None
        
        import random
        
        # Multiple entropy sources for true randomness
        time_factor = (current_time % 10000) / 10000.0
        seed_factor = (variation_seed % 10000) / 10000.0
        sector_hash = hash(str(sector_stocks[0].get('sector', ''))) % 10000 / 10000.0
        
        # Combine entropy sources
        combined_entropy = int((time_factor + seed_factor + sector_hash) * 1000000) % 1000000
        
        # Sort stocks by volatility based on risk profile
        if risk_profile in ['very-conservative', 'conservative']:
            sector_stocks.sort(key=lambda x: x['volatility'])
        else:
            sector_stocks.sort(key=lambda x: x['volatility'], reverse=True)
        
        # Dynamic sampling based on multiple factors
        sample_size = min(len(sector_stocks), 50)  # Sample up to 50 stocks
        
        # Use multiple sampling strategies for maximum diversity
        strategy = combined_entropy % 4
        
        if strategy == 0:
            # Strategy 0: Random sampling from top stocks
            random.seed(combined_entropy)
            sampled = random.sample(sector_stocks[:sample_size], min(20, sample_size))
        elif strategy == 1:
            # Strategy 1: Every nth stock with dynamic step
            step = (combined_entropy % 5) + 2  # Step 2-6
            sampled = sector_stocks[::step][:20]
        elif strategy == 2:
            # Strategy 2: Middle-out sampling
            mid = len(sector_stocks) // 2
            start = max(0, mid - 10)
            end = min(len(sector_stocks), mid + 10)
            sampled = sector_stocks[start:end]
        else:
            # Strategy 3: Weighted random sampling
            random.seed(combined_entropy)
            weights = [1.0 / (i + 1) for i in range(sample_size)]  # Higher weight for better stocks
            sampled = random.choices(sector_stocks[:sample_size], weights=weights, k=min(20, sample_size))
        
        if not sampled:
            return sector_stocks[0]  # Fallback
        
        # Final selection with additional randomness
        random.seed(combined_entropy + variation_seed)
        return random.choice(sampled)
    
    def _optimize_correlation(self, selected_stocks: List[Dict]) -> List[Dict]:
        """Optimize portfolio by minimizing correlation between selected stocks - OPTIMIZED VERSION"""
        if len(selected_stocks) < 2:
            return selected_stocks
        
        try:
            # OPTIMIZATION 1: Quick validation before expensive operations
            returns_data = {}
            valid_stocks = []
            
            for stock in selected_stocks:
                if 'returns' in stock and stock['returns'] and len(stock['returns']) > 0:
                    # OPTIMIZATION 2: Use only last 12 months for speed
                    returns = stock['returns'][-12:] if len(stock['returns']) >= 12 else stock['returns']
                    if len(returns) >= 3:  # Minimum 3 data points
                        returns_data[stock['symbol']] = returns
                        valid_stocks.append(stock)
            
            if len(returns_data) < 2:
                return selected_stocks
            
            # OPTIMIZATION 3: Skip correlation if we have too few valid stocks
            if len(valid_stocks) < len(selected_stocks) * 0.5:  # Less than 50% valid
                return selected_stocks
            
            # OPTIMIZATION 4: Use numpy for faster correlation calculation
            import numpy as np
            
            # Create aligned returns matrix
            symbols = list(returns_data.keys())
            min_length = min(len(returns_data[sym]) for sym in symbols)
            
            if min_length < 3:
                return selected_stocks
            
            # Align all returns to same length
            aligned_returns = np.array([returns_data[sym][:min_length] for sym in symbols])
            
            # Calculate correlation matrix using numpy (much faster)
            correlation_matrix = np.corrcoef(aligned_returns)
            
            # Find stocks with lowest average correlation
            avg_correlations = {}
            for i, symbol in enumerate(symbols):
                correlations = correlation_matrix[i]
                # Remove self-correlation (1.0)
                other_correlations = np.delete(correlations, i)
                avg_correlations[symbol] = np.mean(other_correlations)
            
            # Sort stocks by average correlation (ascending)
            sorted_symbols = sorted(avg_correlations.keys(), key=lambda x: avg_correlations[x])
            
            # Reorder selected stocks based on correlation optimization
            optimized_stocks = []
            for symbol in sorted_symbols:
                stock = next(s for s in selected_stocks if s['symbol'] == symbol)
                optimized_stocks.append(stock)
            
            # Add remaining stocks that weren't in correlation analysis
            for stock in selected_stocks:
                if stock['symbol'] not in sorted_symbols:
                    optimized_stocks.append(stock)
            
            logger.info(f"🔄 Correlation optimization completed. Avg correlation: {avg_correlations[sorted_symbols[0]]:.3f}")
            return optimized_stocks
            
        except Exception as e:
            logger.debug(f"Correlation optimization skipped: {e}")
            return selected_stocks
    
    def invalidate_cache(self):
        """Invalidate the stock cache to force fresh data fetch - thread-safe"""
        with self._cache_lock:
            self._stock_cache = {}
            self._cache_timestamp = None
        logger.info("🗑️ Stock cache invalidated (thread-safe)")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        with self._cache_lock:
            cache_size = len(self._stock_cache) if self._stock_cache else 0
            cache_age = 0
            if self._cache_timestamp:
                from datetime import datetime
                cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            
            return {
                'cache_size': cache_size,
                'cache_age_seconds': cache_age,
                'cache_ttl_hours': self.CACHE_TTL_HOURS,
                'cache_valid': cache_age < (self.CACHE_TTL_HOURS * 3600)
            }
    
    def _create_portfolio_allocations(self, selected_stocks: List[Dict], portfolio_size: int, variation_id: int = 0) -> List[Dict]:
        """Create portfolio allocations with weights - Multiple templates to reduce duplicates"""
        if not selected_stocks:
            return []
        
        # Multiple weight templates per portfolio size to increase variation
        # EXPANDED: 15 templates instead of 10 for 50% more variation
        weight_templates = {
            3: [
                [0.42, 0.33, 0.25],  # Template 1: 42/33/25
                [0.38, 0.37, 0.25],  # Template 2: 38/37/25
                [0.45, 0.30, 0.25],  # Template 3: 45/30/25
                [0.35, 0.35, 0.30],  # Template 4: 35/35/30
                [0.50, 0.30, 0.20],  # Template 5: 50/30/20
                [0.40, 0.40, 0.20],  # Template 6: 40/40/20
                [0.30, 0.35, 0.35],  # Template 7: 30/35/35
                [0.48, 0.32, 0.20],  # Template 8: 48/32/20
                [0.33, 0.33, 0.34],  # Template 9: 33/33/34
                [0.44, 0.28, 0.28],  # Template 10: 44/28/28
                [0.36, 0.34, 0.30],  # Template 11: 36/34/30
                [0.41, 0.29, 0.30],  # Template 12: 41/29/30
                [0.39, 0.31, 0.30],  # Template 13: 39/31/30
                [0.37, 0.33, 0.30],  # Template 14: 37/33/30
                [0.43, 0.27, 0.30]   # Template 15: 43/27/30
            ],
            4: [
                [0.32, 0.25, 0.23, 0.20],  # Template 1: 32/25/23/20
                [0.28, 0.26, 0.24, 0.22],  # Template 2: 28/26/24/22
                [0.30, 0.27, 0.23, 0.20],  # Template 3: 30/27/23/20
                [0.35, 0.30, 0.20, 0.15],  # Template 4: 35/30/20/15
                [0.25, 0.25, 0.25, 0.25],  # Template 5: 25/25/25/25
                [0.40, 0.25, 0.20, 0.15],  # Template 6: 40/25/20/15
                [0.30, 0.30, 0.25, 0.15],  # Template 7: 30/30/25/15
                [0.28, 0.28, 0.24, 0.20],  # Template 8: 28/28/24/20
                [0.33, 0.27, 0.22, 0.18],  # Template 9: 33/27/22/18
                [0.26, 0.26, 0.26, 0.22],  # Template 10: 26/26/26/22
                [0.29, 0.29, 0.21, 0.21],  # Template 11: 29/29/21/21
                [0.31, 0.27, 0.23, 0.19],  # Template 12: 31/27/23/19
                [0.27, 0.31, 0.21, 0.21],  # Template 13: 27/31/21/21
                [0.25, 0.25, 0.25, 0.25],  # Template 14: 25/25/25/25 (equal weight)
                [0.34, 0.26, 0.22, 0.18]   # Template 15: 34/26/22/18
            ]
        }

        # Use variation_id for template selection with random component for more diversity
        templates = weight_templates.get(portfolio_size, [[0.25] * portfolio_size])
        
        # DYNAMIC template selection for near 100% diversity
        import random
        import time
        
        # Use multiple entropy sources for true randomness
        current_time = int(time.time() * 1000000) % 1000000  # Microsecond precision
        variation_factor = variation_id * 1000 + variation_id * 17 + (variation_id % 13) * 23
        entropy_seed = current_time + variation_factor + len(selected_stocks) * 7
        
        random.seed(entropy_seed)
        
        # ENHANCED template tracking for near 100% diversity
        # Use variation_id as key to track templates per generation session
        session_key = f"session_{variation_id // 12}"  # New session every 12 variations
        
        if not hasattr(self, '_used_templates_by_session'):
            self._used_templates_by_session = {}
        
        if session_key not in self._used_templates_by_session:
            self._used_templates_by_session[session_key] = set()
        
        used_templates = self._used_templates_by_session[session_key]
        
        # Get available templates (not used in this session)
        available_templates = [i for i in range(len(templates)) if i not in used_templates]
        
        # If we've used all templates in this session, reset for next session
        if not available_templates:
            used_templates.clear()
            available_templates = list(range(len(templates)))
        
        # Select from available templates
        template_idx = random.choice(available_templates)
        used_templates.add(template_idx)
        
        # Clean up old sessions to prevent memory leaks
        if len(self._used_templates_by_session) > 10:
            oldest_sessions = list(self._used_templates_by_session.keys())[:-5]
            for old_session in oldest_sessions:
                del self._used_templates_by_session[old_session]
        
        weights = templates[template_idx]
        
        allocations = []
        for i, stock in enumerate(selected_stocks):
            allocation = {
                'symbol': stock['symbol'],
                'allocation': weights[i] * 100,  # Convert to percentage
                'name': stock['name'],
                'assetType': 'stock',
                'sector': stock['sector'],
                'volatility': stock['volatility']
            }
            allocations.append(allocation)
        
        return allocations
    
    def _get_fallback_portfolio(self, risk_profile: str, variation_id: int = 0) -> Dict:
        """Dynamic fallback portfolio from pre-computed pool of high-quality stocks
        
        Instead of hardcoded portfolios, this selects from a pool of the top stocks
        that meet the risk profile criteria, rotating through them based on variation_id
        to ensure each fallback portfolio is unique.
        
        Returns: Complete portfolio object (not just allocations)
        """
        logger.warning(f"⚠️ Using fallback portfolio for {risk_profile} (variation {variation_id})")

        # Get fallback pool for this risk profile
        fallback_pool = self._get_fallback_pool(risk_profile)
        portfolio_size = self.PORTFOLIO_SIZE.get(risk_profile, 4)
        
        if len(fallback_pool) < portfolio_size:
            # Not enough stocks in pool, use emergency fallback
            logger.error(f"❌ Fallback pool too small ({len(fallback_pool)} stocks), using emergency fallback")
            return self._get_emergency_fallback(risk_profile)
        
        # Use variation_id to deterministically select stocks from pool
        # This ensures different fallback portfolios for different variation_ids
        import random
        random.seed(f"{risk_profile}_{variation_id}_fallback")
        
        # Select stocks ensuring sector diversity
        selected_stocks = []
        used_sectors = set()
        
        # Shuffle pool for this seed
        pool_copy = fallback_pool.copy()
        random.shuffle(pool_copy)
        
        # First pass: one stock per sector (for diversity)
        for stock in pool_copy:
            if stock['sector'] not in used_sectors:
                selected_stocks.append(stock)
                used_sectors.add(stock['sector'])
                if len(selected_stocks) >= portfolio_size:
                    break
        
        # Second pass: fill remaining slots if needed
        if len(selected_stocks) < portfolio_size:
            remaining_stocks = [s for s in pool_copy if s not in selected_stocks]
            selected_stocks.extend(remaining_stocks[:portfolio_size - len(selected_stocks)])
        
        # Create allocations using standard templates
        allocations = self._create_portfolio_allocations(selected_stocks[:portfolio_size], portfolio_size, variation_id)
        
        # Return complete portfolio object (FIXED: was returning just allocations)
        from datetime import datetime
        return {
            'name': f'Fallback Portfolio {variation_id + 1}',
            'description': f'Fallback portfolio for {risk_profile} risk profile',
            'allocations': allocations,
            'expectedReturn': 0.15,  # Conservative estimate
            'risk': 0.25,  # Conservative estimate
            'diversificationScore': 60.0,  # Moderate score
            'sectorBreakdown': self._calculate_sector_breakdown(allocations),
            'variation_id': variation_id,
            'risk_profile': risk_profile,
            'generated_at': datetime.now().isoformat(),
            'data_dependency_hash': 'fallback_hash'
        }
    
    def _get_fallback_pool(self, risk_profile: str) -> List[Dict]:
        """Get pre-computed fallback pool of top stocks for a risk profile
        
        These pools are based on actual analysis of Redis data and contain
        the highest-quality stocks that meet each profile's criteria.
        """
        # Fallback pools discovered from analyze_volatility_ranges.py
        # These are real stocks from Redis with appropriate risk characteristics
        fallback_pools = {
            'very-conservative': [
                {'symbol': 'VIG', 'name': 'Vanguard Dividend Appreciation ETF', 'sector': 'Financial Services', 'assetType': 'stock'},
                {'symbol': 'VTV', 'name': 'Vanguard Value Index Fund ETF', 'sector': 'Financial Services', 'assetType': 'stock'},
                {'symbol': 'SPLG', 'name': 'SPDR Portfolio S&P 500 ETF', 'sector': 'Financial Services', 'assetType': 'stock'},
                {'symbol': 'VOO', 'name': 'Vanguard S&P 500 ETF', 'sector': 'Financial Services', 'assetType': 'stock'},
                {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF', 'sector': 'Financial Services', 'assetType': 'stock'},
                {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'assetType': 'stock'},
                {'symbol': 'PG', 'name': 'Procter & Gamble', 'sector': 'Consumer Defensive', 'assetType': 'stock'},
                {'symbol': 'KO', 'name': 'Coca-Cola', 'sector': 'Consumer Defensive', 'assetType': 'stock'},
            ],
            'conservative': [
                {'symbol': 'WM', 'name': 'Waste Management Inc.', 'sector': 'Industrials', 'assetType': 'stock'},
                {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'KMB', 'name': 'Kimberly-Clark Corporation', 'sector': 'Consumer Defensive', 'assetType': 'stock'},
                {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'assetType': 'stock'},
                {'symbol': 'PG', 'name': 'Procter & Gamble', 'sector': 'Consumer Defensive', 'assetType': 'stock'},
                {'symbol': 'WMT', 'name': 'Walmart Inc.', 'sector': 'Consumer Defensive', 'assetType': 'stock'},
                {'symbol': 'VZ', 'name': 'Verizon', 'sector': 'Communication Services', 'assetType': 'stock'},
                {'symbol': 'T', 'name': 'AT&T Inc.', 'sector': 'Communication Services', 'assetType': 'stock'},
            ],
            'moderate': [
                {'symbol': 'EIX', 'name': 'Edison International', 'sector': 'Utilities', 'assetType': 'stock'},
                {'symbol': 'ALLE', 'name': 'Allegion plc', 'sector': 'Industrials', 'assetType': 'stock'},
                {'symbol': 'PNC', 'name': 'PNC Financial Services Group', 'sector': 'Financial Services', 'assetType': 'stock'},
                {'symbol': 'NTRS', 'name': 'Northern Trust Corporation', 'sector': 'Financial Services', 'assetType': 'stock'},
                {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'MSFT', 'name': 'Microsoft', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'AMZN', 'name': 'Amazon.com', 'sector': 'Consumer Cyclical', 'assetType': 'stock'},
            ],
            'aggressive': [
                {'symbol': 'NVDA', 'name': 'NVIDIA', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Cyclical', 'assetType': 'stock'},
                {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'META', 'name': 'Meta Platforms', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'sector': 'Communication Services', 'assetType': 'stock'},
                {'symbol': 'ADBE', 'name': 'Adobe Inc.', 'sector': 'Technology', 'assetType': 'stock'},
            ],
            'very-aggressive': [
                {'symbol': 'TTD', 'name': 'The Trade Desk Inc.', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'MSTR', 'name': 'MicroStrategy Inc', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'PDD', 'name': 'PDD Holdings Inc.', 'sector': 'Consumer Cyclical', 'assetType': 'stock'},
                {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Cyclical', 'assetType': 'stock'},
                {'symbol': 'NVDA', 'name': 'NVIDIA', 'sector': 'Technology', 'assetType': 'stock'},
                {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'sector': 'Technology', 'assetType': 'stock'},
            ]
        }
        
        return fallback_pools.get(risk_profile, fallback_pools['moderate'])
    
    def _get_emergency_fallback(self, risk_profile: str) -> Dict:
        """Ultimate emergency fallback when even the pool fails"""
        logger.error(f"❌ Using EMERGENCY fallback for {risk_profile}")
        
        # Simple, guaranteed-to-work portfolios
        emergency_fallbacks = {
            'very-conservative': [
                {'symbol': 'SPY', 'allocation': 40, 'name': 'SPDR S&P 500 ETF', 'assetType': 'stock'},
                {'symbol': 'JNJ', 'allocation': 30, 'name': 'Johnson & Johnson', 'assetType': 'stock'},
                {'symbol': 'PG', 'allocation': 20, 'name': 'Procter & Gamble', 'assetType': 'stock'},
                {'symbol': 'KO', 'allocation': 10, 'name': 'Coca-Cola', 'assetType': 'stock'}
            ],
            'conservative': [
                {'symbol': 'QQQ', 'allocation': 35, 'name': 'Invesco QQQ Trust', 'assetType': 'stock'},
                {'symbol': 'WM', 'allocation': 30, 'name': 'Waste Management', 'assetType': 'stock'},
                {'symbol': 'JNJ', 'allocation': 25, 'name': 'Johnson & Johnson', 'assetType': 'stock'},
                {'symbol': 'VZ', 'allocation': 10, 'name': 'Verizon', 'assetType': 'stock'}
            ],
            'moderate': [
                {'symbol': 'AAPL', 'allocation': 32, 'name': 'Apple Inc.', 'assetType': 'stock'},
                {'symbol': 'MSFT', 'allocation': 25, 'name': 'Microsoft', 'assetType': 'stock'},
                {'symbol': 'GOOGL', 'allocation': 23, 'name': 'Alphabet Inc.', 'assetType': 'stock'},
                {'symbol': 'AMZN', 'allocation': 20, 'name': 'Amazon.com', 'assetType': 'stock'}
            ],
            'aggressive': [
                {'symbol': 'NVDA', 'allocation': 40, 'name': 'NVIDIA', 'assetType': 'stock'},
                {'symbol': 'TSLA', 'allocation': 35, 'name': 'Tesla Inc.', 'assetType': 'stock'},
                {'symbol': 'AMD', 'allocation': 25, 'name': 'Advanced Micro Devices', 'assetType': 'stock'}
            ],
            'very-aggressive': [
                {'symbol': 'TTD', 'allocation': 40, 'name': 'The Trade Desk Inc.', 'assetType': 'stock'},
                {'symbol': 'TSLA', 'allocation': 35, 'name': 'Tesla Inc.', 'assetType': 'stock'},
                {'symbol': 'NVDA', 'allocation': 25, 'name': 'NVIDIA', 'assetType': 'stock'}
            ]
        }
        
        # Get the emergency allocations
        emergency_allocations = emergency_fallbacks.get(risk_profile, emergency_fallbacks['moderate'])
        
        # Return complete portfolio object
        from datetime import datetime
        return {
            'name': f'Emergency Fallback Portfolio',
            'description': f'Emergency fallback portfolio for {risk_profile} risk profile',
            'allocations': emergency_allocations,
            'expectedReturn': 0.12,  # Conservative estimate
            'risk': 0.30,  # Conservative estimate
            'diversificationScore': 50.0,  # Lower score for emergency
            'sectorBreakdown': self._calculate_sector_breakdown(emergency_allocations),
            'variation_id': 0,
            'risk_profile': risk_profile,
            'generated_at': datetime.now().isoformat(),
            'data_dependency_hash': 'emergency_fallback_hash'
        }
    
    def _calculate_sector_breakdown(self, allocations: List[Dict]) -> Dict:
        """Calculate sector breakdown from allocations"""
        sector_breakdown = {}
        for allocation in allocations:
            sector = allocation.get('sector', 'Unknown')
            allocation_pct = allocation.get('allocation', 0)
            sector_breakdown[sector] = sector_breakdown.get(sector, 0) + allocation_pct
        return sector_breakdown
    
    
    def get_stock_selection_summary(self, risk_profile: str) -> Dict:
        """Get summary of stock selection criteria for a risk profile"""
        volatility_range = self.RISK_PROFILE_VOLATILITY[risk_profile]
        portfolio_size = self.PORTFOLIO_SIZE[risk_profile]
        sector_weights = self.SECTOR_WEIGHTS.get(risk_profile, {})
        
        return {
            'risk_profile': risk_profile,
            'volatility_range': {
                'min': f"{volatility_range[0]:.1%}",
                'max': f"{volatility_range[1]:.1%}",
                'target': f"{(volatility_range[0] + volatility_range[1]) / 2:.1%}"
            },
            'portfolio_size': portfolio_size,
            'sector_weights': sector_weights,
            'selection_criteria': {
                'sector_diversification': 'Yes - avoid over-concentration',
                'volatility_matching': f'Target: {volatility_range[0]:.1%} - {volatility_range[1]:.1%}',
                'portfolio_optimization': f'{portfolio_size} stocks minimum',
                'correlation_optimization': 'Yes - minimize portfolio risk'
            }
        }

    def _validate_ticker_data(self, ticker_info: Dict) -> bool:
        """Validate ticker data for inclusion in stock selection"""
        try:
            # Check if essential data exists
            if not ticker_info:
                return False
            
            # Check if price data exists
            if not ticker_info.get('current_price', 0):
                return False
            
            # Check if volatility data exists
            if ticker_info.get('annualized_volatility', 0) <= 0:
                return False
            
            # Check if return data exists
            if ticker_info.get('annualized_return', 0) == 0:
                return False
            
            # Check data quality
            data_quality = ticker_info.get('data_quality', 'Unknown')
            if data_quality == 'corrupted' or data_quality == 'missing':
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"⚠️ Data validation failed: {e}")
            return False
