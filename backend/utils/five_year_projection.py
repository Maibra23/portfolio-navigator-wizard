#!/usr/bin/env python3
"""
Five-year portfolio projection with Swedish tax and transaction costs.

Supports two modes:
1. Deterministic (legacy): Three fixed scenarios based on expected_return +/- 0.5*risk
2. Monte Carlo (recommended): GBM-based stochastic simulation with confidence bands

Uses SwedishTaxCalculator and AvanzaCourtageCalculator for Sweden-realistic figures.
"""

import logging
from typing import Dict, List, Any, Optional, Literal

from .swedish_tax_calculator import SwedishTaxCalculator
from .transaction_cost_calculator import AvanzaCourtageCalculator

logger = logging.getLogger(__name__)


def run_five_year_projection(
    initial_capital: float,
    weights: Dict[str, float],
    expected_return: float,
    risk: float,
    account_type: str,
    tax_year: int,
    courtage_class: str,
    rebalancing_frequency: str = "quarterly",
    mode: Literal["deterministic", "monte_carlo"] = "monte_carlo",
    shock_scenario: Optional[str] = None,
    num_simulations: int = 5000,
) -> Dict[str, Any]:
    """
    Project portfolio value over 5 years with tax and cost drag.

    Args:
        initial_capital: Starting portfolio value (SEK).
        weights: Ticker -> weight (fraction, sum 1).
        expected_return: Annual expected return (decimal, e.g. 0.08).
        risk: Annual volatility (decimal, e.g. 0.15).
        account_type: "ISK", "KF", or "AF".
        tax_year: 2025 or 2026.
        courtage_class: Avanza courtage class.
        rebalancing_frequency: "monthly", "quarterly", "semi-annual", "annual".
        mode: "deterministic" (legacy) or "monte_carlo" (recommended).
        shock_scenario: Optional shock scenario name (e.g., "mild_recession").
        num_simulations: Number of Monte Carlo simulations (default 5000).

    Returns:
        {
            "years": [0, 1, 2, 3, 4, 5],
            "optimistic": [v0, v1, v2, v3, v4, v5],  # p75 in MC mode
            "base": [...],                            # p50 in MC mode
            "pessimistic": [...],                     # p25 in MC mode
            # Additional fields in monte_carlo mode:
            "confidence_bands": {...},
            "monthly_points": [...],
            "probability_loss": float,
            "mode": "monte_carlo" | "deterministic"
        }
    """
    if mode == "monte_carlo":
        return _run_monte_carlo_projection(
            initial_capital=initial_capital,
            weights=weights,
            expected_return=expected_return,
            risk=risk,
            account_type=account_type,
            tax_year=tax_year,
            courtage_class=courtage_class,
            rebalancing_frequency=rebalancing_frequency,
            shock_scenario=shock_scenario,
            num_simulations=num_simulations,
        )
    else:
        return _run_deterministic_projection(
            initial_capital=initial_capital,
            weights=weights,
            expected_return=expected_return,
            risk=risk,
            account_type=account_type,
            tax_year=tax_year,
            courtage_class=courtage_class,
            rebalancing_frequency=rebalancing_frequency,
        )


