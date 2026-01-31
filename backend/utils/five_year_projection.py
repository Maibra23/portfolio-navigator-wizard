#!/usr/bin/env python3
"""
Five-year portfolio projection with Swedish tax and transaction costs.
Produces three regression-based scenarios: optimistic, base, pessimistic.
Uses SwedishTaxCalculator and AvanzaCourtageCalculator for Sweden-realistic figures.
"""

import logging
from typing import Dict, List, Any, Optional

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
) -> Dict[str, Any]:
    """
    Project portfolio value over 5 years with tax and cost drag.

    Three scenarios (regression-based):
    - Base: expected_return
    - Optimistic: expected_return + 0.5 * risk (higher path)
    - Pessimistic: expected_return - 0.5 * risk (lower path)

    Args:
        initial_capital: Starting portfolio value (SEK).
        weights: Ticker -> weight (fraction, sum 1).
        expected_return: Annual expected return (decimal, e.g. 0.08).
        risk: Annual volatility (decimal, e.g. 0.15).
        account_type: "ISK", "KF", or "AF".
        tax_year: 2025 or 2026.
        courtage_class: Avanza courtage class.
        rebalancing_frequency: "monthly", "quarterly", "semi-annual", "annual".

    Returns:
        {
            "years": [0, 1, 2, 3, 4, 5],
            "optimistic": [v0, v1, v2, v3, v4, v5],
            "base": [...],
            "pessimistic": [...],
        }
    """
    tax_calc = SwedishTaxCalculator()
    cost_calc = AvanzaCourtageCalculator()

    # Regression-based scenario returns (annual)
    r_base = expected_return
    r_optimistic = expected_return + 0.5 * risk
    r_pessimistic = expected_return - 0.5 * risk

    # Build portfolio positions for cost estimation (value per ticker from total value)
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
            # AF: tax on imputed gains (simplified: value * return as realized gain)
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
    }
