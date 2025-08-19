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
from .ticker_store import ticker_store

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
        
        # Cache for stock data to avoid repeated processing
        self._stock_cache = {}
        self._cache_timestamp = None
        self.CACHE_TTL_HOURS = 24  # Cache for 24 hours
        
        # Enhanced sector categories for better diversification
        self.SECTOR_CATEGORIES = {
            'technology': ['Technology'],
            'communication': ['Communication Services'],
            'healthcare': ['Healthcare', 'Biotechnology', 'Pharmaceuticals'],
            'financial': ['Financial Services', 'Banks', 'Insurance'],
            'consumer_staples': ['Consumer Staples'],
            'consumer_discretionary': ['Consumer Discretionary', 'Retail'],
            'industrial': ['Industrials', 'Manufacturing', 'Transportation'],
            'energy': ['Energy', 'Oil & Gas'],
            'utilities': ['Utilities'],
            'materials': ['Materials', 'Mining', 'Chemicals'],
            'real_estate': ['Real Estate']
        }
        
        # Risk profile volatility targets (annualized) - Updated for 2024 market conditions
        self.RISK_PROFILE_VOLATILITY = {
            'very-conservative': (0.08, 0.18),    # 8-18% annual volatility (increased from 5-12%)
            'conservative': (0.15, 0.25),         # 15-25% annual volatility (increased from 10-18%)
            'moderate': (0.22, 0.32),             # 22-32% annual volatility (increased from 15-25%)
            'aggressive': (0.30, 0.42),           # 30-42% annual volatility (increased from 20-35%)
            'very-aggressive': (0.38, 0.55)       # 38-55% annual volatility (increased from 25-45%)
        }
        
        # Portfolio size by risk profile
        self.PORTFOLIO_SIZE = {
            'very-conservative': 4,  # More stocks for diversification
            'conservative': 4,        # More stocks for stability
            'moderate': 4,            # Balanced approach
            'aggressive': 3,          # Focused growth
            'very-aggressive': 3      # Concentrated growth
        }
        
        # Sector allocation weights by risk profile
        self.SECTOR_WEIGHTS = {
            'very-conservative': {
                'healthcare': 0.35,      # Stable, defensive
                'consumer_staples': 0.30, # Essential goods
                'utilities': 0.20,        # Regulated, stable
                'financial': 0.15        # Conservative banks
            },
            'conservative': {
                'healthcare': 0.30,      # Stable growth
                'consumer_staples': 0.25, # Reliable income
                'technology': 0.20,      # Blue chip tech
                'financial': 0.15,       # Established banks
                'industrial': 0.10       # Infrastructure
            },
            'moderate': {
                'technology': 0.30,      # Growth + stability
                'healthcare': 0.25,      # Balanced growth
                'financial': 0.20,       # Diversified exposure
                'consumer_discretionary': 0.15, # Cyclical growth
                'industrial': 0.10       # Economic exposure
            },
            'aggressive': {
                'technology': 0.40,      # High growth
                'consumer_discretionary': 0.25, # Growth potential
                'communication': 0.20,   # Innovation
                'healthcare': 0.15       # Growth healthcare
            },
            'very-aggressive': {
                'technology': 0.50,      # Maximum growth
                'consumer_discretionary': 0.30, # High momentum
                'communication': 0.20    # Disruptive tech
            }
        }
    
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
    
    def select_stocks_for_risk_profile_deterministic(self, risk_profile: str, variation_seed: int) -> List[Dict]:
        """
        Select optimal stocks for a given risk profile using deterministic algorithm
        This method eliminates randomization for consistent portfolio generation
        """
        logger.info(f"🔍 Selecting stocks deterministically for {risk_profile} risk profile (seed: {variation_seed})...")
        
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
            
            # Select stocks ensuring sector diversification with deterministic algorithm
            selected_stocks = self._select_diversified_stocks_deterministic(
                filtered_stocks, risk_profile, variation_seed
            )
            
            # Create portfolio allocations
            portfolio_size = self.PORTFOLIO_SIZE[risk_profile]
            allocations = self._create_portfolio_allocations(selected_stocks, portfolio_size)
            
            logger.info(f"✅ Selected {len(allocations)} stocks deterministically for {risk_profile} profile")
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error selecting stocks deterministically: {e}")
            return self._get_fallback_portfolio(risk_profile)
    
    def _get_available_stocks_with_metrics(self) -> List[Dict]:
        """Get all available stocks with their metrics from cache - LAZY INITIALIZATION VERSION"""
        from datetime import datetime
        import time
        
        current_time = datetime.now()
        
        # Check if cache is still valid
        if (self._stock_cache and self._cache_timestamp and 
            (current_time - self._cache_timestamp).total_seconds() < self._cache_ttl_hours * 3600):
            logger.info("⚡ Using cached stock data (cache hit)")
            return self._stock_cache
        
        # Cache miss - populate on-demand (lazy initialization)
        logger.info("🔄 Cache miss - performing lazy initialization of stock selection cache...")
        
        # Add timeout protection
        start_time = time.time()
        max_processing_time = 30  # 30 seconds timeout
        
        try:
            logger.info("🔍 Starting optimized stock selection process (lazy initialization)...")
            
            # Get all available tickers
            all_tickers = self.data_service.all_tickers
            logger.info(f"📊 Total tickers available: {len(all_tickers)}")
            
            # Phase 1: Quick pre-filtering
            logger.info("⚡ Phase 1: Quick pre-filtering...")
            pre_filtered = []
            for ticker in all_tickers:
                try:
                    # Basic validation
                    if len(ticker) >= 1 and ticker.isalpha():
                        pre_filtered.append(ticker)
                except:
                    continue
            
            logger.info(f"✅ Pre-filtered to {len(pre_filtered)} tickers")
            
            # Phase 2: Batch processing stocks
            logger.info("⚡ Phase 2: Batch processing stocks...")
            available_stocks = []
            batch_size = 50
            total_batches = (len(pre_filtered) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(pre_filtered))
                batch_tickers = pre_filtered[start_idx:end_idx]
                
                logger.info(f"📦 Processing batch {batch_num + 1}/{total_batches} ({start_idx + 1}-{end_idx})")
                
                for ticker in batch_tickers:
                    try:
                        # Get ticker info with timeout protection
                        ticker_info = self.data_service.get_ticker_info(ticker)
                        if ticker_info and self._validate_ticker_data(ticker_info):
                            stock_data = {
                                'ticker': ticker,
                                'company_name': ticker_info.get('company_name', ticker),
                                'sector': ticker_info.get('sector', 'Unknown'),
                                'industry': ticker_info.get('industry', 'Unknown'),
                                'volatility': ticker_info.get('annualized_volatility', 0),
                                'return': ticker_info.get('annualized_return', 0),
                                'price': ticker_info.get('current_price', 0),
                                'data_quality': ticker_info.get('data_quality', 'Unknown')
                            }
                            available_stocks.append(stock_data)
                    except Exception as e:
                        logger.debug(f"⚠️ Skipping {ticker}: {e}")
                        continue
                
                # Progress update
                progress = ((batch_num + 1) / total_batches) * 100
                logger.info(f"📊 Progress: {progress:.1f}% - Found {len(available_stocks)} stocks so far")
                
                # Check timeout
                if time.time() - start_time > max_processing_time:
                    logger.warning(f"⚠️ Timeout reached after {max_processing_time}s - returning partial results")
                    break
            
            # Cache the results
            self._stock_cache = available_stocks
            self._cache_timestamp = current_time
            
            logger.info(f"✅ Found {len(available_stocks)} stocks with complete data")
            logger.info("💾 Stock data cached for 24 hours")
            
            return available_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in stock selection: {e}")
            if self._stock_cache:
                logger.info("⚠️ Returning cached data due to error")
                return self._stock_cache
            return []
        
        finally:
            processing_time = time.time() - start_time
            if processing_time > max_processing_time:
                logger.warning(f"⚠️ Stock selection took {processing_time:.1f}s (exceeded {max_processing_time}s timeout)")
            else:
                logger.info(f"⚡ Stock selection completed in {processing_time:.1f}s")
    
    def _quick_pre_filter_tickers(self, all_tickers: List[str]) -> List[str]:
        """Quick pre-filtering to reduce processing load"""
        pre_filtered = []
        
        # Priority 1: S&P 500 stocks (most liquid)
        sp500_tickers = [t for t in all_tickers if t in getattr(ticker_store, 'sp500_tickers', [])]
        pre_filtered.extend(sp500_tickers[:200])  # Top 200 S&P 500
        
        # Priority 2: NASDAQ 100 stocks (growth focus)
        nasdaq_tickers = [t for t in all_tickers if t in getattr(ticker_store, 'nasdaq100_tickers', [])]
        nasdaq_tickers = [t for t in nasdaq_tickers if t not in pre_filtered]
        pre_filtered.extend(nasdaq_tickers[:100])  # Top 100 NASDAQ
        
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
                
                # Get company info
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
        
        # Final optimization: minimize correlation
        if len(selected_stocks) >= 2:
            selected_stocks = self._optimize_correlation(selected_stocks)
        
        return selected_stocks[:portfolio_size]
    
    def _select_diversified_stocks_deterministic(self, stocks: List[Dict], risk_profile: str, variation_seed: int) -> List[Dict]:
        """Select stocks ensuring sector diversification with deterministic algorithm"""
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
        
        # First pass: select stocks based on sector weights with deterministic selection
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
                best_stock = self._select_best_stock_from_sector_deterministic(sector_stocks, risk_profile, variation_seed)
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
                best_stock = self._select_best_stock_from_sector_deterministic(sector_stocks, risk_profile, variation_seed)
                if best_stock:
                    selected_stocks.append(best_stock)
                    sector_count[sector] += 1
        
        # If we still have slots, fill with best remaining stocks
        if len(selected_stocks) < portfolio_size:
            remaining_stocks = [s for s in stocks if s not in selected_stocks]
            remaining_stocks.sort(key=lambda x: x['volatility'])  # Sort by volatility
            
            for stock in remaining_stocks[:portfolio_size - len(selected_stocks)]:
                selected_stocks.append(stock)
        
        # Final optimization: minimize correlation
        if len(selected_stocks) >= 2:
            selected_stocks = self._optimize_correlation(selected_stocks)
        
        return selected_stocks[:portfolio_size]
    
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
        """Select the best stock from a sector using deterministic algorithm"""
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
        
        # Use variation seed to deterministically select from top stocks
        top_stocks = sector_stocks[:min(3, len(sector_stocks))]
        if len(top_stocks) == 1:
            return top_stocks[0]
        else:
            # Deterministic selection based on variation seed
            selection_index = variation_seed % len(top_stocks)
            return top_stocks[selection_index]
    
    def _optimize_correlation(self, selected_stocks: List[Dict]) -> List[Dict]:
        """Optimize portfolio by minimizing correlation between selected stocks"""
        if len(selected_stocks) < 2:
            return selected_stocks
        
        try:
            # Calculate correlation matrix
            returns_data = {}
            for stock in selected_stocks:
                if 'returns' in stock and len(stock['returns']) > 0:
                    returns_data[stock['symbol']] = stock['returns']
            
            if len(returns_data) < 2:
                return selected_stocks
            
            # Create returns DataFrame
            returns_df = pd.DataFrame(returns_data)
            correlation_matrix = returns_df.corr()
            
            # Find stocks with lowest average correlation
            avg_correlations = {}
            for symbol in returns_df.columns:
                correlations = correlation_matrix[symbol].drop(symbol)
                avg_correlations[symbol] = correlations.mean()
            
            # Sort stocks by average correlation (ascending)
            sorted_symbols = sorted(avg_correlations.keys(), key=lambda x: avg_correlations[x])
            
            # Reorder selected stocks based on correlation optimization
            optimized_stocks = []
            for symbol in sorted_symbols:
                stock = next(s for s in selected_stocks if s['symbol'] == symbol)
                optimized_stocks.append(stock)
            
            logger.info(f"🔄 Correlation optimization completed. Avg correlation: {avg_correlations[sorted_symbols[0]]:.3f}")
            return optimized_stocks
            
        except Exception as e:
            logger.warning(f"Correlation optimization failed: {e}, returning original selection")
            return selected_stocks
    
    def invalidate_cache(self):
        """Invalidate the stock cache to force fresh data fetch"""
        self._stock_cache = {}
        self._cache_timestamp = None
        logger.info("🗑️ Stock cache invalidated")
    
    def _create_portfolio_allocations(self, selected_stocks: List[Dict], portfolio_size: int) -> List[Dict]:
        """Create portfolio allocations with weights"""
        if not selected_stocks:
            return []
        
        # Calculate weights based on portfolio size
        if portfolio_size == 3:
            # 3-stock portfolio: 40%, 35%, 25%
            weights = [0.40, 0.35, 0.25]
        else:  # 4-stock portfolio
            # 4-stock portfolio: 30%, 25%, 25%, 20%
            weights = [0.30, 0.25, 0.25, 0.20]
        
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
    
    def _get_fallback_portfolio(self, risk_profile: str) -> List[Dict]:
        """Fallback portfolio if selection fails"""
        logger.warning(f"⚠️ Using fallback portfolio for {risk_profile}")
        
        # Fallback portfolios based on risk profile
        fallback_portfolios = {
            'very-conservative': [
                {'symbol': 'JNJ', 'allocation': 40, 'name': 'Johnson & Johnson', 'assetType': 'stock'},
                {'symbol': 'PG', 'allocation': 30, 'name': 'Procter & Gamble', 'assetType': 'stock'},
                {'symbol': 'KO', 'allocation': 20, 'name': 'Coca-Cola', 'assetType': 'stock'},
                {'symbol': 'VZ', 'allocation': 10, 'name': 'Verizon', 'assetType': 'stock'}
            ],
            'conservative': [
                {'symbol': 'JNJ', 'allocation': 35, 'name': 'Johnson & Johnson', 'assetType': 'stock'},
                {'symbol': 'PG', 'allocation': 30, 'name': 'Procter & Gamble', 'assetType': 'stock'},
                {'symbol': 'KO', 'allocation': 25, 'name': 'Coca-Cola', 'assetType': 'stock'},
                {'symbol': 'VZ', 'allocation': 10, 'name': 'Verizon', 'assetType': 'stock'}
            ],
            'moderate': [
                {'symbol': 'AAPL', 'allocation': 30, 'name': 'Apple Inc.', 'assetType': 'stock'},
                {'symbol': 'MSFT', 'allocation': 25, 'name': 'Microsoft', 'assetType': 'stock'},
                {'symbol': 'GOOGL', 'allocation': 25, 'name': 'Alphabet Inc.', 'assetType': 'stock'},
                {'symbol': 'AMZN', 'allocation': 20, 'name': 'Amazon.com', 'assetType': 'stock'}
            ],
            'aggressive': [
                {'symbol': 'NVDA', 'allocation': 35, 'name': 'NVIDIA', 'assetType': 'stock'},
                {'symbol': 'TSLA', 'allocation': 30, 'name': 'Tesla Inc.', 'assetType': 'stock'},
                {'symbol': 'AMD', 'allocation': 20, 'name': 'Advanced Micro Devices', 'assetType': 'stock'},
                {'symbol': 'META', 'allocation': 15, 'name': 'Meta Platforms', 'assetType': 'stock'}
            ],
            'very-aggressive': [
                {'symbol': 'NVDA', 'allocation': 40, 'name': 'NVIDIA', 'assetType': 'stock'},
                {'symbol': 'TSLA', 'allocation': 35, 'name': 'Tesla Inc.', 'assetType': 'stock'},
                {'symbol': 'AMD', 'allocation': 15, 'name': 'Advanced Micro Devices', 'assetType': 'stock'},
                {'symbol': 'META', 'allocation': 10, 'name': 'Meta Platforms', 'assetType': 'stock'}
            ]
        }
        
        return fallback_portfolios.get(risk_profile, fallback_portfolios['moderate'])
    
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