def _run_monte_carlo_projection(
    initial_capital: float,
    weights: Dict[str, float],
    expected_return: float,
    risk: float,
    account_type: str,
    tax_year: int,
    courtage_class: str,
    rebalancing_frequency: str,
    shock_scenario: Optional[str],
    num_simulations: int,
) -> Dict[str, Any]:
    """Run Monte Carlo projection with confidence bands."""
    try:
        from .monte_carlo_projection import monte_carlo_projector
        from .shock_scenarios import get_scenario

        # Run base simulation with tax drag
        mc_result = monte_carlo_projector.simulate_paths_with_tax_drag(
            initial_capital=initial_capital,
            annual_expected_return=expected_return,
            annual_volatility=risk,
            account_type=account_type,
            tax_year=tax_year,
            courtage_class=courtage_class,
            weights=weights,
            rebalancing_frequency=rebalancing_frequency,
            years=5,
            num_simulations=num_simulations,
        )

        # Apply shock scenario if requested
        if shock_scenario:
            scenario = get_scenario(shock_scenario)
            if scenario:
                mc_result = monte_carlo_projector.apply_shock_scenario(
                    base_result=mc_result,
                    shock_scenario=scenario,
                    initial_capital=initial_capital,
                )

        # Extract percentile paths
        percentiles = mc_result.get('percentiles', {})
        time_points = mc_result.get('time_points', [])

        # Downsample to annual points for backward compatibility
        # Monthly indices: 0, 12, 24, 36, 48, 60
        annual_indices = [0, 12, 24, 36, 48, 60]
        years = [0, 1, 2, 3, 4, 5]

        def extract_annual(path: List[float]) -> List[float]:
            """Extract annual values from monthly path."""
            return [round(path[i], 2) if i < len(path) else path[-1] for i in annual_indices]

        # Map percentiles to legacy scenario names for backward compatibility
        optimistic = extract_annual(percentiles.get('p75', [initial_capital] * 61))
        base = extract_annual(percentiles.get('p50', [initial_capital] * 61))
        pessimistic = extract_annual(percentiles.get('p25', [initial_capital] * 61))

        # Build confidence bands (monthly resolution for smooth charts)
        confidence_bands = {
            'p5': [round(v, 2) for v in percentiles.get('p5', [])],
            'p10': [round(v, 2) for v in percentiles.get('p10', [])],
            'p25': [round(v, 2) for v in percentiles.get('p25', [])],
            'p50': [round(v, 2) for v in percentiles.get('p50', [])],
            'p75': [round(v, 2) for v in percentiles.get('p75', [])],
            'p90': [round(v, 2) for v in percentiles.get('p90', [])],
            'p95': [round(v, 2) for v in percentiles.get('p95', [])],
        }

        # Round monthly time points to 3 decimal places
        monthly_points = [round(t, 3) for t in time_points]

        # Calculate additional metrics
        probability_loss = mc_result.get('probability_loss', 0.0)
        probability_loss_20pct = mc_result.get('probability_loss_20pct', 0.0)
        statistics = mc_result.get('statistics', {})

        return {
            "years": years,
            "optimistic": optimistic,
            "base": base,
            "pessimistic": pessimistic,
            "confidence_bands": confidence_bands,
            "monthly_points": monthly_points,
            "probability_loss": round(probability_loss, 1),
            "probability_loss_20pct": round(probability_loss_20pct, 1),
            "mode": "monte_carlo",
            "shock_scenario": shock_scenario,
            "statistics": {
                "mean_final": round(statistics.get('mean_final', base[-1]), 2),
                "median_final": round(statistics.get('median_final', base[-1]), 2),
                "p5_final": round(percentiles.get('p5', [0])[-1] if percentiles.get('p5') else 0, 2),
                "p95_final": round(percentiles.get('p95', [0])[-1] if percentiles.get('p95') else 0, 2),
            },
            "parameters": {
                "expected_return": expected_return,
                "risk": risk,
                "account_type": account_type,
                "num_simulations": num_simulations,
            }
        }

    except Exception as e:
        logger.error(f"Monte Carlo projection failed, falling back to deterministic: {e}")
        # Fall back to deterministic mode
        result = _run_deterministic_projection(
            initial_capital=initial_capital,
            weights=weights,
            expected_return=expected_return,
            risk=risk,
            account_type=account_type,
            tax_year=tax_year,
            courtage_class=courtage_class,
            rebalancing_frequency=rebalancing_frequency,
        )
        result["mode"] = "deterministic"
        result["fallback_reason"] = str(e)
        return result


