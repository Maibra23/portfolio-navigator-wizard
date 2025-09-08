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
    """Generates strategy-specific portfolios with Pure vs Personalized variants"""
    
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
        
        self.PORTFOLIOS_PER_STRATEGY = 5
    
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
        
        for portfolio_id in range(self.PORTFOLIOS_PER_STRATEGY):
            try:
                seed = self._generate_strategy_seed(strategy, portfolio_id, is_pure=True)
                random.seed(seed)
                
                selected_stocks = self._select_stocks_for_strategy_pure(strategy, portfolio_id)
                if not selected_stocks:
                    continue
                
                allocations = self._create_strategy_allocations(selected_stocks, strategy, is_pure=True)
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
                
                allocations = self._create_strategy_allocations(selected_stocks, strategy, is_pure=False, risk_profile=risk_profile)
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
            
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id)
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
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id)
            
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in Pure Risk filtering: {e}")
            return self._select_diversified_stocks_basic(stocks, 5)
    
    def _filter_for_return_pure(self, stocks: List[Dict], portfolio_id: int) -> List[Dict]:
        """Filter stocks for Pure Return strategy"""
        try:
            df = pd.DataFrame(stocks)
            
            if 'expected_return' in df.columns:
                return_threshold = df['expected_return'].quantile(0.6)
                df = df[df['expected_return'] >= return_threshold]
            
            growth_sectors = ['technology', 'healthcare', 'consumer_discretionary', 'communication']
            df['growth_score'] = df['sector'].apply(
                lambda x: 1 if any(growth_sector in str(x).lower() for growth_sector in growth_sectors) else 0
            )
            
            df = df.sort_values(['growth_score', 'expected_return'], ascending=[False, False])
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id)
            
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
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id, min_sectors)
            
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
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id, min_sectors)
            
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in Personalized Risk filtering: {e}")
            return self._select_diversified_stocks_basic(stocks, 5)
    
    def _filter_for_return_personalized(self, stocks: List[Dict], risk_profile: str, portfolio_id: int) -> List[Dict]:
        """Filter stocks for Personalized Return strategy"""
        try:
            df = pd.DataFrame(stocks)
            risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
            
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
            selected_stocks = self._select_diversified_stocks_by_sector(df, 5, portfolio_id, min_sectors)
            
            return selected_stocks
            
        except Exception as e:
            logger.error(f"❌ Error in Personalized Return filtering: {e}")
            return self._select_diversified_stocks_basic(stocks, 5)
    
    def _apply_risk_profile_constraints(self, stocks: List[Dict], risk_profile: str) -> List[Dict]:
        """Apply risk profile constraints to stock selection"""
        try:
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
    
    def _select_diversified_stocks_by_sector(self, df: pd.DataFrame, count: int, portfolio_id: int, min_sectors: int = 3) -> List[Dict]:
        """Select stocks ensuring sector diversity"""
        if len(df) < count:
            return df.to_dict('records')
        
        try:
            random.seed(portfolio_id)
            sectors = df['sector'].unique()
            if len(sectors) < min_sectors:
                min_sectors = len(sectors)
            
            selected_stocks = []
            sectors_per_stock = max(1, count // min_sectors)
            
            for sector in sectors[:min_sectors]:
                sector_stocks = df[df['sector'] == sector]
                if len(sector_stocks) > 0:
                    sector_stocks = sector_stocks.head(sectors_per_stock)
                    selected_stocks.extend(sector_stocks.to_dict('records'))
            
            if len(selected_stocks) < count:
                remaining_stocks = df[~df.index.isin([stock.get('index', i) for i, stock in enumerate(selected_stocks)])]
                additional_needed = count - len(selected_stocks)
                additional_stocks = remaining_stocks.head(additional_needed)
                selected_stocks.extend(additional_stocks.to_dict('records'))
            
            selected_stocks = selected_stocks[:count]
            logger.debug(f"✅ Selected {len(selected_stocks)} stocks from {min_sectors} sectors")
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
                                   is_pure: bool, risk_profile: str = None) -> List[Dict]:
        """Create portfolio allocations based on strategy and constraints"""
        if not stocks:
            return []
        
        try:
            if strategy == 'diversification':
                allocations = self._create_diversification_allocations(stocks, is_pure, risk_profile)
            elif strategy == 'risk':
                allocations = self._create_risk_allocations(stocks, is_pure, risk_profile)
            elif strategy == 'return':
                allocations = self._create_return_allocations(stocks, is_pure, risk_profile)
            else:
                allocations = self._create_equal_allocations(stocks)
            
            if not self._validate_allocations(allocations, risk_profile):
                logger.warning("⚠️ Allocations failed validation, using equal weighting")
                allocations = self._create_equal_allocations(stocks)
            
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error creating strategy allocations: {e}")
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
        """Create risk allocations with risk profile constraints"""
        try:
            risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
            max_single_weight = risk_constraints.get('max_single_stock_weight', 0.4)
            
            total_inverse_vol = sum(1.0 / max(stock.get('volatility', 0.01), 0.01) for stock in stocks)
            
            allocations = []
            for stock in stocks:
                inverse_vol = 1.0 / max(stock.get('volatility', 0.01), 0.01)
                weight = inverse_vol / total_inverse_vol
                
                if weight > max_single_weight:
                    weight = max_single_weight
                
                allocations.append({
                    'symbol': stock.get('symbol', 'UNKNOWN'),
                    'allocation': weight,
                    'sector': stock.get('sector', 'Unknown')
                })
            
            # Normalize allocations
            total_allocation = sum(alloc['allocation'] for alloc in allocations)
            if total_allocation > 0:
                for alloc in allocations:
                    alloc['allocation'] /= total_allocation
            
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error in constrained risk allocations: {e}")
            return self._create_equal_allocations(stocks)
    
    def _create_constrained_return_allocations(self, stocks: List[Dict], risk_profile: str) -> List[Dict]:
        """Create return allocations with risk profile constraints"""
        try:
            risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
            max_single_weight = risk_constraints.get('max_single_stock_weight', 0.4)
            
            total_return = sum(max(stock.get('expected_return', 0.0), 0.0) for stock in stocks)
            
            if total_return <= 0:
                return self._create_equal_allocations(stocks)
            
            allocations = []
            for stock in stocks:
                return_value = max(stock.get('expected_return', 0.0), 0.0)
                weight = return_value / total_return
                
                if weight > max_single_weight:
                    weight = max_single_weight
                
                allocations.append({
                    'symbol': stock.get('symbol', 'UNKNOWN'),
                    'allocation': weight,
                    'sector': stock.get('sector', 'Unknown')
                })
            
            # Normalize allocations
            total_allocation = sum(alloc['allocation'] for alloc in allocations)
            if total_allocation > 0:
                for alloc in allocations:
                    alloc['allocation'] /= total_allocation
            
            return allocations
            
        except Exception as e:
            logger.error(f"❌ Error in constrained return allocations: {e}")
            return self._create_equal_allocations(stocks)
    
    def _validate_allocations(self, allocations: List[Dict], risk_profile: str = None) -> bool:
        """Validate portfolio allocations"""
        if not allocations:
            return False
        
        try:
            total_allocation = sum(alloc['allocation'] for alloc in allocations)
            if abs(total_allocation - 1.0) > 0.01:
                return False
            
            if any(alloc['allocation'] < 0 for alloc in allocations):
                return False
            
            if risk_profile:
                risk_constraints = self.RISK_PROFILE_CONSTRAINTS[risk_profile]
                max_single_weight = risk_constraints.get('max_single_stock_weight', 1.0)
                if any(alloc['allocation'] > max_single_weight for alloc in allocations):
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
            
            metrics = {
                'expected_return': self._calculate_expected_return(allocations, strategy),
                'risk': self._calculate_portfolio_risk(allocations, strategy),
                'sharpe_ratio': self._calculate_sharpe_ratio(allocations, strategy),
                'diversification_score': self._calculate_diversification_score(allocations, strategy),
                'sector_breakdown': dict(sector_breakdown),
                'num_stocks': len(allocations),
                'strategy': strategy
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error calculating strategy portfolio metrics: {e}")
            return self._get_fallback_metrics(strategy)
    
    def _calculate_expected_return(self, allocations: List[Dict], strategy: str) -> float:
        """Calculate expected return for portfolio"""
        try:
            if strategy == 'return':
                return 0.15
            elif strategy == 'risk':
                return 0.08
            else:  # diversification
                return 0.12
        except Exception as e:
            logger.error(f"❌ Error calculating expected return: {e}")
            return 0.10
    
    def _calculate_portfolio_risk(self, allocations: List[Dict], strategy: str) -> float:
        """Calculate portfolio risk (volatility)"""
        try:
            if strategy == 'risk':
                return 0.18
            elif strategy == 'return':
                return 0.28
            else:  # diversification
                return 0.22
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio risk: {e}")
            return 0.20
    
    def _calculate_sharpe_ratio(self, allocations: List[Dict], strategy: str) -> float:
        """Calculate Sharpe ratio for portfolio"""
        try:
            expected_return = self._calculate_expected_return(allocations, strategy)
            risk = self._calculate_portfolio_risk(allocations, strategy)
            
            if risk > 0:
                return (expected_return - 0.02) / risk
            return 0.5
        except Exception as e:
            logger.error(f"❌ Error calculating Sharpe ratio: {e}")
            return 0.5
    
    def _calculate_diversification_score(self, allocations: List[Dict], strategy: str) -> float:
        """Calculate diversification score for portfolio"""
        try:
            num_stocks = len(allocations)
            num_sectors = len(set(alloc.get('sector', 'Unknown') for alloc in allocations))
            
            stock_score = min(100, num_stocks * 20)
            sector_score = min(50, num_sectors * 10)
            
            return stock_score + sector_score
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
        """Get available stocks with metrics from the data service - Redis only"""
        if not self.stock_selector:
            logger.error("❌ Stock selector not initialized")
            return []
        
        try:
            # Use Redis-only method to get stocks
            return self._get_stocks_from_redis_only()
        except Exception as e:
            logger.error(f"❌ Error getting available stocks: {e}")
            return []
    
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
            
            # Debug: Check first few tickers in detail
            logger.info("🔍 Debug: Checking first 5 tickers in detail...")
            
            for i, ticker in enumerate(all_tickers):
                try:
                    # Check if we have all required data in Redis
                    has_prices = self.data_service._is_cached(ticker, 'prices')
                    has_sector = self.data_service._is_cached(ticker, 'sector')
                    has_metrics = self.data_service._is_cached(ticker, 'metrics')
                    
                    # Convert Redis return values to proper booleans
                    has_prices_bool = bool(has_prices)
                    has_sector_bool = bool(has_sector)
                    has_metrics_bool = bool(has_metrics)
                    
                    # Debug logging for first few tickers
                    if i < 5:
                        logger.info(f"🔍 {ticker}: prices={has_prices}({has_prices_bool}), sector={has_sector}({has_sector_bool}), metrics={has_metrics}({has_metrics_bool})")
                    
                    # Use boolean values for the condition
                    if not (has_prices_bool and has_sector_bool):
                        cache_miss_count += 1
                        if i < 5:  # Log first few misses
                            logger.info(f"⚠️ {ticker}: Skipped - missing required data (prices: {has_prices_bool}, sector: {has_sector_bool})")
                        continue
                    
                    # Load data from Redis cache only
                    cached_prices = self.data_service._load_from_cache(ticker, 'prices')
                    cached_sector = self.data_service._load_from_cache(ticker, 'sector')
                    cached_metrics = self.data_service._load_from_cache(ticker, 'metrics')
                    
                    if i < 5:
                        logger.info(f"🔍 {ticker}: Loaded - prices={cached_prices is not None}, sector={cached_sector is not None}, metrics={cached_metrics is not None}")
                    
                    # Check if cached data is valid using pandas-safe methods
                    prices_valid = cached_prices is not None and not cached_prices.empty if hasattr(cached_prices, 'empty') else cached_prices is not None
                    sector_valid = cached_sector is not None and len(cached_sector) > 0 if isinstance(cached_sector, dict) else cached_sector is not None
                    
                    if not prices_valid or not sector_valid:
                        cache_miss_count += 1
                        if i < 5:  # Log first few misses
                            logger.debug(f"⚠️ {ticker}: Skipped - data loading failed (prices: {prices_valid}, sector: {sector_valid})")
                        continue
                    
                    # Calculate basic metrics from cached data
                    if cached_prices is not None and len(cached_prices) > 1:
                        # Calculate volatility from price changes
                        price_changes = cached_prices.pct_change().dropna()
                        volatility = price_changes.std() * (252 ** 0.5)  # Annualized
                        
                        # Calculate return from price change
                        if len(cached_prices) > 12:  # At least 1 year of data
                            annual_return = ((cached_prices.iloc[-1] / cached_prices.iloc[-12]) - 1)
                        else:
                            annual_return = ((cached_prices.iloc[-1] / cached_prices.iloc[0]) - 1) * (12 / len(cached_prices))
                    else:
                        volatility = 0.2  # Default volatility
                        annual_return = 0.1  # Default return
                    
                    # Use cached metrics if available, otherwise calculate from prices
                    if cached_metrics:
                        volatility = cached_metrics.get('risk', volatility)
                        annual_return = cached_metrics.get('annualized_return', annual_return)
                    
                    stock_data = {
                        'symbol': ticker,
                        'ticker': ticker,
                        'company_name': cached_sector.get('companyName', ticker),
                        'sector': cached_sector.get('sector', 'Unknown'),
                        'industry': cached_sector.get('industry', 'Unknown'),
                        'volatility': volatility,
                        'expected_return': annual_return,
                        'current_price': cached_prices.iloc[-1] if not cached_prices.empty else 0,
                        'data_quality': 'cached',
                        'cached': True
                    }
                    
                    available_stocks.append(stock_data)
                    cache_hit_count += 1
                    
                    # Debug logging for first few successful stocks
                    if i < 5:
                        logger.info(f"✅ {ticker}: Added successfully - {stock_data['sector']}, vol={volatility:.4f}, ret={annual_return:.4f}")
                    
                except Exception as e:
                    cache_miss_count += 1
                    if i < 5:  # Log first few errors
                        logger.error(f"❌ {ticker}: Error processing - {e}")
                    continue
            
            logger.info(f"✅ Found {len(available_stocks)} stocks with complete Redis data")
            logger.info(f"📊 Cache hits: {cache_hit_count}, Cache misses: {cache_miss_count}")
            
            if cache_miss_count > 0:
                logger.info(f"⚠️ {cache_miss_count} tickers skipped due to missing cache data")
            
            return available_stocks
            
        except Exception as e:
            logger.error(f"❌ Error getting stocks from Redis: {e}")
            return []
    
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
