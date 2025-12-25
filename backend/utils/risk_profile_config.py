"""
Risk Profile Configuration - Single Source of Truth

This module defines all risk profile limits and volatility ranges used across the project.
All other modules should import from here to ensure consistency.

Based on ticker volatility analysis (1,443 tickers):
- Median volatility: 27.93%
- 75th percentile: 35.45%
- 90th percentile: 46.84%

Diversification factor: ~0.72 (for 4 stocks with correlation ~0.3)
Portfolio volatility ≈ Individual stock volatility × 0.72
"""

from typing import Dict, Tuple

# =============================================================================
# VOLATILITY RANGES - Used for filtering individual tickers
# =============================================================================
# These ranges determine which individual stocks are eligible for each risk profile.
# Format: (min_volatility, max_volatility) as decimals (e.g., 0.18 = 18%)

RISK_PROFILE_VOLATILITY: Dict[str, Tuple[float, float]] = {
    'very-conservative': (0.05, 0.18),    # 5-18% annual volatility
    'conservative': (0.15, 0.25),         # 15-25% annual volatility
    'moderate': (0.22, 0.32),             # 22-32% annual volatility
    'aggressive': (0.28, 0.42),           # UPDATED: 28-42% annual volatility (expanded from 28-35% based on pool analysis - 70 tickers available)
    'very-aggressive': (0.32, 0.55)       # UPDATED: 32-55% annual volatility (expanded from 32-47% based on pool analysis - 36 tickers available)
}

# =============================================================================
# MAX RISK LIMITS - Used for portfolio optimization constraints
# =============================================================================
# These limits constrain the maximum volatility of the optimized portfolio.
# Derived from volatility range upper bounds with adjustments for aggressive profiles
# based on actual ticker distribution percentiles.

RISK_PROFILE_MAX_RISK: Dict[str, float] = {
    'very-conservative': 0.18,  # 18% - From range upper bound
    'conservative': 0.25,       # 25% - From range upper bound
    'moderate': 0.32,           # 32% - From range upper bound
    'aggressive': 0.42,         # UPDATED: 42% - Expanded from 35% to match volatility range (based on pool analysis)
    'very-aggressive': 0.55     # UPDATED: 55% - Expanded from 47% to match volatility range (based on pool analysis)
}

# Maximum risk with 10% buffer for restrictive ranges
# Applied when base limits are too restrictive and cause excessive rejections
RISK_PROFILE_MAX_RISK_WITH_BUFFER: Dict[str, float] = {
    'very-conservative': 0.18 * 1.10,  # 19.8% - 10% buffer
    'conservative': 0.25 * 1.10,       # 27.5% - 10% buffer
    'moderate': 0.32 * 1.10,           # 35.2% - 10% buffer
    'aggressive': 0.42 * 1.10,         # 46.2% - 10% buffer
    'very-aggressive': 0.55 * 1.10     # 60.5% - 10% buffer
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_max_risk_for_profile(risk_profile: str, use_buffer: bool = False) -> float:
    """
    Get maximum portfolio risk constraint for a risk profile.
    
    Args:
        risk_profile: One of 'very-conservative', 'conservative', 'moderate', 
                     'aggressive', 'very-aggressive'
        use_buffer: If True, apply 10% buffer for restrictive ranges
    
    Returns:
        Maximum allowed portfolio volatility as decimal (e.g., 0.25 = 25%)
    """
    if use_buffer:
        return RISK_PROFILE_MAX_RISK_WITH_BUFFER.get(risk_profile, 0.32 * 1.10)
    return RISK_PROFILE_MAX_RISK.get(risk_profile, 0.32)  # Default to moderate


def get_volatility_range_for_profile(risk_profile: str) -> Tuple[float, float]:
    """
    Get volatility range for filtering individual tickers.
    
    Args:
        risk_profile: One of 'very-conservative', 'conservative', 'moderate',
                     'aggressive', 'very-aggressive'
    
    Returns:
        Tuple of (min_volatility, max_volatility) as decimals
    """
    return RISK_PROFILE_VOLATILITY.get(risk_profile, (0.22, 0.32))  # Default to moderate


def get_risk_profile_display_info(risk_profile: str) -> Dict[str, str]:
    """
    Get display-friendly information about a risk profile.
    
    Returns:
        Dict with 'max_risk_pct' and 'volatility_range_pct' as formatted strings
    """
    max_risk = RISK_PROFILE_MAX_RISK.get(risk_profile, 0.32)
    vol_range = RISK_PROFILE_VOLATILITY.get(risk_profile, (0.22, 0.32))
    
    return {
        'max_risk_pct': f"{max_risk * 100:.0f}%",
        'volatility_range_pct': f"{vol_range[0] * 100:.0f}%-{vol_range[1] * 100:.0f}%",
        'max_risk': max_risk,
        'volatility_range': vol_range
    }


# =============================================================================
# VALIDATION
# =============================================================================

def validate_risk_profile(risk_profile: str) -> bool:
    """Check if a risk profile is valid."""
    return risk_profile in RISK_PROFILE_MAX_RISK


VALID_RISK_PROFILES = list(RISK_PROFILE_MAX_RISK.keys())
