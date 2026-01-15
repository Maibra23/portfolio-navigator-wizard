#!/usr/bin/env python3
"""
Enhanced Portfolio Configuration
================================
Implements portfolio variation strategies using configuration from risk_profile_config.py

All return ranges, risk parameters, and targets are imported from the centralized
risk_profile_config.py to ensure consistency across the application.
"""

from typing import Dict, Tuple, List

# Import from unified configuration (SINGLE SOURCE OF TRUTH)
from .risk_profile_config import (
    UNIFIED_RISK_PROFILE_CONFIG,
    RISK_PROFILE_RETURN_RANGES,
    RISK_PROFILE_RETURN_TARGETS,
    RISK_PROFILE_QUALITY_CONTROL,
)


class EnhancedPortfolioConfig:
    """
    Enhanced portfolio configuration with:
    1. Return ranges imported from unified config
    2. Diversification score variation within profiles
    3. Stock count variation within profiles  
    4. Return target gradation to ensure uniqueness
    
    All return ranges and risk parameters are imported from risk_profile_config.py
    to maintain consistency across the application.
    """
    
    # ==========================================================================
    # RETURN RANGES - Imported from unified config
    # ==========================================================================
    ENHANCED_RETURN_RANGES: Dict[str, Tuple[float, float]] = RISK_PROFILE_RETURN_RANGES
    
    # ==========================================================================
    # DIVERSIFICATION VARIATION - Natural variation within profiles
    # ==========================================================================
    DIVERSIFICATION_VARIATION: Dict[str, Tuple[float, float]] = {
        profile: config['diversification_range']
        for profile, config in UNIFIED_RISK_PROFILE_CONFIG.items()
    }
    
    # ==========================================================================
    # STOCK COUNT RANGES - Imported from unified config
    # ==========================================================================
    STOCK_COUNT_RANGES: Dict[str, Tuple[int, int]] = {
        profile: config['stock_count_range']
        for profile, config in UNIFIED_RISK_PROFILE_CONFIG.items()
    }
    
    # ==========================================================================
    # RETURN TARGET GRADATION - Imported from unified config
    # ==========================================================================
    RETURN_TARGET_GRADATION: Dict[str, List[float]] = RISK_PROFILE_RETURN_TARGETS
    
    # Test configuration for 30 portfolios (50% of total)
    TEST_PORTFOLIOS_PER_PROFILE = 6  # 6 per profile × 5 profiles = 30 total
    
    # ==========================================================================
    # QUALITY CONTROL - Imported from unified config
    # ==========================================================================
    ENHANCED_QUALITY_CONTROL: Dict[str, Dict] = RISK_PROFILE_QUALITY_CONTROL
    
    @classmethod
    def get_return_target(cls, risk_profile: str, portfolio_index: int) -> float:
        """Get specific return target for a portfolio to ensure uniqueness"""
        targets = cls.RETURN_TARGET_GRADATION.get(risk_profile, [0.10])
        # Cycle through targets, ensuring each portfolio gets a unique target
        target_index = portfolio_index % len(targets)
        return targets[target_index] / 100.0  # Convert to decimal
    
    @classmethod
    def get_diversification_score(cls, risk_profile: str, portfolio_index: int) -> float:
        """Get diversification score with variation within profile"""
        import random
        
        # Use portfolio index as seed for consistent results
        random.seed(portfolio_index + hash(risk_profile))
        
        div_range = cls.DIVERSIFICATION_VARIATION.get(risk_profile, (75.0, 100.0))
        score = random.uniform(div_range[0], div_range[1])
        
        # Round to 1 decimal place
        return round(score, 1)
    
    @classmethod
    def get_stock_count(cls, risk_profile: str, portfolio_index: int) -> int:
        """Get stock count with variation within profile"""
        import random
        
        # Use portfolio index as seed for consistent results
        random.seed(portfolio_index + hash(risk_profile) + 42)  # Different seed
        
        count_range = cls.STOCK_COUNT_RANGES.get(risk_profile, (3, 5))
        count = random.randint(count_range[0], count_range[1])
        
        return count
    
    @classmethod
    def get_adaptive_return_target(cls, risk_profile: str, available_stocks: list, portfolio_index: int) -> float:
        """
        STRATEGY 1B ADAPTIVE TARGETING: Generate target based on actual stock returns
        with STRICT NON-OVERLAPPING RANGE ENFORCEMENT
        """
        import random
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not available_stocks or len(available_stocks) < 2:
            logger.warning(f"Adaptive targeting unavailable for {risk_profile} - insufficient stocks")
            return cls.get_return_target(risk_profile, portfolio_index)
        
        try:
            # Get strict non-overlapping range for this risk profile
            strict_min, strict_max = cls.ENHANCED_RETURN_RANGES[risk_profile]
            
            # Get actual returns from available stocks
            actual_returns = []
            for stock in available_stocks:
                return_val = stock.get('return', 0)
                if return_val > 0:
                    actual_returns.append(return_val)
            
            if not actual_returns:
                logger.warning(f"Adaptive targeting unavailable for {risk_profile} - no valid returns")
                return cls.get_return_target(risk_profile, portfolio_index)
            
            min_return = min(actual_returns)
            max_return = max(actual_returns)
            mean_return = sum(actual_returns) / len(actual_returns)
            
            # STRATEGY 1B: Adaptive targeting within strict non-overlapping bounds
            # Calculate adaptive target range but enforce strict profile boundaries
            adaptive_min = max(strict_min, min_return + (max_return - min_return) * 0.6)
            adaptive_max = min(strict_max, min_return + (max_return - min_return) * 0.85)
            
            # Ensure we have a valid range
            if adaptive_min >= adaptive_max:
                # If adaptive range is invalid, use strict range
                adaptive_min = strict_min
                adaptive_max = strict_max
            
            # Use portfolio index as seed for consistency across runs
            random.seed(portfolio_index + hash(risk_profile))
            
            # Generate target within constrained range
            if random.random() < 0.7:  # 70% chance to use mean-biased target
                # Target closer to mean but within strict bounds
                mean_biased_min = max(adaptive_min, min(mean_return * 0.8, strict_max))
                mean_biased_max = min(adaptive_max, max(mean_return * 1.2, strict_min))
                target = random.uniform(mean_biased_min, mean_biased_max)
            else:  # 30% chance to use full constrained range
                target = random.uniform(adaptive_min, adaptive_max)
            
            # Final enforcement: ensure target is within strict bounds
            target = max(strict_min, min(strict_max, target))
            
            logger.debug(f"Strategy 1B adaptive target for {risk_profile}: {target:.2%} (strict: {strict_min:.2%}-{strict_max:.2%}, stock range: {min_return:.2%}-{max_return:.2%})")
            return target
            
        except Exception as e:
            logger.warning(f"Strategy 1B adaptive targeting failed for {risk_profile}: {e}")
            return cls.get_return_target(risk_profile, portfolio_index)
    
    @classmethod
    def get_enhanced_targets(cls, risk_profile: str) -> dict:
        """Get enhanced quality control targets for a risk profile"""
        return cls.ENHANCED_QUALITY_CONTROL.get(risk_profile, cls.ENHANCED_QUALITY_CONTROL['moderate'])
