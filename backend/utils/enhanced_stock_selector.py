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
        Enhanced stock filtering that maximizes pool utilization
        """
        try:
            logger.debug(f"🔍 Enhanced filtering for {risk_profile} (need {portfolio_size} stocks)")
            
            # Step 1: Filter by volatility range
            volatility_range = self.RISK_PROFILE_VOLATILITY[risk_profile]
            volatility_filtered = self._filter_stocks_by_volatility(available_stocks, volatility_range)
            logger.debug(f"  After volatility filtering: {len(volatility_filtered)} stocks")
            
            # Step 2: Apply return-based filtering with flexibility
            if return_target is not None:
                # For return targeting, be more flexible with stock selection
                return_tolerance = 0.05  # 5% tolerance
                
                # Prioritize stocks within return target range
                target_range_stocks = [
                    s for s in volatility_filtered 
                    if s.get('return', 0) >= (return_target - return_tolerance) and 
                       s.get('return', 0) <= (return_target + return_tolerance * 2)
                ]
                
                # If we have enough stocks in target range, use them
                if len(target_range_stocks) >= portfolio_size:
                    logger.debug(f"  Using {len(target_range_stocks)} stocks within return target range")
                    return target_range_stocks
                
                # Otherwise, use all volatility-filtered stocks but prioritize by return potential
                logger.debug(f"  Only {len(target_range_stocks)} stocks in target range, using all {len(volatility_filtered)} stocks")
                return volatility_filtered
            
            # Step 3: Standard filtering (no return target)
            # Filter out negative returns if we have enough positive return stocks
            positive_return_stocks = [s for s in volatility_filtered if s.get('return', 0) > 0]
            
            if len(positive_return_stocks) >= portfolio_size * 2:  # Need 2x portfolio size for good selection
                logger.debug(f"  Using {len(positive_return_stocks)} stocks with positive returns")
                return positive_return_stocks
            elif len(positive_return_stocks) >= portfolio_size:
                logger.debug(f"  Using {len(positive_return_stocks)} positive return stocks (minimum needed)")
                return positive_return_stocks
            else:
                logger.debug(f"  Only {len(positive_return_stocks)} positive return stocks, using all {len(volatility_filtered)} stocks")
                return volatility_filtered
                
        except Exception as e:
            logger.error(f"❌ Enhanced filtering failed: {e}")
            # Fallback to basic volatility filtering
            volatility_range = self.RISK_PROFILE_VOLATILITY[risk_profile]
            return self._filter_stocks_by_volatility(available_stocks, volatility_range)
    
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
            return self._create_simple_allocations(selected_stocks)
    
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
    
    def _create_simple_allocations(self, selected_stocks: List[Dict]) -> List[Dict]:
        """Create varied allocations using 15 diverse allocation templates"""
        if not selected_stocks:
            return []
        
        import random
        
        # 15 diverse allocation templates for different stock counts
        ALLOCATION_TEMPLATES = {
            3: [
                # Balanced patterns
                [35, 35, 30], [40, 30, 30], [30, 40, 30],
                # Concentrated patterns
                [50, 30, 20], [45, 35, 20], [40, 40, 20],
                # Growth-focused patterns
                [60, 25, 15], [55, 30, 15], [50, 35, 15],
                # Conservative patterns
                [40, 30, 30], [35, 35, 30], [30, 35, 35],
                # Specialized patterns
                [45, 30, 25], [40, 35, 25], [35, 40, 25]
            ],
            4: [
                # Equal weight variations
                [25, 25, 25, 25], [30, 25, 25, 20], [25, 30, 25, 20],
                # Balanced concentrated
                [35, 25, 25, 15], [30, 30, 25, 15], [25, 30, 30, 15],
                # Growth-focused
                [40, 25, 20, 15], [35, 30, 20, 15], [30, 35, 20, 15],
                # Conservative spread
                [30, 25, 25, 20], [25, 30, 25, 20], [25, 25, 30, 20],
                # Specialized
                [35, 30, 20, 15], [30, 35, 20, 15], [25, 35, 25, 15]
            ],
            5: [
                # Equal weight
                [20, 20, 20, 20, 20], [25, 20, 20, 20, 15], [20, 25, 20, 20, 15],
                # Balanced
                [30, 20, 20, 15, 15], [25, 25, 20, 15, 15], [20, 25, 25, 15, 15],
                # Concentrated
                [35, 20, 15, 15, 15], [30, 25, 15, 15, 15], [25, 30, 15, 15, 15],
                # Growth-focused
                [40, 20, 15, 15, 10], [35, 25, 15, 15, 10], [30, 30, 15, 15, 10],
                # Conservative
                [25, 20, 20, 20, 15], [20, 25, 20, 20, 15], [20, 20, 25, 20, 15]
            ],
            6: [
                # Equal weight
                [17, 17, 17, 17, 16, 16], [20, 17, 17, 17, 15, 14], [17, 20, 17, 17, 15, 14],
                # Balanced
                [25, 17, 17, 15, 13, 13], [20, 20, 17, 15, 14, 14], [17, 20, 20, 15, 14, 14],
                # Concentrated
                [30, 17, 15, 15, 13, 10], [25, 20, 15, 15, 13, 12], [20, 25, 15, 15, 13, 12],
                # Growth-focused
                [35, 17, 15, 13, 12, 8], [30, 20, 15, 13, 12, 10], [25, 25, 15, 13, 12, 10],
                # Conservative
                [22, 18, 18, 18, 12, 12], [20, 20, 18, 18, 12, 12], [18, 20, 20, 18, 12, 12]
            ]
        }
        
        num_stocks = len(selected_stocks)
        
        # Select appropriate template
        if num_stocks in ALLOCATION_TEMPLATES:
            weights = random.choice(ALLOCATION_TEMPLATES[num_stocks])
        else:
            # Fallback for other stock counts
            base_weight = 100.0 / num_stocks
            weights = []
            for i in range(num_stocks):
                variation = random.uniform(-3, 3)  # ±3% variation
                weight = max(5, min(50, base_weight + variation))  # Keep between 5% and 50%
                weights.append(round(weight, 1))
            
            # Normalize to sum to 100%
            total = sum(weights)
            weights = [round(w * 100 / total, 1) for w in weights]
        
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
