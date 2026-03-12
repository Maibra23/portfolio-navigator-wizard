#!/usr/bin/env python3
"""
Dynamic Weighting System
Implements optimization-based portfolio weighting to achieve target returns and risk
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class DynamicWeightingSystem:
    """
    Multi-objective dynamic weighting system with return AND risk targeting.

    Uses covariance-aware risk calculation (matching the validator in port_analytics)
    to ensure optimizer output is consistent with downstream quality checks.

    Weight bounds: [5%, 50%] per stock, sum to 100%.
    """

    def __init__(self):
        self.min_weight = 0.05  # 5% minimum allocation
        self.max_weight = 0.50  # 50% maximum allocation
        self.weight_precision = 0.01  # 1% precision
        self.max_iterations = 1000
        self.return_tolerance = 0.07  # 7% above target acceptable
        self.extended_tolerance = 0.10  # 10% for limited availability scenarios

    def calculate_optimal_weights(
        self,
        stocks: List[Dict],
        target_return: float,
        limited_availability: bool = False,
        risk_range: Optional[Tuple[float, float]] = None,
    ) -> Tuple[List[float], Dict]:
        """
        Calculate optimal weights targeting both return and risk constraints.

        Args:
            stocks: List of stock dicts with 'return', 'risk', and optionally 'sector' keys
            target_return: Target portfolio return (decimal, e.g. 0.18 = 18%)
            limited_availability: If True, allows wider return tolerance
            risk_range: Optional (min_risk, max_risk) for the quality risk range.
                       When provided, the optimizer penalises deviations outside this band.

        Returns:
            Tuple of (weights, optimization_results)
        """
        try:
            if len(stocks) < 2:
                return [1.0], {'success': True, 'message': 'Single stock, equal weight'}

            n_stocks = len(stocks)
            returns = np.array([s.get('return', 0.10) for s in stocks])
            # Stock dicts use 'volatility' (from portfolio_stock_selector), not 'risk'
            risks = np.array([s.get('volatility', s.get('risk', 0.15)) for s in stocks])

            correlation_matrix = self._estimate_correlation_matrix(n_stocks, stocks)

            tolerance = self.extended_tolerance if limited_availability else self.return_tolerance

            # Build covariance matrix from individual risks + correlation
            # cov(i,j) = sigma_i * sigma_j * rho_ij
            cov_matrix = np.outer(risks, risks) * correlation_matrix

            def portfolio_metrics(weights):
                """Calculate portfolio return and covariance-aware risk."""
                w = np.array(weights)
                portfolio_return = float(np.dot(w, returns))

                # sigma_p = sqrt(w^T @ Cov @ w)  — matches port_analytics validator
                portfolio_variance = float(w @ cov_matrix @ w)
                portfolio_risk = float(np.sqrt(max(portfolio_variance, 0.0)))

                return portfolio_return, portfolio_risk

            def objective(weights):
                """
                Multi-objective: minimise weighted sum of return and risk deviations.

                Return penalty: penalise if outside [target, target + tolerance]
                Risk penalty:   penalise if outside risk_range (when provided)

                alpha = 1.0 (return weight), beta = 0.5 (risk weight)
                Risk is weighted lower because the return target is the primary driver,
                and risk has more natural variance due to correlation effects.
                """
                portfolio_return, portfolio_risk = portfolio_metrics(weights)

                # Return deviation (same flexible band as before)
                if portfolio_return > target_return + tolerance:
                    return_dev = portfolio_return - (target_return + tolerance)
                elif portfolio_return < target_return:
                    return_dev = target_return - portfolio_return
                else:
                    return_dev = 0.0

                # Risk deviation (only when risk_range is provided)
                risk_dev = 0.0
                if risk_range is not None:
                    min_risk, max_risk = risk_range
                    if portfolio_risk > max_risk:
                        risk_dev = portfolio_risk - max_risk
                    elif portfolio_risk < min_risk:
                        risk_dev = min_risk - portfolio_risk

                alpha = 1.0
                beta = 0.5
                return alpha * return_dev + beta * risk_dev

            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
            ]

            bounds = [(self.min_weight, self.max_weight) for _ in range(n_stocks)]

            x0 = np.array([1.0 / n_stocks] * n_stocks)

            result = minimize(
                objective, x0, method='SLSQP',
                bounds=bounds, constraints=constraints,
                options={'maxiter': self.max_iterations, 'ftol': 1e-9}
            )

            if result.success:
                optimal_weights = result.x.tolist()
                portfolio_return, portfolio_risk = portfolio_metrics(optimal_weights)

                above_target = [s for s in stocks if s.get('return', 0.10) >= target_return]
                below_target = [s for s in stocks if s.get('return', 0.10) < target_return]

                optimization_results = {
                    'success': True,
                    'portfolio_return': portfolio_return,
                    'portfolio_risk': portfolio_risk,
                    'return_deviation': abs(portfolio_return - target_return),
                    'above_target_stocks': len(above_target),
                    'below_target_stocks': len(below_target),
                    'tolerance_used': tolerance,
                    'risk_range_used': risk_range,
                    'iterations': result.nit,
                    'message': 'Optimization successful'
                }

                logger.debug(
                    f"Dynamic weighting successful: "
                    f"{portfolio_return:.2%} return, {portfolio_risk:.2%} risk"
                )
                return optimal_weights, optimization_results
            else:
                logger.warning(f"Optimization did not converge: {result.message}")
                # Use return-proportional heuristic instead of 1/N to avoid generic equal-weight portfolios
                fallback_weights = self._return_proportional_fallback_weights(stocks, target_return)
                portfolio_return, portfolio_risk = portfolio_metrics(fallback_weights)

                return fallback_weights, {
                    'success': False,
                    'portfolio_return': portfolio_return,
                    'portfolio_risk': portfolio_risk,
                    'return_deviation': abs(portfolio_return - target_return),
                    'message': f'Optimization failed, using return-proportional weights: {result.message}'
                }

        except Exception as e:
            logger.error(f"Dynamic weighting calculation failed: {e}")
            fallback_weights = self._return_proportional_fallback_weights(stocks, target_return)
            return fallback_weights, {
                'success': False,
                'portfolio_return': 0.10,
                'portfolio_risk': 0.15,
                'return_deviation': abs(0.10 - target_return),
                'message': f'Calculation error: {str(e)}'
            }

    def _return_proportional_fallback_weights(
        self, stocks: List[Dict], target_return: float
    ) -> List[float]:
        """
        When optimization fails, use return-proportional weights (bounded) instead of 1/N
        so portfolios are differentiated rather than equal-weight.
        """
        n = len(stocks)
        if n < 1:
            return []
        if n == 1:
            return [1.0]
        raw_returns = np.array([max(1e-6, s.get('return', 0.10)) for s in stocks])
        r_min = raw_returns.min()
        scores = raw_returns - r_min + 1e-6
        w = scores / scores.sum()
        # Clip and renormalize until stable so result stays in [min_weight, max_weight]
        for _ in range(20):
            w = np.clip(w, self.min_weight, self.max_weight)
            s = w.sum()
            if abs(s - 1.0) < 1e-9:
                break
            w = w / s
        w = np.clip(w, self.min_weight, self.max_weight)
        s = float(w.sum())
        if s <= 0:
            return ([1.0 / n] * n)
        # Fix weights at max, scale the rest so total = 1 (avoids float pushing any weight > max)
        at_max = w >= self.max_weight - 1e-9
        k = int(np.sum(at_max))
        rest_target = 1.0 - k * self.max_weight
        rest_mask = ~at_max
        if rest_target <= 0 or np.sum(rest_mask) == 0:
            return ([1.0 / n] * n)
        rest_sum = float(np.sum(w[rest_mask]))
        if rest_sum > 1e-9:
            out = np.empty(n)
            out[at_max] = self.max_weight
            out[rest_mask] = w[rest_mask] * (rest_target / rest_sum)
            w = out
        return w.tolist()

    def _estimate_correlation_matrix(self, n_stocks: int, stocks: List[Dict]) -> np.ndarray:
        """
        Estimate correlation matrix based on sector information.
        Same-sector stocks get moderate correlation (0.3),
        cross-sector stocks get low correlation (0.1).
        """
        try:
            corr_matrix = np.eye(n_stocks)

            sectors = [s.get('sector', 'Unknown') for s in stocks]

            for i in range(n_stocks):
                for j in range(i + 1, n_stocks):
                    if sectors[i] == sectors[j] and sectors[i] != 'Unknown':
                        corr_matrix[i, j] = corr_matrix[j, i] = 0.3
                    else:
                        corr_matrix[i, j] = corr_matrix[j, i] = 0.1

            return corr_matrix

        except Exception as e:
            logger.debug(f"Correlation matrix estimation failed: {e}")
            return np.eye(n_stocks)

    def validate_weights(self, weights: List[float]) -> Dict:
        """Validate that weights meet constraints."""
        try:
            total_weight = sum(weights)
            min_w = min(weights)
            max_w = max(weights)

            validation = {
                'valid': True,
                'total_weight': total_weight,
                'min_weight': min_w,
                'max_weight': max_w,
                'issues': []
            }

            if abs(total_weight - 1.0) > 0.001:
                validation['valid'] = False
                validation['issues'].append(f"Weights sum to {total_weight:.3f}, should be 1.0")

            if min_w < self.min_weight:
                validation['valid'] = False
                validation['issues'].append(f"Minimum weight {min_w:.3f} below limit {self.min_weight}")

            if max_w > self.max_weight:
                validation['valid'] = False
                validation['issues'].append(f"Maximum weight {max_w:.3f} above limit {self.max_weight}")

            return validation

        except Exception as e:
            return {
                'valid': False,
                'total_weight': 0,
                'min_weight': 0,
                'max_weight': 0,
                'issues': [f"Validation error: {str(e)}"]
            }