def _run_deterministic_projection(
    initial_capital: float,
    weights: Dict[str, float],
    expected_return: float,
    risk: float,
    account_type: str,
    tax_year: int,
    courtage_class: str,
    rebalancing_frequency: str,
) -> Dict[str, Any]:
    """
    Legacy deterministic projection (three fixed scenarios).

    Note: This mode is preserved for backward compatibility.
    The Monte Carlo mode is recommended for more realistic projections.
    """
    tax_calc = SwedishTaxCalculator()
    cost_calc = AvanzaCourtageCalculator()

    # Scenario returns (annual)
    # IMPROVED: Use more realistic scenario spreads
    # - Optimistic: 75th percentile approximation (mean + 0.67 * std)
    # - Base: Expected return (50th percentile / mean)
    # - Pessimistic: 25th percentile approximation (mean - 0.67 * std)
    # The 0.67 factor comes from the normal distribution quantile z_0.75 ≈ 0.674
    r_base = expected_return
    r_optimistic = expected_return + 0.67 * risk
    r_pessimistic = expected_return - 0.67 * risk

    def positions_from_value(total_value: float) -> List[Dict[str, Any]]:
        return [
            {"ticker": t, "value": total_value * w, "shares": 1}
            for t, w in weights.items()
            if w > 0
        ]

    def annual_tax_for_value(value: float, scenario_return: float) -> float:
        if account_type.upper() in ["ISK", "KF"]:
            result = tax_calc.calculate_tax(
                account_type=account_type,
                tax_year=tax_year,
                capital_underlag=value,
            )
            return result.get("annual_tax", 0.0)
        elif account_type.upper() == "AF":
            estimated_gain = value * scenario_return
            result = tax_calc.calculate_tax(
                account_type=account_type,
                tax_year=tax_year,
                realized_gains=max(0, estimated_gain),
                dividends=0.0,
                fund_holdings=0.0,
            )
            return result.get("total_tax", 0.0)
        return 0.0

    def annual_rebalancing_cost(value: float) -> float:
        if value <= 0:
            return 0.0
        positions = positions_from_value(value)
        try:
            rebal = cost_calc.estimate_rebalancing_cost(
                transactions=[{"value": p["value"]} for p in positions],
                courtage_class=courtage_class,
                frequency=rebalancing_frequency,
            )
            return rebal.get("annual_cost", 0.0)
        except Exception as e:
            logger.warning(f"Rebalancing cost estimation failed: {e}")
            return 0.0

    years = [0, 1, 2, 3, 4, 5]
    optimistic = [initial_capital]
    base = [initial_capital]
    pessimistic = [initial_capital]

    for year in range(1, 6):
        v_opt_prev = optimistic[year - 1]
        v_base_prev = base[year - 1]
        v_pess_prev = pessimistic[year - 1]

        tax_opt = annual_tax_for_value(v_opt_prev, r_optimistic)
        tax_base = annual_tax_for_value(v_base_prev, r_base)
        tax_pess = annual_tax_for_value(v_pess_prev, r_pessimistic)

        cost_opt = annual_rebalancing_cost(v_opt_prev)
        cost_base = annual_rebalancing_cost(v_base_prev)
        cost_pess = annual_rebalancing_cost(v_pess_prev)

        v_opt = v_opt_prev * (1 + r_optimistic) - tax_opt - cost_opt
        v_base = v_base_prev * (1 + r_base) - tax_base - cost_base
        v_pess = v_pess_prev * (1 + r_pessimistic) - tax_pess - cost_pess

        # Floor at 0
        v_opt = max(0.0, v_opt)
        v_base = max(0.0, v_base)
        v_pess = max(0.0, v_pess)

        optimistic.append(round(v_opt, 2))
        base.append(round(v_base, 2))
        pessimistic.append(round(v_pess, 2))

    return {
        "years": years,
        "optimistic": optimistic,
        "base": base,
        "pessimistic": pessimistic,
        "mode": "deterministic",
    }


def get_projection_scenarios() -> List[Dict[str, Any]]:
    """Get available shock scenarios for projection."""
    try:
        from .shock_scenarios import list_scenarios
        return list_scenarios()
    except Exception as e:
        logger.error(f"Error listing scenarios: {e}")
        return []
