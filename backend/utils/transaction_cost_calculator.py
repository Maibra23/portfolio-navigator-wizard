#!/usr/bin/env python3
"""
Transaction Cost Calculator
Implements Avanza courtage calculation logic for different courtage classes.

Source-of-truth: Avanza courtage tiers and thresholds (check avanza.se for current rates).
PARAMETERS_AS_OF: 2025-01 (update when Avanza changes courtage; run tests to flag outdated params).
"""

import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

# Single source-of-truth date for parameter validity
PARAMETERS_AS_OF = "2025-01"


class CourtageClass(str, Enum):
    """Avanza courtage classes"""
    START = "start"
    MINI = "mini"
    SMALL = "small"
    MEDIUM = "medium"
    FAST_PRIS = "fastPris"


class AvanzaCourtageCalculator:
    """
    Calculates Avanza courtage (transaction costs) for different courtage classes.
    Based on Avanza's courtage rules (avanza.se).
    """
    
    # Courtage rules by class
    COURTAGE_RULES = {
        'start': {
            'description': 'Start - Up to 50,000 SEK or 500 free trades',
            'free_trades': 500,
            'free_amount': 50000.0,
            'after_free': lambda val: 0  # Free after threshold
        },
        'mini': {
            'description': 'Mini - 1 SEK or 0.25%',
            'function': lambda val: 1 if val <= 400 else val * 0.0025
        },
        'small': {
            'description': 'Small - 39 SEK or 0.15%',
            'function': lambda val: 39 if val <= 26000 else val * 0.0015
        },
        'medium': {
            'description': 'Medium - 69 SEK or 0.069%',
            'function': lambda val: 69 if val <= 100000 else val * 0.00069
        },
        'fastPris': {
            'description': 'Fast Pris - Fixed 99 SEK',
            'function': lambda val: 99
        }
    }
    
    # Rebalancing frequency multipliers (transactions per year)
    REBALANCING_FREQUENCY = {
        'monthly': 12,
        'quarterly': 4,
        'semi-annual': 2,
        'annual': 1
    }
    
    def __init__(self):
        """Initialize the calculator"""
        pass
    
    def _validate_input(self, value: float, field_name: str) -> None:
        """Validate input values"""
        if value is None:
            raise ValueError(f"{field_name} cannot be None")
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative")
        if not isinstance(value, (int, float)):
            raise ValueError(f"{field_name} must be a number")
    
    def calculate_courtage(self, order_value: float, courtage_class: str) -> float:
        """
        Calculate courtage for a single order
        
        Args:
            order_value: Value of the order in SEK
            courtage_class: Courtage class ("start", "mini", "small", "medium", "fastPris")
            
        Returns:
            Courtage amount in SEK
        """
        self._validate_input(order_value, "order_value")
        
        # Normalize courtage class (case-insensitive, handle fastPris/fastpris)
        courtage_class_lower = courtage_class.lower()
        if courtage_class_lower == "fastpris":
            courtage_class_normalized = "fastPris"
        else:
            courtage_class_normalized = courtage_class_lower
        
        if courtage_class_normalized not in self.COURTAGE_RULES:
            raise ValueError(f"Invalid courtage class: {courtage_class}. "
                           f"Valid classes: {list(self.COURTAGE_RULES.keys())}")
        
        rule = self.COURTAGE_RULES[courtage_class_normalized]
        
        # Handle start class with free trades
        if courtage_class_normalized == 'start':
            # For start class, first 500 trades or 50,000 SEK are free
            # After that, it's free (0 SEK)
            return 0.0
        
        # For other classes, use the function
        if 'function' in rule:
            courtage = rule['function'](order_value)
            return round(courtage, 2)
        
        return 0.0
    
    def estimate_setup_cost(self, portfolio: List[Dict], 
                           courtage_class: str) -> Dict[str, any]:
        """
        Calculate total setup cost for a portfolio
        
        Args:
            portfolio: List of portfolio positions with 'ticker', 'shares', 'value' keys
            courtage_class: Courtage class to use
            
        Returns:
            Dictionary with setup cost breakdown
        """
        if not portfolio:
            return {
                "total_setup_cost": 0.0,
                "transaction_count": 0,
                "breakdown": []
            }
        
        total_cost = 0.0
        breakdown = []
        
        for position in portfolio:
            ticker = position.get('ticker', position.get('symbol', 'UNKNOWN'))
            value = position.get('value', 0.0)
            shares = position.get('shares', 0)
            
            if value <= 0:
                continue
            
            courtage = self.calculate_courtage(value, courtage_class)
            total_cost += courtage
            
            breakdown.append({
                "ticker": ticker,
                "shares": shares,
                "value": round(value, 2),
                "courtage": round(courtage, 2)
            })
        
        return {
            "total_setup_cost": round(total_cost, 2),
            "transaction_count": len(breakdown),
            "breakdown": breakdown
        }
    
    def estimate_rebalancing_cost(self, transactions: List[Dict], 
                                  courtage_class: str, 
                                  frequency: str = 'quarterly') -> Dict[str, any]:
        """
        Estimate annual rebalancing costs
        
        Args:
            transactions: List of transactions with 'value' key
            courtage_class: Courtage class to use
            frequency: Rebalancing frequency ("monthly", "quarterly", "semi-annual", "annual")
            
        Returns:
            Dictionary with rebalancing cost estimates
        """
        if frequency not in self.REBALANCING_FREQUENCY:
            raise ValueError(f"Invalid frequency: {frequency}. "
                           f"Valid frequencies: {list(self.REBALANCING_FREQUENCY.keys())}")
        
        if not transactions:
            return {
                "per_rebalance_cost": 0.0,
                "rebalances_per_year": self.REBALANCING_FREQUENCY[frequency],
                "annual_cost": 0.0,
                "transaction_count": 0
            }
        
        # Calculate cost per rebalancing
        per_rebalance_cost = 0.0
        for transaction in transactions:
            value = transaction.get('value', 0.0)
            if value > 0:
                per_rebalance_cost += self.calculate_courtage(value, courtage_class)
        
        # Calculate annual cost
        rebalances_per_year = self.REBALANCING_FREQUENCY[frequency]
        annual_cost = per_rebalance_cost * rebalances_per_year
        
        return {
            "per_rebalance_cost": round(per_rebalance_cost, 2),
            "rebalances_per_year": rebalances_per_year,
            "annual_cost": round(annual_cost, 2),
            "transaction_count": len(transactions)
        }
    
    def estimate_total_costs(self, portfolio: List[Dict], 
                            courtage_class: str,
                            rebalancing_frequency: str = 'quarterly',
                            rebalancing_transactions: Optional[List[Dict]] = None) -> Dict[str, any]:
        """
        Estimate total costs (setup + rebalancing)
        
        Args:
            portfolio: Initial portfolio positions
            courtage_class: Courtage class to use
            rebalancing_frequency: How often to rebalance
            rebalancing_transactions: Estimated transactions per rebalance (if None, uses portfolio)
            
        Returns:
            Dictionary with total cost breakdown
        """
        setup_cost_data = self.estimate_setup_cost(portfolio, courtage_class)
        
        # Use portfolio as default for rebalancing if not specified
        if rebalancing_transactions is None:
            rebalancing_transactions = portfolio
        
        rebalancing_cost_data = self.estimate_rebalancing_cost(
            rebalancing_transactions, 
            courtage_class, 
            rebalancing_frequency
        )
        
        total_first_year_cost = setup_cost_data["total_setup_cost"] + rebalancing_cost_data["annual_cost"]
        
        return {
            "courtage_class": courtage_class,
            "setup_cost": setup_cost_data["total_setup_cost"],
            "setup_breakdown": setup_cost_data["breakdown"],
            "annual_rebalancing_cost": rebalancing_cost_data["annual_cost"],
            "per_rebalance_cost": rebalancing_cost_data["per_rebalance_cost"],
            "rebalancing_frequency": rebalancing_frequency,
            "total_first_year_cost": round(total_first_year_cost, 2)
        }
    
    def find_optimal_courtage_class(self, portfolio: List[Dict],
                                   rebalancing_frequency: str = 'quarterly') -> Dict[str, any]:
        """
        Find the optimal courtage class for a given portfolio
        
        Args:
            portfolio: Portfolio positions
            rebalancing_frequency: Rebalancing frequency
            
        Returns:
            Dictionary with recommended class and potential savings
        """
        costs_by_class = {}
        
        for courtage_class in self.COURTAGE_RULES.keys():
            if courtage_class == 'start':
                # Skip start class for optimization (it's free but limited)
                continue
            
            total_costs = self.estimate_total_costs(
                portfolio, 
                courtage_class, 
                rebalancing_frequency
            )
            costs_by_class[courtage_class] = total_costs["total_first_year_cost"]
        
        if not costs_by_class:
            return {
                "recommended_class": "medium",
                "potential_savings": 0.0,
                "all_costs": {}
            }
        
        # Find minimum cost
        recommended_class = min(costs_by_class, key=costs_by_class.get)
        min_cost = costs_by_class[recommended_class]
        
        # Compare with medium (most common)
        medium_cost = costs_by_class.get('medium', min_cost)
        potential_savings = max(0.0, medium_cost - min_cost)
        
        return {
            "recommended_class": recommended_class,
            "potential_savings": round(potential_savings, 2),
            "all_costs": {k: round(v, 2) for k, v in costs_by_class.items()}
        }
