"""
Conservative Portfolio Generation Approach
=========================================

This module implements a conservative generation approach with asymmetric tolerance
for aggressive profiles. It can be toggled on/off and compared against the standard approach.

Key differences from standard approach:
1. Asymmetric tolerance: Accepts high returns, rejects low returns for aggressive profiles
2. Conservative return caps: 60% for aggressive, 75% for very-aggressive
3. Widened return and risk ranges
4. Modular design for easy comparison and toggling
"""

import logging
from typing import Dict, Tuple, Optional

from .risk_profile_config import UNIFIED_RISK_PROFILE_CONFIG

logger = logging.getLogger(__name__)

# Conservative configuration (from test results)
CONSERVATIVE_CONFIG = {
    'aggressive': {
        'return_range': (0.14, 0.50),
        'max_realistic_return': 0.60,
        'quality_risk_range': (0.18, 0.55),
        'return_tolerance_upper': 0.10,
        'return_tolerance_lower': 0.01,
    },
    'very-aggressive': {
        'return_range': (0.17, 0.65),
        'max_realistic_return': 0.75,
        'quality_risk_range': (0.22, 0.65),
        'return_tolerance_upper': 0.15,
        'return_tolerance_lower': 0.01,
    },
}


class ConservativePortfolioGenerator:
    """Conservative portfolio generation approach with asymmetric tolerance.

    This class provides methods to:
    1. Apply conservative configuration to risk profiles
    2. Assess portfolio quality with asymmetric tolerance
    3. Check if conservative approach should be used for a profile
    """

    def __init__(self, enabled: bool = True, apply_to_profiles: Optional[list] = None) -> None:
        """Initialize conservative generator.

        Args:
            enabled: Whether conservative approach is enabled
            apply_to_profiles: List of profiles to apply to (default: ['aggressive', 'very-aggressive'])
        """
        self.enabled = enabled
        self.apply_to_profiles = apply_to_profiles or ['aggressive', 'very-aggressive']
        self.original_configs: Dict[str, Dict] = {}

    def should_use_conservative(self, risk_profile: str) -> bool:
        """Check if conservative approach should be used for this profile."""
        return self.enabled and risk_profile in self.apply_to_profiles

    def apply_conservative_config(self, risk_profile: str) -> Dict:
        """Apply conservative configuration to a risk profile.

        Returns the original config for restoration.
        """
        if not self.should_use_conservative(risk_profile):
            return {}

        if risk_profile not in CONSERVATIVE_CONFIG:
            logger.warning("⚠️ No conservative config for %s, using standard", risk_profile)
            return {}

        # Store original config
        original = {
            'return_range': UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['return_range'],
            'max_realistic_return': UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['max_realistic_return'],
            'quality_risk_range': UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['quality_risk_range'],
            'return_tolerance': UNIFIED_RISK_PROFILE_CONFIG[risk_profile].get('return_tolerance', 0.04),
        }

        self.original_configs[risk_profile] = original

        # Apply conservative config
        conservative = CONSERVATIVE_CONFIG[risk_profile]
        UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['return_range'] = conservative['return_range']
        UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['max_realistic_return'] = conservative['max_realistic_return']
        UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['quality_risk_range'] = conservative['quality_risk_range']
        UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['return_tolerance'] = conservative.get('return_tolerance_upper', 0.10)

        logger.info("✅ Applied conservative config to %s", risk_profile)
        return original

    def restore_original_config(self, risk_profile: str) -> None:
        """Restore original configuration for a risk profile."""
        if risk_profile in self.original_configs:
            orig = self.original_configs[risk_profile]
            UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['return_range'] = orig['return_range']
            UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['max_realistic_return'] = orig['max_realistic_return']
            UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['quality_risk_range'] = orig['quality_risk_range']
            UNIFIED_RISK_PROFILE_CONFIG[risk_profile]['return_tolerance'] = orig['return_tolerance']
            logger.info("✅ Restored original config for %s", risk_profile)

    def assess_portfolio_quality_asymmetric(
        self,
        risk_profile: str,
        metrics: Dict,
        return_target: float,
    ) -> Optional[Tuple[str, Dict]]:
        """Asymmetric quality assessment for aggressive profiles.

        For aggressive profiles:
        - ACCEPT high returns (relaxed upper bound, up to max_realistic_return)
        - REJECT low returns (strict lower bound, 1% tolerance)

        For other profiles:
        - Use standard symmetric logic (handled by caller)

        Returns:
            Tuple[str, Dict]: (status, details) or None to fall back to standard logic.
        """
        if not self.should_use_conservative(risk_profile):
            # Use standard symmetric logic (handled by caller)
            return None

        try:
            config = UNIFIED_RISK_PROFILE_CONFIG.get(risk_profile)
            if not config:
                return ("REJECT", {"error": "No config found"})

            ret = metrics.get('expected_return', metrics.get('expectedReturn', 0))
            risk = metrics.get('risk', 0)

            # Ensure decimal format
            if ret > 1.0:
                ret = ret / 100.0
            if risk > 1.0:
                risk = risk / 100.0

            min_ret, max_ret = config['return_range']
            min_risk, max_risk = config['quality_risk_range']
            max_risk_variance = config.get('max_risk_variance', 0.08)
            risk_max = max_risk + max_risk_variance

            # ASYMMETRIC TOLERANCE for aggressive profiles
            return_violation_pct = 0.0

            # Lower bound: STRICT (1% tolerance)
            if ret < min_ret:
                return_violation_pct = (min_ret - ret) * 100.0
                if return_violation_pct > 1.0:  # Strict: only 1% tolerance below minimum
                    return (
                        "REJECT",
                        {
                            "return": ret * 100.0,
                            "risk": risk * 100.0,
                            "return_violation": return_violation_pct,
                            "risk_violation": 0.0,
                            "max_violation": return_violation_pct,
                            "reason": "return_below_minimum",
                        },
                    )

            # Upper bound: RELAXED (up to max_realistic_return)
            elif ret > max_ret:
                return_violation_pct = (ret - max_ret) * 100.0
                max_allowed = config.get('max_realistic_return', 0.60)

                # Check against max_realistic_return (hard cap)
                if ret > max_allowed:
                    return (
                        "REJECT",
                        {
                            "return": ret * 100.0,
                            "risk": risk * 100.0,
                            "return_violation": return_violation_pct,
                            "risk_violation": 0.0,
                            "max_violation": return_violation_pct,
                            "reason": "return_exceeds_max_allowed",
                        },
                    )

                # Accept with relaxed tolerance (up to max_allowed)
                return (
                    "ACCEPTABLE",
                    {
                        "return": ret * 100.0,
                        "risk": risk * 100.0,
                        "return_violation": return_violation_pct,
                        "risk_violation": 0.0,
                        "max_violation": return_violation_pct,
                    },
                )

            # Risk: Standard symmetric logic
            risk_violation_pct = 0.0
            if risk < min_risk:
                risk_violation_pct = (min_risk - risk) * 100.0
                if risk_violation_pct > 2.0:
                    return (
                        "REJECT",
                        {
                            "return": ret * 100.0,
                            "risk": risk * 100.0,
                            "return_violation": return_violation_pct,
                            "risk_violation": risk_violation_pct,
                            "max_violation": risk_violation_pct,
                            "reason": "risk_below_minimum",
                        },
                    )
            elif risk > risk_max:
                risk_violation_pct = (risk - risk_max) * 100.0
                if risk_violation_pct > 2.0:
                    return (
                        "REJECT",
                        {
                            "return": ret * 100.0,
                            "risk": risk * 100.0,
                            "return_violation": return_violation_pct,
                            "risk_violation": risk_violation_pct,
                            "max_violation": risk_violation_pct,
                            "reason": "risk_exceeds_maximum",
                        },
                    )

            # If we get here, portfolio is acceptable
            max_violation_pct = max(return_violation_pct, risk_violation_pct)
            if max_violation_pct == 0:
                return (
                    "COMPLIANT",
                    {
                        "return": ret * 100.0,
                        "risk": risk * 100.0,
                        "return_violation": return_violation_pct,
                        "risk_violation": risk_violation_pct,
                        "max_violation": max_violation_pct,
                    },
                )

            return (
                "ACCEPTABLE",
                {
                    "return": ret * 100.0,
                    "risk": risk * 100.0,
                    "return_violation": return_violation_pct,
                    "risk_violation": risk_violation_pct,
                    "max_violation": max_violation_pct,
                },
            )

        except Exception as e:  # pragma: no cover - safety net
            logger.error("Error in asymmetric quality assessment: %s", e)
            return ("REJECT", {"error": str(e)})
