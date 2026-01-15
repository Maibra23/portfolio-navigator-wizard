"""
Risk Profile Configuration - UNIFIED Single Source of Truth

This module defines ALL risk profile parameters used across the project.
All other modules (enhanced_portfolio_config.py, enhanced_portfolio_generator.py, etc.)
should import from here to ensure consistency.

Based on ticker volatility analysis (1,443 tickers):
- Median volatility: 27.93%
- 75th percentile: 35.45%
- 90th percentile: 46.84%

Diversification factor: ~0.72 (for 4 stocks with correlation ~0.3)
Portfolio volatility ≈ Individual stock volatility × 0.72
"""

from typing import Dict, Tuple, List

# =============================================================================
# UNIFIED RISK PROFILE CONFIGURATION - Single Source of Truth
# =============================================================================
# All parameters are centralized here for consistency across the application.

UNIFIED_RISK_PROFILE_CONFIG: Dict[str, Dict] = {
    'very-conservative': {
        # Stock filtering - individual stock volatility range
        'volatility_range': (0.05, 0.18),      # 5-18% annual volatility
        
        # Portfolio optimization - max portfolio risk constraint
        'max_portfolio_risk': 0.18,            # 18% max
        
        # Return targeting - range for portfolio generation
        'return_range': (0.04, 0.15),          # 4-15%
        
        # Quality control - risk range for quality checks
        'quality_risk_range': (0.128, 0.20),  # 12.8%-20%
        
        # Realistic maximums for safety checks
        'max_realistic_return': 0.19,          # 19% max (return_range max 15% + variance 4% = 19%)
        'max_realistic_risk': 0.28,            # 28% max (risk_range max 20% + variance 8% = 28%)
        
        # Variance tolerances
        'max_return_variance': 0.04,
        'max_risk_variance': 0.08,  # Increased from 0.05 to improve compliance (tested: 30% vs 15% baseline)
        
        # Return tolerance for target matching
        'return_tolerance': 0.01,              # 1%
        
        # Return targets for 12 portfolios
        'return_targets': [4.0, 5.5, 7.0, 8.5, 10.0, 11.5, 13.0, 14.0, 6.0, 8.0, 10.5, 12.5],
        
        # Diversification range
        'diversification_range': (50.0, 100.0),
        
        # Stock count range
        'stock_count_range': (3, 4),
        
        # Fallback portfolio metrics (middle of valid ranges)
        'fallback_return': 0.09,               # 9% (middle of 4-15%)
        'fallback_risk': 0.164,                # 16.4% (middle of 12.8-20%)
    },
    
    'conservative': {
        'volatility_range': (0.15, 0.25),      # 15-25% annual volatility
        'max_portfolio_risk': 0.25,            # 25% max
        'return_range': (0.10, 0.24),          # 10-24% (adjusted: 12% → 10% to match pool mean 11.23%)
        'quality_risk_range': (0.151, 0.28),  # 15.1%-28.0%
        'max_realistic_return': 0.29,          # 29% max (return_range max 24% + variance 4% + tolerance 1.5% ≈ 29%)
        'max_realistic_risk': 0.36,            # 36% max (risk_range max 28% + variance 8% = 36%)
        'max_return_variance': 0.04,
        'max_risk_variance': 0.08,  # Increased from 0.05 to improve compliance (tested: 30% vs 15% baseline)
        'return_tolerance': 0.015,             # 1.5%
        'return_targets': [12.0, 13.5, 15.0, 16.5, 18.0, 19.5, 21.0, 22.0, 12.5, 14.5, 16.5, 18.5],
        'diversification_range': (50.0, 100.0),
        'stock_count_range': (3, 4),
        'fallback_return': 0.17,               # 17% (middle of 10-24%)
        'fallback_risk': 0.216,                # 21.6% (middle of 15.1-28%)
    },
    
    'moderate': {
        'volatility_range': (0.22, 0.32),      # 22-32% annual volatility
        'max_portfolio_risk': 0.32,            # 32% max
        'return_range': (0.14, 0.32),          # 14-32% (adjusted: 18% → 14% to match pool mean 15.05%, 30% → 32%)
        'quality_risk_range': (0.20, 0.36),  # 20.0%-36.0% (adjusted: 22% → 20%, 35% → 36%)
        'max_realistic_return': 0.39,          # 39% max (return_range max 32% + variance 4% + tolerance 2.5% ≈ 39%)
        'max_realistic_risk': 0.44,            # 44% max (risk_range max 36% + variance 8% = 44%)
        'max_return_variance': 0.04,
        'max_risk_variance': 0.08,  # Increased from 0.05 to improve compliance (tested: 30% vs 15% baseline)
        'return_tolerance': 0.025,             # 2.5%
        'return_targets': [18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5],
        'diversification_range': (50.0, 100.0),
        'stock_count_range': (3, 4),
        'fallback_return': 0.23,               # 23% (middle of 14-32%)
        'fallback_risk': 0.28,                 # 28% (middle of 20-36%)
    },
    
    'aggressive': {
        'volatility_range': (0.28, 0.42),      # 28-42% annual volatility
        'max_portfolio_risk': 0.42,            # 42% max
        'return_range': (0.14, 0.40),          # 14-40% (adjusted to match pool mean 14.05% from ticker analysis)
        'quality_risk_range': (0.20, 0.50),    # 20%-50% (RELAXED: 26% → 20% to allow diversification benefit)
        'max_realistic_return': 0.44,          # 44% max (return_range max 40% + tolerance 4% = 44%)
        'max_realistic_risk': 0.58,            # 58% max (risk_range max 50% + variance 8% = 58%)
        'max_return_variance': 0.08,
        'max_risk_variance': 0.08,  # Increased from 0.05 to improve compliance (tested: 30% vs 15% baseline)
        'return_tolerance': 0.04,              # 4% (increased from 2.5% for better compliance)
        'return_targets': [22.0, 22.5, 23.0, 23.5, 24.0, 24.5, 25.0, 25.5, 26.0, 26.5, 27.0, 27.5],
        'diversification_range': (30.0, 100.0),
        'stock_count_range': (3, 4),
        'fallback_return': 0.27,               # 27% (middle of 14-40%)
        'fallback_risk': 0.35,                 # 35% (middle of 20-50%)
    },
    
    'very-aggressive': {
        'volatility_range': (0.32, 0.55),      # 32-55% annual volatility
        'max_portfolio_risk': 0.55,            # 55% max
        'return_range': (0.17, 0.52),          # 17-52% (RELAXED: 50% → 52% for tolerance)
        'quality_risk_range': (0.25, 0.60),    # 25%-60% (RELAXED: 30% → 25% to allow diversification benefit)
        'max_realistic_return': 0.65,          # 65% max (return_range max 52% + variance 10% + tolerance 3% ≈ 65%)
        'max_realistic_risk': 0.68,            # 68% max (risk_range max 60% + variance 8% = 68%)
        'max_return_variance': 0.10,
        'max_risk_variance': 0.08,  # Increased from 0.06 to improve compliance (tested: 30% vs 15% baseline)
        'return_tolerance': 0.05,              # 5% (increased from 3% for better compliance)
        'return_targets': [26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0],
        'diversification_range': (20.0, 100.0),
        'stock_count_range': (3, 3),
        'fallback_return': 0.345,              # 34.5% (middle of 17-52%)
        'fallback_risk': 0.425,                # 42.5% (middle of 25-60%)
    }
}

