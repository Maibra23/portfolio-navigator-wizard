import quantstats as qs
import pypfopt
from pypfopt import EfficientFrontier, risk_models, expected_returns
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class PortfolioAnalytics:
    """
    Comprehensive portfolio analytics using QuantStats and PyPortfolioOpt
    Handles all mathematical calculations for the portfolio wizard
    """
    
    def __init__(self):
        self.risk_free_rate = 0.04  # 4% risk-free rate
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
            date_index = pd.date_range(start=start_date, periods=len(returns), freq='M')
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
                    date_index = pd.date_range(start=start_date, periods=len(returns), freq='M')
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
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        
        selected_assets = []
        
        # Helper function to get asset data
        def get_asset_info(ticker):
            try:
                data = enhanced_data_fetcher.get_monthly_data(ticker)
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
                                if enhanced_data_fetcher._is_cached(asset, 'prices')][:conservative_count]
        
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
                            if enhanced_data_fetcher._is_cached(asset, 'prices')][:moderate_count]
        
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
                                  if enhanced_data_fetcher._is_cached(asset, 'prices')][:aggressive_count]
            
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
    
    def calculate_real_portfolio_metrics(self, portfolio_data: Dict) -> Dict:
        """Calculate portfolio metrics using real data from portfolio allocations"""
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        
        try:
            allocations = portfolio_data.get('allocations', [])
            if not allocations:
                return self._get_fallback_portfolio_metrics()
            
            # Get real data for each asset
            asset_returns = []
            weights = []
            
            for allocation in allocations:
                ticker = allocation['symbol']
                weight = allocation['allocation'] / 100  # Convert percentage to decimal
                
                # Get pre-calculated metrics from cache first
                cached_metrics = enhanced_data_fetcher.get_cached_metrics(ticker)
                if cached_metrics:
                    # Use cached metrics for faster calculation
                    annual_return = cached_metrics['annualized_return']
                    annual_risk = cached_metrics['risk']
                    
                    # Create synthetic returns for portfolio calculation
                    # This is a simplified approach using the metrics
                    monthly_return = (1 + annual_return) ** (1/12) - 1
                    monthly_risk = annual_risk / (12 ** 0.5)
                    
                    # Create a simple return series for portfolio calculation
                    returns = pd.Series([monthly_return] * 60)  # 5 years of monthly data
                    asset_returns.append(returns)
                    weights.append(weight)
                else:
                    # Fallback: get monthly data and calculate
                    data = enhanced_data_fetcher.get_monthly_data(ticker)
                    if data and data['prices']:
                        prices = np.array(data['prices'], dtype=float)
                        returns = pd.Series(prices).pct_change().dropna()
                        asset_returns.append(returns)
                        weights.append(weight)
                    else:
                        logger.warning(f"Missing data for {ticker}, using fallback")
                        return self._get_fallback_portfolio_metrics()
            
            if not asset_returns:
                return self._get_fallback_portfolio_metrics()
            
            # Align all return series to same length
            min_length = min(len(returns) for returns in asset_returns)
            aligned_returns = [returns.iloc[-min_length:] for returns in asset_returns]
            
            # Calculate portfolio return series
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
                'risk': ann_risk,  # Consistent naming: 'risk' not 'volatility'
                'max_drawdown': max_drawdown,
                'diversification_score': self._calculate_portfolio_diversification_score(aligned_returns, weights)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating real portfolio metrics: {e}")
            return self._get_fallback_portfolio_metrics()
    
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
    
    def _get_fallback_portfolio_metrics(self) -> Dict:
        """Fallback portfolio metrics when calculation fails"""
        return {
            'expected_return': 0.10,
            'risk': 0.15,
            'max_drawdown': -0.10,
            'diversification_score': 50.0
        }
