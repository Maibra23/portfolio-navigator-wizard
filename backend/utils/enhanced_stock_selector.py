#!/usr/bin/env python3
"""
Enhanced Stock Selector
Supports enhanced portfolio generation with targeting parameters
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import random
from .portfolio_stock_selector import PortfolioStockSelector
from .dynamic_weighting_system import DynamicWeightingSystem

logger = logging.getLogger(__name__)

class EnhancedStockSelector(PortfolioStockSelector):
    """
    Enhanced Stock Selector that extends PortfolioStockSelector with:
    1. Support for return targeting
    2. Support for diversification targeting
    3. Support for dynamic stock count
    4. Enhanced sector weighting based on targets
    """
    
    def __init__(self, data_service=None):
        super().__init__(data_service)
        
        # Initialize dynamic weighting system
        self.dynamic_weighting = DynamicWeightingSystem()
        
        # Portfolio size mapping (compatibility with parent class)
        self.PORTFOLIO_SIZE = {
            'very-conservative': 4,
            'conservative': 4,
            'moderate': 4,
            'aggressive': 4,
            'very-aggressive': 4
        }
        
        # Enhanced sector categories with return potential mapping
        self.SECTOR_RETURN_POTENTIAL = {
            'technology': {'very-conservative': 0.04, 'conservative': 0.10, 'moderate': 0.13, 'aggressive': 0.20, 'very-aggressive': 0.35},
            'communication': {'very-conservative': 0.05, 'conservative': 0.11, 'moderate': 0.14, 'aggressive': 0.21, 'very-aggressive': 0.32},
            'healthcare': {'very-conservative': 0.06, 'conservative': 0.12, 'moderate': 0.15, 'aggressive': 0.18, 'very-aggressive': 0.28},
            'financial': {'very-conservative': 0.05, 'conservative': 0.09, 'moderate': 0.12, 'aggressive': 0.16, 'very-aggressive': 0.25},
            'consumer_staples': {'very-conservative': 0.06, 'conservative': 0.08, 'moderate': 0.10, 'aggressive': 0.13, 'very-aggressive': 0.18},
            'consumer_discretionary': {'very-conservative': 0.04, 'conservative': 0.09, 'moderate': 0.13, 'aggressive': 0.19, 'very-aggressive': 0.30},
            'industrial': {'very-conservative': 0.05, 'conservative': 0.10, 'moderate': 0.12, 'aggressive': 0.17, 'very-aggressive': 0.26},
            'energy': {'very-conservative': 0.03, 'conservative': 0.08, 'moderate': 0.11, 'aggressive': 0.18, 'very-aggressive': 0.28},
            'utilities': {'very-conservative': 0.06, 'conservative': 0.08, 'moderate': 0.10, 'aggressive': 0.12, 'very-aggressive': 0.16},
            'materials': {'very-conservative': 0.04, 'conservative': 0.09, 'moderate': 0.12, 'aggressive': 0.17, 'very-aggressive': 0.27},
            'real_estate': {'very-conservative': 0.06, 'conservative': 0.09, 'moderate': 0.11, 'aggressive': 0.14, 'very-aggressive': 0.20}
        }
        
        logger.info("🚀 Enhanced Stock Selector initialized")
    
    def get_available_stocks(self, risk_profile: str) -> List[Dict]:
        """Get available stocks for a risk profile - compatibility method"""
        try:
            # Use the portfolio stock selector's method to get stocks with metrics
            from .portfolio_stock_selector import PortfolioStockSelector
            selector = PortfolioStockSelector(self.data_service)
            return selector._get_available_stocks_with_metrics()
        except Exception as e:
            logger.error(f"Error getting available stocks: {e}")
            return []
    
    def select_stocks_for_portfolio(self, risk_profile: str, portfolio_size: int, 
                                  available_stocks: List[Dict] = None,
                                  diversification_target: float = None,
                                  return_target: float = None) -> List[Dict]:
        """
        Enhanced stock selection with targeting support
        
        Args:
            risk_profile: Risk profile for the portfolio
            portfolio_size: Number of stocks to select
            available_stocks: Pre-filtered stock list
            diversification_target: Target diversification score
            return_target: Target return rate
            
        Returns:
            List of stock allocations
        """
        logger.info(f"🔍 Enhanced stock selection for {risk_profile}")
        logger.info(f"  📊 Portfolio size: {portfolio_size}")
        logger.info(f"  🎯 Return target: {return_target:.2%}" if return_target else "  🎯 Return target: None")
        logger.info(f"  🎯 Diversification target: {diversification_target:.1f}" if diversification_target else "  🎯 Diversification target: None")
        
        try:
            # Get available stocks if not provided
            if not available_stocks:
                available_stocks = self._get_available_stocks_with_metrics()
            
            if not available_stocks:
                logger.warning(f"⚠️ No stocks available for {risk_profile}")
                return self._get_fallback_portfolio(risk_profile, portfolio_size)
            
            # IMPROVED: Enhanced stock filtering with better pool utilization
            filtered_stocks = self._enhanced_stock_filtering(
                available_stocks, risk_profile, portfolio_size, return_target
            )
            
            logger.info(f"✅ Enhanced filtering resulted in {len(filtered_stocks)} stocks")
            
            # Use enhanced targeting logic with return prioritization
            selected_stocks = self._select_stocks_with_targeting(
                filtered_stocks, 
                risk_profile, 
                portfolio_size, 
                return_target,
                diversification_target
            )
            
            if not selected_stocks:
                logger.warning(f"⚠️ No stocks selected, using fallback")
                fallback = self._get_fallback_portfolio(risk_profile, portfolio_size)
                logger.warning(f"🔴 FALLBACK USED for {risk_profile} - {len(fallback)} allocations")
                return fallback
            
            # POST-SELECTION VALIDATION: Ensure selected stocks match profile requirements
            volatility_range = self.RISK_PROFILE_VOLATILITY[risk_profile]
            validated_stocks = self._validate_selected_stocks(selected_stocks, risk_profile, volatility_range)
            
            if not validated_stocks or len(validated_stocks) < portfolio_size:
                logger.warning(f"⚠️ Selected stocks failed validation ({len(validated_stocks)}/{portfolio_size}), using fallback")
                fallback = self._get_fallback_portfolio(risk_profile, portfolio_size)
                logger.warning(f"🔴 FALLBACK USED for {risk_profile} - {len(fallback)} allocations")
                return fallback
            
            selected_stocks = validated_stocks
            
            # POST-SELECTION VALIDATION: Ensure selected stocks match profile requirements
            selected_stocks = self._validate_selected_stocks(selected_stocks, risk_profile, volatility_range)
            
            if not selected_stocks:
                logger.warning(f"⚠️ Selected stocks failed validation, using fallback")
                return self._get_fallback_portfolio(risk_profile, portfolio_size)
            
            # FIXED: Use dynamic weighting with flexible return targeting
            allocations = self._create_dynamic_allocations(
                selected_stocks, return_target
            )
            
            logger.info(f"✅ Selected {len(allocations)} stocks for {risk_profile} with dynamic weighting")
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Enhanced stock selection failed: {e}")
            return self._get_fallback_portfolio(risk_profile, portfolio_size)
    
    def _select_stocks_with_targeting(self, stocks: List[Dict], risk_profile: str, 
                                    portfolio_size: int, return_target: float = None,
                                    diversification_target: float = None) -> List[Dict]:
        """Select stocks with enhanced targeting logic"""
        
        # Enable return targeting for better portfolio performance
        if return_target:
            stocks = self._prioritize_stocks_by_return_potential(stocks, risk_profile, return_target)
        
        # Select diversified stocks
        selected_stocks = self._select_diversified_stocks_enhanced(
            stocks, risk_profile, portfolio_size, diversification_target
        )
        
        return selected_stocks
    
    def _enhanced_stock_filtering(self, available_stocks: List[Dict], risk_profile: str, 
                                portfolio_size: int, return_target: float = None) -> List[Dict]:
        """
        Enhanced stock filtering with STRICT volatility range enforcement
        """
        try:
            logger.debug(f"🔍 Enhanced filtering for {risk_profile} (need {portfolio_size} stocks)")
            
            # Step 1: Filter by volatility range - STRICT ENFORCEMENT
            volatility_range = self.RISK_PROFILE_VOLATILITY[risk_profile]
            min_vol, max_vol = volatility_range
            
            # STRICT: Only include stocks within volatility range
            volatility_filtered = []
            for stock in available_stocks:
                stock_vol = stock.get('volatility', 0)
                # Handle both decimal (0.25) and percentage (25.0) formats
                if stock_vol > 1.0:
                    stock_vol = stock_vol / 100
                
                if min_vol <= stock_vol <= max_vol:
                    volatility_filtered.append(stock)
            
            logger.debug(f"  After STRICT volatility filtering ({min_vol:.1%}-{max_vol:.1%}): {len(volatility_filtered)} stocks")
            
            # VALIDATION: Verify all filtered stocks are actually in range
            for stock in volatility_filtered[:5]:  # Check first 5
                stock_vol = stock.get('volatility', 0)
                if stock_vol > 1.0:
                    stock_vol = stock_vol / 100
                if not (min_vol <= stock_vol <= max_vol):
                    logger.error(f"  ⚠️ VALIDATION FAILED: Stock {stock.get('symbol')} has volatility {stock_vol:.1%} outside range {min_vol:.1%}-{max_vol:.1%}")
            
            # Step 2: STRICT: Filter out negative returns - NEVER allow them
            positive_return_stocks = []
            for stock in volatility_filtered:
                stock_return = stock.get('return', 0)
                # Handle both decimal (0.15) and percentage (15.0) formats
                if stock_return > 1.0:
                    stock_return = stock_return / 100
                
                if stock_return > 0:  # STRICT: Must be positive
                    positive_return_stocks.append(stock)
                else:
                    logger.debug(f"  Rejected {stock.get('symbol')}: non-positive return {stock_return:.2%}")
            
            logger.debug(f"  After positive return filtering: {len(positive_return_stocks)} stocks")
            
            if len(positive_return_stocks) < portfolio_size:
                logger.error(
                    f"  ⚠️ INSUFFICIENT POSITIVE RETURN STOCKS: "
                    f"Only {len(positive_return_stocks)}/{len(volatility_filtered)} stocks have positive returns. "
                    f"Need at least {portfolio_size} for portfolio size {portfolio_size}."
                )
                return []  # Return empty - let generation fail rather than create bad portfolio
            
            # Step 3: Apply return-based filtering with profile-specific flexibility
            if return_target is not None:
                # Increase tolerance for higher-risk profiles to allow more diverse stock combinations
                tolerance_map = {
                    'very-conservative': 0.03,   # Keep tight for conservative (3%)
                    'conservative': 0.04,        # Slightly relaxed (4%)
                    'moderate': 0.08,            # Increased tolerance for diversity (8%)
                    'aggressive': 0.08,          # Increased tolerance for diversity (8%)
                    'very-aggressive': 0.10      # Most relaxed for maximum diversity (10%)
                }
                return_tolerance = tolerance_map.get(risk_profile, 0.05)
                
                # Prioritize by return proximity to target
                positive_return_stocks.sort(
                    key=lambda s: abs(s.get('return', 0) - return_target)
                )
                
                logger.debug(f"  Using {len(positive_return_stocks)} stocks, prioritized by return proximity to {return_target:.2%} (tolerance: {return_tolerance:.2%})")
                return positive_return_stocks
            
            # Step 4: Standard filtering (no return target) - already filtered for positive returns
                logger.debug(f"  Using {len(positive_return_stocks)} stocks with positive returns")
                return positive_return_stocks
                
        except Exception as e:
            logger.error(f"❌ Enhanced filtering failed: {e}")
            # Fallback to basic volatility filtering
            volatility_range = self.RISK_PROFILE_VOLATILITY[risk_profile]
            return self._filter_stocks_by_volatility(available_stocks, volatility_range)
    
    def _validate_selected_stocks(self, selected_stocks: List[Dict], risk_profile: str, 
                                  volatility_range: Tuple[float, float]) -> List[Dict]:
        """
        Validate that selected stocks match profile requirements:
        - All stocks within volatility range
        - All stocks have positive returns
        """
        if not selected_stocks:
            return []
        
        min_vol, max_vol = volatility_range
        validated_stocks = []
        
        for stock in selected_stocks:
            # Check volatility
            stock_vol = stock.get('volatility', 0)
            if stock_vol > 1.0:
                stock_vol = stock_vol / 100
            
            if not (min_vol <= stock_vol <= max_vol):
                logger.warning(
                    f"  ⚠️ Rejected {stock.get('symbol')}: volatility {stock_vol:.1%} "
                    f"outside range {min_vol:.1%}-{max_vol:.1%}"
                )
                continue
            
            # Check return
            stock_return = stock.get('return', 0)
            if stock_return > 1.0:
                stock_return = stock_return / 100
            
            if stock_return <= 0:
                logger.warning(
                    f"  ⚠️ Rejected {stock.get('symbol')}: non-positive return {stock_return:.2%}"
                )
                continue
            
            validated_stocks.append(stock)
        
        if len(validated_stocks) < len(selected_stocks):
            logger.warning(
                f"  ⚠️ Validation removed {len(selected_stocks) - len(validated_stocks)} stocks "
                f"({len(validated_stocks)}/{len(selected_stocks)} remain)"
            )
        
        return validated_stocks
    
    def _create_dynamic_allocations(self, selected_stocks: List[Dict], 
                                  return_target: float) -> List[Dict]:
        """Create allocations using dynamic weighting system with flexible return targeting"""
        try:
            if not selected_stocks:
                return []
            
            # Check if we have limited stock availability (less than 5 stocks)
            limited_availability = len(selected_stocks) < 5
            
            # Calculate optimal weights using dynamic weighting system
            optimal_weights, optimization_results = self.dynamic_weighting.calculate_optimal_weights(
                selected_stocks, return_target, limited_availability=limited_availability
            )
            
            # Create allocations with dynamic weights
            allocations = []
            for i, stock in enumerate(selected_stocks):
                weight = optimal_weights[i] if i < len(optimal_weights) else 1.0 / len(selected_stocks)
                allocations.append({
                    'symbol': stock.get('symbol', 'UNKNOWN'),
                    'allocation': round(weight * 100, 1)  # Convert to percentage
                })
            
            # Validate weights
            validation = self.dynamic_weighting.validate_weights(optimal_weights)
            if not validation['valid']:
                logger.warning(f"⚠️ Weight validation issues: {validation['issues']}")
            
            logger.debug(f"  📊 Dynamic weighting results:")
            logger.debug(f"    Portfolio return: {optimization_results.get('portfolio_return', 0):.2%}")
            logger.debug(f"    Portfolio risk: {optimization_results.get('portfolio_risk', 0):.2%}")
            logger.debug(f"    Return deviation: {optimization_results.get('return_deviation', 0):.3f}")
            logger.debug(f"    Tolerance used: {optimization_results.get('tolerance_used', 0):.1%}")
            logger.debug(f"    Above target stocks: {optimization_results.get('above_target_stocks', 0)}")
            logger.debug(f"    Below target stocks: {optimization_results.get('below_target_stocks', 0)}")
            
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Dynamic allocation creation failed: {e}")
            # Fallback to simple equal weights
            return self._create_simple_allocations(selected_stocks, portfolio_index)
    
    def _prioritize_stocks_by_return_potential(self, stocks: List[Dict], 
                                             risk_profile: str, return_target: float) -> List[Dict]:
        """Prioritize stocks from sectors that can achieve the return target"""
        
        # Calculate sector weights based on return potential
        sector_weights = {}
        for sector, potential_map in self.SECTOR_RETURN_POTENTIAL.items():
            sector_potential = potential_map.get(risk_profile, 0.10)
            
            # Higher weight for sectors closer to target return
            weight = max(0.1, 1.0 - abs(sector_potential - return_target))
            sector_weights[sector] = weight
        
        # Sort stocks by sector weight and return potential
        for stock in stocks:
            sector = stock.get('sector', 'Unknown')
            sector_weight = sector_weights.get(sector, 0.1)
            
            # Get individual stock return potential (use actual returns from cache)
            stock_return = stock.get('annualized_return', stock.get('annual_return', 0.10))
            if stock_return is None or stock_return == 0:
                # Fallback: calculate from price data if available
                if 'prices' in stock and stock['prices']:
                    try:
                        import pandas as pd
                        import numpy as np
                        prices = stock['prices']
                        if isinstance(prices, dict):
                            prices = pd.Series(prices)
                            prices.index = pd.to_datetime(prices.index)
                            prices = prices.sort_index()
                        elif isinstance(prices, list):
                            prices = pd.Series(prices)
                        
                        if len(prices) > 1:
                            returns = prices.pct_change().dropna()
                            monthly_return = returns.mean()
                            stock_return = (1 + monthly_return) ** 12 - 1
                        else:
                            stock_return = 0.10  # Default 10%
                    except:
                        stock_return = 0.10  # Default 10%
            
            return_score = max(0.1, 1.0 - abs(stock_return - return_target))
            
            # Combined score: sector weight + individual return score
            stock['targeting_score'] = sector_weight * 0.6 + return_score * 0.4
        
        # Sort by targeting score (descending)
        stocks.sort(key=lambda x: x.get('targeting_score', 0.1), reverse=True)
        
        logger.debug(f"  📈 Prioritized {len(stocks)} stocks by return potential")
        return stocks
    
    def _select_diversified_stocks_enhanced(self, stocks: List[Dict], risk_profile: str, 
                                          portfolio_size: int, diversification_target: float = None) -> List[Dict]:
        """Enhanced diversified stock selection with targeting support"""
        
        selected_stocks = []
        sector_count = defaultdict(int)
        
        # Group stocks by sector
        stocks_by_sector = defaultdict(list)
        for stock in stocks:
            sector = stock.get('sector', 'Unknown')
            if sector != 'Unknown':
                stocks_by_sector[sector].append(stock)
        
        # Calculate optimal sector distribution based on diversification target
        if diversification_target:
            sector_distribution = self._calculate_optimal_sector_distribution(
                len(stocks_by_sector), portfolio_size, diversification_target
            )
        else:
            # Default distribution
            sector_distribution = {sector: 1 for sector in list(stocks_by_sector.keys())[:portfolio_size]}
        
        # Select stocks from each sector
        for sector, target_count in sector_distribution.items():
            if len(selected_stocks) >= portfolio_size:
                break
                
            if sector in stocks_by_sector:
                sector_stocks = stocks_by_sector[sector]
                
                # Sort by targeting score if available
                if sector_stocks and 'targeting_score' in sector_stocks[0]:
                    sector_stocks.sort(key=lambda x: x.get('targeting_score', 0), reverse=True)
                
                # Select best stocks from this sector
                for _ in range(min(target_count, len(sector_stocks))):
                    if len(selected_stocks) >= portfolio_size:
                        break
                    
                    stock = sector_stocks.pop(0)
                    selected_stocks.append(stock)
                    sector_count[sector] += 1
        
        # If we need more stocks, fill from remaining stocks
        remaining_stocks = [s for stock_list in stocks_by_sector.values() for s in stock_list]
        remaining_stocks = [s for s in remaining_stocks if s not in selected_stocks]
        
        while len(selected_stocks) < portfolio_size and remaining_stocks:
            # Sort by targeting score if available
            if remaining_stocks and 'targeting_score' in remaining_stocks[0]:
                remaining_stocks.sort(key=lambda x: x.get('targeting_score', 0), reverse=True)
            
            stock = remaining_stocks.pop(0)
            selected_stocks.append(stock)
        
        logger.debug(f"  🎯 Selected {len(selected_stocks)} stocks from {len(set(s.get('sector', 'Unknown') for s in selected_stocks))} sectors")
        return selected_stocks
    
    def _calculate_optimal_sector_distribution(self, available_sectors: int, 
                                             portfolio_size: int, diversification_target: float) -> Dict[str, int]:
        """Calculate optimal sector distribution based on diversification target"""
        
        # Higher diversification target = more sectors, fewer stocks per sector
        # Lower diversification target = fewer sectors, more stocks per sector
        
        if diversification_target >= 90:
            # High diversification: use many sectors, 1-2 stocks per sector
            sectors_to_use = min(available_sectors, portfolio_size)
            stocks_per_sector = max(1, portfolio_size // sectors_to_use)
            remainder = portfolio_size % sectors_to_use
            
        elif diversification_target >= 75:
            # Medium-high diversification: balanced approach
            sectors_to_use = min(available_sectors, max(3, portfolio_size // 2))
            stocks_per_sector = max(1, portfolio_size // sectors_to_use)
            remainder = portfolio_size % sectors_to_use
            
        else:
            # Lower diversification: fewer sectors, more concentration
            sectors_to_use = min(available_sectors, max(2, portfolio_size // 3))
            stocks_per_sector = max(1, portfolio_size // sectors_to_use)
            remainder = portfolio_size % sectors_to_use
        
        # Create distribution
        distribution = {}
        sector_names = list(range(sectors_to_use))  # Use indices as sector names
        
        for i, sector in enumerate(sector_names):
            count = stocks_per_sector
            if i < remainder:  # Distribute remainder stocks
                count += 1
            distribution[f'sector_{sector}'] = count
        
        return distribution
    
    def _create_enhanced_allocations(self, selected_stocks: List[Dict], portfolio_size: int,
                                   return_target: float = None, diversification_target: float = None) -> List[Dict]:
        """Create enhanced allocations with targeting-aware weighting"""
        
        if not selected_stocks:
            return []
        
        # Enhanced weight templates based on targeting
        if diversification_target and diversification_target >= 90:
            # High diversification: more balanced weights
            weight_templates = [
                [0.30, 0.25, 0.25, 0.20],  # Balanced
                [0.35, 0.25, 0.20, 0.20],  # Slightly top-heavy
                [0.25, 0.25, 0.25, 0.25],  # Equal weights
            ]
        elif diversification_target and diversification_target >= 75:
            # Medium diversification: moderate concentration
            weight_templates = [
                [0.40, 0.30, 0.30],        # 3 stocks
                [0.35, 0.30, 0.20, 0.15],  # 4 stocks
                [0.45, 0.35, 0.20],        # 3 stocks concentrated
            ]
        else:
            # Lower diversification: more concentrated
            weight_templates = [
                [0.50, 0.30, 0.20],        # 3 stocks concentrated
                [0.45, 0.35, 0.20],        # 3 stocks
                [0.40, 0.30, 0.20, 0.10],  # 4 stocks concentrated
            ]
        
        # Select appropriate template based on portfolio size
        template = None
        for t in weight_templates:
            if len(t) == len(selected_stocks):
                template = t
                break
        
        # Fallback: create equal weights
        if not template:
            template = [1.0 / len(selected_stocks)] * len(selected_stocks)
        
        # Adjust weights if we have return targeting
        if return_target:
            template = self._adjust_weights_for_return_target(selected_stocks, template, return_target)
        
        # Create allocations
        allocations = []
        for i, stock in enumerate(selected_stocks):
            weight = template[i] if i < len(template) else template[-1]
            allocation = {
                'symbol': stock.get('ticker', stock.get('symbol', 'UNKNOWN')),
                'allocation': round(weight * 100, 1)  # Convert to percentage
            }
            allocations.append(allocation)
        
        # Ensure allocations sum to 100%
        total_allocation = sum(a['allocation'] for a in allocations)
        if total_allocation != 100.0:
            # Adjust the last allocation to make it sum to 100%
            allocations[-1]['allocation'] = round(100.0 - sum(a['allocation'] for a in allocations[:-1]), 1)
        
        logger.debug(f"  📊 Created allocations: {[a['allocation'] for a in allocations]}")
        return allocations
    
    def _adjust_weights_for_return_target(self, selected_stocks: List[Dict], 
                                        template: List[float], return_target: float) -> List[float]:
        """Adjust weights to favor stocks closer to return target"""
        
        # Calculate return scores for each stock
        return_scores = []
        for stock in selected_stocks:
            stock_return = stock.get('annualized_return', stock.get('annual_return', 0.10))
            # Higher score for stocks closer to target
            score = max(0.1, 1.0 - abs(stock_return - return_target))
            return_scores.append(score)
        
        # Normalize scores
        total_score = sum(return_scores)
        if total_score > 0:
            return_scores = [score / total_score for score in return_scores]
        else:
            return_scores = template  # Use original template if no scores
        
        # Blend with original template (70% targeting, 30% original)
        adjusted_weights = []
        for i in range(len(template)):
            adjusted = return_scores[i] * 0.7 + template[i] * 0.3
            adjusted_weights.append(adjusted)
        
        # Normalize to sum to 1.0
        total_weight = sum(adjusted_weights)
        if total_weight > 0:
            adjusted_weights = [w / total_weight for w in adjusted_weights]
        
        return adjusted_weights
    
    def _get_fallback_portfolio(self, risk_profile: str, portfolio_size: int) -> List[Dict]:
        """Get fallback portfolio with appropriate size"""
        
        # Common fallback stocks by risk profile
        fallback_stocks = {
            'very-conservative': ['PG', 'JNJ', 'KO', 'WMT', 'MCD', 'PEP'],
            'conservative': ['AAPL', 'MSFT', 'JNJ', 'PG', 'KO', 'V'],
            'moderate': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA'],
            'aggressive': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMD'],
            'very-aggressive': ['TSLA', 'NVDA', 'AMD', 'NFLX', 'ZM', 'ROKU']
        }
        
        symbols = fallback_stocks.get(risk_profile, ['AAPL', 'MSFT', 'GOOGL'])
        symbols = symbols[:portfolio_size]  # Take only what we need
        
        # Equal weight allocation
        weight = 100.0 / len(symbols)
        allocations = [{'symbol': symbol, 'allocation': round(weight, 1)} for symbol in symbols]
        
        # Adjust last allocation to ensure sum is 100%
        if allocations:
            total = sum(a['allocation'] for a in allocations[:-1])
            allocations[-1]['allocation'] = round(100.0 - total, 1)
        
        logger.warning(f"⚠️ Using fallback portfolio: {[a['symbol'] for a in allocations]}")
        return allocations
    
    def _create_simple_allocations(self, selected_stocks: List[Dict], portfolio_index: int = None) -> List[Dict]:
        """Create allocations using expanded template system with 15-20 templates per stock count"""
        if not selected_stocks:
            return []
        
        import random
        import time
        
        num_stocks = len(selected_stocks)
        
        # Expanded allocation templates for 3 and 4 stock portfolios
        ALLOCATION_TEMPLATES = {
            3: [
                # Equal weight variations
                [33, 33, 34], [34, 33, 33], [33, 34, 33], [33.3, 33.3, 33.4],
                # Balanced patterns
                [35, 35, 30], [40, 30, 30], [30, 40, 30], [38, 32, 30], [32, 38, 30],
                # Concentrated patterns
                [50, 30, 20], [45, 35, 20], [40, 40, 20], [48, 28, 24], [42, 38, 20],
                # Growth-focused patterns
                [60, 25, 15], [55, 30, 15], [50, 35, 15], [58, 28, 14], [52, 32, 16],
                # Conservative patterns
                [36, 32, 32], [34, 34, 32], [32, 36, 32],
                # Specialized patterns
                [45, 30, 25], [40, 35, 25], [35, 40, 25], [43, 32, 25], [37, 38, 25]
            ],
            4: [
                # Equal weight variations
                [25, 25, 25, 25], [26, 25, 25, 24], [25, 26, 25, 24], [25, 25, 26, 24],
                # Balanced concentrated
                [35, 25, 25, 15], [30, 30, 25, 15], [25, 30, 30, 15], [32, 28, 25, 15], [28, 32, 25, 15],
                # Growth-focused
                [40, 25, 20, 15], [35, 30, 20, 15], [30, 35, 20, 15], [38, 27, 20, 15], [33, 32, 20, 15],
                # Conservative spread
                [30, 25, 25, 20], [25, 30, 25, 20], [25, 25, 30, 20], [28, 27, 25, 20], [27, 28, 25, 20],
                # Specialized
                [35, 30, 20, 15], [30, 35, 20, 15], [25, 35, 25, 15], [33, 32, 20, 15], [28, 37, 20, 15],
                # High concentration
                [45, 20, 18, 17], [50, 20, 15, 15], [42, 22, 18, 18], [48, 18, 17, 17]
            ]
        }
        
        # Only support 3 and 4 stock portfolios
        if num_stocks not in [3, 4]:
            # Fallback to equal weight for unexpected stock counts
            base_weight = 100.0 / num_stocks
            weights = [round(base_weight, 1) for _ in range(num_stocks)]
            # Adjust last weight to ensure sum is 100
            total = sum(weights[:-1])
            weights[-1] = round(100.0 - total, 1)
        else:
            # Use portfolio_index and current time for truly random selection
            if portfolio_index is not None:
                # Create unique seed based on portfolio index and current time
                seed_value = int(time.time() * 1000000) + (portfolio_index * 12345) + num_stocks * 789
                random.seed(seed_value)
            
            # Select random template from expanded pool
            templates = ALLOCATION_TEMPLATES.get(num_stocks, [])
            if templates:
                weights = list(random.choice(templates))
            else:
                # Fallback to equal weight if no templates available
                base_weight = 100.0 / num_stocks
                weights = [round(base_weight, 1) for _ in range(num_stocks)]
            
            # Normalize to sum to exactly 100%
            total = sum(weights)
            if abs(total - 100.0) > 0.1:
                # Adjust weights proportionally
                factor = 100.0 / total
                weights = [round(w * factor, 1) for w in weights]
            
            # Final adjustment to ensure exact sum
            total = sum(weights)
            diff = 100.0 - total
            if abs(diff) > 0.01:
                # Add/subtract from largest weight to fix rounding
                max_idx = weights.index(max(weights))
                weights[max_idx] = round(weights[max_idx] + diff, 1)
        
        # Create allocations
        allocations = []
        for i, stock in enumerate(selected_stocks):
            allocation = {
                'symbol': stock.get('ticker', stock.get('symbol', 'UNKNOWN')),
                'allocation': weights[i],
                'sector': stock.get('sector', 'Unknown')  # FIXED: Preserve sector information
            }
            allocations.append(allocation)
        
        # Ensure sum is exactly 100%
        total = sum(a['allocation'] for a in allocations)
        if abs(total - 100.0) > 0.1:
            diff = 100.0 - total
            allocations[-1]['allocation'] = round(allocations[-1]['allocation'] + diff, 1)
        
        return allocations