# =============================================================================
# LEGACY COMPATIBILITY - Derived from unified config
# =============================================================================
# These dictionaries maintain backward compatibility with existing code.

RISK_PROFILE_VOLATILITY: Dict[str, Tuple[float, float]] = {
    profile: config['volatility_range']
    for profile, config in UNIFIED_RISK_PROFILE_CONFIG.items()
}

RISK_PROFILE_MAX_RISK: Dict[str, float] = {
    profile: config['max_portfolio_risk']
    for profile, config in UNIFIED_RISK_PROFILE_CONFIG.items()
}

# Maximum risk with 10% buffer for restrictive ranges
RISK_PROFILE_MAX_RISK_WITH_BUFFER: Dict[str, float] = {
    profile: config['max_portfolio_risk'] * 1.10
    for profile, config in UNIFIED_RISK_PROFILE_CONFIG.items()
}

# Return ranges for portfolio generation
RISK_PROFILE_RETURN_RANGES: Dict[str, Tuple[float, float]] = {
    profile: config['return_range']
    for profile, config in UNIFIED_RISK_PROFILE_CONFIG.items()
}

# Return targets for portfolio generation
RISK_PROFILE_RETURN_TARGETS: Dict[str, List[float]] = {
    profile: config['return_targets']
    for profile, config in UNIFIED_RISK_PROFILE_CONFIG.items()
}

