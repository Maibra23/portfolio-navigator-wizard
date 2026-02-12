import quantstats as qs
import pypfopt
from pypfopt import EfficientFrontier, risk_models, expected_returns
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)

class PortfolioAnalytics:
    """
    Comprehensive portfolio analytics using QuantStats and PyPortfolioOpt
    Handles all mathematical calculations for the portfolio wizard
    """
    
    def __init__(self):
        self.risk_free_rate = 0.038  # 4% risk-free rate
        qs.extend_pandas()  # Extend pandas with QuantStats methods
    
    def calculate_asset_metrics(self, prices: List[float]) -> Dict:
        """
        Calculate comprehensive metrics for single asset using QuantStats
        Args:
            prices: List of monthly adjusted close prices
        Returns:
            Dict with comprehensive asset metrics
        """
        try:
            # Convert to pandas Series with datetime index
            price_series = pd.Series(prices)
            returns = price_series.pct_change().dropna()
            
            if len(returns) < 12:  # Need at least 12 months
                return self._get_fallback_metrics()
            
            # Create datetime index for QuantStats (monthly data)
            start_date = pd.Timestamp('2020-01-01')
            date_index = pd.date_range(start=start_date, periods=len(returns), freq='ME')
            returns.index = date_index
            
            # Calculate metrics using numpy/pandas (more reliable than QuantStats for monthly data)
            # For monthly data: sqrt(12) for annualization
            annual_factor = np.sqrt(12)
            
            # Calculate basic statistics
            monthly_return = returns.mean()
            monthly_risk = returns.std()  # Renamed from volatility to risk
            
            # Annualize metrics
            ann_return = (1 + monthly_return) ** 12 - 1  # Compound annual return
            ann_risk = monthly_risk * annual_factor      # Annualized risk
            
            # Calculate max drawdown manually (more reliable than QuantStats)
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdowns = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            metrics = {
                'annualized_return': ann_return,
                'risk': ann_risk,  # Renamed from volatility to risk
                'max_drawdown': max_drawdown,
                'data_points': len(returns),
                'data_quality': 'good' if len(returns) >= 180 else 'limited'  # 15 years of monthly data
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating asset metrics: {e}")
            return self._get_fallback_metrics()
    
    def two_asset_analysis(self, ticker1: str, prices1: List[float], 
                          ticker2: str, prices2: List[float]) -> Dict:
        """
        Educational two-asset comparison with comprehensive analysis
        Args:
            ticker1, ticker2: Asset tickers
            prices1, prices2: Monthly adjusted close prices
        Returns:
            Dict with comprehensive two-asset analysis
        """
        try:
            # Calculate individual asset metrics
            asset1_metrics = self.calculate_asset_metrics(prices1)
            asset2_metrics = self.calculate_asset_metrics(prices2)
            
            # Calculate correlation
            returns1 = pd.Series(prices1).pct_change().dropna()
            returns2 = pd.Series(prices2).pct_change().dropna()
            
            # Align returns for correlation calculation
            min_length = min(len(returns1), len(returns2))
            returns1_aligned = returns1.iloc[-min_length:]
            returns2_aligned = returns2.iloc[-min_length:]
            
            correlation = returns1_aligned.corr(returns2_aligned)
            if pd.isna(correlation):
                correlation = 0.0
            
            # Generate portfolio combinations
            portfolios = self._generate_portfolio_combinations(
                asset1_metrics, asset2_metrics, correlation
            )
            
            return {
                'ticker1': ticker1.upper(),
                'ticker2': ticker2.upper(),
                'asset1_stats': {
                    'ticker': ticker1.upper(),
                    'annualized_return': asset1_metrics['annualized_return'],
                    'annualized_volatility': asset1_metrics['risk'],
                    'price_history': prices1,
                    'last_price': prices1[-1] if prices1 else 0,
                    'data_points': asset1_metrics['data_points'],
                    'data_quality': asset1_metrics['data_quality']
                },
                'asset2_stats': {
                    'ticker': ticker2.upper(),
                    'annualized_return': asset2_metrics['annualized_return'],
                    'annualized_volatility': asset2_metrics['risk'],
                    'price_history': prices2,
                    'last_price': prices2[-1] if prices2 else 0,
                    'data_points': asset2_metrics['data_points'],
                    'data_quality': asset2_metrics['data_quality']
                },
                'correlation': correlation,
                'portfolios': portfolios,
                'educational_insights': self._generate_educational_insights(
                    asset1_metrics, asset2_metrics, correlation
                )
            }
            
        except Exception as e:
            logger.error(f"Error in two-asset analysis: {e}")
            return self._get_fallback_two_asset_analysis(ticker1, ticker2)
    
    def generate_risk_portfolios(self, risk_profile: str, 
                                available_assets: List[str]) -> List[Dict]:
        """
        Generate risk-based portfolio recommendations (max 4 assets)
        Args:
            risk_profile: User's risk profile
            available_assets: List of available asset tickers
        Returns:
            List of portfolio recommendations
        """
        try:
            # Asset classification (stocks only - no bonds)
            conservative_assets = ['JNJ', 'PG', 'KO', 'VZ', 'WMT', 'JPM', 'UNH']
            moderate_assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'VTI', 'VOO', 'SPY']
            aggressive_assets = ['NVDA', 'TSLA', 'AMD', 'META', 'XLK', 'VUG', 'QQQ']
            
            # Risk-based allocation rules (stocks only)
            allocation_rules = {
                'very-conservative': {'low_vol': 70, 'moderate': 25, 'high_growth': 5},
                'conservative': {'low_vol': 50, 'moderate': 40, 'high_growth': 10},
                'moderate': {'low_vol': 30, 'moderate': 60, 'high_growth': 10},
                'aggressive': {'low_vol': 15, 'moderate': 75, 'high_growth': 10},
                'very-aggressive': {'low_vol': 5, 'moderate': 85, 'high_growth': 10}
            }
            
            rule = allocation_rules.get(risk_profile, allocation_rules['moderate'])
            
            # Generate 3 different portfolio options
            portfolios = []
            for i in range(3):
                # Shuffle assets for variety
                import random
                shuffled_conservative = conservative_assets.copy()
                shuffled_moderate = moderate_assets.copy()
                shuffled_aggressive = aggressive_assets.copy()
                random.shuffle(shuffled_conservative)
                random.shuffle(shuffled_moderate)
                random.shuffle(shuffled_aggressive)
                
                portfolio = self._select_assets_by_risk(
                    rule, shuffled_conservative, shuffled_moderate, shuffled_aggressive
                )
                portfolio = portfolio[:4]  # Limit to 4 assets
                
                # Calculate portfolio metrics using real data
                portfolio_metrics = self.calculate_real_portfolio_metrics(portfolio)
                
                portfolios.append({
                    'name': f'Portfolio Option {i+1}',
                    'description': self._generate_portfolio_description(risk_profile, i),
                    'allocations': portfolio,
                    'metrics': portfolio_metrics,
                    'range_estimates': self.simple_range_estimates(portfolio_metrics)
                })
            
            return portfolios
            
        except Exception as e:
            logger.error(f"Error generating risk portfolios: {e}")
            return self._get_fallback_portfolios(risk_profile)
    
    def calculate_portfolio_metrics(self, weights: List[float], 
                                  asset_returns: List[pd.Series]) -> Dict:
        """
        Calculate portfolio-level metrics using QuantStats
        Args:
            weights: Portfolio weights
            asset_returns: List of return series for each asset
        Returns:
            Dict with portfolio metrics
        """
        try:
            # Ensure all return series have datetime index
            aligned_returns = []
            for returns in asset_returns:
                if not isinstance(returns.index, pd.DatetimeIndex):
                    start_date = pd.Timestamp('2020-01-01')
                    date_index = pd.date_range(start=start_date, periods=len(returns), freq='ME')
                    returns.index = date_index
                aligned_returns.append(returns)
            
            # Create portfolio return series
            portfolio_returns = pd.Series(0.0, index=aligned_returns[0].index)
            for i, (weight, returns) in enumerate(zip(weights, aligned_returns)):
                portfolio_returns += weight * returns
            
            # Calculate metrics using numpy/pandas (more reliable than QuantStats)
            annual_factor = np.sqrt(12)  # For monthly data
            
            # Calculate basic statistics
            monthly_return = portfolio_returns.mean()
            monthly_risk = portfolio_returns.std()
            
            # Annualize metrics
            ann_return = (1 + monthly_return) ** 12 - 1  # Compound annual return
            ann_risk = monthly_risk * annual_factor      # Annualized risk
            
            # Calculate max drawdown manually
            cumulative = (1 + portfolio_returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdowns = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            metrics = {
                'expected_return': ann_return,
                'risk': ann_risk,
                'max_drawdown': max_drawdown,
                'diversification_score': self._calculate_diversification_score(weights, aligned_returns)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return self._get_fallback_portfolio_metrics()
    
    def simple_range_estimates(self, portfolio_metrics: Dict) -> Dict:
        """
        Generate simple range estimates without mentioning historical data
        Args:
            portfolio_metrics: Portfolio metrics dictionary
        Returns:
            Dict with range estimates and enhanced color coding
        """
        try:
            expected_return = portfolio_metrics.get('expected_return', 0.10)
            volatility = portfolio_metrics.get('volatility', 0.15)
            sharpe_ratio = portfolio_metrics.get('sharpe_ratio', 0.4)
            max_drawdown = portfolio_metrics.get('max_drawdown', -0.10)
            diversification_score = portfolio_metrics.get('diversification_score', 50.0)
            
            # Enhanced color coding logic
            def get_return_color(ret):
                if ret > 0.15: return 'green'  # Excellent
                elif ret > 0.10: return 'lime'  # Good
                elif ret > 0.06: return 'yellow'  # Fair
                else: return 'orange'  # Poor
            
            def get_risk_color(risk):
                if risk < 0.10: return 'green'  # Low risk
                elif risk < 0.15: return 'lime'  # Moderate risk
                elif risk < 0.25: return 'yellow'  # High risk
                else: return 'red'  # Very high risk
            
            def get_sharpe_color(sharpe):
                if sharpe > 1.0: return 'green'  # Excellent
                elif sharpe > 0.5: return 'lime'  # Good
                elif sharpe > 0.0: return 'yellow'  # Fair
                else: return 'red'  # Poor
            
            def get_diversification_color(score):
                if score > 80: return 'green'  # Excellent diversification
                elif score > 60: return 'lime'  # Good diversification
                elif score > 40: return 'yellow'  # Fair diversification
                else: return 'orange'  # Poor diversification
            
            # Generate confidence intervals
            return_variance = volatility * 0.5  # Estimate return variance
            risk_variance = volatility * 0.2  # Estimate risk variance
            
            return {
                'return_range': f"{max(0, expected_return*100-return_variance*100):.1f}% - {(expected_return*100+return_variance*100):.1f}%",
                'risk_range': f"{max(0, volatility*100-risk_variance*100):.1f}% - {(volatility*100+risk_variance*100):.1f}%",
                'confidence': "Based on current market conditions",
                'detailed_metrics': {
                    'expected_return': {
                        'value': f"{expected_return*100:.1f}%",
                        'color': get_return_color(expected_return),
                        'label': 'Expected Return'
                    },
                    'volatility': {
                        'value': f"{volatility*100:.1f}%",
                        'color': get_risk_color(volatility),
                        'label': 'Risk (Volatility)'
                    },
                    'sharpe_ratio': {
                        'value': f"{sharpe_ratio:.2f}",
                        'color': get_sharpe_color(sharpe_ratio),
                        'label': 'Sharpe Ratio'
                    },
                    'max_drawdown': {
                        'value': f"{abs(max_drawdown)*100:.1f}%",
                        'color': 'green' if max_drawdown > -0.10 else 'yellow' if max_drawdown > -0.20 else 'red',
                        'label': 'Max Drawdown'
                    },
                    'diversification_score': {
                        'value': f"{diversification_score:.1f}",
                        'color': get_diversification_color(diversification_score),
                        'label': 'Diversification Score'
                    }
                },
                'color_coding': {
                    'return': get_return_color(expected_return),
                    'risk': get_risk_color(volatility),
                    'sharpe': get_sharpe_color(sharpe_ratio),
                    'diversification': get_diversification_color(diversification_score)
                },
                'performance_grade': self._calculate_performance_grade(portfolio_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error generating range estimates: {e}")
            return {
                'return_range': "8-12%",
                'risk_range': "12-18%",
                'confidence': "Based on current market conditions",
                'detailed_metrics': {
                    'expected_return': {'value': '10.0%', 'color': 'lime', 'label': 'Expected Return'},
                    'volatility': {'value': '15.0%', 'color': 'yellow', 'label': 'Risk (Volatility)'},
                    'sharpe_ratio': {'value': '0.40', 'color': 'yellow', 'label': 'Sharpe Ratio'},
                    'max_drawdown': {'value': '10.0%', 'color': 'green', 'label': 'Max Drawdown'},
                    'diversification_score': {'value': '50.0', 'color': 'yellow', 'label': 'Diversification Score'}
                },
                'color_coding': {'return': 'lime', 'risk': 'yellow', 'sharpe': 'yellow', 'diversification': 'yellow'},
                'performance_grade': 'B'
            }
    
    def _calculate_performance_grade(self, portfolio_metrics: Dict) -> str:
        """Calculate overall performance grade for portfolio"""
        try:
            expected_return = portfolio_metrics.get('expected_return', 0.10)
            volatility = portfolio_metrics.get('volatility', 0.15)
            sharpe_ratio = portfolio_metrics.get('sharpe_ratio', 0.4)
            diversification_score = portfolio_metrics.get('diversification_score', 50.0)
            
            # Scoring system (0-100)
            return_score = min(100, max(0, (expected_return - 0.02) * 500))  # 2% baseline
            risk_score = min(100, max(0, (0.30 - volatility) * 333))  # Lower risk = higher score
            sharpe_score = min(100, max(0, sharpe_ratio * 50))  # Sharpe ratio scoring
            div_score = diversification_score  # Already 0-100
            
            # Weighted average
            overall_score = (return_score * 0.3 + risk_score * 0.3 + sharpe_score * 0.25 + div_score * 0.15)
            
            # Convert to letter grade
            if overall_score >= 90: return 'A+'
            elif overall_score >= 85: return 'A'
            elif overall_score >= 80: return 'A-'
            elif overall_score >= 75: return 'B+'
            elif overall_score >= 70: return 'B'
            elif overall_score >= 65: return 'B-'
            elif overall_score >= 60: return 'C+'
            elif overall_score >= 55: return 'C'
            elif overall_score >= 50: return 'C-'
            elif overall_score >= 45: return 'D+'
            elif overall_score >= 40: return 'D'
            else: return 'F'
            
        except Exception as e:
            logger.error(f"Error calculating performance grade: {e}")
            return 'B'
    
    def _generate_portfolio_combinations(self, asset1_metrics: Dict, 
                                       asset2_metrics: Dict, correlation: float) -> List[Dict]:
        """Generate portfolio combinations with different weights"""
        combinations = [
            [1.0, 0.0],    # 100% asset1
            [0.75, 0.25],  # 75% asset1, 25% asset2
            [0.5, 0.5],    # 50% each
            [0.25, 0.75],  # 25% asset1, 75% asset2
            [0.0, 1.0]     # 100% asset2
        ]
        
        portfolios = []
        for w1, w2 in combinations:
            # Portfolio return
            portfolio_return = w1 * asset1_metrics['annualized_return'] + w2 * asset2_metrics['annualized_return']
            
            # Portfolio risk
            portfolio_risk = np.sqrt(
                w1**2 * asset1_metrics['risk']**2 + 
                w2**2 * asset2_metrics['risk']**2 + 
                2 * w1 * w2 * asset1_metrics['risk'] * 
                asset2_metrics['risk'] * correlation
            )
            
            # Sharpe ratio
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            
            portfolios.append({
                "weights": [w1, w2],
                "return": portfolio_return,
                "risk": portfolio_risk,
                "sharpe_ratio": sharpe_ratio,
                "weight_asset1_pct": w1 * 100,
                "weight_asset2_pct": w2 * 100,
                "is_optimal": False  # Will be set later
            })
        
        # Find optimal portfolio (highest Sharpe ratio)
        if portfolios:
            optimal_idx = max(range(len(portfolios)), key=lambda i: portfolios[i]['sharpe_ratio'])
            portfolios[optimal_idx]['is_optimal'] = True
        
        return portfolios
    
    def calculate_custom_portfolio(self, weight1: float, asset1_metrics: Dict, 
                                 asset2_metrics: Dict, correlation: float) -> Dict:
        """
        Calculate portfolio metrics for custom weight allocation
        Args:
            weight1: Weight for asset 1 (0-1)
            asset1_metrics: Metrics for asset 1
            asset2_metrics: Metrics for asset 2
            correlation: Correlation between assets
        Returns:
            Dict with portfolio metrics
        """
        try:
            w1 = weight1
            w2 = 1.0 - weight1
            
            # Portfolio return
            portfolio_return = w1 * asset1_metrics['annualized_return'] + w2 * asset2_metrics['annualized_return']
            
            # Portfolio risk
            portfolio_risk = np.sqrt(
                w1**2 * asset1_metrics['risk']**2 + 
                w2**2 * asset2_metrics['risk']**2 + 
                2 * w1 * w2 * asset1_metrics['risk'] * 
                asset2_metrics['risk'] * correlation
            )
            
            return {
                "weights": [w1, w2],
                "return": portfolio_return,
                "risk": portfolio_risk,
                "sharpe_ratio": 0, # Removed Sharpe ratio calculation
                "weight_asset1_pct": w1 * 100,
                "weight_asset2_pct": w2 * 100,
                "diversification_benefit": self._calculate_diversification_benefit(
                    asset1_metrics, asset2_metrics, correlation, w1, w2
                )
            }
            
        except Exception as e:
            logger.error(f"Error calculating custom portfolio: {e}")
            return {
                "weights": [0.5, 0.5],
                "return": 0.10,
                "risk": 0.15,
                "sharpe_ratio": 0.4,
                "weight_asset1_pct": 50,
                "weight_asset2_pct": 50,
                "diversification_benefit": 0.0
            }
    
    def _calculate_diversification_benefit(self, asset1_metrics: Dict, asset2_metrics: Dict, 
                                         correlation: float, w1: float, w2: float) -> float:
        """Calculate diversification benefit compared to individual assets"""
        try:
            # Portfolio risk
            portfolio_risk = np.sqrt(
                w1**2 * asset1_metrics['risk']**2 + 
                w2**2 * asset2_metrics['risk']**2 + 
                2 * w1 * w2 * asset1_metrics['risk'] * 
                asset2_metrics['risk'] * correlation
            )
            
            # Weighted average of individual risks
            weighted_avg_risk = w1 * asset1_metrics['risk'] + w2 * asset2_metrics['risk']
            
            # Diversification benefit (risk reduction)
            benefit = (weighted_avg_risk - portfolio_risk) / weighted_avg_risk if weighted_avg_risk > 0 else 0
            
            return max(0, benefit * 100)  # Return as percentage
            
        except Exception as e:
            logger.error(f"Error calculating diversification benefit: {e}")
            return 0.0
    
    def _generate_educational_insights(self, asset1_metrics: Dict, 
                                     asset2_metrics: Dict, correlation: float) -> Dict:
        """Generate educational insights for two-asset comparison"""
        insights = {
            'risk_comparison': '',
            'return_comparison': '',
            'diversification_benefit': '',
            'recommendation': ''
        }
        
        # Risk comparison
        if asset1_metrics['risk'] > asset2_metrics['risk']:
            insights['risk_comparison'] = f"{asset1_metrics.get('ticker', 'Asset 1')} is more volatile than {asset2_metrics.get('ticker', 'Asset 2')}"
        else:
            insights['risk_comparison'] = f"{asset2_metrics.get('ticker', 'Asset 2')} is more volatile than {asset1_metrics.get('ticker', 'Asset 1')}"
        
        # Return comparison
        if asset1_metrics['annualized_return'] > asset2_metrics['annualized_return']:
            insights['return_comparison'] = f"{asset1_metrics.get('ticker', 'Asset 1')} has higher historical returns than {asset2_metrics.get('ticker', 'Asset 2')}"
        else:
            insights['return_comparison'] = f"{asset2_metrics.get('ticker', 'Asset 2')} has higher historical returns than {asset1_metrics.get('ticker', 'Asset 1')}"
        
        # Diversification benefit
        if abs(correlation) < 0.3:
            insights['diversification_benefit'] = "These assets have low correlation, providing good diversification benefits"
        elif abs(correlation) < 0.7:
            insights['diversification_benefit'] = "These assets have moderate correlation, providing some diversification benefits"
        else:
            insights['diversification_benefit'] = "These assets have high correlation, providing limited diversification benefits"
        
        return insights
    
    def _select_assets_by_risk(self, rule: Dict, conservative: List[str], 
                              moderate: List[str], aggressive: List[str]) -> List[Dict]:
        """Select assets based on risk allocation rules with real data"""
        def get_ticker_monthly_data(ticker: str) -> Optional[Dict[str, Any]]:
            """
            Get monthly data for a ticker using Redis-first approach
            Returns: Dict with prices, dates, sector, industry, company name
            """
            try:
                from utils.redis_first_data_service import redis_first_data_service
                return redis_first_data_service.get_monthly_data(ticker)
            except Exception as e:
                logger.error(f"Error getting monthly data for {ticker}: {e}")
                return None

        def get_ticker_cached_metrics(ticker: str) -> Optional[Dict[str, Any]]:
            """
            Get cached metrics for a ticker using Redis-first approach
            Returns: Dict with cached metrics or None
            """
            try:
                from utils.redis_first_data_service import redis_first_data_service
                return redis_first_data_service.get_cached_metrics(ticker)
            except Exception as e:
                logger.error(f"Error getting cached metrics for {ticker}: {e}")
                return None

        def is_ticker_cached(ticker: str) -> bool:
            """
            Check if ticker data is cached using Redis-first approach
            Returns: True if cached, False otherwise
            """
            try:
                from utils.redis_first_data_service import redis_first_data_service
                return redis_first_data_service._is_cached(ticker, 'prices')
            except Exception as e:
                logger.error(f"Error checking cache for {ticker}: {e}")
                return False
        
        selected_assets = []
        
        # Helper function to get asset data
        def get_asset_info(ticker):
            try:
                data = get_ticker_monthly_data(ticker)
                if data:
                    return {
                        'symbol': ticker,
                        'name': data.get('company_name', ticker),
                        'sector': data.get('sector', 'Unknown'),
                        'industry': data.get('industry', 'Unknown')
                    }
                return None
            except:
                return None
        
        # Select conservative assets
        conservative_count = min(2, max(1, int(rule['low_vol'] / 30)))  # 1-2 assets
        available_conservative = [asset for asset in conservative 
                                if is_ticker_cached(asset)][:conservative_count]
        
        for ticker in available_conservative:
            asset_info = get_asset_info(ticker)
            if asset_info:
                selected_assets.append({
                    'symbol': ticker,
                    'allocation': rule['low_vol'] / len(available_conservative),
                    'type': 'conservative',
                    'name': asset_info['name'],
                    'sector': asset_info['sector']
                })
        
        # Select moderate assets
        moderate_count = min(2, max(1, int(rule['moderate'] / 30)))
        available_moderate = [asset for asset in moderate 
                            if is_ticker_cached(asset)][:moderate_count]
        
        for ticker in available_moderate:
            asset_info = get_asset_info(ticker)
            if asset_info:
                selected_assets.append({
                    'symbol': ticker,
                    'allocation': rule['moderate'] / len(available_moderate),
                    'type': 'moderate',
                    'name': asset_info['name'],
                    'sector': asset_info['sector']
                })
        
        # Select aggressive assets (if allocation > 0)
        if rule['high_growth'] > 0:
            aggressive_count = min(1, max(0, int(rule['high_growth'] / 20)))
            available_aggressive = [asset for asset in aggressive 
                                  if is_ticker_cached(asset)][:aggressive_count]
            
            for ticker in available_aggressive:
                asset_info = get_asset_info(ticker)
                if asset_info:
                    selected_assets.append({
                        'symbol': ticker,
                        'allocation': rule['high_growth'] / len(available_aggressive),
                        'type': 'aggressive',
                        'name': asset_info['name'],
                        'sector': asset_info['sector']
                    })
        
        # Ensure we have exactly 4 assets and allocations sum to 100
        selected_assets = selected_assets[:4]  # Limit to 4
        
        # Normalize allocations to sum to 100
        total_allocation = sum(asset['allocation'] for asset in selected_assets)
        if total_allocation > 0:
            for asset in selected_assets:
                asset['allocation'] = (asset['allocation'] / total_allocation) * 100
        
        return selected_assets
    
    def calculate_real_portfolio_metrics(self, portfolio_data: Dict, risk_profile: str = None) -> Dict:
        """Calculate portfolio metrics using real data from portfolio allocations"""
        def get_ticker_monthly_data(ticker: str) -> Optional[Dict[str, Any]]:
            """
            Get monthly data for a ticker using Redis-first approach
            Returns: Dict with prices, dates, sector, industry, company name
            """
            try:
                from utils.redis_first_data_service import redis_first_data_service
                return redis_first_data_service.get_monthly_data(ticker)
            except Exception as e:
                logger.error(f"Error getting monthly data for {ticker}: {e}")
                return None

        def get_ticker_cached_metrics(ticker: str) -> Optional[Dict[str, Any]]:
            """
            Get cached metrics for a ticker using Redis-first approach
            Returns: Dict with cached metrics or None
            """
            try:
                from utils.redis_first_data_service import redis_first_data_service
                return redis_first_data_service.get_cached_metrics(ticker)
            except Exception as e:
                logger.error(f"Error getting cached metrics for {ticker}: {e}")
                return None

        def is_ticker_cached(ticker: str) -> bool:
            """
            Check if ticker data is cached using Redis-first approach
            Returns: True if cached, False otherwise
            """
            try:
                from utils.redis_first_data_service import redis_first_data_service
                return redis_first_data_service._is_cached(ticker, 'prices')
            except Exception as e:
                logger.error(f"Error checking cache for {ticker}: {e}")
                return False
        
        try:
            allocations = portfolio_data.get('allocations', [])
            if not allocations:
                return self._get_fallback_portfolio_metrics(risk_profile)

            # Get real data for each asset
            raw_returns: list = []  # Can contain either pd.Series or dict with cached metrics
            raw_weights: list[float] = []

            for allocation in allocations:
                ticker = allocation['symbol']
                weight = allocation['allocation'] / 100  # percentage to decimal

                # Get pre-calculated metrics from cache first
                cached_metrics = get_ticker_cached_metrics(ticker)
                if cached_metrics:
                    # Handle different naming conventions for cached metrics
                    annual_return = None
                    annual_risk = None
                    
                    # Try different possible key names
                    # Note: annualized_return may be stored as percentage (12) or decimal (0.12)
                    if cached_metrics.get('annualized_return') is not None:
                        annual_return = float(cached_metrics['annualized_return'])
                    elif cached_metrics.get('annual_return') is not None:
                        annual_return = float(cached_metrics['annual_return'])
                    elif cached_metrics.get('expected_return') is not None:
                        annual_return = float(cached_metrics['expected_return'])
                    # Normalize to decimal: if value > 1, assume percentage format
                    if annual_return is not None and abs(annual_return) > 1:
                        annual_return = annual_return / 100.0
                    
                    if cached_metrics.get('risk') is not None:
                        annual_risk = float(cached_metrics['risk'])
                    elif cached_metrics.get('annual_risk') is not None:
                        annual_risk = float(cached_metrics['annual_risk'])
                    elif cached_metrics.get('annualized_risk') is not None:
                        annual_risk = float(cached_metrics['annualized_risk'])
                    elif cached_metrics.get('volatility') is not None:
                        annual_risk = float(cached_metrics['volatility'])
                    # Normalize to decimal: if value > 1, assume percentage format
                    if annual_risk is not None and annual_risk > 1:
                        annual_risk = annual_risk / 100.0
                    
                    # Only use cached metrics if both return and risk are available
                    if annual_return is not None and annual_risk is not None:
                        # Use cached metrics directly for portfolio calculation
                        # Store annual metrics for weighted calculation
                        raw_returns.append({
                            'annual_return': annual_return,
                            'annual_risk': annual_risk,
                            'weight': weight,
                            'use_cached': True,
                            'ticker': ticker
                        })
                        raw_weights.append(weight)
                        continue

                # Fallback: get monthly data and calculate
                data = get_ticker_monthly_data(ticker)
                if data and data.get('prices'):
                    prices = np.array(data['prices'], dtype=float)
                    if prices.size >= 3:
                        returns = pd.Series(prices).pct_change().dropna()
                        raw_returns.append(returns)
                        raw_weights.append(weight)
                        continue

                # Warm-and-retry: attempt to fetch data via Redis-first service
                try:
                    from utils.redis_first_data_service import redis_first_data_service as _rds
                    _ = _rds.get_monthly_data(ticker)
                    _ = _rds.get_ticker_info(ticker)
                    # Re-attempt loading using helpers
                    data_retry = get_ticker_monthly_data(ticker)
                    if data_retry and data_retry.get('prices'):
                        prices = np.array(data_retry['prices'], dtype=float)
                        if prices.size >= 3:
                            returns = pd.Series(prices).pct_change().dropna()
                            raw_returns.append(returns)
                            raw_weights.append(weight)
                            continue
                except Exception:
                    pass

                # If still unavailable, skip this ticker (do not synthesize)
                logger.warning(f"Skipping {ticker}: no cached/sourced data available after warm retry")

            if not raw_returns:
                return self._get_fallback_portfolio_metrics(risk_profile)

            # Separate cached metrics from calculated returns
            cached_assets = []
            calculated_assets = []
            
            for i, asset_data in enumerate(raw_returns):
                if isinstance(asset_data, dict) and asset_data.get('use_cached'):
                    cached_assets.append(asset_data)
                else:
                    calculated_assets.append(asset_data)
            
            # Debug logging
            logger.info(f"Portfolio calculation debug: {len(cached_assets)} cached assets, {len(calculated_assets)} calculated assets")
            logger.info(f"raw_returns length: {len(raw_returns)}")
            
            # Calculate portfolio metrics using the appropriate method
            if cached_assets and calculated_assets:
                # Mixed case: combine cached and calculated assets
                # For cached assets, use their annual metrics
                # For calculated assets, compute from return series
                
                # Process calculated assets to get their metrics
                calculated_returns = []
                calculated_weights_list = []
                
                for i, asset_data in enumerate(raw_returns):
                    if not (isinstance(asset_data, dict) and asset_data.get('use_cached')):
                        calculated_returns.append(asset_data)
                        calculated_weights_list.append(raw_weights[i])
                
                if calculated_returns:
                    # Calculate metrics for calculated assets
                    min_length = min(len(returns) for returns in calculated_returns)
                    aligned_calc_returns = [returns.iloc[-min_length:] for returns in calculated_returns]
                    
                    # Calculate annual return and risk for each calculated asset
                    annual_factor = np.sqrt(12)
                    calculated_metrics = []
                    for returns in aligned_calc_returns:
                        monthly_return = returns.mean()
                        monthly_risk = returns.std()
                        ann_return = (1 + monthly_return) ** 12 - 1
                        ann_risk = monthly_risk * annual_factor
                        calculated_metrics.append({
                            'annual_return': ann_return,
                            'annual_risk': ann_risk
                        })
                    
                    # Combine cached and calculated assets
                    all_assets = []
                    all_weights = []
                    
                    for asset in cached_assets:
                        all_assets.append({
                            'annual_return': asset['annual_return'],
                            'annual_risk': asset['annual_risk'],
                            'ticker': asset['ticker']
                        })
                        all_weights.append(asset['weight'])
                    
                    for i, metrics in enumerate(calculated_metrics):
                        all_assets.append(metrics)
                        all_weights.append(calculated_weights_list[i])
                    
                    # Normalize weights
                    total_weight = sum(all_weights)
                    if total_weight <= 0:
                        return self._get_fallback_portfolio_metrics(risk_profile)
                    normalized_weights = np.array([w / total_weight for w in all_weights])
                    
                    # Calculate portfolio return
                    weighted_return = sum(asset['annual_return'] * weight for asset, weight in zip(all_assets, normalized_weights))
                    
                    # Reject negative returns
                    if weighted_return <= 0:
                        logger.warning(
                            f"Portfolio calculation rejected: Negative return {weighted_return:.2%} "
                            f"from mixed assets"
                        )
                        return self._get_fallback_portfolio_metrics(risk_profile)
                    
                    # For risk calculation with mixed assets, use simplified approach
                    # Try to get correlation matrix for all tickers if possible
                    try:
                        tickers = [asset.get('ticker', f'CALC_{i}') for i, asset in enumerate(all_assets)]
                        # Only use correlation if we have tickers for all assets
                        if all(t and not t.startswith('CALC_') for t in tickers):
                            correlation_matrix = self._get_correlation_matrix_for_tickers(tickers)
                            individual_risks = np.array([asset['annual_risk'] for asset in all_assets])
                            
                            portfolio_variance = 0
                            for i in range(len(normalized_weights)):
                                for j in range(len(normalized_weights)):
                                    if i == j:
                                        portfolio_variance += (normalized_weights[i] ** 2) * (individual_risks[i] ** 2)
                                    else:
                                        correlation = correlation_matrix.iloc[i, j] if hasattr(correlation_matrix, 'iloc') else correlation_matrix[i][j]
                                        if pd.isna(correlation):
                                            correlation = 0.0
                                        portfolio_variance += normalized_weights[i] * normalized_weights[j] * correlation * individual_risks[i] * individual_risks[j]
                            
                            weighted_risk = np.sqrt(max(portfolio_variance, 0.0))
                        else:
                            # Fallback: use diversification factor
                            simple_weighted_risk = sum(asset['annual_risk'] * weight for asset, weight in zip(all_assets, normalized_weights))
                            diversification_factor = 0.72
                            weighted_risk = simple_weighted_risk * diversification_factor
                    except Exception as e:
                        logger.warning(f"Could not calculate correlation-based risk for mixed assets, using diversification factor: {e}")
                        simple_weighted_risk = sum(asset['annual_risk'] * weight for asset, weight in zip(all_assets, normalized_weights))
                        diversification_factor = 0.72
                        weighted_risk = simple_weighted_risk * diversification_factor
                    
                    ann_return = weighted_return
                    ann_risk = weighted_risk
                    
                    # Calculate diversification score
                    allocations = portfolio_data.get('allocations', [])
                    if allocations:
                        diversification_score = self._calculate_simple_diversification_score(allocations)
                    else:
                        diversification_score = min(100, len(all_assets) * 25)
                    
                    logger.info(f"Portfolio calculation using mixed assets: {len(cached_assets)} cached, {len(calculated_returns)} calculated")
                    logger.info(f"  Weighted return: {weighted_return:.2%}, Weighted risk: {weighted_risk:.2%}")
                    
                    # Clear calculated_assets to prevent falling through to elif calculated_assets block
                    calculated_assets = []
                else:
                    # No calculated assets after filtering, treat as cached-only
                    # Set calculated_assets to empty so it falls through to cached-only path
                    calculated_assets = []
            
            if cached_assets and not calculated_assets:
                # All assets have cached metrics - use proper portfolio theory
                total_weight = sum(asset['weight'] for asset in cached_assets)
                if total_weight <= 0:
                    return self._get_fallback_portfolio_metrics()
                
                # Normalize weights
                normalized_weights = np.array([asset['weight'] / total_weight for asset in cached_assets])
                
                # Calculate portfolio return (weighted average is correct for returns)
                weighted_return = sum(asset['annual_return'] * weight for asset, weight in zip(cached_assets, normalized_weights))
                
                # CRITICAL: Reject portfolios with negative returns
                if weighted_return <= 0:
                    logger.warning(
                        f"Portfolio calculation rejected: Negative return {weighted_return:.2%} "
                        f"from stocks: {[a['ticker'] for a in cached_assets]}"
                    )
                    # Return fallback metrics instead
                    return self._get_fallback_portfolio_metrics(risk_profile)
                
                # CRITICAL FIX: Calculate portfolio risk using correlation matrix
                # Get correlation data for these tickers
                tickers = [asset['ticker'] for asset in cached_assets]
                
                # Try to get correlation matrix from cached data or calculate it
                try:
                    correlation_matrix = self._get_correlation_matrix_for_tickers(tickers)
                    
                    # Extract individual risks
                    individual_risks = np.array([asset['annual_risk'] for asset in cached_assets])
                    
                    # Calculate portfolio variance using proper formula:
                    # σ²_portfolio = Σᵢ Σⱼ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ
                    portfolio_variance = 0
                    for i in range(len(normalized_weights)):
                        for j in range(len(normalized_weights)):
                            if i == j:
                                # Diagonal: individual asset variance
                                portfolio_variance += (normalized_weights[i] ** 2) * (individual_risks[i] ** 2)
                            else:
                                # Off-diagonal: correlation term
                                correlation = correlation_matrix.iloc[i, j] if hasattr(correlation_matrix, 'iloc') else correlation_matrix[i][j]
                                if pd.isna(correlation):
                                    correlation = 0.0  # Default to no correlation if missing
                                portfolio_variance += normalized_weights[i] * normalized_weights[j] * correlation * individual_risks[i] * individual_risks[j]
                    
                    # Portfolio risk is square root of variance
                    weighted_risk = np.sqrt(max(portfolio_variance, 0.0))
                    
                except Exception as e:
                    logger.warning(f"Could not calculate correlation-based risk, using diversification factor: {e}")
                    # Fallback: Use diversification factor (0.72) to approximate correlation effects
                    # This is better than simple weighted average
                    simple_weighted_risk = sum(asset['annual_risk'] * weight for asset, weight in zip(cached_assets, normalized_weights))
                    diversification_factor = 0.72  # Based on typical correlation of ~0.3 for 4 stocks
                    weighted_risk = simple_weighted_risk * diversification_factor
                
                ann_return = weighted_return
                ann_risk = weighted_risk
                
                # Calculate simple diversification score using allocations data
                # Extract allocations from portfolio data
                allocations = portfolio_data.get('allocations', [])
                if allocations:
                    # Use simple diversification score: stock count + sector count
                    diversification_score = self._calculate_simple_diversification_score(allocations)
                else:
                    diversification_score = min(100, len(cached_assets) * 25)  # Fallback
                
                # Debug logging
                logger.info(f"Portfolio calculation using cached metrics: {len(cached_assets)} assets")
                for i, asset in enumerate(cached_assets):
                    logger.info(f"  {asset['ticker']}: {asset['annual_return']:.2%} return, {asset['annual_risk']:.2%} risk, weight={normalized_weights[i]:.2%}")
                logger.info(f"  Weighted return: {weighted_return:.2%}, Weighted risk: {weighted_risk:.2%}")
                
            elif calculated_assets:
                # Some assets need calculation - use the original method
                # Filter to only calculated assets (not cached)
                asset_returns = []
                calculated_weights = []
                
                for i, asset_data in enumerate(raw_returns):
                    if not (isinstance(asset_data, dict) and asset_data.get('use_cached')):
                        asset_returns.append(asset_data)
                        calculated_weights.append(raw_weights[i])
                
                if not asset_returns:
                    return self._get_fallback_portfolio_metrics(risk_profile)
                
                # Normalize weights of calculated assets to sum to 1
                total_weight = sum(calculated_weights)
                if total_weight <= 0:
                    return self._get_fallback_portfolio_metrics(risk_profile)
                weights = [w / total_weight for w in calculated_weights]
                
                # Align all return series to same length
                min_length = min(len(returns) for returns in asset_returns)
                aligned_returns = [returns.iloc[-min_length:] for returns in asset_returns]
                
                # Calculate portfolio return series
                portfolio_returns = pd.Series(0.0, index=aligned_returns[0].index)
                for i, (weight, returns) in enumerate(zip(weights, aligned_returns)):
                    portfolio_returns += weight * returns
                
                # Calculate metrics using numpy/pandas
                annual_factor = np.sqrt(12)  # For monthly data
                
                # Calculate basic statistics
                monthly_return = portfolio_returns.mean()
                monthly_risk = portfolio_returns.std()
                
                # Calculate portfolio risk using proper correlation matrix
                if len(aligned_returns) > 1:
                    # Create correlation matrix
                    returns_df = pd.concat(aligned_returns, axis=1)
                    corr_matrix = returns_df.corr()
                    
                    # Ensure correlation matrix size matches aligned_returns
                    n_assets = len(aligned_returns)
                    if corr_matrix.shape[0] != n_assets or corr_matrix.shape[1] != n_assets:
                        logger.warning(f"Correlation matrix size mismatch: expected {n_assets}x{n_assets}, got {corr_matrix.shape}")
                        # Fallback to simple risk calculation
                        monthly_risk = portfolio_returns.std()
                    else:
                        # Calculate portfolio variance using weights and correlation
                        portfolio_variance = 0
                        for i in range(n_assets):
                            for j in range(n_assets):
                                if i == j:
                                    # Diagonal: individual asset variance
                                    asset_risk = aligned_returns[i].std()
                                    portfolio_variance += (weights[i] ** 2) * (asset_risk ** 2)
                                else:
                                    # Off-diagonal: correlation term
                                    correlation = corr_matrix.iloc[i, j] if not pd.isna(corr_matrix.iloc[i, j]) else 0
                                    asset_i_risk = aligned_returns[i].std()
                                    asset_j_risk = aligned_returns[j].std()
                                    portfolio_variance += 2 * weights[i] * weights[j] * correlation * asset_i_risk * asset_j_risk
                        
                        # Portfolio risk is square root of variance
                        monthly_risk = np.sqrt(max(portfolio_variance, 0.0))
                
                # Annualize metrics
                ann_return = (1 + monthly_return) ** 12 - 1  # Compound annual return
                ann_risk = monthly_risk * annual_factor      # Annualized risk
                
                # CRITICAL: Reject portfolios with negative returns
                if ann_return <= 0:
                    logger.warning(
                        f"Portfolio calculation rejected: Negative return {ann_return:.2%} "
                        f"from calculated assets"
                    )
                    # Return fallback metrics instead
                    return self._get_fallback_portfolio_metrics(risk_profile)
                
                # Calculate diversification score
                diversification_score = self._calculate_portfolio_diversification_score(aligned_returns, weights)
                
            else:
                return self._get_fallback_portfolio_metrics()
            
            # Calculate max drawdown - only for calculated assets
            max_drawdown = -0.10  # Default fallback value
            if calculated_assets and 'portfolio_returns' in locals():
                try:
                    cumulative = (1 + portfolio_returns).cumprod()
                    rolling_max = cumulative.expanding().max()
                    drawdowns = (cumulative - rolling_max) / rolling_max
                    max_drawdown = float(drawdowns.min())
                except Exception as e:
                    logger.warning(f"Failed to calculate max drawdown: {e}")
                    max_drawdown = -0.10
            
            # CRITICAL: Final validation - reject negative returns
            if ann_return <= 0:
                logger.warning(
                    f"Portfolio calculation FINAL REJECTION: Negative return {ann_return:.2%} "
                    f"after all calculations. Using fallback."
                )
                return self._get_fallback_portfolio_metrics(risk_profile)
            
            # Ensure all metrics are JSON-compliant (no NaN, inf, or -inf)
            ann_return = self._sanitize_metric_value(ann_return, 0.10)  # Default to 10% if invalid
            ann_risk = self._sanitize_metric_value(ann_risk, 0.15)      # Default to 15% if invalid
            max_drawdown = self._sanitize_metric_value(max_drawdown, -0.10)  # Default to -10% if invalid
            
            # CRITICAL: Double-check after sanitization
            if ann_return <= 0:
                logger.warning(f"Portfolio return still non-positive after sanitization: {ann_return:.2%}")
                return self._get_fallback_portfolio_metrics(risk_profile)
            
            # Calculate diversification score - use consistent method matching recommendation system
            # Always use sophisticated method for consistency with recommendation generation
            allocations = portfolio_data.get('allocations', [])
            if allocations:
                # Use sophisticated diversification calculation to match recommendation system
                diversification_score = self._calculate_sophisticated_diversification_score(allocations)
            elif calculated_assets and 'aligned_returns' in locals() and 'weights' in locals():
                # Fallback to correlation-based if no allocations but have calculated assets
                diversification_score = self._calculate_portfolio_diversification_score(aligned_returns, weights)
            elif cached_assets:
                # Fallback for cached assets without allocations
                diversification_score = min(100, len(cached_assets) * 25)
            else:
                # Final fallback
                diversification_score = 50.0
            
            diversification_score = self._sanitize_metric_value(diversification_score, 50.0)  # Default to 50 if invalid
            
            metrics = {
                'expected_return': ann_return,
                'risk': ann_risk,  # Consistent naming: 'risk' not 'volatility'
                'max_drawdown': max_drawdown,
                'diversification_score': diversification_score
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating real portfolio metrics: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._get_fallback_portfolio_metrics()
    
    def _calculate_allocation_diversification_score(self, weights: List[float]) -> float:
        """Ultra-simple diversification score: stock count + sector count only"""
        try:
            if not weights or len(weights) < 2:
                return 0.0
            
            # This method is now simplified - actual diversification calculation
            # is done in the main portfolio calculation using allocations data
            # which includes sector information
            
            # For backward compatibility, return a basic score based on stock count
            num_stocks = len(weights)
            stock_score = min(60, num_stocks * 12)  # Max 60 points for 5+ stocks
            
            # Basic fallback score (will be overridden by actual calculation)
            return min(100, stock_score + 40)  # Assume 40 points for sector diversity
            
        except Exception as e:
            logger.error(f"Error calculating allocation diversification score: {e}")
            return 75.0  # Realistic fallback value
    
    def _calculate_sophisticated_diversification_score(self, allocations: List[Dict]) -> float:
        """
        Enhanced diversification score with improved sector diversity, correlation, and variation
        """
        try:
            if not allocations or len(allocations) < 2:
                return 0.0
            
            # Extract weights and tickers
            weights = [alloc.get('allocation', 0) / 100.0 for alloc in allocations]  # Convert to decimal
            tickers = [alloc.get('symbol', '') for alloc in allocations]
            
            # Get sector info - enrich from Redis if not provided in allocation
            sectors = []
            for alloc in allocations:
                sector = alloc.get('sector')
                if not sector or sector == 'Unknown':
                    # Try to get sector from Redis
                    ticker = alloc.get('symbol', '')
                    if ticker:
                        try:
                            from utils.redis_first_data_service import redis_first_data_service
                            ticker_info = redis_first_data_service.get_ticker_info(ticker)
                            if ticker_info:
                                sector = ticker_info.get('sector', 'Unknown')
                        except Exception:
                            sector = 'Unknown'
                    else:
                        sector = 'Unknown'
                sectors.append(sector or 'Unknown')
            
            # Calculate concentration metrics
            weights_array = np.array(weights)
            max_weight = np.max(weights_array)
            min_weight = np.min(weights_array)
            weight_std = np.std(weights_array)
            
            # Calculate Herfindahl-Hirschman Index (HHI) - concentration measure
            hhi = np.sum(weights_array ** 2)
            
            # Convert HHI to base diversification score
            base_diversification = max(0.0, (1 - hhi) * 100)
            
            # Stock count adjustment (more stocks = higher potential diversification) - INCREASED
            n_stocks = len(weights)
            stock_bonus = min(10.0, (n_stocks - 3) * 2.0)  # Increased from 1.5 to 2.0, max from 8 to 10
            
            # Weight distribution evenness (more even = higher diversification) - INCREASED
            weight_evenness = 1 - (max_weight - min_weight)
            evenness_bonus = weight_evenness * 5  # Increased from 3 to 5
            
            # Weight variance penalty (higher variance = lower diversification) - INCREASED
            variance_penalty = min(10.0, weight_std * 30)  # Increased from 5 to 10, multiplier from 20 to 30
            
            # IMPROVED Sector diversification analysis
            sector_counts = {}
            sector_weights = {}
            
            for sector, weight in zip(sectors, weights):
                if sector in sector_counts:
                    sector_counts[sector] += 1
                    sector_weights[sector] += weight
                else:
                    sector_counts[sector] = 1
                    sector_weights[sector] = weight
            
            # Calculate sector concentration using HHI
            total_sector_weight = sum(sector_weights.values())
            sector_hhi = sum((w / total_sector_weight) ** 2 for w in sector_weights.values()) if total_sector_weight > 0 else 1.0
            
            # Sector concentration penalty - IMPROVED
            sector_concentration = max(sector_weights.values()) if sector_weights else 1.0
            sector_penalty = max(0, (sector_concentration - 0.4) * 15)  # Increased penalty, starts at 40% instead of 50%
            
            # Sector diversity bonus - IMPROVED
            num_unique_sectors = len([s for s in sector_counts.keys() if s != 'Unknown'])
            # Use sector HHI for more accurate bonus
            sector_diversity_score = (1 - sector_hhi) * 15  # Up to 15 points (increased from 12)
            sector_bonus = min(15.0, sector_diversity_score + (num_unique_sectors * 1.5))  # Increased multipliers
            
            # ADDED: Correlation factor (if price data available)
            correlation_penalty = 0.0
            try:
                # Try to get correlation from ticker price data
                from utils.redis_first_data_service import redis_first_data_service
                
                returns_data = {}
                valid_tickers = []
                
                for ticker in tickers:
                    if ticker:
                        data = redis_first_data_service.get_monthly_data(ticker)
                        if data and 'prices' in data and len(data['prices']) > 1:
                            prices = pd.Series(data['prices'])
                            returns = prices.pct_change().dropna()
                            if len(returns) >= 3:
                                returns_data[ticker] = returns
                                valid_tickers.append(ticker)
                
                # Calculate correlation if we have at least 2 valid tickers
                if len(returns_data) >= 2:
                    # Align returns to same length
                    min_length = min(len(returns_data[t]) for t in valid_tickers)
                    if min_length >= 3:
                        aligned_returns = {t: returns_data[t][:min_length] for t in valid_tickers}
                        returns_df = pd.DataFrame(aligned_returns)
                        corr_matrix = returns_df.corr()
                        
                        # Calculate weighted average correlation
                        total_weight = 0
                        weighted_corr = 0
                        for i, ticker1 in enumerate(valid_tickers):
                            for j, ticker2 in enumerate(valid_tickers):
                                if i < j:  # Avoid double counting
                                    weight_pair = weights[i] * weights[j]
                                    corr_value = abs(corr_matrix.loc[ticker1, ticker2])
                                    if not pd.isna(corr_value):
                                        weighted_corr += weight_pair * corr_value
                                        total_weight += weight_pair
                        
                        if total_weight > 0:
                            avg_correlation = weighted_corr / total_weight
                            # Align with recommendation system: penalize correlation above 0.3 (same threshold)
                            # Strategy optimizer uses: (avg_corr - 0.3) * 25, we use similar but adjusted for additional factors
                            correlation_penalty = max(0, (avg_correlation - 0.3) * 20)  # Penalize above 0.3, up to ~14 points
                
            except Exception as e:
                logger.debug(f"Correlation calculation skipped: {e}")
                correlation_penalty = 0.0
            
            # ADDED: Shannon entropy for weight distribution
            weight_entropy = -sum(w * np.log(w + 1e-10) for w in weights_array if w > 0)
            max_entropy = np.log(n_stocks)
            entropy_ratio = weight_entropy / max_entropy if max_entropy > 0 else 0
            entropy_bonus = entropy_ratio * 8  # Up to 8 points bonus for high entropy
            
            # Calculate final score with all factors
            final_score = (base_diversification + stock_bonus + evenness_bonus + 
                          sector_bonus + entropy_bonus - variance_penalty - sector_penalty - correlation_penalty)
            
            # REMOVED: Random variation and hash-based variation causes inconsistency
            # Use deterministic score based on actual portfolio characteristics only
            # This ensures consistency when same portfolio is calculated multiple times
            # and matches recommendation system behavior
            
            # Normalize to match recommendation system range (0-100)
            # Strategy optimizer caps at 100, we use same range for consistency
            return max(0.0, min(100.0, round(final_score, 1)))
            
        except Exception as e:
            logger.error(f"Error calculating sophisticated diversification score: {e}")
            return 65.0  # Realistic fallback value
    
    def _calculate_simple_diversification_score(self, allocations: List[Dict]) -> float:
        """
        Ultra-simple diversification score: only sector count + stock count
        """
        try:
            num_stocks = len(allocations)
            sectors = set(alloc.get('sector', 'Unknown') for alloc in allocations)
            num_sectors = len(sectors)
            
            # Stock count score (max 60 points for 5+ stocks)
            stock_score = min(60, num_stocks * 12)
            
            # Sector count score (max 40 points for 5+ sectors)  
            sector_score = min(40, num_sectors * 8)
            
            # Total score (0-100)
            total_score = stock_score + sector_score
            
            return min(100, max(0, total_score))
            
        except Exception as e:
            logger.error(f"Error calculating simple diversification score: {e}")
            return 75.0
    
    def _calculate_portfolio_diversification_score(self, asset_returns: List[pd.Series], weights: List[float]) -> float:
        """Calculate diversification score for portfolio"""
        try:
            if len(asset_returns) < 2:
                return 0.0
            
            # Create correlation matrix
            returns_df = pd.concat(asset_returns, axis=1)
            corr_matrix = returns_df.corr()
            
            # Calculate weighted average correlation
            total_weight_pairs = 0
            weighted_correlation = 0
            
            for i in range(len(weights)):
                for j in range(i + 1, len(weights)):
                    weight_pair = weights[i] * weights[j]
                    correlation = corr_matrix.iloc[i, j]
                    
                    if not pd.isna(correlation):
                        weighted_correlation += weight_pair * abs(correlation)
                        total_weight_pairs += weight_pair
            
            avg_correlation = weighted_correlation / total_weight_pairs if total_weight_pairs > 0 else 0
            
            # Convert to diversification score (0-100)
            diversification_score = max(0, 100 - (avg_correlation * 100))
            
            return round(diversification_score, 1)
            
        except Exception as e:
            logger.error(f"Error calculating portfolio diversification score: {e}")
            return 50.0
    
    def _calculate_diversification_score(self, weights: List[float], 
                                       asset_returns: List[pd.Series]) -> float:
        """Calculate diversification score based on correlation matrix"""
        try:
            # Create correlation matrix
            returns_df = pd.concat(asset_returns, axis=1)
            corr_matrix = returns_df.corr()
            
            # Calculate average correlation (excluding diagonal)
            n = len(corr_matrix)
            total_corr = 0
            count = 0
            
            for i in range(n):
                for j in range(n):
                    if i != j:
                        total_corr += abs(corr_matrix.iloc[i, j])
                        count += 1
            
            avg_correlation = total_corr / count if count > 0 else 0
            
            # Convert to diversification score (0-100)
            diversification_score = max(0, 100 - (avg_correlation * 100))
            
            return round(diversification_score, 1)
            
        except Exception as e:
            logger.error(f"Error calculating diversification score: {e}")
            return 50.0  # Default score
    
    def _generate_portfolio_description(self, risk_profile: str, option: int) -> str:
        """Generate portfolio description based on risk profile and option"""
        descriptions = {
            'very-conservative': [
                'Maximum capital preservation with stable dividend stocks',
                'Conservative growth with low volatility assets',
                'Income-focused portfolio with defensive positioning'
            ],
            'conservative': [
                'Balanced conservative approach with steady growth',
                'Dividend growth strategy with moderate risk',
                'Stable portfolio with defensive characteristics'
            ],
            'moderate': [
                'Balanced growth and value approach',
                'Moderate risk with diversified exposure',
                'Growth-oriented with risk management'
            ],
            'aggressive': [
                'Growth-focused with higher return potential',
                'Sector rotation strategy for maximum growth',
                'High-growth portfolio with calculated risk'
            ],
            'very-aggressive': [
                'Maximum growth potential with highest risk tolerance',
                'Technology and growth-focused strategy',
                'High-conviction growth portfolio'
            ]
        }
        
        profile_descriptions = descriptions.get(risk_profile, descriptions['moderate'])
        return profile_descriptions[option % len(profile_descriptions)]
    
    def _get_fallback_metrics(self) -> Dict:
        """Fallback metrics when calculation fails"""
        return {
            'annualized_return': 0.10,
            'risk': 0.15,
            'max_drawdown': -0.10,
            'data_points': 0,
            'data_quality': 'limited'
        }
    
    def _get_fallback_two_asset_analysis(self, ticker1: str, ticker2: str) -> Dict:
        """Fallback two-asset analysis when calculation fails"""
        return {
            'ticker1': ticker1.upper(),
            'ticker2': ticker2.upper(),
            'asset1_stats': {
                'ticker': ticker1.upper(),
                'annualized_return': 0.12,
                'annualized_volatility': 0.20,
                'sharpe_ratio': 0.4,
                'price_history': [],
                'last_price': 0,
                'data_points': 0,
                'data_quality': 'limited'
            },
            'asset2_stats': {
                'ticker': ticker2.upper(),
                'annualized_return': 0.10,
                'annualized_volatility': 0.15,
                'sharpe_ratio': 0.4,
                'price_history': [],
                'last_price': 0,
                'data_points': 0,
                'data_quality': 'limited'
            },
            'correlation': 0.3,
            'portfolios': [],
            'educational_insights': {
                'risk_comparison': 'Unable to calculate risk comparison',
                'return_comparison': 'Unable to calculate return comparison',
                'diversification_benefit': 'Unable to calculate diversification benefits',
                'recommendation': 'Please try again with different assets'
            }
        }
    
    def _get_fallback_portfolios(self, risk_profile: str) -> List[Dict]:
        """Fallback portfolios when calculation fails"""
        return [
            {
                'name': 'Fallback Portfolio',
                'description': 'Conservative fallback portfolio',
                'allocations': [
                    {'symbol': 'AAPL', 'allocation': 25, 'type': 'moderate'},
                    {'symbol': 'MSFT', 'allocation': 25, 'type': 'moderate'},
                    {'symbol': 'GOOGL', 'allocation': 25, 'type': 'moderate'},
                    {'symbol': 'AMZN', 'allocation': 25, 'type': 'moderate'}
                ],
                'metrics': self._get_fallback_portfolio_metrics(),
                'range_estimates': {
                    'return_range': '8-12%',
                    'risk_range': '12-18%',
                    'confidence': 'Based on current market conditions',
                    'color_coding': {'return': 'green', 'risk': 'orange', 'sharpe': 'blue'}
                }
            }
        ]
    
    def _get_correlation_matrix_for_tickers(self, tickers: List[str]) -> pd.DataFrame:
        """Get correlation matrix for given tickers"""
        try:
            from utils.redis_first_data_service import redis_first_data_service
            
            # Get monthly returns for all tickers
            returns_data = {}
            for ticker in tickers:
                data = redis_first_data_service.get_monthly_data(ticker)
                if data and data.get('prices'):
                    prices = pd.Series(data['prices'])
                    returns = prices.pct_change().dropna()
                    if len(returns) >= 12:  # Need at least 12 months
                        returns_data[ticker] = returns
            
            if len(returns_data) < 2:
                # Not enough data, return identity matrix (no correlation)
                return pd.DataFrame(np.eye(len(tickers)), index=tickers, columns=tickers)
            
            # Align returns to same time period
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()  # Remove rows with missing data
            
            if len(returns_df) < 12:
                # Not enough overlapping data
                return pd.DataFrame(np.eye(len(tickers)), index=tickers, columns=tickers)
            
            # Calculate correlation matrix
            correlation_matrix = returns_df.corr().fillna(0.0)
            
            # Ensure all tickers are in the matrix (add missing ones with zero correlation)
            for ticker in tickers:
                if ticker not in correlation_matrix.index:
                    correlation_matrix.loc[ticker] = 0.0
                    correlation_matrix[ticker] = 0.0
                if ticker not in correlation_matrix.columns:
                    correlation_matrix[ticker] = 0.0
            
            # Reorder to match ticker order
            correlation_matrix = correlation_matrix.loc[tickers, tickers]
            
            return correlation_matrix
            
        except Exception as e:
            logger.warning(f"Error calculating correlation matrix: {e}")
            # Return identity matrix (no correlation) as fallback
            return pd.DataFrame(np.eye(len(tickers)), index=tickers, columns=tickers)
    
    def _get_fallback_portfolio_metrics(self, risk_profile: str = None) -> Dict:
        """Fallback portfolio metrics when calculation fails"""
        try:
            from .risk_profile_config import get_fallback_metrics_for_profile
            # Default to moderate if no profile provided
            profile = risk_profile if risk_profile else 'moderate'
            fallback_metrics = get_fallback_metrics_for_profile(profile)
            
            # CRITICAL: Ensure fallback has positive return
            if fallback_metrics.get('expected_return', 0) <= 0:
                logger.warning(f"Fallback metrics have non-positive return, using default")
                fallback_metrics['expected_return'] = 0.10
            
            logger.warning(f"🔴 Using fallback metrics for {profile}: return={fallback_metrics.get('expected_return', 0)*100:.2f}%")
            return fallback_metrics
        except Exception as e:
            logger.warning(f"Error getting fallback metrics for {risk_profile}: {e}")
        
        # Final fallback with guaranteed positive return
        return {
            'expected_return': 0.10,  # Guaranteed positive
            'risk': 0.15,
            'diversification_score': 50.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': -0.10,
            'data_quality': 'fallback'
        }
    
    def _sanitize_metric_value(self, value: float, default_value: float) -> float:
        """
        Ensure metric values are JSON-compliant by replacing NaN, inf, -inf with default values
        
        Args:
            value: The metric value to sanitize
            default_value: The default value to use if the metric is invalid
            
        Returns:
            A JSON-compliant float value
        """
        import math
        
        # Check for NaN, inf, or -inf
        if math.isnan(value) or math.isinf(value):
            logger.warning(f"Invalid metric value detected: {value}, using default: {default_value}")
            return default_value
        
        # Ensure the value is a finite number
        if not isinstance(value, (int, float)):
            logger.warning(f"Non-numeric metric value detected: {type(value)}, using default: {default_value}")
            return default_value
            
        return float(value)

    # NEW: Dynamic Portfolio Generation Methods
    def generate_dynamic_portfolios(self, risk_profile: str, available_assets: List[str], 
                                  target_return: Optional[float] = None, 
                                  max_risk: Optional[float] = None,
                                  num_portfolios: int = 5) -> List[Dict]:
        """
        Generate dynamic portfolios based on risk profile and available assets
        Uses advanced optimization techniques for personalized recommendations
        
        Args:
            risk_profile: User's risk tolerance level
            available_assets: List of available ticker symbols
            target_return: Optional target return constraint
            max_risk: Optional maximum risk constraint
            num_portfolios: Number of portfolios to generate
            
        Returns:
            List of optimized portfolio configurations
        """
        try:
            # Get asset metrics for all available assets
            asset_metrics = self._get_asset_metrics_batch(available_assets)
            if not asset_metrics:
                logger.warning("No asset metrics available for dynamic portfolio generation")
                return self._get_fallback_portfolios(risk_profile)
            
            # Apply risk profile constraints
            filtered_assets = self._filter_assets_by_risk_profile(asset_metrics, risk_profile)
            
            # Generate optimized portfolios using different strategies
            portfolios = []
            
            # Strategy 1: Risk-Adjusted Return Optimization (Sharpe Ratio)
            sharpe_portfolio = self._optimize_sharpe_ratio(filtered_assets, target_return, max_risk)
            if sharpe_portfolio:
                portfolios.append(sharpe_portfolio)
            
            # Strategy 2: Risk Parity Optimization
            risk_parity_portfolio = self._optimize_risk_parity(filtered_assets, target_return, max_risk)
            if risk_parity_portfolio:
                portfolios.append(risk_parity_portfolio)
            
            # Strategy 3: Maximum Diversification
            max_div_portfolio = self._optimize_diversification(filtered_assets, target_return, max_risk)
            if max_div_portfolio:
                portfolios.append(max_div_portfolio)
            
            # Strategy 4: Target Return Optimization
            if target_return:
                target_portfolio = self._optimize_target_return(filtered_assets, target_return, max_risk)
                if target_portfolio:
                    portfolios.append(target_portfolio)
            
            # Strategy 5: Minimum Risk (for conservative profiles)
            if risk_profile in ['very-conservative', 'conservative']:
                min_risk_portfolio = self._optimize_minimum_risk(filtered_assets)
                if min_risk_portfolio:
                    portfolios.append(min_risk_portfolio)
            
            # Fill remaining slots with random combinations if needed
            while len(portfolios) < num_portfolios:
                random_portfolio = self._generate_random_portfolio(filtered_assets, risk_profile)
                if random_portfolio:
                    portfolios.append(random_portfolio)
            
            # Rank portfolios by risk-adjusted performance
            ranked_portfolios = self._rank_portfolios_by_performance(portfolios, risk_profile)
            
            return ranked_portfolios[:num_portfolios]
            
        except Exception as e:
            logger.error(f"Error generating dynamic portfolios: {e}")
            return self._get_fallback_portfolios(risk_profile)

    def _get_asset_metrics_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """Get metrics for multiple assets efficiently"""
        # This would integrate with your enhanced data fetcher
        # For now, return mock data structure
        asset_metrics = {}
        for ticker in tickers:
            asset_metrics[ticker] = {
                'expected_return': np.random.uniform(0.08, 0.35),
                'risk': np.random.uniform(0.15, 0.45),
                'sector': 'Technology',  # Mock sector
                'correlation_data': np.random.uniform(-0.3, 0.8, 100)  # Mock correlation
            }
        return asset_metrics

    def _filter_assets_by_risk_profile(self, asset_metrics: Dict[str, Dict], risk_profile: str) -> Dict[str, Dict]:
        """Filter assets based on risk profile constraints"""
        risk_constraints = {
            'very-conservative': {'max_risk': 0.15, 'min_return': 0.05, 'max_return': 0.12},
            'conservative': {'max_risk': 0.20, 'min_return': 0.08, 'max_return': 0.15},
            'moderate': {'max_risk': 0.25, 'min_return': 0.10, 'max_return': 0.20},
            'aggressive': {'max_risk': 0.35, 'min_return': 0.15, 'max_return': 0.30},
            'very-aggressive': {'max_risk': 0.50, 'min_return': 0.20, 'max_return': 0.40}
        }
        
        constraints = risk_constraints.get(risk_profile, risk_constraints['moderate'])
        
        filtered = {}
        for ticker, metrics in asset_metrics.items():
            if (constraints['min_return'] <= metrics['expected_return'] <= constraints['max_return'] and
                metrics['risk'] <= constraints['max_risk']):
                filtered[ticker] = metrics
        
        return filtered

    def _optimize_sharpe_ratio(self, assets: Dict[str, Dict], target_return: Optional[float] = None, 
                              max_risk: Optional[float] = None) -> Optional[Dict]:
        """Optimize portfolio for maximum Sharpe ratio"""
        try:
            # Create returns matrix (mock data for now)
            returns_matrix = self._create_returns_matrix(assets)
            
            # Use PyPortfolioOpt for optimization
            ef = EfficientFrontier.from_returns(returns_matrix)
            
            if target_return:
                ef.efficient_return(target_return)
            elif max_risk:
                ef.efficient_risk(max_risk)
            else:
                ef.max_sharpe()
            
            weights = ef.clean_weights()
            
            # Calculate portfolio metrics
            portfolio_return = ef.portfolio_return()
            portfolio_risk = ef.portfolio_risk()
            sharpe_ratio = ef.portfolio_sharpe()
            
            return {
                'strategy': 'Sharpe Ratio Optimization',
                'weights': weights,
                'expected_return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe_ratio': sharpe_ratio,
                'diversification_score': self._calculate_diversification_from_weights(weights, returns_matrix)
            }
            
        except Exception as e:
            logger.error(f"Error in Sharpe ratio optimization: {e}")
            return None

    def _optimize_risk_parity(self, assets: Dict[str, Dict], target_return: Optional[float] = None, 
                             max_risk: Optional[float] = None) -> Optional[Dict]:
        """Optimize portfolio for risk parity (equal risk contribution)"""
        try:
            returns_matrix = self._create_returns_matrix(assets)
            
            # Risk parity optimization
            ef = EfficientFrontier.from_returns(returns_matrix)
            ef.risk_parity()
            
            weights = ef.clean_weights()
            
            # Calculate metrics
            portfolio_return = ef.portfolio_return()
            portfolio_risk = ef.portfolio_risk()
            
            return {
                'strategy': 'Risk Parity Optimization',
                'weights': weights,
                'expected_return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe_ratio': (portfolio_return - self.risk_free_rate) / portfolio_risk,
                'diversification_score': self._calculate_diversification_from_weights(weights, returns_matrix)
            }
            
        except Exception as e:
            logger.error(f"Error in risk parity optimization: {e}")
            return None

    def _optimize_diversification(self, assets: Dict[str, Dict], target_return: Optional[float] = None, 
                                max_risk: Optional[float] = None) -> Optional[Dict]:
        """Optimize portfolio for maximum diversification"""
        try:
            # Simple diversification optimization: minimize correlation
            tickers = list(assets.keys())
            n_assets = len(tickers)
            
            # Generate correlation matrix (mock for now)
            correlation_matrix = np.random.uniform(-0.3, 0.8, (n_assets, n_assets))
            np.fill_diagonal(correlation_matrix, 1.0)
            
            # Find assets with lowest average correlation
            avg_correlations = np.mean(np.abs(correlation_matrix), axis=1)
            best_indices = np.argsort(avg_correlations)[:min(5, n_assets)]
            
            # Equal weight allocation
            weights = {tickers[i]: 1.0/len(best_indices) for i in best_indices}
            
            # Calculate portfolio metrics
            portfolio_return = sum(assets[tickers[i]]['expected_return'] * weights[tickers[i]] for i in best_indices)
            portfolio_risk = sum(assets[tickers[i]]['risk'] * weights[tickers[i]] for i in best_indices)
            
            return {
                'strategy': 'Maximum Diversification',
                'weights': weights,
                'expected_return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe_ratio': (portfolio_return - self.risk_free_rate) / portfolio_risk,
                'diversification_score': 95.0  # High diversification score
            }
            
        except Exception as e:
            logger.error(f"Error in diversification optimization: {e}")
            return None

    def _optimize_target_return(self, assets: Dict[str, Dict], target_return: float, 
                               max_risk: Optional[float] = None) -> Optional[Dict]:
        """Optimize portfolio for target return with minimum risk"""
        try:
            returns_matrix = self._create_returns_matrix(assets)
            
            ef = EfficientFrontier.from_returns(returns_matrix)
            ef.efficient_return(target_return)
            
            weights = ef.clean_weights()
            
            portfolio_return = ef.portfolio_return()
            portfolio_risk = ef.portfolio_risk()
            
            return {
                'strategy': f'Target Return ({target_return:.1%})',
                'weights': weights,
                'expected_return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe_ratio': (portfolio_return - self.risk_free_rate) / portfolio_risk,
                'diversification_score': self._calculate_diversification_from_weights(weights, returns_matrix)
            }
            
        except Exception as e:
            logger.error(f"Error in target return optimization: {e}")
            return None

    def _optimize_minimum_risk(self, assets: Dict[str, Dict]) -> Optional[Dict]:
        """Optimize portfolio for minimum risk"""
        try:
            returns_matrix = self._create_returns_matrix(assets)
            
            ef = EfficientFrontier.from_returns(returns_matrix)
            ef.min_volatility()
            
            weights = ef.clean_weights()
            
            portfolio_return = ef.portfolio_return()
            portfolio_risk = ef.portfolio_risk()
            
            return {
                'strategy': 'Minimum Risk',
                'weights': weights,
                'expected_return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe_ratio': (portfolio_return - self.risk_free_rate) / portfolio_risk,
                'diversification_score': self._calculate_diversification_from_weights(weights, returns_matrix)
            }
            
        except Exception as e:
            logger.error(f"Error in minimum risk optimization: {e}")
            return None

    def _generate_random_portfolio(self, assets: Dict[str, Dict], risk_profile: str) -> Optional[Dict]:
        """Generate a random portfolio for diversity"""
        try:
            tickers = list(assets.keys())
            if len(tickers) < 3:
                return None
            
            # Random selection of 3-5 assets
            n_assets = min(5, max(3, len(tickers)))
            selected_tickers = np.random.choice(tickers, n_assets, replace=False)
            
            # Random weights (will be normalized)
            weights_array = np.random.uniform(0.1, 1.0, n_assets)
            weights_array = weights_array / weights_array.sum()
            
            weights = {ticker: weight for ticker, weight in zip(selected_tickers, weights_array)}
            
            # Calculate metrics
            portfolio_return = sum(assets[ticker]['expected_return'] * weights[ticker] for ticker in selected_tickers)
            portfolio_risk = sum(assets[ticker]['risk'] * weights[ticker] for ticker in selected_tickers)
            
            return {
                'strategy': 'Random Diversification',
                'weights': weights,
                'expected_return': portfolio_return,
                'risk': portfolio_risk,
                'sharpe_ratio': (portfolio_return - self.risk_free_rate) / portfolio_risk,
                'diversification_score': np.random.uniform(60, 85)
            }
            
        except Exception as e:
            logger.error(f"Error generating random portfolio: {e}")
            return None

    def _rank_portfolios_by_performance(self, portfolios: List[Dict], risk_profile: str) -> List[Dict]:
        """Rank portfolios by performance based on risk profile preferences"""
        def scoring_function(portfolio):
            # Base score from Sharpe ratio
            sharpe_score = portfolio.get('sharpe_ratio', 0) * 10
            
            # Risk profile adjustment
            risk_adjustments = {
                'very-conservative': {'risk_penalty': 2.0, 'return_bonus': 0.5},
                'conservative': {'risk_penalty': 1.5, 'return_bonus': 0.8},
                'moderate': {'risk_penalty': 1.0, 'return_bonus': 1.0},
                'aggressive': {'risk_penalty': 0.5, 'return_bonus': 1.5},
                'very-aggressive': {'risk_penalty': 0.2, 'return_bonus': 2.0}
            }
            
            adjustment = risk_adjustments.get(risk_profile, risk_adjustments['moderate'])
            
            # Risk penalty (higher risk = lower score for conservative profiles)
            risk_penalty = portfolio.get('risk', 0) * adjustment['risk_penalty']
            
            # Return bonus (higher returns = higher score for aggressive profiles)
            return_bonus = portfolio.get('expected_return', 0) * adjustment['return_bonus']
            
            # Diversification bonus
            div_bonus = portfolio.get('diversification_score', 50) / 100
            
            return sharpe_score - risk_penalty + return_bonus + div_bonus
        
        # Sort portfolios by score
        ranked_portfolios = sorted(portfolios, key=scoring_function, reverse=True)
        
        # Add ranking information
        for i, portfolio in enumerate(ranked_portfolios):
            portfolio['rank'] = i + 1
            portfolio['score'] = scoring_function(portfolio)
        
        return ranked_portfolios

    def _create_returns_matrix(self, assets: Dict[str, Dict]) -> pd.DataFrame:
        """Create returns matrix for optimization (mock data for now)"""
        # In real implementation, this would use actual historical returns
        # For now, create synthetic returns based on asset metrics
        
        returns_data = {}
        for ticker, metrics in assets.items():
            # Generate synthetic monthly returns based on annual metrics
            monthly_return = (1 + metrics['expected_return']) ** (1/12) - 1
            monthly_risk = metrics['risk'] / np.sqrt(12)
            
            # Generate 60 months of returns
            returns = np.random.normal(monthly_return, monthly_risk, 60)
            returns_data[ticker] = returns
        
        return pd.DataFrame(returns_data)

    def _calculate_diversification_from_weights(self, weights: Dict[str, float], returns_matrix: pd.DataFrame) -> float:
        """Calculate diversification score from weights and returns"""
        try:
            # Calculate correlation matrix
            corr_matrix = returns_matrix.corr()
            
            # Calculate weighted average correlation
            tickers = list(weights.keys())
            total_weight = 0
            weighted_correlation = 0
            
            for i, ticker1 in enumerate(tickers):
                for j, ticker2 in enumerate(tickers):
                    if i < j:  # Avoid double counting
                        weight_pair = weights[ticker1] * weights[ticker2]
                        correlation = abs(corr_matrix.loc[ticker1, ticker2])
                        
                        weighted_correlation += weight_pair * correlation
                        total_weight += weight_pair
            
            if total_weight > 0:
                avg_correlation = weighted_correlation / total_weight
                diversification_score = max(0, 100 - (avg_correlation * 100))
                return round(diversification_score, 1)
            else:
                return 50.0
                
        except Exception as e:
            logger.error(f"Error calculating diversification: {e}")
            return 50.0

    # ==================== NEW: Monte Carlo Simulation ====================
    
    def run_monte_carlo_simulation(self, 
                                   expected_return: float, 
                                   risk: float, 
                                   num_simulations: int = 10000,
                                   time_horizon_years: float = 1.0,
                                   seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation to generate return distribution
        
        Args:
            expected_return: Annual expected return (e.g., 0.12 for 12%)
            risk: Annual volatility/risk (e.g., 0.20 for 20%)
            num_simulations: Number of simulations to run (default 10,000)
            time_horizon_years: Investment time horizon in years (default 1 year)
            seed: Optional RNG seed for reproducible results; None for non-deterministic.
            
        Returns:
            Dict with simulation results including:
            - simulated_returns: List of simulated returns
            - percentiles: Dict with 5th, 25th, 50th, 75th, 95th percentiles
            - probability_positive: Probability of positive returns
            - probability_loss_thresholds: Dict with probabilities of various loss levels
            - histogram_data: Binned data for histogram visualization
            - statistics: Mean, std, min, max of simulated returns
        """
        try:
            # Generate random returns using normal distribution
            # For simplicity, assuming returns follow normal distribution
            # In practice, could use log-normal or more sophisticated models
            
            # Guard against zero or negative volatility (would make normal degenerate)
            risk_effective = max(float(risk), 0.01) if risk is not None else 0.01
            
            # Annualized parameters adjusted for time horizon
            adjusted_return = expected_return * time_horizon_years
            adjusted_risk = risk_effective * np.sqrt(time_horizon_years)
            
            # Generate simulated returns (optional seed for reproducibility)
            if seed is not None:
                np.random.seed(seed)
            simulated_returns = np.random.normal(adjusted_return, adjusted_risk, num_simulations)
            
            # Calculate percentiles
            percentiles = {
                'p5': float(np.percentile(simulated_returns, 5)),
                'p25': float(np.percentile(simulated_returns, 25)),
                'p50': float(np.percentile(simulated_returns, 50)),  # Median
                'p75': float(np.percentile(simulated_returns, 75)),
                'p95': float(np.percentile(simulated_returns, 95)),
            }
            
            # Calculate probability of positive returns
            probability_positive = float(np.sum(simulated_returns > 0) / num_simulations * 100)
            
            # Calculate probability of various loss levels
            probability_loss_thresholds = {
                'loss_5pct': float(np.sum(simulated_returns < -0.05) / num_simulations * 100),
                'loss_10pct': float(np.sum(simulated_returns < -0.10) / num_simulations * 100),
                'loss_20pct': float(np.sum(simulated_returns < -0.20) / num_simulations * 100),
                'loss_30pct': float(np.sum(simulated_returns < -0.30) / num_simulations * 100),
            }
            
            # Create histogram data for visualization (30 bins)
            hist_counts, bin_edges = np.histogram(simulated_returns, bins=30)
            histogram_data = []
            for i in range(len(hist_counts)):
                bin_center = (bin_edges[i] + bin_edges[i+1]) / 2
                histogram_data.append({
                    'return': float(bin_center),
                    'return_pct': float(bin_center * 100),
                    'count': int(hist_counts[i]),
                    'frequency': float(hist_counts[i] / num_simulations * 100)
                })
            
            # Calculate statistics
            statistics = {
                'mean': float(np.mean(simulated_returns)),
                'std': float(np.std(simulated_returns)),
                'min': float(np.min(simulated_returns)),
                'max': float(np.max(simulated_returns)),
                'median': float(np.median(simulated_returns)),
            }
            
            # Generate probability statements for UI
            probability_statements = self._generate_probability_statements(
                percentiles, probability_positive, probability_loss_thresholds, time_horizon_years
            )
            
            return {
                'simulated_returns': simulated_returns.tolist()[:100],  # Return only first 100 for size
                'percentiles': percentiles,
                'probability_positive': probability_positive,
                'probability_loss_thresholds': probability_loss_thresholds,
                'histogram_data': histogram_data,
                'statistics': statistics,
                'probability_statements': probability_statements,
                'parameters': {
                    'expected_return': expected_return,
                    'risk': risk,
                    'num_simulations': num_simulations,
                    'time_horizon_years': time_horizon_years,
                    'seed': seed
                }
            }
            
        except Exception as e:
            logger.error(f"Error running Monte Carlo simulation: {e}")
            return self._get_fallback_monte_carlo()
    
    def _generate_probability_statements(self, 
                                        percentiles: Dict[str, float],
                                        probability_positive: float,
                                        probability_loss: Dict[str, float],
                                        time_horizon: float) -> List[str]:
        """Generate human-readable probability statements"""
        statements = []
        
        horizon_text = f"{int(time_horizon)} year" if time_horizon == 1 else f"{time_horizon:.1f} years"
        
        # Positive return statement
        statements.append(f"{probability_positive:.0f}% chance of positive returns over {horizon_text}")
        
        # Expected range statement
        statements.append(
            f"Expected range: {percentiles['p25']*100:.1f}% to {percentiles['p75']*100:.1f}% (50% confidence)"
        )
        
        # Wider range statement
        statements.append(
            f"Wider range: {percentiles['p5']*100:.1f}% to {percentiles['p95']*100:.1f}% (90% confidence)"
        )
        
        # Loss probability statements
        if probability_loss['loss_10pct'] > 5:
            statements.append(f"{probability_loss['loss_10pct']:.0f}% chance of losing more than 10%")
        
        if probability_loss['loss_20pct'] > 2:
            statements.append(f"{probability_loss['loss_20pct']:.0f}% chance of losing more than 20%")
        
        return statements
    
    def _get_fallback_monte_carlo(self) -> Dict[str, Any]:
        """Fallback Monte Carlo results when calculation fails"""
        return {
            'simulated_returns': [],
            'percentiles': {'p5': -0.15, 'p25': 0.0, 'p50': 0.10, 'p75': 0.20, 'p95': 0.35},
            'probability_positive': 65.0,
            'probability_loss_thresholds': {'loss_5pct': 20.0, 'loss_10pct': 10.0, 'loss_20pct': 3.0, 'loss_30pct': 1.0},
            'histogram_data': [],
            'statistics': {'mean': 0.10, 'std': 0.15, 'min': -0.30, 'max': 0.50, 'median': 0.10},
            'probability_statements': ['Unable to calculate probabilities'],
            'parameters': {'expected_return': 0.10, 'risk': 0.15, 'num_simulations': 0, 'time_horizon_years': 1.0, 'seed': None}
        }

    # ==================== NEW: Quality Score Metrics ====================
    
    def calculate_sortino_ratio(self, 
                               returns: Optional[pd.Series] = None,
                               expected_return: float = 0.0,
                               risk: float = 0.0,
                               risk_free_rate: float = 0.038) -> float:
        """
        Calculate Sortino Ratio (risk-adjusted return using downside deviation)
        
        The Sortino ratio is similar to Sharpe but only penalizes downside volatility,
        making it more appropriate for investors who care more about losses than gains.
        
        Args:
            returns: Optional time series of returns (if available)
            expected_return: Annual expected return (used if returns not available)
            risk: Annual volatility (used to estimate downside deviation if returns not available)
            risk_free_rate: Risk-free rate (default 3.8%)
            
        Returns:
            Sortino ratio as float
        """
        try:
            if returns is not None and len(returns) > 12:
                # Calculate from actual returns
                excess_returns = returns - (risk_free_rate / 12)  # Monthly risk-free rate
                downside_returns = excess_returns[excess_returns < 0]
                
                if len(downside_returns) > 0:
                    downside_deviation = np.sqrt(np.mean(downside_returns ** 2)) * np.sqrt(12)  # Annualize
                else:
                    downside_deviation = risk * 0.5  # Estimate if no negative returns
                
                annual_return = (1 + returns.mean()) ** 12 - 1
                sortino = (annual_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
            else:
                # Estimate from expected return and risk
                # Assume downside deviation is roughly 70% of total volatility
                downside_deviation = risk * 0.7
                sortino = (expected_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
            
            return round(float(sortino), 3)
            
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0.0
    
    def calculate_consistency_score(self, 
                                   returns: Optional[pd.Series] = None,
                                   expected_return: float = 0.0,
                                   risk: float = 0.0) -> float:
        """
        Calculate Consistency Score based on coefficient of variation
        
        Lower CV means more consistent returns relative to the mean.
        Uses improved formula: score = 100 * exp(-cv) for better scaling.
        
        Args:
            returns: Optional time series of returns
            expected_return: Annual expected return
            risk: Annual volatility
            
        Returns:
            Consistency score (0-100)
        """
        try:
            import math
            
            if returns is not None and len(returns) > 12:
                # Calculate from actual returns
                mean_return = returns.mean()
                std_return = returns.std()
                
                if abs(mean_return) > 1e-6:  # Avoid division by zero
                    cv = abs(std_return / mean_return)
                else:
                    # If mean is near zero, use risk-based estimate
                    if risk > 0:
                        cv = risk / 0.15  # Assume 15% typical return for normalization
                    else:
                        return 50.0  # Default if no data
            else:
                # Estimate from expected return and risk
                if abs(expected_return) > 1e-6:  # Avoid division by zero
                    cv = abs(risk / expected_return)
                else:
                    # If expected return is zero/negative, use risk-based estimate
                    if risk > 0:
                        cv = risk / 0.15  # Assume 15% typical return for normalization
                    else:
                        return 50.0  # Default if no data
            
            # Improved formula: exponential decay for better scaling
            # CV of 0 = 100, CV of 0.5 = ~61, CV of 1 = ~37, CV of 2 = ~14
            # This gives non-zero scores even for high CV values
            consistency_score = 100 * math.exp(-min(cv, 3.0))  # Cap CV at 3 for stability
            
            # Ensure score is in valid range
            consistency_score = max(0.0, min(100.0, consistency_score))
            
            return round(float(consistency_score), 1)
            
        except Exception as e:
            logger.error(f"Error calculating consistency score: {e}")
            return 50.0
    
    def calculate_risk_profile_compliance(self, 
                                         portfolio_risk: float, 
                                         risk_profile: str) -> float:
        """
        Calculate how well the portfolio risk matches the user's risk profile
        
        Uses UNIFIED configuration from risk_profile_config.py for consistency
        with portfolio generation and optimization.
        
        Args:
            portfolio_risk: Portfolio volatility (e.g., 0.20 for 20%)
            risk_profile: User's risk profile ('very-conservative' to 'very-aggressive')
            
        Returns:
            Compliance score (0-100), where 100 means perfect match
        """
        try:
            # Import unified configuration (single source of truth)
            from .risk_profile_config import get_quality_risk_range_for_profile
            
            # Get risk ranges from unified config (returns tuple: (min_risk, max_risk))
            min_risk, max_risk = get_quality_risk_range_for_profile(risk_profile)
            
            # Calculate ideal risk as midpoint of the range
            ideal_risk = (min_risk + max_risk) / 2.0
            
            # Perfect score if within ideal range
            if min_risk <= portfolio_risk <= max_risk:
                # Calculate how close to ideal
                distance_from_ideal = abs(portfolio_risk - ideal_risk)
                range_width = max_risk - min_risk
                
                # Score based on distance from ideal (closer = higher)
                compliance = 100 - (distance_from_ideal / range_width * 50)
            else:
                # Outside acceptable range - penalize
                if portfolio_risk < min_risk:
                    distance = min_risk - portfolio_risk
                else:
                    distance = portfolio_risk - max_risk
                
                # Penalize based on how far outside
                range_width = max_risk - min_risk
                penalty = min(50, (distance / range_width) * 100)
                compliance = 50 - penalty
            
            return round(max(0, min(100, float(compliance))), 1)
            
        except Exception as e:
            logger.error(f"Error calculating risk profile compliance: {e}")
            return 50.0
    
    def calculate_quality_score(self,
                               expected_return: float,
                               risk: float,
                               risk_profile: str,
                               diversification_score: float,
                               returns: Optional[pd.Series] = None) -> Dict[str, Any]:
        """
        Calculate composite Multi-Factor Quality Score
        
        Weights:
        - Risk Profile Compliance: 40%
        - Sortino Ratio: 30%
        - Diversification Score: 20%
        - Consistency Score: 10%
        
        Args:
            expected_return: Annual expected return
            risk: Annual volatility
            risk_profile: User's risk profile
            diversification_score: Pre-calculated diversification score (0-100)
            returns: Optional time series of returns
            
        Returns:
            Dict with overall score and factor breakdown
        """
        try:
            # Calculate individual factors
            sortino = self.calculate_sortino_ratio(returns, expected_return, risk)
            consistency = self.calculate_consistency_score(returns, expected_return, risk)
            risk_compliance = self.calculate_risk_profile_compliance(risk, risk_profile)
            
            # Normalize Sortino to 0-100 scale
            # Sortino of 0 = 0, Sortino of 2+ = 100
            sortino_normalized = min(100, max(0, sortino * 50))
            
            # Calculate weighted composite score
            weights = {
                'risk_profile_compliance': 0.40,
                'sortino_ratio': 0.30,
                'diversification': 0.20,
                'consistency': 0.10
            }
            
            composite_score = (
                risk_compliance * weights['risk_profile_compliance'] +
                sortino_normalized * weights['sortino_ratio'] +
                diversification_score * weights['diversification'] +
                consistency * weights['consistency']
            )
            
            # Factor breakdown for UI
            factor_breakdown = {
                'risk_profile_compliance': {
                    'score': risk_compliance,
                    'weight': weights['risk_profile_compliance'] * 100,
                    'label': 'Risk Profile Match',
                    'description': 'How well risk matches your profile'
                },
                'sortino_ratio': {
                    'score': sortino_normalized,
                    'raw_value': sortino,
                    'weight': weights['sortino_ratio'] * 100,
                    'label': 'Downside Protection',
                    'description': 'Risk-adjusted return focusing on losses'
                },
                'diversification': {
                    'score': diversification_score,
                    'weight': weights['diversification'] * 100,
                    'label': 'Diversification',
                    'description': 'Spread across sectors and correlations'
                },
                'consistency': {
                    'score': consistency,
                    'weight': weights['consistency'] * 100,
                    'label': 'Return Consistency',
                    'description': 'Stability of returns over time'
                }
            }
            
            # Generate quality rating
            if composite_score >= 85:
                rating = 'Excellent'
                rating_color = 'green'
            elif composite_score >= 70:
                rating = 'Good'
                rating_color = 'blue'
            elif composite_score >= 55:
                rating = 'Fair'
                rating_color = 'yellow'
            else:
                rating = 'Needs Improvement'
                rating_color = 'red'
            
            return {
                'composite_score': round(composite_score, 1),
                'rating': rating,
                'rating_color': rating_color,
                'factor_breakdown': factor_breakdown,
                'weights_used': weights
            }
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return {
                'composite_score': 50.0,
                'rating': 'Unknown',
                'rating_color': 'gray',
                'factor_breakdown': {},
                'weights_used': {}
            }
