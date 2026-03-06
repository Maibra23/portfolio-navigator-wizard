#!/usr/bin/env python3
"""
Strategy Portfolio Optimizer
Generates strategy-specific portfolios with Pure vs Personalized variants
"""

import logging
import random
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from .portfolio_stock_selector import PortfolioStockSelector
from .port_analytics import PortfolioAnalytics
from .redis_portfolio_manager import RedisPortfolioManager

logger = logging.getLogger(__name__)

class StrategyPortfolioOptimizer:
    """Generates strategy-specific portfolios with Pure vs Personalized variants
    
    Optimized version with:
    - Stock pool caching (loads all tickers once)
    - Pre-generation support
    - Redis storage and retrieval
    - Fast cache-first operation
    """
    
    def __init__(self, data_service=None, redis_manager=None):
        self.data_service = data_service
        self.redis_manager = redis_manager
        self.stock_selector = PortfolioStockSelector(data_service) if data_service else None
        self.portfolio_analytics = PortfolioAnalytics()
        
        # Strategy configuration
        self.STRATEGIES = {
            'diversification': {'name': 'Diversification', 'description': 'Low correlation, balanced sector exposure'},
            'risk': {'name': 'Risk Minimization', 'description': 'Low volatility, defensive positioning'},
            'return': {'name': 'Return Maximization', 'description': 'High expected return, growth focus'}
        }
        
        # Risk profile constraints
        self.RISK_PROFILE_CONSTRAINTS = {
            'very-conservative': {'max_volatility': 0.22, 'max_single_stock_weight': 0.30, 'min_sectors': 4},
            'conservative': {'max_volatility': 0.26, 'max_single_stock_weight': 0.35, 'min_sectors': 4},
            'moderate': {'max_volatility': 0.32, 'max_single_stock_weight': 0.40, 'min_sectors': 3},
            'aggressive': {'max_volatility': 0.42, 'max_single_stock_weight': 0.45, 'min_sectors': 3},
            'very-aggressive': {'max_volatility': 1.0, 'max_single_stock_weight': 0.50, 'min_sectors': 3}
        }
        
        self.PORTFOLIOS_PER_STRATEGY = 6  # Generate 6 portfolios per strategy for better variety
        
        # Stock pool caching - loads all stocks once
        self._stock_pool_cache = None
        self._cache_timestamp = None
        self._cache_ttl_seconds = 3600  # 1 hour TTL
    
    def generate_strategy_portfolio_buckets(self, strategy: str, risk_profiles: List[str] = None) -> Dict:
        """Generate complete strategy portfolio buckets for all risk profiles"""
        if risk_profiles is None:
            risk_profiles = list(self.RISK_PROFILE_CONSTRAINTS.keys())
        
        logger.info(f"🚀 Generating strategy portfolio buckets for '{strategy}' strategy")
        
        try:
            # Generate Pure Strategy portfolios (no risk profile constraints)
            pure_portfolios = self._generate_pure_strategy_portfolios(strategy)
            
            # Generate Personalized Strategy portfolios for each risk profile
            personalized_portfolios = {}
            for risk_profile in risk_profiles:
                personalized_portfolios[risk_profile] = self._generate_personalized_strategy_portfolios(
                    strategy, risk_profile
                )
            
            # Create metadata and structure result
            metadata = self._create_strategy_metadata(strategy, risk_profiles, pure_portfolios, personalized_portfolios)
            result = {
                'pure': {strategy: pure_portfolios},
                'personalized': personalized_portfolios,
                'metadata': metadata
            }
            
            logger.info(f"✅ Successfully generated strategy buckets for '{strategy}'")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to generate strategy portfolio buckets: {e}")
            raise
    
    def _generate_pure_strategy_portfolios(self, strategy: str) -> List[Dict]:
        """Generate Pure Strategy portfolios with NO risk profile constraints"""
        logger.info(f"🔓 Generating Pure Strategy portfolios for '{strategy}' (unconstrained)")
        
        portfolios = []
        strategy_config = self.STRATEGIES[strategy]
        used_compositions = set()  # Enforce unique ticker compositions within pure set
        
        for portfolio_id in range(self.PORTFOLIOS_PER_STRATEGY):
            try:
                # Retry a few times to avoid duplicate compositions
                success = False
                for attempt in range(5):
                    seed = self._generate_strategy_seed(strategy, portfolio_id + attempt * 13, is_pure=True)
                    random.seed(seed)
                    
                    selected_stocks = self._select_stocks_for_strategy_pure(strategy, portfolio_id + attempt)
                    if not selected_stocks:
                        continue
                    
                    allocations = self._create_strategy_allocations(selected_stocks, strategy, is_pure=True, portfolio_id=portfolio_id + attempt)
                    # Enforce ETF / Unknown sector filtering defensively
                    allocations = [a for a in allocations if a.get('sector') not in (None, 'Unknown')]
                    # Composition key
                    comp = tuple(sorted(a.get('symbol') for a in allocations))
                    if comp and comp not in used_compositions and len(comp) >= 2:
                        used_compositions.add(comp)
                        metrics = self._calculate_strategy_portfolio_metrics(allocations, strategy)
                        portfolio = {
                            'id': f"pure_{strategy}_{portfolio_id}",
                            'name': f"Pure {strategy_config['name']} Portfolio {portfolio_id + 1}",
                            'description': f"Unconstrained {strategy_config['description']} portfolio",
                            'strategy': strategy,
                            'type': 'pure',
                            'risk_profile': None,
                            'allocations': allocations,
                            'metrics': metrics,
                            'generated_at': datetime.now().isoformat(),
                            'constraints_applied': 'none'
                        }
                        portfolios.append(portfolio)
                        success = True
                        break
                if not success:
                    logger.warning(f"⚠️ Could not generate unique composition for pure {strategy} portfolio {portfolio_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to generate Pure Strategy portfolio {portfolio_id}: {e}")
                continue
        
        logger.info(f"✅ Generated {len(portfolios)} Pure Strategy portfolios for '{strategy}'")
        return portfolios
    
    def _generate_personalized_strategy_portfolios(self, strategy: str, risk_profile: str) -> List[Dict]:
        """Generate Personalized Strategy portfolios with risk profile constraints"""
        logger.info(f"🎯 Generating Personalized Strategy portfolios for '{strategy}' + '{risk_profile}'")
        
        portfolios = []
        strategy_config = self.STRATEGIES[strategy]
        risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
        
        for portfolio_id in range(self.PORTFOLIOS_PER_STRATEGY):
            try:
                seed = self._generate_strategy_seed(strategy, portfolio_id, is_pure=False, risk_profile=risk_profile)
                random.seed(seed)
                
                selected_stocks = self._select_stocks_for_strategy_personalized(strategy, risk_profile, portfolio_id)
                if not selected_stocks:
                    continue
                
                allocations = self._create_strategy_allocations(selected_stocks, strategy, is_pure=False, risk_profile=risk_profile, portfolio_id=portfolio_id)
                metrics = self._calculate_strategy_portfolio_metrics(allocations, strategy)
                
                portfolio = {
                    'id': f"personalized_{strategy}_{risk_profile}_{portfolio_id}",
                    'name': f"Personalized {strategy_config['name']} Portfolio {portfolio_id + 1}",
                    'description': f"{strategy_config['description']} portfolio adjusted for {risk_profile} risk profile",
                    'strategy': strategy,
                    'type': 'personalized',
                    'risk_profile': risk_profile,
                    'allocations': allocations,
                    'metrics': metrics,
                    'generated_at': datetime.now().isoformat(),
                    'constraints_applied': f"strategy_{strategy}_risk_{risk_profile}"
                }
                
                portfolios.append(portfolio)
                
            except Exception as e:
                logger.error(f"❌ Failed to generate Personalized Strategy portfolio {portfolio_id}: {e}")
                continue
        
        logger.info(f"✅ Generated {len(portfolios)} Personalized Strategy portfolios for '{strategy}' + '{risk_profile}'")
        return portfolios
    
    def _select_stocks_for_strategy_pure(self, strategy: str, portfolio_id: int) -> List[Dict]:
        """Select stocks for Pure Strategy portfolio (no risk profile constraints)"""
        try:
            available_stocks = self._get_available_stocks()
            if not available_stocks:
                return []
            
            # FIRST: Filter out negative returns
            available_stocks = self._filter_negative_returns(available_stocks)
            if not available_stocks:
                logger.warning(f"⚠️ No stocks with positive returns available for {strategy} strategy")
                return []
            
            if strategy == 'diversification':
                return self._filter_for_diversification_pure(available_stocks, portfolio_id)
            elif strategy == 'risk':
                return self._filter_for_risk_pure(available_stocks, portfolio_id)
            elif strategy == 'return':
                return self._filter_for_return_pure(available_stocks, portfolio_id)
            else:
                logger.error(f"❌ Unknown strategy: {strategy}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error selecting stocks for Pure Strategy: {e}")
            return []
    
    def _select_stocks_for_strategy_personalized(self, strategy: str, risk_profile: str, portfolio_id: int) -> List[Dict]:
        """Select stocks for Personalized Strategy portfolio (with risk profile constraints)"""
        try:
            available_stocks = self._get_available_stocks()
            if not available_stocks:
                return []
            
            constrained_stocks = self._apply_risk_profile_constraints(available_stocks, risk_profile)
            
            if strategy == 'diversification':
                return self._filter_for_diversification_personalized(constrained_stocks, risk_profile, portfolio_id)
            elif strategy == 'risk':
                return self._filter_for_risk_personalized(constrained_stocks, risk_profile, portfolio_id)
            elif strategy == 'return':
                return self._filter_for_return_personalized(constrained_stocks, risk_profile, portfolio_id)
            else:
                logger.error(f"❌ Unknown strategy: {strategy}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error selecting stocks for Personalized Strategy: {e}")
            return []
    
    def _filter_for_diversification_pure(self, stocks: List[Dict], portfolio_id: int) -> List[Dict]:
        """Filter stocks for Pure Diversification strategy"""
        try:
            df = pd.DataFrame(stocks)
            if 'sector' not in df.columns:
                return self._select_diversified_stocks_basic(df.to_dict('records'), 5)
            
            if 'volatility' in df.columns:
                df = df[df['volatility'] <= 0.8]
            
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id, 3, 'diversification')
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in Pure Diversification filtering: {e}")
            return self._select_diversified_stocks_basic(stocks, 5)
    
    def _filter_for_risk_pure(self, stocks: List[Dict], portfolio_id: int) -> List[Dict]:
        """Filter stocks for Pure Risk strategy"""
        try:
            df = pd.DataFrame(stocks)
            
            if 'volatility' in df.columns:
                volatility_threshold = df['volatility'].quantile(0.3)
                df = df[df['volatility'] <= volatility_threshold]
            
            defensive_sectors = ['utilities', 'consumer_staples', 'healthcare', 'real_estate']
            df['defensive_score'] = df['sector'].apply(
                lambda x: 1 if any(def_sector in str(x).lower() for def_sector in defensive_sectors) else 0
            )
            
            df = df.sort_values(['defensive_score', 'volatility'], ascending=[False, True])
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id, 3, 'risk')
            
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in Pure Risk filtering: {e}")
            return self._select_diversified_stocks_basic(stocks, 5)
    
    def _filter_for_return_pure(self, stocks: List[Dict], portfolio_id: int) -> List[Dict]:
        """Filter stocks for Pure Return strategy"""
        try:
            df = pd.DataFrame(stocks)
            
            # Ensure no negative returns (already filtered, but double-check)
            if 'expected_return' in df.columns:
                df = df[df['expected_return'] > 0]
                if len(df) == 0:
                    logger.warning("⚠️ No stocks with positive returns after filtering")
                    return []
            
            if 'expected_return' in df.columns:
                return_threshold = df['expected_return'].quantile(0.6)
                df = df[df['expected_return'] >= return_threshold]
            
            growth_sectors = ['technology', 'healthcare', 'consumer_discretionary', 'communication']
            df['growth_score'] = df['sector'].apply(
                lambda x: 1 if any(growth_sector in str(x).lower() for growth_sector in growth_sectors) else 0
            )
            
            df = df.sort_values(['growth_score', 'expected_return'], ascending=[False, False])
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id, 3, 'return')
            
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in Pure Return filtering: {e}")
            return self._select_diversified_stocks_basic(stocks, 5)
    
    def _filter_for_diversification_personalized(self, stocks: List[Dict], risk_profile: str, portfolio_id: int) -> List[Dict]:
        """Filter stocks for Personalized Diversification strategy"""
        try:
            df = pd.DataFrame(stocks)
            risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
            
            if 'volatility' in df.columns:
                max_vol = risk_constraints['max_volatility']
                df = df[df['volatility'] <= max_vol]
            
            min_sectors = risk_constraints['min_sectors']
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id, min_sectors, 'diversification')
            
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in Personalized Diversification filtering: {e}")
            return self._select_diversified_stocks_basic(stocks, 5)
    
    def _filter_for_risk_personalized(self, stocks: List[Dict], risk_profile: str, portfolio_id: int) -> List[Dict]:
        """Filter stocks for Personalized Risk strategy"""
        try:
            df = pd.DataFrame(stocks)
            risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
            
            if 'volatility' in df.columns:
                max_vol = risk_constraints['max_volatility']
                df = df[df['volatility'] <= max_vol]
            
            defensive_sectors = ['utilities', 'consumer_staples', 'healthcare', 'real_estate']
            df['defensive_score'] = df['sector'].apply(
                lambda x: 1 if any(def_sector in str(x).lower() for def_sector in defensive_sectors) else 0
            )
            
            df = df.sort_values(['defensive_score', 'volatility'], ascending=[False, True])
            min_sectors = risk_constraints['min_sectors']
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id, min_sectors, 'risk')
            
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in Personalized Risk filtering: {e}")
            return self._select_diversified_stocks_basic(stocks, 5)
    
    def _filter_for_return_personalized(self, stocks: List[Dict], risk_profile: str, portfolio_id: int) -> List[Dict]:
        """Filter stocks for Personalized Return strategy"""
        try:
            df = pd.DataFrame(stocks)
            risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
            
            # Ensure no negative returns (already filtered, but double-check)
            if 'expected_return' in df.columns:
                df = df[df['expected_return'] > 0]
                if len(df) == 0:
                    logger.warning("⚠️ No stocks with positive returns after filtering")
                    return []
            
            if 'volatility' in df.columns:
                max_vol = risk_constraints['max_volatility']
                df = df[df['volatility'] <= max_vol]
            
            if 'expected_return' in df.columns:
                return_threshold = df['expected_return'].quantile(0.5)
                df = df[df['expected_return'] >= return_threshold]
            
            growth_sectors = ['technology', 'healthcare', 'consumer_discretionary', 'communication']
            df['growth_score'] = df['sector'].apply(
                lambda x: 1 if any(growth_sector in str(x).lower() for growth_sector in growth_sectors) else 0
            )
            
            df = df.sort_values(['growth_score', 'expected_return'], ascending=[False, False])
            min_sectors = risk_constraints['min_sectors']
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id, min_sectors, 'return')
            
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in Personalized Return filtering: {e}")
            return self._select_diversified_stocks_basic(stocks, 5)
    
    def _filter_negative_returns(self, stocks: List[Dict]) -> List[Dict]:
        """Filter out stocks with negative expected returns - STRICT NO NEGATIVE RETURNS"""
        if not stocks:
            return []
        
        try:
            # Filter out any stock with negative or zero expected return
            positive_return_stocks = [
                s for s in stocks 
                if s.get('expected_return', 0) > 0
            ]
            
            filtered_count = len(stocks) - len(positive_return_stocks)
            if filtered_count > 0:
                logger.info(f"🚫 Filtered out {filtered_count} stocks with non-positive returns")
            
            return positive_return_stocks
            
        except Exception as e:
            logger.error(f"❌ Error filtering negative returns: {e}")
            return stocks
    
    def _apply_risk_profile_constraints(self, stocks: List[Dict], risk_profile: str) -> List[Dict]:
        """Apply risk profile constraints to stock selection"""
        try:
            # FIRST: Filter out negative returns
            stocks = self._filter_negative_returns(stocks)
            
            risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
            df = pd.DataFrame(stocks)
            
            if 'volatility' in df.columns:
                max_vol = risk_constraints['max_volatility']
                df = df[df['volatility'] <= max_vol]
            
            logger.debug(f"✅ Applied risk profile constraints for {risk_profile}: {len(df)} stocks remain")
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"❌ Error applying risk profile constraints: {e}")
            return stocks
    
    def _select_diversified_stocks_by_sector(self, df: pd.DataFrame, count: int, portfolio_id: int, min_sectors: int = 3, strategy: str = 'diversification') -> List[Dict]:
        """Select stocks ensuring sector diversity"""
        if len(df) < count:
            return df.to_dict('records')
        
        try:
            # Use portfolio_id as seed for deterministic but diverse selection
            random.seed(portfolio_id)
            
            # Shuffle sectors to get variety across portfolios
            sectors = df['sector'].unique()
            sectors = list(sectors)
            random.shuffle(sectors)
            if len(sectors) < min_sectors:
                min_sectors = len(sectors)
            
            selected_stocks = []
            sectors_per_stock = max(1, count // min_sectors)
            
            for sector in sectors[:min_sectors]:
                sector_stocks = df[df['sector'] == sector]
                if len(sector_stocks) > 0:
                    # Shuffle and select to get variety
                    sector_list = sector_stocks.to_dict('records')
                    random.shuffle(sector_list)
                    selected_stocks.extend(sector_list[:sectors_per_stock])
            
            if len(selected_stocks) < count:
                # Get symbols of already selected stocks
                selected_symbols = [stock.get('symbol', '') for stock in selected_stocks]
                # Filter out already selected stocks
                remaining_stocks = df[~df['symbol'].isin(selected_symbols)]
                additional_needed = count - len(selected_stocks)
                if len(remaining_stocks) > 0:
                    remaining_list = remaining_stocks.to_dict('records')
                    random.shuffle(remaining_list)
                    selected_stocks.extend(remaining_list[:additional_needed])
            
            selected_stocks = selected_stocks[:count]
            stock_symbols = [s.get('symbol', 'UNKNOWN') for s in selected_stocks]
            logger.info(f"✅ Selected {len(selected_stocks)} stocks from {min_sectors} sectors: {stock_symbols}")
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in sector-based stock selection: {e}")
            return df.head(count).to_dict('records')
    
    def _select_diversified_stocks_basic(self, stocks: List[Dict], count: int) -> List[Dict]:
        """Basic stock selection when advanced filtering fails"""
        if len(stocks) <= count:
            return stocks
        return stocks[:count]
    
    def _create_strategy_allocations(self, stocks: List[Dict], strategy: str, 
                                   is_pure: bool, risk_profile: str = None, portfolio_id: int = 0) -> List[Dict]:
        """
        Create portfolio allocations using strategy-specific weighting logic.
        
        - Diversification: sector-balanced allocations
        - Risk: inverse-volatility weighting (with risk-profile caps when personalized)
        - Return: return-proportional weighting (with risk-profile caps when personalized)
        
        Falls back to equal-weighted allocations on error.
        """
        if not stocks:
            return []
        
        try:
            # Normalize stock data to ensure required fields are present
            normalized_stocks = []
            for stock in stocks:
                normalized_stock = {
                    'symbol': stock.get('symbol', stock.get('ticker', 'UNKNOWN')),
                    'name': stock.get('name', stock.get('company_name', stock.get('symbol', 'Unknown'))),
                    'sector': stock.get('sector', 'Unknown'),
                    'volatility': stock.get('volatility', 0.2),
                    'expected_return': stock.get('expected_return', stock.get('return', 0.1)),
                }
                normalized_stocks.append(normalized_stock)
            
            # Strategy-specific allocation
            if strategy == 'diversification':
                allocations = self._create_diversification_allocations(normalized_stocks, is_pure, risk_profile)
            elif strategy == 'risk':
                allocations = self._create_risk_allocations(normalized_stocks, is_pure, risk_profile)
            elif strategy == 'return':
                allocations = self._create_return_allocations(normalized_stocks, is_pure, risk_profile)
            else:
                logger.warning(f"⚠️ Unknown strategy '{strategy}', using equal-weight allocations")
                allocations = self._create_equal_allocations(normalized_stocks)
            
            # Validate allocations (sum to 1.0, respect risk constraints when provided)
            if not self._validate_allocations(allocations, risk_profile):
                logger.warning(
                    f"⚠️ Strategy allocations failed validation (total={sum(a['allocation'] for a in allocations):.4f}), "
                    f"falling back to equal-weight allocations"
                )
                return self._create_equal_allocations(normalized_stocks)
            
            logger.info(f"✅ Created allocations using strategy-specific logic for {strategy} strategy ({len(allocations)} stocks)")
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error creating strategy allocations for {strategy}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_equal_allocations(stocks)
    
    def _create_diversification_allocations(self, stocks: List[Dict], is_pure: bool, risk_profile: str = None) -> List[Dict]:
        """Create allocations optimized for diversification strategy"""
        try:
            sector_groups = defaultdict(list)
            for stock in stocks:
                sector = stock.get('sector', 'Unknown')
                sector_groups[sector].append(stock)
            
            num_sectors = len(sector_groups)
            if num_sectors == 0:
                return self._create_equal_allocations(stocks)
            
            sector_weight = 1.0 / num_sectors
            allocations = []
            
            for sector, sector_stocks in sector_groups.items():
                stock_weight = sector_weight / len(sector_stocks)
                for stock in sector_stocks:
                    allocations.append({
                        'symbol': stock.get('symbol', 'UNKNOWN'),
                        'allocation': stock_weight,
                        'sector': sector
                    })
            
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error in diversification allocations: {e}")
            return self._create_equal_allocations(stocks)
    
    def _create_risk_allocations(self, stocks: List[Dict], is_pure: bool, risk_profile: str = None) -> List[Dict]:
        """Create allocations optimized for risk minimization strategy"""
        try:
            sorted_stocks = sorted(stocks, key=lambda x: x.get('volatility', 1.0))
            
            if is_pure:
                total_inverse_vol = sum(1.0 / max(stock.get('volatility', 0.01), 0.01) for stock in sorted_stocks)
                
                allocations = []
                for stock in sorted_stocks:
                    inverse_vol = 1.0 / max(stock.get('volatility', 0.01), 0.01)
                    weight = inverse_vol / total_inverse_vol
                    allocations.append({
                        'symbol': stock.get('symbol', 'UNKNOWN'),
                        'allocation': weight,
                        'sector': stock.get('sector', 'Unknown')
                    })
                
                return allocations
            else:
                return self._create_constrained_risk_allocations(sorted_stocks, risk_profile)
                
        except Exception as e:
            logger.error(f"❌ Error in risk allocations: {e}")
            return self._create_equal_allocations(stocks)
    
    def _create_return_allocations(self, stocks: List[Dict], is_pure: bool, risk_profile: str = None) -> List[Dict]:
        """Create allocations optimized for return maximization strategy"""
        try:
            sorted_stocks = sorted(stocks, key=lambda x: x.get('expected_return', 0.0), reverse=True)
            
            if is_pure:
                total_return = sum(max(stock.get('expected_return', 0.0), 0.0) for stock in sorted_stocks)
                
                if total_return <= 0:
                    return self._create_equal_allocations(stocks)
                
                allocations = []
                for stock in sorted_stocks:
                    return_value = max(stock.get('expected_return', 0.0), 0.0)
                    weight = return_value / total_return
                    allocations.append({
                        'symbol': stock.get('symbol', 'UNKNOWN'),
                        'allocation': weight,
                        'sector': stock.get('sector', 'Unknown')
                    })
                
                return allocations
            else:
                return self._create_constrained_return_allocations(sorted_stocks, risk_profile)
                
        except Exception as e:
            logger.error(f"❌ Error in return allocations: {e}")
            return self._create_equal_allocations(stocks)
    
    def _create_equal_allocations(self, stocks: List[Dict]) -> List[Dict]:
        """Create equal-weighted allocations"""
        if not stocks:
            return []
        
        weight_per_stock = 1.0 / len(stocks)
        return [
            {
                'symbol': stock.get('symbol', 'UNKNOWN'),
                'allocation': weight_per_stock,
                'sector': stock.get('sector', 'Unknown')
            }
            for stock in stocks
        ]
    
    def _create_constrained_risk_allocations(self, stocks: List[Dict], risk_profile: str) -> List[Dict]:
        """Create risk allocations with risk profile constraints using iterative capping"""
        try:
            risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
            max_single_weight = risk_constraints.get('max_single_stock_weight', 0.4)
            
            # Calculate initial inverse-volatility weights
            weights = {}
            for stock in stocks:
                symbol = stock.get('symbol', 'UNKNOWN')
                inverse_vol = 1.0 / max(stock.get('volatility', 0.01), 0.01)
                weights[symbol] = {'weight': inverse_vol, 'stock': stock, 'capped': False}
            
            # Iterative capping and redistribution
            allocations = self._iterative_cap_and_normalize(weights, max_single_weight)
            
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error in constrained risk allocations: {e}")
            return self._create_equal_allocations(stocks)
    
    def _create_constrained_return_allocations(self, stocks: List[Dict], risk_profile: str) -> List[Dict]:
        """Create return allocations with risk profile constraints using iterative capping"""
        try:
            risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
            max_single_weight = risk_constraints.get('max_single_stock_weight', 0.4)
            
            # Calculate initial return-proportional weights
            weights = {}
            for stock in stocks:
                symbol = stock.get('symbol', 'UNKNOWN')
                return_value = max(stock.get('expected_return', 0.0), 0.0)
                weights[symbol] = {'weight': return_value, 'stock': stock, 'capped': False}
            
            # Check if all returns are zero or negative
            total_weight = sum(w['weight'] for w in weights.values())
            if total_weight <= 0:
                return self._create_equal_allocations(stocks)
            
            # Iterative capping and redistribution
            allocations = self._iterative_cap_and_normalize(weights, max_single_weight)
            
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error in constrained return allocations: {e}")
            return self._create_equal_allocations(stocks)
    
    def _iterative_cap_and_normalize(self, weights: Dict, max_weight: float, max_iterations: int = 10) -> List[Dict]:
        """Iteratively cap and normalize weights to ensure sum=1.0 and no weight exceeds max"""
        try:
            for iteration in range(max_iterations):
                # Normalize weights
                total = sum(w['weight'] for w in weights.values() if not w['capped'])
                capped_total = sum(max_weight for w in weights.values() if w['capped'])
                remaining = 1.0 - capped_total
                
                if total <= 0:
                    # All remaining weights are zero, distribute equally among uncapped
                    uncapped = [k for k, v in weights.items() if not v['capped']]
                    if uncapped:
                        equal_weight = remaining / len(uncapped)
                        for symbol in uncapped:
                            weights[symbol]['weight'] = equal_weight
                    break
                
                # Normalize uncapped weights to fill remaining allocation
                scale_factor = remaining / total
                any_exceeded = False
                
                for symbol, data in weights.items():
                    if not data['capped']:
                        normalized_weight = data['weight'] * scale_factor
                        if normalized_weight > max_weight:
                            data['weight'] = max_weight
                            data['capped'] = True
                            any_exceeded = True
                        else:
                            data['weight'] = normalized_weight
                
                if not any_exceeded:
                    break
            
            # Build final allocations
            allocations = []
            for symbol, data in weights.items():
                stock = data['stock']
                allocations.append({
                    'symbol': symbol,
                    'allocation': data['weight'],
                    'sector': stock.get('sector', 'Unknown')
                })
            
            # Final normalization to ensure sum = 1.0
            total_allocation = sum(a['allocation'] for a in allocations)
            if total_allocation > 0 and abs(total_allocation - 1.0) > 0.0001:
                for alloc in allocations:
                    alloc['allocation'] /= total_allocation
            
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error in iterative cap and normalize: {e}")
            # Return equal weights as fallback
            return [
                {
                    'symbol': symbol,
                    'allocation': 1.0 / len(weights),
                    'sector': data['stock'].get('sector', 'Unknown')
                }
                for symbol, data in weights.items()
            ]
    
    def _validate_allocations(self, allocations: List[Dict], risk_profile: str = None) -> bool:
        """Validate portfolio allocations with improved tolerance"""
        if not allocations:
            return False
        
        try:
            total_allocation = sum(alloc['allocation'] for alloc in allocations)
            
            # Check sum is approximately 1.0 (allow 1% tolerance)
            if abs(total_allocation - 1.0) > 0.01:
                logger.debug(f"Validation failed: total={total_allocation:.4f}, expected ~1.0")
                return False
            
            # Check no negative allocations
            negative_allocs = [a for a in allocations if a['allocation'] < 0]
            if negative_allocs:
                logger.debug(f"Validation failed: {len(negative_allocs)} negative allocations")
                return False
            
            # Check max single stock weight if risk profile provided
            if risk_profile and risk_profile in self.RISK_PROFILE_CONSTRAINTS:
                risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
                max_single_weight = risk_constraints.get('max_single_stock_weight', 1.0)
                
                # Allow small tolerance (0.5%) for floating point precision
                exceeded = [a for a in allocations if a['allocation'] > max_single_weight + 0.005]
                if exceeded:
                    logger.debug(f"Validation failed: {len(exceeded)} allocations exceed max weight {max_single_weight}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating allocations: {e}")
            return False
    
    def _calculate_strategy_portfolio_metrics(self, allocations: List[Dict], strategy: str) -> Dict:
        """Calculate portfolio metrics for strategy portfolios"""
        try:
            if not allocations:
                return self._get_fallback_metrics(strategy)
            
            sector_breakdown = defaultdict(float)
            for alloc in allocations:
                sector = alloc.get('sector', 'Unknown')
                sector_breakdown[sector] += alloc['allocation']
            
            # Calculate core metrics
            expected_return = self._calculate_expected_return(allocations, strategy)
            risk = self._calculate_portfolio_risk(allocations, strategy)
            sharpe_ratio = self._calculate_sharpe_ratio(allocations, strategy)
            
            # Cap return-strategy portfolios at 90% expected return to avoid unrealistic results
            if strategy == 'return' and expected_return > 0.90:
                logger.warning(
                    f"⚠️ Capping expected return for return strategy portfolio from {expected_return:.2%} to 90.00%"
                )
                expected_return = 0.90
            
            # Use the same sophisticated diversification score as the main recommendation system
            try:
                analytics_allocations = [
                    {
                        'symbol': alloc.get('symbol', 'UNKNOWN'),
                        # Convert from decimal (0-1) to percentage (0-100) for analytics
                        'allocation': float(alloc.get('allocation', 0.0)) * 100.0,
                        'sector': alloc.get('sector', 'Unknown')
                    }
                    for alloc in allocations
                ]
                diversification_score = self.portfolio_analytics._calculate_sophisticated_diversification_score(
                    analytics_allocations
                )
            except Exception as e:
                logger.error(f"❌ Error calculating sophisticated diversification score for strategy portfolio: {e}")
                diversification_score = self._calculate_diversification_score(allocations, strategy)
            
            metrics = {
                'expected_return': expected_return,
                'risk': risk,
                'sharpe_ratio': sharpe_ratio,
                'diversification_score': diversification_score,
                'sector_breakdown': dict(sector_breakdown),
                'num_stocks': len(allocations),
                'strategy': strategy
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculating strategy portfolio metrics: {e}")
            return self._get_fallback_metrics(strategy)
    
    def _calculate_expected_return(self, allocations: List[Dict], strategy: str) -> float:
        """Calculate expected return using Redis price data (annualized).
        
        Prefers cached metrics (expected_return) over recalculating from prices.
        Filters out assets with non-positive expected returns instead of forcing a positive fallback.
        """
        try:
            if not allocations:
                return 0.10
            # Build per-asset annualized returns - prefer cached metrics over price calculation
            weights = []
            rets = []
            for alloc in allocations:
                symbol = alloc.get('symbol')
                w = float(alloc.get('allocation', 0.0))
                if w <= 0 or not symbol:
                    continue
                
                # FIRST: Try to use cached metrics (expected_return or annualized_return) - more stable
                metrics = self.data_service._load_from_cache(symbol, 'metrics') if hasattr(self.data_service, '_load_from_cache') else None
                if metrics and isinstance(metrics, dict):
                    # Prefer expected_return (stored as decimal); fallback to annualized_return (may be % or decimal)
                    raw_ret = metrics.get('expected_return')
                    if raw_ret is None:
                        raw_ret = metrics.get('annualized_return', 0.10)
                    annual_ret = float(raw_ret)
                    # Normalize: cache may store percentage (e.g. 29.14) or decimal (0.2914)
                    if abs(annual_ret) > 1.0:
                        annual_ret = annual_ret / 100.0
                    # Clamp to realistic range (0% to 100%) to avoid outliers
                    annual_ret = max(0.0, min(1.0, annual_ret))
                    # Keep only assets with strictly positive expected returns
                    if annual_ret > 0:
                        weights.append(w)
                        rets.append(annual_ret)
                        continue
                    else:
                        logger.info(f"ℹ️ {symbol} has non-positive cached return ({annual_ret:.2%}), excluding from expected return calculation")
                        continue
                
                # FALLBACK: Calculate from prices if metrics not available
                prices = self.data_service._load_from_cache(symbol, 'prices') if hasattr(self.data_service, '_load_from_cache') else None
                if prices is None or getattr(prices, 'empty', False) or len(prices) < 3:
                    # Not enough data to estimate return, skip this asset
                    logger.info(f"ℹ️ {symbol} has insufficient price data for return calculation, excluding from expected return calculation")
                    continue
                else:
                    # monthly series -> annualized return over last 12 months (or scale)
                    import pandas as pd
                    s = prices
                    if isinstance(s, list):
                        s = pd.Series(s)
                    if len(s) >= 12:
                        annual_ret = float((s.iloc[-1] / s.iloc[-12]) - 1)
                    else:
                        annual_ret = float(((s.iloc[-1] / s.iloc[0]) - 1) * (12 / len(s)))
                    # Clamp to realistic range (0% to 100%) to avoid outliers from bad data
                    annual_ret = max(0.0, min(1.0, annual_ret))
                    # Keep only assets with strictly positive calculated returns
                    if annual_ret > 0:
                        weights.append(w)
                        rets.append(annual_ret)
                    else:
                        logger.info(f"ℹ️ {symbol} has non-positive calculated return ({annual_ret:.2%}), excluding from expected return calculation")
            
            if not weights:
                logger.warning("⚠️ No assets with positive expected returns found, using 10% fallback")
                return 0.10
            
            total_w = sum(weights) or 1.0
            # Normalize if needed
            weights = [w / total_w for w in weights]
            portfolio_return = sum(w * r for w, r in zip(weights, rets))
            
            # At this point portfolio_return should already be positive given filtering,
            # but keep a minimal safeguard.
            if portfolio_return <= 0:
                logger.warning(f"⚠️ Portfolio has non-positive return after filtering ({portfolio_return:.2%}), using 10% fallback")
                return 0.10
            # Final clamp to realistic max (90%) so stored metrics are never unrealistic
            portfolio_return = min(portfolio_return, 0.90)
            return float(portfolio_return)
        except Exception as e:
            logger.error(f"❌ Error calculating expected return: {e}")
            return 0.10
    
    def _calculate_portfolio_risk(self, allocations: List[Dict], strategy: str) -> float:
        """Calculate portfolio risk using covariance from cached monthly returns (annualized)."""
        try:
            if not allocations:
                return 0.20
            import pandas as pd
            import numpy as np
            symbols = []
            weights = []
            for alloc in allocations:
                symbol = alloc.get('symbol')
                w = float(alloc.get('allocation', 0.0))
                if w <= 0 or not symbol:
                    continue
                symbols.append(symbol)
                weights.append(w)
            total_w = sum(weights) or 1.0
            weights = np.array([w / total_w for w in weights])
            # Build returns DataFrame
            returns = {}
            for sym in symbols:
                prices = self.data_service._load_from_cache(sym, 'prices') if hasattr(self.data_service, '_load_from_cache') else None
                if prices is None or getattr(prices, 'empty', False) or len(prices) < 3:
                    continue
                s = prices
                if isinstance(s, list):
                    s = pd.Series(s)
                r = s.pct_change().dropna()
                if len(r) >= 3:
                    returns[sym] = r
            if len(returns) < 1:
                return 0.20
            # Align by shortest series
            df = pd.DataFrame(returns)
            cov_m = df.cov() * 12  # annualize covariance (monthly to annual)
            # Use per-asset annualized vol from covariance diagonal
            portfolio_var = float(weights.T @ cov_m.values @ weights)
            portfolio_vol = float(np.sqrt(max(portfolio_var, 0.0)))
            return portfolio_vol
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio risk: {e}")
            return 0.20
    
    def _calculate_sharpe_ratio(self, allocations: List[Dict], strategy: str) -> float:
        """Calculate Sharpe ratio for portfolio"""
        try:
            expected_return = self._calculate_expected_return(allocations, strategy)
            risk = self._calculate_portfolio_risk(allocations, strategy)
            # Use the same risk-free rate as the main analytics system for consistency
            risk_free_rate = getattr(self.portfolio_analytics, 'risk_free_rate', 0.038)
            
            if risk > 0:
                return (expected_return - risk_free_rate) / risk
            return 0.5
        except Exception as e:
            logger.error(f"❌ Error calculating Sharpe ratio: {e}")
            return 0.5
    
    def _calculate_diversification_score(self, allocations: List[Dict], strategy: str) -> float:
        """Calculate diversification score (0-100) using HHI, sectors, and correlation."""
        try:
            import numpy as np
            import pandas as pd
            if not allocations or len(allocations) < 2:
                return 50.0
            weights = np.array([float(a.get('allocation', 0.0)) for a in allocations])
            total = weights.sum() or 1.0
            weights = weights / total
            # HHI-based base diversification
            hhi = float(np.sum(weights ** 2))
            base = max(0.0, (1.0 - hhi) * 100.0)
            # Sector diversity bonus (0-15)
            sectors = [a.get('sector', 'Unknown') for a in allocations]
            sector_hhi_map = {}
            sector_weights = {}
            for s, w in zip(sectors, weights):
                if s == 'Unknown':
                    continue
                sector_weights[s] = sector_weights.get(s, 0.0) + w
            if sector_weights:
                sw = np.array(list(sector_weights.values()))
                sw = sw / (sw.sum() or 1.0)
                sector_hhi = float(np.sum(sw ** 2))
                sector_bonus = (1.0 - sector_hhi) * 15.0
            else:
                sector_bonus = 0.0
            # Correlation penalty (0-10)
            symbols = [a.get('symbol') for a in allocations]
            returns = {}
            for sym in symbols:
                prices = self.data_service._load_from_cache(sym, 'prices') if hasattr(self.data_service, '_load_from_cache') else None
                if prices is None or getattr(prices, 'empty', False) or len(prices) < 3:
                    continue
                s = prices
                if isinstance(s, list):
                    s = pd.Series(s)
                r = s.pct_change().dropna()
                if len(r) >= 3:
                    returns[sym] = r
            corr_penalty = 0.0
            if len(returns) >= 2:
                df = pd.DataFrame(returns)
                c = df.corr().fillna(0.0)
                # weighted average absolute correlation
                wa = 0.0; tw = 0.0
                for i in range(len(symbols)):
                    for j in range(i+1, len(symbols)):
                        wpair = float(weights[i] * weights[j]) if i < len(weights) and j < len(weights) else 0.0
                        if wpair > 0 and symbols[i] in c.columns and symbols[j] in c.columns:
                            wa += wpair * abs(float(c.loc[symbols[i], symbols[j]]))
                            tw += wpair
                avg_corr = (wa / tw) if tw > 0 else 0.0
                corr_penalty = max(0.0, (avg_corr - 0.3) * 25.0)  # penalize above 0.3 up to ~17.5
            score = base + sector_bonus - corr_penalty
            return float(max(0.0, min(100.0, round(score, 1))))
        except Exception as e:
            logger.error(f"❌ Error calculating diversification score: {e}")
            return 75.0
    
    def _get_fallback_metrics(self, strategy: str) -> Dict:
        """Get fallback metrics when calculation fails"""
        return {
            'expected_return': 0.10,
            'risk': 0.20,
            'sharpe_ratio': 0.5,
            'diversification_score': 75.0,
            'sector_breakdown': {},
            'num_stocks': 0,
            'strategy': strategy
        }
    
    def _get_available_stocks(self) -> List[Dict]:
        """Get available stocks with metrics from the data service - Redis only
        
        OPTIMIZED: Uses in-memory cache to avoid loading all stocks repeatedly.
        Cache is refreshed every hour or on-demand.
        """
        if not self.stock_selector:
            logger.error("❌ Stock selector not initialized")
            return []
        
        try:
            # Check if cache is valid
            if self._is_stock_pool_cache_valid():
                logger.info(f"✅ Using cached stock pool ({len(self._stock_pool_cache)} stocks)")
                return self._stock_pool_cache
            
            # Cache miss or expired - refresh
            logger.info("🔄 Refreshing stock pool cache...")
            self._stock_pool_cache = self._get_stocks_from_redis_only()
            self._cache_timestamp = datetime.now()
            logger.info(f"✅ Stock pool cache refreshed ({len(self._stock_pool_cache)} stocks)")
            
            return self._stock_pool_cache
        except Exception as e:
            logger.error(f"❌ Error getting available stocks: {e}")
            return []
    
    def _is_stock_pool_cache_valid(self) -> bool:
        """Check if the stock pool cache is still valid"""
        if self._stock_pool_cache is None or self._cache_timestamp is None:
            return False
        
        # Check TTL
        cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
        return cache_age < self._cache_ttl_seconds
    
    def invalidate_stock_pool_cache(self):
        """Manually invalidate the stock pool cache"""
        logger.info("🗑️  Invalidating stock pool cache")
        self._stock_pool_cache = None
        self._cache_timestamp = None
    
    def _get_stocks_from_redis_only(self) -> List[Dict]:
        """Get stocks using only Redis cached data - no external API calls"""
        try:
            if not self.data_service or not hasattr(self.data_service, 'redis_client'):
                logger.error("❌ Redis client not available")
                return []
            
            redis_client = self.data_service.redis_client
            all_tickers = self.data_service.all_tickers
            
            logger.info(f"🔍 Getting stocks from Redis cache only - {len(all_tickers)} tickers available")
            
            available_stocks = []
            cache_miss_count = 0
            cache_hit_count = 0
            
            # OPTIMIZED: Batch check and load using pipeline for faster processing
            logger.info("⚡ Using optimized batch loading...")
            
            # Batch check existence first (faster than loading)
            price_keys = [f"ticker_data:prices:{t}" for t in all_tickers]
            sector_keys = [f"ticker_data:sector:{t}" for t in all_tickers]
            
            # Use pipeline for batch existence checks
            pipe = redis_client.pipeline()
            for key in price_keys + sector_keys:
                pipe.exists(key)
            existence_results = pipe.execute()
            
            # Split results
            price_exists = existence_results[:len(price_keys)]
            sector_exists = existence_results[len(price_keys):]
            
            # Filter to only tickers with both prices and sector
            valid_tickers = [
                ticker for i, ticker in enumerate(all_tickers)
                if price_exists[i] and sector_exists[i]
            ]
            
            logger.info(f"⚡ Found {len(valid_tickers)}/{len(all_tickers)} tickers with prices+sector data")
            
            # OPTIMIZED: Batch load sector and metrics data using pipeline
            logger.info(f"⚡ Batch loading data for {len(valid_tickers)} valid tickers...")
            
            # Batch load sector and metrics data
            sector_data_keys = [f"ticker_data:sector:{t}" for t in valid_tickers]
            metrics_data_keys = [f"ticker_data:metrics:{t}" for t in valid_tickers]
            
            pipe = redis_client.pipeline()
            for key in sector_data_keys + metrics_data_keys:
                pipe.get(key)
            batch_results = pipe.execute()
            
            sector_data_raw = batch_results[:len(valid_tickers)]
            metrics_data_raw = batch_results[len(valid_tickers):]
            
            import json as json_lib
            import pickle
            
            for i, ticker in enumerate(valid_tickers):
                try:
                    # Parse sector data
                    cached_sector = None
                    if sector_data_raw[i]:
                        try:
                            cached_sector = json_lib.loads(sector_data_raw[i])
                        except:
                            try:
                                cached_sector = pickle.loads(sector_data_raw[i])
                            except:
                                pass
                    
                    if not cached_sector or not isinstance(cached_sector, dict):
                        cache_miss_count += 1
                        continue
                    
                    # Parse metrics data
                    cached_metrics = None
                    if metrics_data_raw[i]:
                        try:
                            cached_metrics = json_lib.loads(metrics_data_raw[i])
                        except:
                            try:
                                cached_metrics = pickle.loads(metrics_data_raw[i])
                            except:
                                pass
                    
                    # Use cached metrics primarily (faster than loading prices)
                    if cached_metrics:
                        volatility = cached_metrics.get('risk', 0.2)
                        annual_return = float(cached_metrics.get('annualized_return', 0.1))
                        # Normalize: cache may store percentage (e.g. 29.14) or decimal (0.2914)
                        if abs(annual_return) > 1.0:
                            annual_return = annual_return / 100.0
                        annual_return = max(0.0, min(1.0, annual_return))
                        current_price = cached_metrics.get('current_price', 0)
                    else:
                        # Only load prices if no metrics available
                        cached_prices = self.data_service._load_from_cache(ticker, 'prices')
                        if cached_prices is not None and len(cached_prices) > 1:
                            price_changes = cached_prices.pct_change().dropna()
                            volatility = price_changes.std() * (252 ** 0.5)
                            if len(cached_prices) > 12:
                                annual_return = ((cached_prices.iloc[-1] / cached_prices.iloc[-12]) - 1)
                            else:
                                annual_return = ((cached_prices.iloc[-1] / cached_prices.iloc[0]) - 1) * (12 / len(cached_prices))
                            current_price = cached_prices.iloc[-1]
                        else:
                            volatility = 0.2
                            annual_return = 0.1
                            current_price = 0
                    
                    stock_data = {
                        'symbol': ticker,
                        'ticker': ticker,
                        'company_name': cached_sector.get('companyName', ticker),
                        'sector': cached_sector.get('sector', 'Unknown'),
                        'industry': cached_sector.get('industry', 'Unknown'),
                        'volatility': volatility,
                        'expected_return': annual_return,
                        'current_price': current_price,
                        'data_quality': 'cached',
                        'cached': True
                    }
                    
                    available_stocks.append(stock_data)
                    cache_hit_count += 1
                    
                except Exception as e:
                    cache_miss_count += 1
                    continue
            
            cache_miss_count += len(all_tickers) - len(valid_tickers)
            
            logger.info(f"✅ Found {len(available_stocks)} stocks with complete Redis data")
            logger.info(f"📊 Cache hits: {cache_hit_count}, Cache misses: {cache_miss_count}")
            
            if cache_miss_count > 0:
                logger.info(f"⚠️ {cache_miss_count} tickers skipped due to missing cache data")
            
            return available_stocks
            
        except Exception as e:
            logger.error(f"❌ Error getting stocks from Redis: {e}")
            return []
    
    # ============================================================================
    # PRE-GENERATION AND REDIS STORAGE METHODS
    # ============================================================================
    
    def pre_generate_all_strategy_portfolios(self) -> Dict:
        """Pre-generate ALL strategy portfolios and store in Redis
        
        This generates:
        - 3 strategies × 6 pure portfolios = 18 pure portfolios
        - 3 strategies × 5 risk profiles × 6 portfolios = 90 personalized portfolios
        - Total: 108 portfolios
        
        Returns:
            Summary of generation with timing and success rates
        """
        logger.info("🚀 Starting pre-generation of ALL strategy portfolios...")
        start_time = datetime.now()
        
        summary = {
            'start_time': start_time.isoformat(),
            'strategies': {},
            'total_portfolios_generated': 0,
            'total_portfolios_stored': 0,
            'errors': []
        }
        
        try:
            # Pre-load stock pool once for all portfolios (optimized batch loading)
            logger.info("📊 Pre-loading stock pool (optimized)...")
            stock_pool = self._get_available_stocks()  # This will cache it
            logger.info(f"✅ Stock pool loaded: {len(stock_pool)} stocks")
            
            # Generate for each strategy
            for strategy in self.STRATEGIES.keys():
                logger.info(f"\n{'='*60}")
                logger.info(f"Generating portfolios for '{strategy}' strategy")
                logger.info(f"{'='*60}")
                
                strategy_start = datetime.now()
                strategy_result = self._pre_generate_strategy(strategy)
                strategy_elapsed = (datetime.now() - strategy_start).total_seconds()
                
                strategy_result['elapsed_seconds'] = strategy_elapsed
                summary['strategies'][strategy] = strategy_result
                summary['total_portfolios_generated'] += strategy_result['portfolios_generated']
                summary['total_portfolios_stored'] += strategy_result['portfolios_stored']
                
                logger.info(f"✅ {strategy}: {strategy_result['portfolios_generated']} generated, "
                           f"{strategy_result['portfolios_stored']} stored in {strategy_elapsed:.1f}s")
            
            # Calculate final timing
            total_elapsed = (datetime.now() - start_time).total_seconds()
            summary['end_time'] = datetime.now().isoformat()
            summary['total_elapsed_seconds'] = total_elapsed
            summary['success'] = True
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🎉 PRE-GENERATION COMPLETE!")
            logger.info(f"{'='*60}")
            logger.info(f"Total Portfolios Generated: {summary['total_portfolios_generated']}")
            logger.info(f"Total Portfolios Stored: {summary['total_portfolios_stored']}")
            logger.info(f"Total Time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} minutes)")
            logger.info(f"Average per Portfolio: {total_elapsed/summary['total_portfolios_generated']:.2f}s")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Pre-generation failed: {e}")
            summary['success'] = False
            summary['errors'].append(str(e))
            return summary
    
    def _pre_generate_strategy(self, strategy: str) -> Dict:
        """Pre-generate all portfolios for a single strategy"""
        result = {
            'strategy': strategy,
            'portfolios_generated': 0,
            'portfolios_stored': 0,
            'pure_count': 0,
            'personalized_count': 0,
            'errors': []
        }
        
        try:
            # Generate Pure portfolios
            logger.info(f"  Generating Pure {strategy} portfolios...")
            pure_portfolios = self._generate_pure_strategy_portfolios(strategy)
            result['pure_count'] = len(pure_portfolios)
            result['portfolios_generated'] += len(pure_portfolios)
            
            # Store Pure portfolios in Redis
            if pure_portfolios:
                stored = self._store_pure_portfolios_in_redis(strategy, pure_portfolios)
                result['portfolios_stored'] += stored
                logger.info(f"  ✅ Pure: {len(pure_portfolios)} generated, {stored} stored")
            
            # Generate Personalized portfolios for each risk profile
            logger.info(f"  Generating Personalized {strategy} portfolios...")
            for risk_profile in self.RISK_PROFILE_CONSTRAINTS.keys():
                try:
                    personalized = self._generate_personalized_strategy_portfolios(strategy, risk_profile)
                    result['personalized_count'] += len(personalized)
                    result['portfolios_generated'] += len(personalized)
                    
                    if personalized:
                        stored = self._store_personalized_portfolios_in_redis(
                            strategy, risk_profile, personalized
                        )
                        result['portfolios_stored'] += stored
                        logger.info(f"  ✅ {risk_profile}: {len(personalized)} generated, {stored} stored")
                        
                except Exception as e:
                    logger.error(f"  ❌ Error with {risk_profile}: {e}")
                    result['errors'].append(f"{risk_profile}: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error pre-generating {strategy}: {e}")
            result['errors'].append(str(e))
            return result
    
    def _store_pure_portfolios_in_redis(self, strategy: str, portfolios: List[Dict]) -> int:
        """Store Pure strategy portfolios in Redis"""
        if not self.redis_manager:
            logger.warning("⚠️  Redis manager not available, skipping storage")
            return 0
        
        stored_count = 0
        redis_key = f"strategy_portfolios:pure:{strategy}"
        
        try:
            # Store as JSON with 1-week TTL
            import json
            portfolio_data = {
                'strategy': strategy,
                'type': 'pure',
                'portfolios': portfolios,
                'generated_at': datetime.now().isoformat(),
                'count': len(portfolios)
            }
            
            self.redis_manager.redis_client.setex(
                redis_key,
                604800,  # 7 days TTL - background regeneration handles refresh before expiry
                json.dumps(portfolio_data)
            )
            stored_count = len(portfolios)
            logger.debug(f"✅ Stored {stored_count} pure {strategy} portfolios in Redis: {redis_key}")
            
        except Exception as e:
            logger.error(f"❌ Error storing pure portfolios in Redis: {e}")
        
        return stored_count
    
    def _store_personalized_portfolios_in_redis(self, strategy: str, risk_profile: str, 
                                                portfolios: List[Dict]) -> int:
        """Store Personalized strategy portfolios in Redis"""
        if not self.redis_manager:
            logger.warning("⚠️  Redis manager not available, skipping storage")
            return 0
        
        stored_count = 0
        redis_key = f"strategy_portfolios:personalized:{strategy}:{risk_profile}"
        
        try:
            # Store as JSON with 1-week TTL
            import json
            portfolio_data = {
                'strategy': strategy,
                'risk_profile': risk_profile,
                'type': 'personalized',
                'portfolios': portfolios,
                'generated_at': datetime.now().isoformat(),
                'count': len(portfolios)
            }
            
            self.redis_manager.redis_client.setex(
                redis_key,
                604800,  # 7 days TTL - background regeneration handles refresh before expiry
                json.dumps(portfolio_data)
            )
            stored_count = len(portfolios)
            logger.debug(f"✅ Stored {stored_count} personalized {strategy}/{risk_profile} "
                        f"portfolios in Redis: {redis_key}")
            
        except Exception as e:
            logger.error(f"❌ Error storing personalized portfolios in Redis: {e}")
        
        return stored_count
    
    def get_pure_portfolios_from_cache(self, strategy: str) -> Optional[List[Dict]]:
        """Retrieve Pure strategy portfolios from Redis cache
        
        Args:
            strategy: Strategy name (diversification, risk, return)
            
        Returns:
            List of portfolios if found, None if not in cache
        """
        if not self.redis_manager:
            return None
        
        redis_key = f"strategy_portfolios:pure:{strategy}"
        
        try:
            import json
            cached_data = self.redis_manager.redis_client.get(redis_key)
            
            if cached_data:
                portfolio_data = json.loads(cached_data)
                logger.info(f"✅ Retrieved {portfolio_data['count']} pure {strategy} portfolios from cache")
                return portfolio_data['portfolios']
            else:
                logger.debug(f"⚠️  No cached pure portfolios found for {strategy}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error retrieving pure portfolios from cache: {e}")
            return None
    
    def get_personalized_portfolios_from_cache(self, strategy: str, risk_profile: str) -> Optional[List[Dict]]:
        """Retrieve Personalized strategy portfolios from Redis cache
        
        Args:
            strategy: Strategy name (diversification, risk, return)
            risk_profile: Risk profile name
            
        Returns:
            List of portfolios if found, None if not in cache
        """
        if not self.redis_manager:
            return None
        
        redis_key = f"strategy_portfolios:personalized:{strategy}:{risk_profile}"
        
        try:
            import json
            cached_data = self.redis_manager.redis_client.get(redis_key)
            
            if cached_data:
                portfolio_data = json.loads(cached_data)
                logger.info(f"✅ Retrieved {portfolio_data['count']} personalized {strategy}/{risk_profile} "
                           f"portfolios from cache")
                return portfolio_data['portfolios']
            else:
                logger.debug(f"⚠️  No cached personalized portfolios found for {strategy}/{risk_profile}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error retrieving personalized portfolios from cache: {e}")
            return None
    
    def get_or_generate_personalized_portfolios(self, strategy: str, risk_profile: str) -> List[Dict]:
        """Get personalized portfolios from cache or generate if not cached
        
        This is the main method to use for retrieving portfolios.
        It implements a cache-first approach for optimal performance.
        
        Args:
            strategy: Strategy name (diversification, risk, return)
            risk_profile: Risk profile name
            
        Returns:
            List of portfolios (from cache or newly generated)
        """
        # Try cache first
        cached_portfolios = self.get_personalized_portfolios_from_cache(strategy, risk_profile)
        
        if cached_portfolios:
            logger.info(f"🚀 Fast path: Using cached portfolios for {strategy}/{risk_profile}")
            return cached_portfolios
        
        # Cache miss - generate
        logger.info(f"🔄 Cache miss: Generating portfolios for {strategy}/{risk_profile}")
        portfolios = self._generate_personalized_strategy_portfolios(strategy, risk_profile)
        
        # Store for future requests
        if portfolios:
            self._store_personalized_portfolios_in_redis(strategy, risk_profile, portfolios)
        
        return portfolios
    
    def clear_all_strategy_caches(self) -> Dict:
        """Clear all strategy portfolio caches from Redis"""
        if not self.redis_manager:
            return {'success': False, 'error': 'Redis manager not available'}
        
        try:
            # Find all strategy portfolio keys
            keys = self.redis_manager.redis_client.keys("strategy_portfolios:*")
            
            if keys:
                deleted = self.redis_manager.redis_client.delete(*keys)
                logger.info(f"🗑️  Cleared {deleted} strategy portfolio caches from Redis")
                return {'success': True, 'deleted_count': deleted}
            else:
                logger.info("ℹ️  No strategy portfolio caches to clear")
                return {'success': True, 'deleted_count': 0}
                
        except Exception as e:
            logger.error(f"❌ Error clearing strategy caches: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_cache_status_detailed(self) -> Dict:
        """Get detailed cache status including TTL information
        
        Returns:
            Detailed cache status with TTL info for display during startup
        """
        if not self.redis_manager:
            return {'success': False, 'error': 'Redis manager not available'}
        
        try:
            # Get all strategy portfolio keys
            keys = self.redis_manager.redis_client.keys("strategy_portfolios:*")
            
            if not keys:
                return {
                    'success': True,
                    'total_cached': 0,
                    'pure_portfolios': 0,
                    'personalized_portfolios': 0,
                    'needs_generation': True,
                    'message': 'No cached portfolios found'
                }
            
            # Count by type
            pure_count = len([k for k in keys if b'pure' in k])
            personalized_count = len([k for k in keys if b'personalized' in k])
            
            # Get TTL information
            ttls = []
            for key in keys:
                ttl = self.redis_manager.redis_client.ttl(key)
                if ttl > 0:
                    ttls.append(ttl)
            
            if ttls:
                min_ttl_seconds = min(ttls)
                max_ttl_seconds = max(ttls)
                avg_ttl_seconds = sum(ttls) / len(ttls)
                
                min_ttl_hours = min_ttl_seconds / 3600
                max_ttl_hours = max_ttl_seconds / 3600
                avg_ttl_hours = avg_ttl_seconds / 3600
            else:
                min_ttl_hours = max_ttl_hours = avg_ttl_hours = 0
            
            # Determine if refresh is needed (when oldest TTL < 24 hours)
            needs_refresh = min_ttl_hours < 24
            
            return {
                'success': True,
                'total_cached': len(keys),
                'pure_portfolios': pure_count,
                'personalized_portfolios': personalized_count,
                'min_ttl_hours': round(min_ttl_hours, 1),
                'max_ttl_hours': round(max_ttl_hours, 1),
                'avg_ttl_hours': round(avg_ttl_hours, 1),
                'needs_refresh': needs_refresh,
                'needs_generation': False,
                'message': 'Portfolios cached and available'
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting cache status: {e}")
            return {'success': False, 'error': str(e)}
    
    def display_cache_status(self):
        """Display strategy portfolio cache status in a formatted way"""
        status = self.get_cache_status_detailed()
        
        if not status.get('success'):
            logger.warning(f"⚠️  Cache status unavailable: {status.get('error')}")
            return
        
        logger.info("=" * 80)
        logger.info("STRATEGY PORTFOLIO CACHE STATUS")
        logger.info("=" * 80)
        
        if status['total_cached'] == 0:
            logger.info("📊 Status: NO CACHED PORTFOLIOS")
            logger.info("⚠️  First-time setup - generation required")
        else:
            logger.info(f"📊 Total Cached: {status['total_cached']} portfolio bundles")
            logger.info(f"   • Pure Strategies: {status['pure_portfolios']} bundles "
                       f"({status['pure_portfolios'] * self.PORTFOLIOS_PER_STRATEGY} portfolios)")
            logger.info(f"   • Personalized: {status['personalized_portfolios']} bundles "
                       f"({status['personalized_portfolios'] * 3} portfolios)")
            logger.info(f"⏱️  TTL Status:")
            logger.info(f"   • Minimum: {status['min_ttl_hours']:.1f} hours remaining")
            logger.info(f"   • Maximum: {status['max_ttl_hours']:.1f} hours remaining")
            logger.info(f"   • Average: {status['avg_ttl_hours']:.1f} hours remaining")
            
            if status['needs_refresh']:
                logger.info(f"🔄 Refresh Status: NEEDED (TTL < 24 hours)")
            else:
                logger.info(f"✅ Refresh Status: Not needed (TTL > 24 hours)")
        
        logger.info(f"💾 Storage: Redis (in-memory cache)")
        logger.info(f"📅 TTL Policy: 1 week (168 hours)")
        logger.info("=" * 80)
    
    # ============================================================================
    # END OF PRE-GENERATION AND REDIS STORAGE METHODS
    # ============================================================================
    
    def check_redis_data_sufficiency(self) -> Dict[str, any]:
        """Check if we have sufficient Redis data for strategy portfolio generation"""
        try:
            if not self.data_service or not hasattr(self.data_service, 'redis_client'):
                return {'sufficient': False, 'reason': 'Redis client not available'}
            
            all_tickers = self.data_service.all_tickers
            total_tickers = len(all_tickers)
            
            # Check cache coverage for each ticker
            prices_cached = 0
            sectors_cached = 0
            metrics_cached = 0
            
            for ticker in all_tickers:
                if self.data_service._is_cached(ticker, 'prices'):
                    prices_cached += 1
                if self.data_service._is_cached(ticker, 'sector'):
                    sectors_cached += 1
                if self.data_service._is_cached(ticker, 'metrics'):
                    metrics_cached += 1
            
            # Calculate coverage percentages
            prices_coverage = (prices_cached / total_tickers) * 100 if total_tickers > 0 else 0
            sectors_coverage = (sectors_cached / total_tickers) * 100 if total_tickers > 0 else 0
            metrics_coverage = (metrics_cached / total_tickers) * 100 if total_tickers > 0 else 0
            
            # Determine if we have sufficient data
            sufficient = prices_coverage >= 80 and sectors_coverage >= 80  # Need at least 80% coverage
            
            result = {
                'sufficient': sufficient,
                'total_tickers': total_tickers,
                'prices_cached': prices_cached,
                'sectors_cached': sectors_cached,
                'metrics_cached': metrics_cached,
                'prices_coverage': round(prices_coverage, 1),
                'sectors_coverage': round(sectors_coverage, 1),
                'metrics_coverage': round(metrics_coverage, 1),
                'recommendation': 'Ready to generate portfolios' if sufficient else 'Need more cached data'
            }
            
            logger.info(f"📊 Redis data sufficiency check: {result['recommendation']}")
            logger.info(f"   • Prices: {prices_coverage:.1f}% ({prices_cached}/{total_tickers})")
            logger.info(f"   • Sectors: {sectors_coverage:.1f}% ({sectors_cached}/{total_tickers})")
            logger.info(f"   • Metrics: {metrics_coverage:.1f}% ({metrics_cached}/{total_tickers})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error checking Redis data sufficiency: {e}")
            return {'sufficient': False, 'reason': f'Error: {e}'}
    
    def _generate_strategy_seed(self, strategy: str, portfolio_id: int, is_pure: bool, risk_profile: str = None) -> int:
        """Generate deterministic seed for strategy portfolio generation"""
        seed_string = f"{strategy}_{portfolio_id}_{'pure' if is_pure else 'personalized'}"
        if risk_profile:
            seed_string += f"_{risk_profile}"
        
        seed_hash = hash(seed_string)
        return abs(seed_hash) % 1000000
    
    def _create_strategy_metadata(self, strategy: str, risk_profiles: List[str], 
                                pure_portfolios: List[Dict], 
                                personalized_portfolios: Dict) -> Dict:
        """Create metadata for the strategy portfolio buckets"""
        return {
            'strategy': strategy,
            'generated_at': datetime.now().isoformat(),
            'total_portfolios': len(pure_portfolios) + sum(len(portfolios) for portfolios in personalized_portfolios.values()),
            'pure_count': len(pure_portfolios),
            'personalized_counts': {profile: len(portfolios) for profile, portfolios in personalized_portfolios.items()},
            'risk_profiles': risk_profiles,
            'strategy_config': self.STRATEGIES[strategy]
        }
