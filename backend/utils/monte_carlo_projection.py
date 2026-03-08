"""
Monte Carlo projection engine using Geometric Brownian Motion (GBM).

Generates stochastic portfolio value paths over a multi-year horizon.
Uses log-normal returns (GBM) which correctly models:
- Prices cannot go negative
- Right-skewed return distributions
- Volatility drag effect

The GBM model: dS = S * (mu * dt + sigma * dW)
Discrete form: S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
where Z ~ N(0,1)
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MonteCarloProjector:
    """
    Monte Carlo simulation engine for portfolio projections.

    Uses Geometric Brownian Motion to generate realistic multi-year
    portfolio value paths with proper log-normal distribution.
    """

    def __init__(self):
        self._tax_calc = None
        self._cost_calc = None

    @property
    def tax_calc(self):
        """Lazy load tax calculator to avoid circular imports."""
        if self._tax_calc is None:
            from .swedish_tax_calculator import SwedishTaxCalculator
            self._tax_calc = SwedishTaxCalculator()
        return self._tax_calc

    @property
    def cost_calc(self):
        """Lazy load cost calculator to avoid circular imports."""
        if self._cost_calc is None:
            from .transaction_cost_calculator import AvanzaCourtageCalculator
            self._cost_calc = AvanzaCourtageCalculator()
        return self._cost_calc

    def simulate_paths(
        self,
        initial_capital: float,
        annual_expected_return: float,
        annual_volatility: float,
        years: int = 5,
        num_simulations: int = 5000,
        monthly_steps: bool = True,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Simulate portfolio value paths using Geometric Brownian Motion.

        Args:
            initial_capital: Starting portfolio value (e.g., 100000 SEK)
            annual_expected_return: Expected annual return as decimal (e.g., 0.08 for 8%)
            annual_volatility: Annual volatility as decimal (e.g., 0.15 for 15%)
            years: Projection horizon in years (default 5)
            num_simulations: Number of Monte Carlo paths (default 5000)
            monthly_steps: If True, use monthly time steps; if False, use annual
            seed: Optional RNG seed for reproducibility

        Returns:
            Dict containing:
            - time_points: List of time values [0, 0.083, 0.167, ..., 5.0] (monthly) or [0, 1, ..., 5] (annual)
            - percentiles: Dict with p5, p10, p25, p50, p75, p90, p95 paths
            - mean_path: List of mean values at each time point
            - probability_loss: Probability of losing money (final < initial)
            - probability_loss_20pct: Probability of losing 20%+ (final < 0.8 * initial)
            - statistics: Dict with final value statistics
        """
        try:
            # Set random seed if provided
            if seed is not None:
                np.random.seed(seed)

            # Guard against invalid inputs
            initial_capital = max(float(initial_capital), 1.0)
            annual_volatility = max(float(annual_volatility), 0.001)  # Minimum 0.1% volatility
            annual_expected_return = float(annual_expected_return)

            # Time discretization
            if monthly_steps:
                dt = 1.0 / 12.0  # Monthly steps
                num_steps = years * 12
            else:
                dt = 1.0  # Annual steps
                num_steps = years

            # Generate time points
            time_points = [i * dt for i in range(num_steps + 1)]

            # GBM parameters
            # Drift term includes the Ito correction: mu - 0.5 * sigma^2
            drift = (annual_expected_return - 0.5 * annual_volatility ** 2) * dt
            diffusion = annual_volatility * np.sqrt(dt)

            # Generate all random shocks at once (vectorized for performance)
            # Shape: (num_simulations, num_steps)
            random_shocks = np.random.standard_normal((num_simulations, num_steps))

            # Calculate log returns for each step
            log_returns = drift + diffusion * random_shocks

            # Cumulative log returns (including time 0)
            cumulative_log_returns = np.zeros((num_simulations, num_steps + 1))
            cumulative_log_returns[:, 1:] = np.cumsum(log_returns, axis=1)

            # Convert to price paths
            paths = initial_capital * np.exp(cumulative_log_returns)

            # Calculate percentiles at each time point
            percentile_values = {
                'p5': np.percentile(paths, 5, axis=0).tolist(),
                'p10': np.percentile(paths, 10, axis=0).tolist(),
                'p25': np.percentile(paths, 25, axis=0).tolist(),
                'p50': np.percentile(paths, 50, axis=0).tolist(),
                'p75': np.percentile(paths, 75, axis=0).tolist(),
                'p90': np.percentile(paths, 90, axis=0).tolist(),
                'p95': np.percentile(paths, 95, axis=0).tolist(),
            }

            # Mean path
            mean_path = np.mean(paths, axis=0).tolist()

            # Final value statistics
            final_values = paths[:, -1]

            # Probability calculations
            probability_loss = float(np.sum(final_values < initial_capital) / num_simulations * 100)
            probability_loss_20pct = float(np.sum(final_values < 0.8 * initial_capital) / num_simulations * 100)
            probability_loss_10pct = float(np.sum(final_values < 0.9 * initial_capital) / num_simulations * 100)
            probability_gain_50pct = float(np.sum(final_values > 1.5 * initial_capital) / num_simulations * 100)
            probability_double = float(np.sum(final_values > 2.0 * initial_capital) / num_simulations * 100)

            statistics = {
                'mean_final': float(np.mean(final_values)),
                'median_final': float(np.median(final_values)),
                'std_final': float(np.std(final_values)),
                'min_final': float(np.min(final_values)),
                'max_final': float(np.max(final_values)),
                'skewness': float(self._calculate_skewness(final_values)),
                'initial_capital': initial_capital,
            }

            return {
                'time_points': time_points,
                'percentiles': percentile_values,
                'mean_path': mean_path,
                'probability_loss': probability_loss,
                'probability_loss_10pct': probability_loss_10pct,
                'probability_loss_20pct': probability_loss_20pct,
                'probability_gain_50pct': probability_gain_50pct,
                'probability_double': probability_double,
                'statistics': statistics,
                'parameters': {
                    'annual_expected_return': annual_expected_return,
                    'annual_volatility': annual_volatility,
                    'years': years,
                    'num_simulations': num_simulations,
                    'monthly_steps': monthly_steps,
                }
            }

        except Exception as e:
            logger.error(f"Error in Monte Carlo simulation: {e}")
            return self._get_fallback_result(initial_capital, years, monthly_steps)

    def simulate_paths_with_tax_drag(
        self,
        initial_capital: float,
        annual_expected_return: float,
        annual_volatility: float,
        account_type: str,
        tax_year: int,
        courtage_class: str,
        weights: Dict[str, float],
        rebalancing_frequency: str = "quarterly",
        years: int = 5,
        num_simulations: int = 5000,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Simulate paths with Swedish tax and transaction cost drag.

        This applies annual tax and rebalancing costs to the percentile paths.
        For performance, we apply costs to the aggregated percentile curves
        rather than to each individual simulation path.

        Args:
            initial_capital: Starting portfolio value (SEK)
            annual_expected_return: Expected annual return (decimal)
            annual_volatility: Annual volatility (decimal)
            account_type: "ISK", "KF", or "AF"
            tax_year: 2025 or 2026
            courtage_class: Avanza courtage class
            weights: Ticker -> weight mapping
            rebalancing_frequency: "monthly", "quarterly", "semi-annual", "annual"
            years: Projection horizon
            num_simulations: Number of simulations
            seed: Optional RNG seed

        Returns:
            Same structure as simulate_paths, but with tax/cost drag applied
        """
        try:
            # First, run the base simulation
            base_result = self.simulate_paths(
                initial_capital=initial_capital,
                annual_expected_return=annual_expected_return,
                annual_volatility=annual_volatility,
                years=years,
                num_simulations=num_simulations,
                monthly_steps=True,
                seed=seed
            )

            # Apply tax and cost drag to each percentile path
            adjusted_percentiles = {}

            for pct_key, pct_path in base_result['percentiles'].items():
                adjusted_path = self._apply_annual_drag(
                    path=pct_path,
                    account_type=account_type,
                    tax_year=tax_year,
                    courtage_class=courtage_class,
                    weights=weights,
                    rebalancing_frequency=rebalancing_frequency,
                    annual_expected_return=annual_expected_return
                )
                adjusted_percentiles[pct_key] = adjusted_path

            # Apply to mean path as well
            adjusted_mean = self._apply_annual_drag(
                path=base_result['mean_path'],
                account_type=account_type,
                tax_year=tax_year,
                courtage_class=courtage_class,
                weights=weights,
                rebalancing_frequency=rebalancing_frequency,
                annual_expected_return=annual_expected_return
            )

            # Recalculate statistics based on adjusted p50 (median)
            adjusted_final = adjusted_percentiles['p50'][-1]

            # Update probability calculations based on adjusted paths
            # Note: These are approximations since we don't have individual paths
            # For more accurate probabilities, we'd need to apply drag to all paths
            probability_loss = self._estimate_probability_below(
                adjusted_percentiles, initial_capital
            )
            probability_loss_20pct = self._estimate_probability_below(
                adjusted_percentiles, 0.8 * initial_capital
            )

            statistics = {
                'mean_final': adjusted_mean[-1],
                'median_final': adjusted_percentiles['p50'][-1],
                'std_final': (adjusted_percentiles['p75'][-1] - adjusted_percentiles['p25'][-1]) / 1.35,  # IQR approximation
                'min_final': adjusted_percentiles['p5'][-1],
                'max_final': adjusted_percentiles['p95'][-1],
                'initial_capital': initial_capital,
                'tax_adjusted': True,
            }

            return {
                'time_points': base_result['time_points'],
                'percentiles': adjusted_percentiles,
                'mean_path': adjusted_mean,
                'probability_loss': probability_loss,
                'probability_loss_20pct': probability_loss_20pct,
                'statistics': statistics,
                'parameters': {
                    **base_result['parameters'],
                    'account_type': account_type,
                    'tax_year': tax_year,
                    'courtage_class': courtage_class,
                    'rebalancing_frequency': rebalancing_frequency,
                    'tax_adjusted': True,
                }
            }

        except Exception as e:
            logger.error(f"Error in tax-adjusted Monte Carlo: {e}")
            # Fall back to non-tax-adjusted simulation
            return self.simulate_paths(
                initial_capital=initial_capital,
                annual_expected_return=annual_expected_return,
                annual_volatility=annual_volatility,
                years=years,
                num_simulations=num_simulations,
                monthly_steps=True,
                seed=seed
            )

    def apply_shock_scenario(
        self,
        base_result: Dict[str, Any],
        shock_scenario: Dict[str, Any],
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Apply a shock scenario to existing simulation results.

        The shock modifies returns and volatility during the shock period,
        creating a divergence from the base case projection.

        Args:
            base_result: Result from simulate_paths or simulate_paths_with_tax_drag
            shock_scenario: Dict with:
                - year_of_shock: When shock starts (1 = year 1)
                - return_modifier: Additive change to returns (e.g., -0.15 for -15%)
                - volatility_modifier: Multiplicative change (e.g., 1.5 for 50% higher)
                - duration_months: How long shock lasts
            initial_capital: Starting portfolio value

        Returns:
            Modified result dict with shocked paths
        """
        try:
            time_points = base_result['time_points']
            percentiles = base_result['percentiles']

            # Extract shock parameters
            year_of_shock = shock_scenario.get('year_of_shock', 1)
            return_modifier = shock_scenario.get('return_modifier', -0.10)
            vol_modifier = shock_scenario.get('volatility_modifier', 1.5)
            duration_months = shock_scenario.get('duration_months', 12)

            # Calculate shock period indices (assuming monthly steps)
            shock_start_idx = year_of_shock * 12
            shock_end_idx = min(shock_start_idx + duration_months, len(time_points) - 1)

            # Apply shock to each percentile path
            shocked_percentiles = {}

            for pct_key, pct_path in percentiles.items():
                shocked_path = list(pct_path)  # Copy

                # Apply shock: reduce values during shock period proportionally
                for i in range(shock_start_idx, len(shocked_path)):
                    if i <= shock_end_idx:
                        # During shock: apply return modifier
                        months_into_shock = i - shock_start_idx
                        # Cumulative shock effect (compounding)
                        shock_factor = (1 + return_modifier / 12) ** (months_into_shock + 1)
                        shocked_path[i] = shocked_path[i] * shock_factor
                    else:
                        # Post-shock: maintain the reduced level (no automatic recovery)
                        # The relative structure is preserved
                        shock_factor = (1 + return_modifier / 12) ** duration_months
                        shocked_path[i] = shocked_path[i] * shock_factor

                shocked_percentiles[pct_key] = shocked_path

            # Apply to mean path
            shocked_mean = list(base_result['mean_path'])
            for i in range(shock_start_idx, len(shocked_mean)):
                if i <= shock_end_idx:
                    months_into_shock = i - shock_start_idx
                    shock_factor = (1 + return_modifier / 12) ** (months_into_shock + 1)
                    shocked_mean[i] = shocked_mean[i] * shock_factor
                else:
                    shock_factor = (1 + return_modifier / 12) ** duration_months
                    shocked_mean[i] = shocked_mean[i] * shock_factor

            # Recalculate statistics
            probability_loss = self._estimate_probability_below(
                shocked_percentiles, initial_capital
            )

            return {
                'time_points': time_points,
                'percentiles': shocked_percentiles,
                'mean_path': shocked_mean,
                'probability_loss': probability_loss,
                'probability_loss_20pct': self._estimate_probability_below(
                    shocked_percentiles, 0.8 * initial_capital
                ),
                'statistics': {
                    'mean_final': shocked_mean[-1],
                    'median_final': shocked_percentiles['p50'][-1],
                    'initial_capital': initial_capital,
                    'shock_applied': True,
                },
                'parameters': {
                    **base_result.get('parameters', {}),
                    'shock_scenario': shock_scenario,
                },
                'shock_period': {
                    'start_month': shock_start_idx,
                    'end_month': shock_end_idx,
                    'description': shock_scenario.get('description', 'Custom shock'),
                }
            }

        except Exception as e:
            logger.error(f"Error applying shock scenario: {e}")
            return base_result

    def _apply_annual_drag(
        self,
        path: List[float],
        account_type: str,
        tax_year: int,
        courtage_class: str,
        weights: Dict[str, float],
        rebalancing_frequency: str,
        annual_expected_return: float
    ) -> List[float]:
        """Apply annual tax and rebalancing costs to a path."""
        adjusted_path = list(path)  # Copy

        # Process each year end (at month 12, 24, 36, 48, 60)
        for year in range(1, 6):
            year_end_idx = year * 12
            if year_end_idx >= len(adjusted_path):
                break

            value_at_year_end = adjusted_path[year_end_idx]
            value_at_year_start = adjusted_path[(year - 1) * 12]

            # Calculate tax
            tax = self._calculate_annual_tax(
                value_at_year_end,
                value_at_year_start,
                account_type,
                tax_year,
                annual_expected_return
            )

            # Calculate rebalancing cost
            rebal_cost = self._calculate_rebalancing_cost(
                value_at_year_end,
                weights,
                courtage_class,
                rebalancing_frequency
            )

            # Apply drag to all subsequent values
            total_drag = tax + rebal_cost
            drag_factor = max(0, (value_at_year_end - total_drag)) / value_at_year_end if value_at_year_end > 0 else 1.0

            for i in range(year_end_idx, len(adjusted_path)):
                adjusted_path[i] = adjusted_path[i] * drag_factor

        return adjusted_path

    def _calculate_annual_tax(
        self,
        current_value: float,
        previous_value: float,
        account_type: str,
        tax_year: int,
        scenario_return: float
    ) -> float:
        """Calculate annual tax based on account type."""
        try:
            if account_type.upper() in ["ISK", "KF"]:
                result = self.tax_calc.calculate_tax(
                    account_type=account_type,
                    tax_year=tax_year,
                    capital_underlag=current_value,
                )
                return result.get("annual_tax", 0.0)
            elif account_type.upper() == "AF":
                # AF: tax on realized gains (simplified)
                gain = current_value - previous_value
                if gain > 0:
                    result = self.tax_calc.calculate_tax(
                        account_type=account_type,
                        tax_year=tax_year,
                        realized_gains=gain,
                        dividends=0.0,
                        fund_holdings=0.0,
                    )
                    return result.get("total_tax", 0.0)
            return 0.0
        except Exception as e:
            logger.warning(f"Tax calculation failed: {e}")
            return 0.0

    def _calculate_rebalancing_cost(
        self,
        portfolio_value: float,
        weights: Dict[str, float],
        courtage_class: str,
        rebalancing_frequency: str
    ) -> float:
        """Calculate annual rebalancing cost."""
        try:
            if portfolio_value <= 0:
                return 0.0

            positions = [
                {"ticker": t, "value": portfolio_value * w, "shares": 1}
                for t, w in weights.items()
                if w > 0
            ]

            rebal = self.cost_calc.estimate_rebalancing_cost(
                transactions=[{"value": p["value"]} for p in positions],
                courtage_class=courtage_class,
                frequency=rebalancing_frequency,
            )
            return rebal.get("annual_cost", 0.0)
        except Exception as e:
            logger.warning(f"Rebalancing cost calculation failed: {e}")
            return 0.0

    def _estimate_probability_below(
        self,
        percentiles: Dict[str, List[float]],
        threshold: float
    ) -> float:
        """
        Estimate probability of final value being below threshold.
        Uses linear interpolation between known percentiles.
        """
        final_values = {
            5: percentiles['p5'][-1],
            10: percentiles['p10'][-1],
            25: percentiles['p25'][-1],
            50: percentiles['p50'][-1],
            75: percentiles['p75'][-1],
            90: percentiles['p90'][-1],
            95: percentiles['p95'][-1],
        }

        # Sort percentiles
        sorted_pcts = sorted(final_values.items())

        # Find where threshold falls
        for i, (pct, val) in enumerate(sorted_pcts):
            if val >= threshold:
                if i == 0:
                    return float(pct)  # Below lowest percentile
                else:
                    # Interpolate between previous and current
                    prev_pct, prev_val = sorted_pcts[i - 1]
                    # Linear interpolation
                    ratio = (threshold - prev_val) / (val - prev_val) if val != prev_val else 0.5
                    return float(prev_pct + ratio * (pct - prev_pct))

        # Above highest percentile
        return 100.0

    def _calculate_skewness(self, values: np.ndarray) -> float:
        """Calculate skewness of distribution."""
        n = len(values)
        if n < 3:
            return 0.0
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            return 0.0
        return float(np.mean(((values - mean) / std) ** 3))

    def _get_fallback_result(
        self,
        initial_capital: float,
        years: int,
        monthly_steps: bool
    ) -> Dict[str, Any]:
        """Return a fallback result when simulation fails."""
        if monthly_steps:
            num_points = years * 12 + 1
            time_points = [i / 12.0 for i in range(num_points)]
        else:
            num_points = years + 1
            time_points = list(range(num_points))

        # Generate flat paths at initial capital
        flat_path = [initial_capital] * num_points

        return {
            'time_points': time_points,
            'percentiles': {
                'p5': flat_path.copy(),
                'p10': flat_path.copy(),
                'p25': flat_path.copy(),
                'p50': flat_path.copy(),
                'p75': flat_path.copy(),
                'p90': flat_path.copy(),
                'p95': flat_path.copy(),
            },
            'mean_path': flat_path.copy(),
            'probability_loss': 50.0,
            'probability_loss_20pct': 25.0,
            'statistics': {
                'mean_final': initial_capital,
                'median_final': initial_capital,
                'std_final': 0.0,
                'min_final': initial_capital,
                'max_final': initial_capital,
                'initial_capital': initial_capital,
                'fallback': True,
            },
            'parameters': {
                'fallback': True,
                'error': 'Simulation failed, using fallback values',
            }
        }


# Module-level instance for convenience
monte_carlo_projector = MonteCarloProjector()