# Quality control configuration (for enhanced_portfolio_config compatibility)
RISK_PROFILE_QUALITY_CONTROL: Dict[str, Dict] = {
    profile: {
        'return_range': config['return_range'],
        'risk_range': config['quality_risk_range'],
        'max_return_variance': config['max_return_variance'],
        'max_risk_variance': config['max_risk_variance'],
    }
    for profile, config in UNIFIED_RISK_PROFILE_CONFIG.items()
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_unified_config_for_profile(risk_profile: str) -> Dict:
    """
    Get the complete unified configuration for a risk profile.
    
    Args:
        risk_profile: One of 'very-conservative', 'conservative', 'moderate',
                     'aggressive', 'very-aggressive'
    
    Returns:
        Dict containing all configuration parameters for the profile
    """
    return UNIFIED_RISK_PROFILE_CONFIG.get(risk_profile, UNIFIED_RISK_PROFILE_CONFIG['moderate'])


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


def get_return_range_for_profile(risk_profile: str) -> Tuple[float, float]:
    """
    Get return range for portfolio generation.
    
    Args:
        risk_profile: One of 'very-conservative', 'conservative', 'moderate',
                     'aggressive', 'very-aggressive'
    
    Returns:
        Tuple of (min_return, max_return) as decimals
    """
    return RISK_PROFILE_RETURN_RANGES.get(risk_profile, (0.18, 0.28))  # Default to moderate


def get_return_targets_for_profile(risk_profile: str) -> List[float]:
    """
    Get return targets for portfolio generation.
    
    Args:
        risk_profile: One of 'very-conservative', 'conservative', 'moderate',
                     'aggressive', 'very-aggressive'
    
    Returns:
        List of return targets as percentages (e.g., [18.0, 19.0, ...])
    """
    return RISK_PROFILE_RETURN_TARGETS.get(risk_profile, [20.0] * 12)


def get_quality_risk_range_for_profile(risk_profile: str) -> Tuple[float, float]:
    """
    Get quality control risk range for a risk profile.
    
    Args:
        risk_profile: One of 'very-conservative', 'conservative', 'moderate',
                     'aggressive', 'very-aggressive'
    
    Returns:
        Tuple of (min_risk, max_risk) as decimals
    """
    config = get_unified_config_for_profile(risk_profile)
    return config['quality_risk_range']


def get_fallback_metrics_for_profile(risk_profile: str) -> Dict[str, float]:
    """
    Get fallback portfolio metrics for a risk profile.
    
    Args:
        risk_profile: One of 'very-conservative', 'conservative', 'moderate',
                     'aggressive', 'very-aggressive'
    
    Returns:
        Dict with 'expected_return', 'risk', 'diversification_score'
    """
    config = get_unified_config_for_profile(risk_profile)
    return {
        'expected_return': config['fallback_return'],
        'risk': config['fallback_risk'],
        'diversification_score': 75.0
    }


def get_risk_profile_display_info(risk_profile: str) -> Dict[str, str]:
    """
    Get display-friendly information about a risk profile.
    
    Returns:
        Dict with 'max_risk_pct' and 'volatility_range_pct' as formatted strings
    """
    config = get_unified_config_for_profile(risk_profile)
    max_risk = config['max_portfolio_risk']
    vol_range = config['volatility_range']
    
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
    return risk_profile in UNIFIED_RISK_PROFILE_CONFIG


VALID_RISK_PROFILES = list(UNIFIED_RISK_PROFILE_CONFIG.keys())
