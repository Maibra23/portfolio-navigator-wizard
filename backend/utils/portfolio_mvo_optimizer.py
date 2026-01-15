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
                          min_overlap_months: int = 12, strict_overlap: bool = True) -> Tuple[Dict[str, float], pd.DataFrame]:
        """
        Get mean returns (μ) and covariance matrix (Σ) from Agent 1 endpoint or internal function
        
        Args:
            tickers: List of ticker symbols
            annualize: Whether to annualize returns
            min_overlap_months: Minimum date overlap required
            strict_overlap: If True, raise error if overlap is insufficient; if False, use available overlap
            
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
                    strict_overlap=strict_overlap
                )
            else:
                # Fallback: would need to import and call directly
                # For now, raise error to indicate function should be provided
                raise ValueError("get_ticker_metrics_func must be provided")
            
            # Check if response contains an error
            if data.get("error"):
                error_msg = data.get("error", "Unknown error")
                metadata = data.get("metadata", {})
                overlap_info = f" (overlap: {metadata.get('overlap_months', 'unknown')} months, required: {metadata.get('min_overlap_required', 'unknown')} months)"
                raise ValueError(f"{error_msg}{overlap_info}")
            
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
                          constraints: Optional[Dict[str, Any]] = None,
                          min_overlap_months: int = 12,
                          strict_overlap: bool = True) -> Dict[str, Any]:
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
            min_overlap_months: Minimum date overlap required (default: 12)
            strict_overlap: If True, raise error if overlap is insufficient (default: True)
            
        Returns:
            Dict with optimized weights and metrics
        """
        try:
            if len(tickers) < 2:
                raise ValueError("At least 2 tickers required for optimization")
            
            # Get metrics from Agent 1 endpoint
            mu_dict, sigma_df = self.get_ticker_metrics(tickers, min_overlap_months=min_overlap_months, strict_overlap=strict_overlap)
            
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
            
            # Perform optimization based on type with fallback mechanisms
            if optimization_type == "max_sharpe":
                strategy_name = "Maximum Sharpe Ratio"
                optimization_successful = False
                
                # Try max_sharpe optimization with progressive fallback
                try:
                    weights = ef.max_sharpe(risk_free_rate=self.risk_free_rate)
                    weights = ef.clean_weights()
                    optimization_successful = True
                except Exception as e:
                    logger.warning(f"⚠️ max_sharpe optimization failed: {e}, trying fallback strategies...")
                    optimization_successful = False
                
                # Check if risk profile constraint is violated and enforce it
                if optimization_successful and risk_profile and max_risk is not None:
                    # Calculate portfolio metrics to check risk
                    # Use same risk_free_rate as max_sharpe() to avoid warnings
                    portfolio_risk_check = ef.portfolio_performance(
                        verbose=False, 
                        risk_free_rate=self.risk_free_rate
                    )[1]
                    if portfolio_risk_check > max_risk:
                        # Re-optimize with risk constraint: create new EfficientFrontier instance
                        # to avoid "already solved problem" error
                        try:
                            ef_constrained = EfficientFrontier(mu, sigma_df)
                            # Apply same constraints if any
                            if constraints:
                                if 'min_weight' in constraints:
                                    ef_constrained.add_constraint(lambda w: w >= constraints['min_weight'])
                                if 'max_weight' in constraints:
                                    ef_constrained.add_constraint(lambda w: w <= constraints['max_weight'])
                            weights = ef_constrained.efficient_risk(max_risk)
                            weights = ef_constrained.clean_weights()
                            ef = ef_constrained  # Use constrained optimizer for metrics calculation
                            strategy_name = f"Maximum Sharpe Ratio (Risk-Constrained ≤{max_risk:.1%})"
                        except Exception as e:
                            logger.warning(f"⚠️ efficient_risk optimization failed: {e}, trying relaxed constraints...")
                            optimization_successful = False
                
                # PRIORITY 1: Constraint relaxation with progressive fallback
                if not optimization_successful:
                    relaxation_attempts = [
                        (1.05, "5% relaxation"),
                        (1.10, "10% relaxation"),
                        (1.15, "15% relaxation"),
                        (None, "min_variance fallback")
                    ]
                    
                    for relaxation_factor, description in relaxation_attempts:
                        try:
                            if relaxation_factor is not None and max_risk is not None:
                                # Try with relaxed risk constraint
                                relaxed_risk = max_risk * relaxation_factor
                                # Check if relaxed risk is still within reasonable bounds
                                profile_max = self._get_max_risk_for_profile(risk_profile) if risk_profile else 0.50
                                if relaxed_risk <= profile_max * 1.2:  # Allow up to 20% over profile max
                                    logger.info(f"🔄 Attempting optimization with {description} (risk: {max_risk:.2%} → {relaxed_risk:.2%})")
                                    ef_relaxed = EfficientFrontier(mu, sigma_df)
                                    if constraints:
                                        if 'min_weight' in constraints:
                                            ef_relaxed.add_constraint(lambda w: w >= constraints['min_weight'])
                                        if 'max_weight' in constraints:
                                            ef_relaxed.add_constraint(lambda w: w <= constraints['max_weight'])
                                    weights = ef_relaxed.efficient_risk(relaxed_risk)
                                    weights = ef_relaxed.clean_weights()
                                    ef = ef_relaxed
                                    strategy_name = f"Maximum Sharpe Ratio ({description}, Risk ≤{relaxed_risk:.1%})"
                                    optimization_successful = True
                                    break
                            else:
                                # Final fallback: min_variance
                                logger.info(f"🔄 Attempting {description}...")
                                ef_fallback = EfficientFrontier(mu, sigma_df)
                                if constraints:
                                    if 'min_weight' in constraints:
                                        ef_fallback.add_constraint(lambda w: w >= constraints['min_weight'])
                                    if 'max_weight' in constraints:
                                        ef_fallback.add_constraint(lambda w: w <= constraints['max_weight'])
                                weights = ef_fallback.min_volatility()
                                weights = ef_fallback.clean_weights()
                                ef = ef_fallback
                                strategy_name = "Minimum Variance (Fallback)"
                                optimization_successful = True
                                break
                        except Exception as e:
                            logger.debug(f"⚠️ {description} failed: {e}")
                            continue
                    
                    if not optimization_successful:
                        raise Exception("All optimization strategies failed, including fallbacks")
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
            
            # Clean weights (remove near-zero weights) if not already cleaned
            if optimization_type != "max_sharpe":
                weights = ef.clean_weights()
            
            # Calculate portfolio metrics
            # IMPORTANT: Use same risk_free_rate as max_sharpe() to avoid PyPortfolioOpt warnings
            # If max_sharpe was used, pass risk_free_rate; otherwise use default
            if optimization_type == "max_sharpe":
                portfolio_return, portfolio_risk, sharpe_ratio = ef.portfolio_performance(
                    verbose=False, 
                    risk_free_rate=self.risk_free_rate
                )
            else:
                portfolio_return = ef.portfolio_performance(verbose=False)[0]
                portfolio_risk = ef.portfolio_performance(verbose=False)[1]
                sharpe_ratio = ef.portfolio_performance(verbose=False)[2]
            
            # Apply safeguards to prevent unrealistic metrics
            # 1. Cap expected return at realistic maximum (50% annual)
            MAX_REALISTIC_RETURN = 0.50
            if portfolio_return > MAX_REALISTIC_RETURN:
                logger.warning(f"⚠️ Capping unrealistic return {portfolio_return:.2%} to {MAX_REALISTIC_RETURN:.1%}")
                portfolio_return = MAX_REALISTIC_RETURN
            
            # 2. Apply minimum risk floor (8% annual volatility minimum)
            MIN_RISK_FLOOR = 0.08
            if portfolio_risk < MIN_RISK_FLOOR:
                logger.debug(f"⚠️ Applying minimum risk floor: {portfolio_risk:.2%} → {MIN_RISK_FLOOR:.1%}")
                portfolio_risk = MIN_RISK_FLOOR
            
            # 3. Recalculate Sharpe ratio with adjusted metrics
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            
            # 4. Cap Sharpe ratio at realistic maximum (2.5)
            MAX_REALISTIC_SHARPE = 2.5
            if sharpe_ratio > MAX_REALISTIC_SHARPE:
                logger.warning(f"⚠️ Capping unrealistic Sharpe ratio {sharpe_ratio:.2f} to {MAX_REALISTIC_SHARPE:.1f}")
                sharpe_ratio = MAX_REALISTIC_SHARPE
            
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
                                   risk_profile: Optional[str] = None,
                                   min_overlap_months: int = 12,
                                   strict_overlap: bool = True) -> List[Dict[str, Any]]:
        """
        Generate efficient frontier points using PyPortfolioOpt
        
        Args:
            tickers: List of ticker symbols
            num_points: Number of frontier points to generate
            risk_profile: Optional risk profile for filtering
            min_overlap_months: Minimum date overlap required (default: 12)
            strict_overlap: If True, raise error if overlap is insufficient (default: True)
            
        Returns:
            List of frontier points with risk, return, and weights
        """
        try:
            if len(tickers) < 2:
                raise ValueError("At least 2 tickers required for efficient frontier")
            
            # Get metrics from Agent 1 endpoint
            mu_dict, sigma_df = self.get_ticker_metrics(tickers, min_overlap_months=min_overlap_months, strict_overlap=strict_overlap)
            
            # Convert mu to pandas Series
            mu = pd.Series(mu_dict)
            
            # Ensure tickers are in same order
            tickers_ordered = list(mu.index)
            sigma_df = sigma_df.loc[tickers_ordered, tickers_ordered]
            
            # First, add minimum variance portfolio explicitly (leftmost point)
            frontier_points = []
            try:
                ef_min_var = EfficientFrontier(mu, sigma_df)
                weights_min_var = ef_min_var.min_volatility()
                weights_min_var = ef_min_var.clean_weights()
                min_var_perf = ef_min_var.portfolio_performance(verbose=False, risk_free_rate=self.risk_free_rate)
                weights_dict_min_var = dict(weights_min_var)
                
                # Apply safeguards
                ret_val = min(float(min_var_perf[0]), 0.50)
                risk_val = max(float(min_var_perf[1]), 0.08)
                sharpe_val = min((ret_val - self.risk_free_rate) / risk_val if risk_val > 0 else 0, 2.5)
                
                frontier_points.append({
                    "return": ret_val,
                    "risk": risk_val,
                    "sharpe_ratio": sharpe_val,
                    "weights": weights_dict_min_var,
                    "weights_list": [weights_dict_min_var.get(ticker, 0.0) for ticker in tickers_ordered],
                    "type": "frontier"
                })
                logger.debug(f"✅ Added minimum variance portfolio: {min_var_perf[1]:.2%} risk, {min_var_perf[0]:.2%} return")
            except Exception as e:
                logger.warning(f"⚠️ Could not add min variance portfolio: {e}")
            
            # Create EfficientFrontier object for the rest of the frontier
            ef = EfficientFrontier(mu, sigma_df)
            
            # Get efficient frontier by varying target returns
            # Find min and max possible returns
            min_ret = mu.min()
            max_ret = mu.max()
            
            # Generate range of target returns (use num_points - 1 since we already added min var)
            target_returns = np.linspace(min_ret, max_ret, max(2, num_points - 1))
            
            for target_return in target_returns:
                try:
                    # Get optimal portfolio for this target return
                    weights = ef.efficient_return(target_return=target_return, market_neutral=False)
                    
                    # Calculate portfolio metrics
                    portfolio_perf = ef.portfolio_performance(verbose=False, risk_free_rate=self.risk_free_rate)
                    mu_val = portfolio_perf[0]  # Expected return
                    sigma_val = portfolio_perf[1]  # Volatility (risk)
                    sharpe = portfolio_perf[2]  # Sharpe ratio
                    
                    # Apply safeguards
                    mu_val = min(float(mu_val), 0.50)
                    sigma_val = max(float(sigma_val), 0.08)
                    sharpe = min((mu_val - self.risk_free_rate) / sigma_val if sigma_val > 0 else 0, 2.5)
                    
                    # Convert weights dict to list
                    weights_dict = dict(weights)
                    weights_list = [weights_dict.get(ticker, 0.0) for ticker in tickers_ordered]
                    
                    frontier_points.append({
                        "return": mu_val,
                        "risk": sigma_val,
                        "sharpe_ratio": sharpe,
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
    
    def generate_inefficient_frontier(self, 
                                     tickers: List[str],
                                     num_points: int = 20,
                                     risk_profile: Optional[str] = None,
                                     min_overlap_months: int = 12,
                                     strict_overlap: bool = True) -> List[Dict[str, Any]]:
        """
        Generate inefficient frontier points (lower part of the hyperbola)
        These represent portfolios with minimum return for given risk levels
        
        Args:
            tickers: List of ticker symbols
            num_points: Number of frontier points to generate
            risk_profile: Optional risk profile for filtering
            min_overlap_months: Minimum date overlap required (default: 12)
            strict_overlap: If True, raise error if overlap is insufficient (default: True)
            
        Returns:
            List of inefficient frontier points with risk, return, and weights
        """
        try:
            if len(tickers) < 2:
                raise ValueError("At least 2 tickers required for inefficient frontier")
            
            from scipy.optimize import minimize
            
            # Get metrics from Agent 1 endpoint
            mu_dict, sigma_df = self.get_ticker_metrics(tickers, min_overlap_months=min_overlap_months, strict_overlap=strict_overlap)
            
            # Convert mu to pandas Series
            mu = pd.Series(mu_dict)
            
            # Ensure tickers are in same order
            tickers_ordered = list(mu.index)
            sigma_df = sigma_df.loc[tickers_ordered, tickers_ordered]
            
            # Convert to numpy arrays
            mu_array = mu.values
            sigma_array = sigma_df.values
            
            # First, get the efficient frontier to determine risk range
            try:
                ef = EfficientFrontier(mu, sigma_df)
                # Get min and max risk from efficient frontier
                ef_min_var = EfficientFrontier(mu, sigma_df)
                weights_min_var = ef_min_var.min_volatility()
                min_var_perf = ef_min_var.portfolio_performance(verbose=False, risk_free_rate=self.risk_free_rate)
                min_risk = min_var_perf[1]
                
                # Get maximum risk (from maximum return portfolio)
                weights_max_ret = ef.max_sharpe(risk_free_rate=self.risk_free_rate)
                max_ret_perf = ef.portfolio_performance(verbose=False, risk_free_rate=self.risk_free_rate)
                max_risk = max_ret_perf[1]
            except Exception as e:
                logger.warning(f"⚠️ Could not determine risk range from efficient frontier: {e}")
                # Fallback: use covariance matrix to estimate risk range
                min_risk = np.sqrt(np.min(np.diag(sigma_array)))
                max_risk = np.sqrt(np.max(np.diag(sigma_array))) * 1.5
            
            # Generate range of target risks
            target_risks = np.linspace(min_risk, max_risk, num_points)
            
            inefficient_frontier_points = []
            
            for target_risk in target_risks:
                try:
                    # Objective: minimize return (negative of maximize return)
                    def objective(weights):
                        portfolio_return = np.dot(weights, mu_array)
                        return portfolio_return  # Minimize return
                    
                    # Constraint: risk equals target risk
                    def risk_constraint(weights):
                        portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(sigma_array, weights)))
                        return portfolio_risk - target_risk
                    
                    # Constraint: weights sum to 1
                    def weights_sum_constraint(weights):
                        return np.sum(weights) - 1.0
                    
                    # Bounds: weights between 0 and 1
                    bounds = [(0.0, 1.0) for _ in range(len(tickers_ordered))]
                    
                    # Initial guess: equal weights
                    initial_weights = np.array([1.0 / len(tickers_ordered)] * len(tickers_ordered))
                    
                    # Constraints
                    constraints = [
                        {'type': 'eq', 'fun': risk_constraint},
                        {'type': 'eq', 'fun': weights_sum_constraint}
                    ]
                    
                    # Optimize: minimize return for given risk
                    result = minimize(
                        objective,
                        initial_weights,
                        method='SLSQP',
                        bounds=bounds,
                        constraints=constraints,
                        options={'maxiter': 1000, 'ftol': 1e-9}
                    )
                    
                    if result.success:
                        weights = result.x
                        # Normalize weights to ensure they sum to 1
                        weights = weights / np.sum(weights)
                        
                        # Calculate portfolio metrics
                        portfolio_return = np.dot(weights, mu_array)
                        portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(sigma_array, weights)))
                        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
                        
                        # Convert weights to dict
                        weights_dict = {ticker: float(weight) for ticker, weight in zip(tickers_ordered, weights)}
                        weights_list = [float(weight) for weight in weights]
                        
                        inefficient_frontier_points.append({
                            "return": float(portfolio_return),
                            "risk": float(portfolio_risk),
                            "sharpe_ratio": float(sharpe_ratio),
                            "weights": weights_dict,
                            "weights_list": weights_list,
                            "type": "inefficient_frontier"
                        })
                    else:
                        logger.debug(f"⚠️ Skipping inefficient frontier point at risk {target_risk:.4f}: {result.message}")
                        continue
                        
                except Exception as e:
                    logger.debug(f"⚠️ Error generating inefficient frontier point at risk {target_risk:.4f}: {e}")
                    continue
            
            logger.info(f"✅ Generated {len(inefficient_frontier_points)} inefficient frontier points")
            return inefficient_frontier_points
            
        except Exception as e:
            logger.error(f"❌ Error generating inefficient frontier: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def generate_random_portfolios(self, 
                                  tickers: List[str],
                                  num_portfolios: int = 300,
                                  risk_profile: Optional[str] = None,
                                  min_overlap_months: int = 12,
                                  strict_overlap: bool = True) -> List[Dict[str, Any]]:
        """
        Generate random portfolios for scatter plot visualization
        
        Args:
            tickers: List of ticker symbols
            num_portfolios: Number of random portfolios to generate
            risk_profile: Optional risk profile for filtering
            min_overlap_months: Minimum date overlap required (default: 12)
            strict_overlap: If True, raise error if overlap is insufficient (default: True)
            
        Returns:
            List of random portfolio points with risk, return, and weights
        """
        try:
            if len(tickers) < 2:
                raise ValueError("At least 2 tickers required for random portfolios")
            
            # Get metrics from Agent 1 endpoint
            mu_dict, sigma_df = self.get_ticker_metrics(tickers, min_overlap_months=min_overlap_months, strict_overlap=strict_overlap)
            
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
        """Get maximum risk constraint for risk profile
        
        Uses centralized config from risk_profile_config.py for consistency.
        Based on volatility range upper bounds with adjustments for aggressive profiles
        derived from actual ticker distribution percentiles.
        """
        from .risk_profile_config import get_max_risk_for_profile
        return get_max_risk_for_profile(risk_profile)
    
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
            
            # Apply safeguards
            MAX_REALISTIC_RETURN = 0.50
            MIN_RISK_FLOOR = 0.08
            MAX_REALISTIC_SHARPE = 2.5
            
            portfolio_return = min(portfolio_return, MAX_REALISTIC_RETURN)
            portfolio_risk = max(portfolio_risk, MIN_RISK_FLOOR)
            
            # Calculate Sharpe ratio
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            sharpe_ratio = min(sharpe_ratio, MAX_REALISTIC_SHARPE)
            
            return {
                "expected_return": float(portfolio_return),
                "risk": float(portfolio_risk),
                "sharpe_ratio": float(sharpe_ratio)
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio metrics: {e}")
            raise
    
    def calculate_capital_market_line(self, 
                                     efficient_frontier: List[Dict[str, Any]],
                                     risk_free_rate: Optional[float] = None,
                                     market_portfolio: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Calculate Capital Market Line (CML) from efficient frontier or market portfolio
        
        CML formula: Return = Rf + (Rm - Rf) / σm * σ
        Where:
        - Rf = risk-free rate
        - Rm = market portfolio return (tangent portfolio)
        - σm = market portfolio risk
        - σ = portfolio risk
        
        Args:
            efficient_frontier: List of efficient frontier points
            risk_free_rate: Risk-free rate (uses self.risk_free_rate if None)
            market_portfolio: Optional market-optimized portfolio dict with 'return' and 'risk' keys.
                            If provided, CML will be calculated from this portfolio instead of
                            finding the tangent portfolio from the efficient frontier.
                            This ensures CML always connects Rf to the market-optimized portfolio.
            
        Returns:
            List of CML points with risk and return
        """
        try:
            rf = risk_free_rate if risk_free_rate is not None else self.risk_free_rate
            
            # If market portfolio is provided, use it directly (ensures CML connects to market-opt portfolio)
            if market_portfolio is not None:
                market_return = market_portfolio.get('return', 0)
                market_risk = market_portfolio.get('risk', 0)
                
                if market_risk <= 0:
                    logger.warning("⚠️ Invalid market portfolio risk for CML calculation")
                    return []
                
                # Calculate market portfolio Sharpe ratio
                market_sharpe = (market_return - rf) / market_risk if market_risk > 0 else 0
                
                logger.info(f"📈 Calculating CML from market-optimized portfolio: {market_return:.2%} return, {market_risk:.2%} risk")
            else:
                # Fallback: Find tangent portfolio from efficient frontier
                if not efficient_frontier or len(efficient_frontier) < 2:
                    logger.warning("⚠️ Insufficient frontier points for CML calculation")
                    return []
                
                # Find tangent portfolio (maximum Sharpe ratio on efficient frontier)
                tangent_portfolio = max(
                    efficient_frontier,
                    key=lambda p: p.get('sharpe_ratio', 0) if p.get('sharpe_ratio') is not None else 0
                )
                
                market_return = tangent_portfolio.get('return', 0)
                market_risk = tangent_portfolio.get('risk', 0)
                
                if market_risk <= 0:
                    logger.warning("⚠️ Invalid market risk for CML calculation")
                    return []
                
                # Calculate market portfolio Sharpe ratio
                market_sharpe = (market_return - rf) / market_risk if market_risk > 0 else 0
                
                logger.info(f"📈 Calculating CML from efficient frontier tangent portfolio: {market_return:.2%} return, {market_risk:.2%} risk")
            
            # Generate CML points
            # CML extends from risk-free rate (0 risk) to 1.5x market risk
            max_risk = market_risk * 1.5
            risk_range = np.linspace(0, max_risk, 50)
            
            cml_points = []
            for risk in risk_range:
                # CML: Return = Rf + Sharpe_market * Risk
                return_val = rf + market_sharpe * risk
                cml_points.append({
                    'risk': float(risk),
                    'return': float(return_val),
                    'type': 'cml',
                    'sharpe_ratio': market_sharpe if risk > 0 else None
                })
            
            logger.info(f"✅ Generated CML with {len(cml_points)} points (market portfolio: {market_return:.2%} return, {market_risk:.2%} risk, Sharpe: {market_sharpe:.3f})")
            return cml_points
            
        except Exception as e:
            logger.error(f"❌ Error calculating CML: {e}")
            import traceback
            traceback.print_exc()
            return []

