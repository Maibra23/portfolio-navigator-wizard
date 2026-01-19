"""
Diversification Constraint Experiments
======================================

This module implements diversification strategies for aggressive profiles.
Strategy 5 (Return Target-Based) is the default for conservative approach.
"""

import logging
from typing import Dict, Optional, Tuple

from .risk_profile_config import UNIFIED_RISK_PROFILE_CONFIG

logger = logging.getLogger(__name__)


class DiversificationExperiment:
    """Base class for diversification experiments."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    def get_diversification_range(
        self,
        risk_profile: str,
        metrics: Optional[Dict] = None,
    ) -> Tuple[float, float]:
        """Get diversification range for this strategy."""
        raise NotImplementedError

    def should_enforce_diversification(
        self,
        risk_profile: str,
        portfolio_index: int,
        metrics: Optional[Dict] = None,
    ) -> bool:
        """Check if diversification should be enforced at this stage."""
        raise NotImplementedError


class Strategy5_ReturnTargetBasedDiversification(DiversificationExperiment):
    """Strategy 5: Return Target-Based Diversification.

    Portfolios targeting higher returns have lower diversification requirements.
    Portfolios targeting lower returns have higher diversification requirements.
    """

    def __init__(self) -> None:
        super().__init__(
            name="Return Target-Based Diversification",
            description="Diversification requirements inversely related to return target",
        )
        # Base diversification ranges for higher-risk profiles
        self.base_ranges = {
            "aggressive": (30.0, 100.0),
            "very-aggressive": (20.0, 100.0),
        }

    def get_diversification_range(
        self,
        risk_profile: str,
        metrics: Optional[Dict] = None,
    ) -> Tuple[float, float]:
        """Return return-target-based diversification range."""
        # For profiles without a special config, fall back to unified config
        if risk_profile not in self.base_ranges:
            config = UNIFIED_RISK_PROFILE_CONFIG.get(risk_profile, {})
            return config.get("diversification_range", (50.0, 100.0))

        base_min, base_max = self.base_ranges[risk_profile]

        # Use return range from unified config
        config = UNIFIED_RISK_PROFILE_CONFIG[risk_profile]
        return_range = config["return_range"]

        # If metrics available, use realized/expected return; otherwise use mid-point of range
        if metrics:
            ret = metrics.get("expected_return", metrics.get("expectedReturn", 0.0))
            if ret > 1.0:
                ret = ret / 100.0
        else:
            # Use middle of return range as proxy
            ret = (return_range[0] + return_range[1]) / 2.0

        # Normalize return to 0–1 scale within the configured range
        if return_range[1] > return_range[0]:
            return_norm = (ret - return_range[0]) / (return_range[1] - return_range[0])
        else:
            return_norm = 0.5

        # Higher return target → lower diversification required
        # adjustment in [0.5, 1.0]
        adjustment = 1.0 - (return_norm * 0.5)
        adjusted_min = base_min * adjustment

        # Never allow diversification minimum below 10%
        return (max(10.0, adjusted_min), base_max)

    def should_enforce_diversification(
        self,
        risk_profile: str,
        portfolio_index: int,
        metrics: Optional[Dict] = None,
    ) -> bool:
        """Always enforce diversification for Strategy 5."""
        return True


# Registry of strategies
DIVERSIFICATION_STRATEGIES: Dict[str, DiversificationExperiment] = {
    "strategy5_return_target_based": Strategy5_ReturnTargetBasedDiversification(),
}


def get_diversification_strategy(strategy_name: str) -> Optional[DiversificationExperiment]:
    """Get a diversification strategy by name."""
    strategy = DIVERSIFICATION_STRATEGIES.get(strategy_name)
    if not strategy:
        logger.warning("Unknown diversification strategy requested: %s", strategy_name)
    return strategy

