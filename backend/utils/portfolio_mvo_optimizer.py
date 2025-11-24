#!/usr/bin/env python3
"""
Portfolio Mean-Variance Optimization (MVO) Engine
Uses PyPortfolioOpt for advanced portfolio optimization
Integrates with Agent 1 endpoints for data preparation
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from pypfopt import EfficientFrontier, risk_models, expected_returns
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices

logger = logging.getLogger(__name__)

class PortfolioMVOptimizer:
    """
    Mean-Variance Optimization engine using PyPortfolioOpt
    Integrates with Agent 1 data preparation endpoints
    """
    
    def __init__(self, get_ticker_metrics_func: Optional[Callable] = None, risk_free_rate: float = 0.038):
        """
        Initialize MVO optimizer
        
        Args:
            get_ticker_metrics_func: Function to get ticker metrics (mu, sigma)
                If None, will use internal calculation
            risk_free_rate: Risk-free rate for Sharpe ratio calculation (default 3.8%)
        """
        self.get_ticker_metrics_func = get_ticker_metrics_func
        self.risk_free_rate = risk_free_rate
        logger.info(f"✅ Portfolio MVO Optimizer initialized (risk-free rate: {risk_free_rate:.1%})")
    
    def get_ticker_metrics(self, tickers: List[str], annualize: bool = True, 
                          min_overlap_months: int = 12) -> Tuple[Dict[str, float], pd.DataFrame]:
        """
        Get mean returns (μ) and covariance matrix (Σ) from Agent 1 endpoint or internal function
        
        Args:
            tickers: List of ticker symbols
            annualize: Whether to annualize returns
            min_overlap_months: Minimum date overlap required
            
        Returns:
            Tuple of (mu_dict, sigma_dataframe)
        """
        try:
            # Use provided function if available (internal call)
            if self.get_ticker_metrics_func:
                data = self.get_ticker_metrics_func(
                    tickers=tickers,
                    annualize=annualize,
                    min_overlap_months=min_overlap_months,
                    strict_overlap=True
                )
            else:
                # Fallback: would need to import and call directly
                # For now, raise error to indicate function should be provided
                raise ValueError("get_ticker_metrics_func must be provided")
            
            # Extract mu (mean returns)
            mu_dict = data.get("mu", {})
            
            # Extract sigma (covariance matrix) and convert to DataFrame
            sigma_dict = data.get("sigma", {})
            if not sigma_dict:
                raise ValueError("No covariance matrix in response")
            
            # Convert nested dict to DataFrame
            ticker_list = list(mu_dict.keys())
            sigma_matrix = np.zeros((len(ticker_list), len(ticker_list)))
            
            for i, ticker1 in enumerate(ticker_list):
                for j, ticker2 in enumerate(ticker_list):
                    sigma_matrix[i, j] = sigma_dict.get(ticker1, {}).get(ticker2, 0.0)
            
            sigma_df = pd.DataFrame(sigma_matrix, index=ticker_list, columns=ticker_list)
            
            logger.info(f"✅ Retrieved metrics for {len(ticker_list)} tickers")
            return mu_dict, sigma_df
            
        except Exception as e:
            logger.error(f"❌ Error processing ticker metrics: {e}")
            raise
    
    def optimize_portfolio(self, 
                          tickers: List[str],
                          optimization_type: str = "max_sharpe",
                          target_return: Optional[float] = None,
                          max_risk: Optional[float] = None,
                          risk_profile: Optional[str] = None,
                          constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Optimize portfolio using Mean-Variance Optimization
        
        Args:
            tickers: List of ticker symbols to optimize
            optimization_type: Type of optimization
                - "max_sharpe": Maximum Sharpe ratio
                - "min_variance": Minimum variance
                - "target_return": Target return optimization
                - "target_risk": Target risk optimization
            target_return: Target return (for target_return optimization)
            max_risk: Maximum risk constraint (for target_risk optimization)
            risk_profile: Risk profile for constraints
            constraints: Additional constraints dict
            
        Returns:
            Dict with optimized weights and metrics
        """
        try:
            if len(tickers) < 2:
                raise ValueError("At least 2 tickers required for optimization")
            
            # Get metrics from Agent 1 endpoint
            mu_dict, sigma_df = self.get_ticker_metrics(tickers)
            
            # Convert mu to pandas Series
            mu = pd.Series(mu_dict)
            
            # Ensure tickers are in same order
            tickers_ordered = list(mu.index)
            sigma_df = sigma_df.loc[tickers_ordered, tickers_ordered]
            
            # Create EfficientFrontier object
            ef = EfficientFrontier(mu, sigma_df)
            
            # Apply risk profile constraints if provided
            if risk_profile:
                max_risk_constraint = self._get_max_risk_for_profile(risk_profile)
                if max_risk is None or max_risk > max_risk_constraint:
                    max_risk = max_risk_constraint
            
            # Apply additional constraints
            if constraints:
                if 'min_weight' in constraints:
                    ef.add_constraint(lambda w: w >= constraints['min_weight'])
                if 'max_weight' in constraints:
                    ef.add_constraint(lambda w: w <= constraints['max_weight'])
            
            # Perform optimization based on type
            if optimization_type == "max_sharpe":
                weights = ef.max_sharpe(risk_free_rate=self.risk_free_rate)
                strategy_name = "Maximum Sharpe Ratio"
            elif optimization_type == "min_variance":
                weights = ef.min_volatility()
                strategy_name = "Minimum Variance"
            elif optimization_type == "target_return":
                if target_return is None:
                    raise ValueError("target_return required for target_return optimization")
                weights = ef.efficient_return(target_return)
                strategy_name = f"Target Return ({target_return:.1%})"
            elif optimization_type == "target_risk":
                if max_risk is None:
                    raise ValueError("max_risk required for target_risk optimization")
                weights = ef.efficient_risk(max_risk)
                strategy_name = f"Target Risk ({max_risk:.1%})"
            else:
                raise ValueError(f"Unknown optimization type: {optimization_type}")
            
            # Clean weights (remove near-zero weights)
            weights = ef.clean_weights()
            
            # Calculate portfolio metrics
            portfolio_return = ef.portfolio_performance(verbose=False)[0]
            portfolio_risk = ef.portfolio_performance(verbose=False)[1]
            sharpe_ratio = ef.portfolio_performance(verbose=False)[2]
            
            # Convert weights dict to list in ticker order
            weights_list = [weights.get(ticker, 0.0) for ticker in tickers_ordered]
            
            result = {
                "optimization_type": optimization_type,
                "strategy_name": strategy_name,
                "weights": weights,
                "weights_list": weights_list,
                "tickers": tickers_ordered,
                "expected_return": float(portfolio_return),
                "risk": float(portfolio_risk),
                "sharpe_ratio": float(sharpe_ratio),
                "risk_free_rate": self.risk_free_rate
            }
            
            logger.info(f"✅ Optimized portfolio: {strategy_name} - Return: {portfolio_return:.2%}, Risk: {portfolio_risk:.2%}, Sharpe: {sharpe_ratio:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error optimizing portfolio: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def generate_efficient_frontier(self, 
                                   tickers: List[str],
                                   num_points: int = 20,
                                   risk_profile: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate efficient frontier points using PyPortfolioOpt
        
        Args:
            tickers: List of ticker symbols
            num_points: Number of frontier points to generate
            risk_profile: Optional risk profile for filtering
            
        Returns:
            List of frontier points with risk, return, and weights
        """
        try:
            if len(tickers) < 2:
                raise ValueError("At least 2 tickers required for efficient frontier")
            
            # Get metrics from Agent 1 endpoint
            mu_dict, sigma_df = self.get_ticker_metrics(tickers)
            
            # Convert mu to pandas Series
            mu = pd.Series(mu_dict)
            
            # Ensure tickers are in same order
            tickers_ordered = list(mu.index)
            sigma_df = sigma_df.loc[tickers_ordered, tickers_ordered]
            
            # Create EfficientFrontier object
            ef = EfficientFrontier(mu, sigma_df)
            
            # Get efficient frontier by varying target returns
            # Find min and max possible returns
            min_ret = mu.min()
            max_ret = mu.max()
            
            # Generate range of target returns
            target_returns = np.linspace(min_ret, max_ret, num_points)
            
            frontier_points = []
            for target_return in target_returns:
                try:
                    # Get optimal portfolio for this target return
                    weights = ef.efficient_return(target_return=target_return, market_neutral=False)
                    
                    # Calculate portfolio metrics
                    portfolio_perf = ef.portfolio_performance(verbose=False, risk_free_rate=self.risk_free_rate)
                    mu_val = portfolio_perf[0]  # Expected return
                    sigma_val = portfolio_perf[1]  # Volatility (risk)
                    sharpe = portfolio_perf[2]  # Sharpe ratio
                    
                    # Convert weights dict to list
                    weights_dict = dict(weights)
                    weights_list = [weights_dict.get(ticker, 0.0) for ticker in tickers_ordered]
                    
                    frontier_points.append({
                        "return": float(mu_val),
                        "risk": float(sigma_val),
                        "sharpe_ratio": float(sharpe),
                        "weights": weights_dict,
                        "weights_list": weights_list,
                        "type": "frontier"
                    })
                except Exception as e:
                    # Skip points that can't be optimized (e.g., constraints not feasible)
                    logger.debug(f"⚠️ Skipping frontier point at return {target_return:.4f}: {e}")
                    continue
            
            logger.info(f"✅ Generated {len(frontier_points)} efficient frontier points")
            return frontier_points
            
        except Exception as e:
            logger.error(f"❌ Error generating efficient frontier: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def generate_random_portfolios(self, 
                                  tickers: List[str],
                                  num_portfolios: int = 200,
                                  risk_profile: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate random portfolios for scatter plot visualization
        
        Args:
            tickers: List of ticker symbols
            num_portfolios: Number of random portfolios to generate
            risk_profile: Optional risk profile for filtering
            
        Returns:
            List of random portfolio points with risk, return, and weights
        """
        try:
            if len(tickers) < 2:
                raise ValueError("At least 2 tickers required for random portfolios")
            
            # Get metrics from Agent 1 endpoint
            mu_dict, sigma_df = self.get_ticker_metrics(tickers)
            
            # Convert mu to pandas Series
            mu = pd.Series(mu_dict)
            
            # Ensure tickers are in same order
            tickers_ordered = list(mu.index)
            sigma_df = sigma_df.loc[tickers_ordered, tickers_ordered]
            
            # Convert to numpy arrays for faster computation
            mu_array = mu.values
            sigma_array = sigma_df.values
            
            random_portfolios = []
            np.random.seed(42)  # For reproducibility
            
            for _ in range(num_portfolios):
                # Generate random weights (Dirichlet distribution for uniform sampling)
                weights = np.random.dirichlet(np.ones(len(tickers_ordered)))
                
                # Calculate portfolio return: w^T * μ
                portfolio_return = np.dot(weights, mu_array)
                
                # Calculate portfolio risk: sqrt(w^T * Σ * w)
                portfolio_risk = np.sqrt(np.dot(weights, np.dot(sigma_array, weights)))
                
                # Calculate Sharpe ratio
                sharpe = (portfolio_return - self.risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
                
                # Convert weights to dict
                weights_dict = {ticker: float(weight) for ticker, weight in zip(tickers_ordered, weights)}
                weights_list = weights.tolist()
                
                random_portfolios.append({
                    "return": float(portfolio_return),
                    "risk": float(portfolio_risk),
                    "sharpe_ratio": float(sharpe),
                    "weights": weights_dict,
                    "weights_list": weights_list,
                    "type": "random"
                })
            
            logger.info(f"✅ Generated {len(random_portfolios)} random portfolios")
            return random_portfolios
            
        except Exception as e:
            logger.error(f"❌ Error generating random portfolios: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _get_max_risk_for_profile(self, risk_profile: str) -> float:
        """Get maximum risk constraint for risk profile"""
        risk_constraints = {
            'very-conservative': 0.08,
            'conservative': 0.12,
            'moderate': 0.16,
            'aggressive': 0.22,
            'very-aggressive': 0.28
        }
        return risk_constraints.get(risk_profile, 0.16)
    
    def calculate_portfolio_metrics(self, 
                                   tickers: List[str],
                                   weights: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate portfolio metrics for given weights
        
        Args:
            tickers: List of ticker symbols
            weights: Dict of ticker -> weight
            
        Returns:
            Dict with portfolio metrics
        """
        try:
            # Get metrics from Agent 1 endpoint
            mu_dict, sigma_df = self.get_ticker_metrics(tickers)
            
            # Convert mu to pandas Series
            mu = pd.Series(mu_dict)
            
            # Ensure tickers are in same order
            tickers_ordered = list(mu.index)
            sigma_df = sigma_df.loc[tickers_ordered, tickers_ordered]
            
            # Convert weights to array
            weights_array = np.array([weights.get(ticker, 0.0) for ticker in tickers_ordered])
            
            # Normalize weights
            weights_array = weights_array / weights_array.sum() if weights_array.sum() > 0 else weights_array
            
            # Calculate portfolio return
            portfolio_return = np.dot(weights_array, mu.values)
            
            # Calculate portfolio risk
            portfolio_risk = np.sqrt(np.dot(weights_array, np.dot(sigma_df.values, weights_array)))
            
            # Calculate Sharpe ratio
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            
            return {
                "expected_return": float(portfolio_return),
                "risk": float(portfolio_risk),
                "sharpe_ratio": float(sharpe_ratio)
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio metrics: {e}")
            raise

