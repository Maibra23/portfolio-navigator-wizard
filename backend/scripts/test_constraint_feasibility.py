#!/usr/bin/env python3
"""
Test script to verify if risk and return constraints can be respected during optimization.

This script:
1. Retrieves portfolios from Redis for each risk profile
2. Attempts to optimize with constraints enforced
3. Tests both risk-only constraints and combined risk+return constraints
4. Reports feasibility and success rates
"""

import sys
import os
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from pypfopt import EfficientFrontier

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.risk_profile_config import RISK_PROFILE_MAX_RISK, get_max_risk_for_profile
from utils.portfolio_mvo_optimizer import PortfolioMVOptimizer
from utils.redis_first_data_service import redis_first_data_service
from utils.port_analytics import PortfolioAnalytics
from routers.portfolio import get_mvo_optimizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_portfolios_from_redis(risk_profile: str, count: int = 5) -> List[Dict[str, Any]]:
    """Get portfolios from Redis for a risk profile."""
    try:
        if not redis_first_data_service.redis_client:
            logger.error("Redis client not available")
            return []
        redis_manager = RedisPortfolioManager(redis_first_data_service.redis_client)
        portfolios = redis_manager.get_portfolio_recommendations(risk_profile, count=count)
        return portfolios if portfolios else []
    except Exception as e:
        logger.error(f"Error getting portfolios for {risk_profile}: {e}")
        return []

def extract_tickers_from_portfolio(portfolio: Dict[str, Any]) -> List[str]:
    """Extract ticker symbols from portfolio."""
    tickers = []
    allocations = portfolio.get('allocations', [])
    for alloc in allocations:
        symbol = alloc.get('symbol') or alloc.get('ticker')
        if symbol:
            tickers.append(symbol.upper())
    return tickers

def test_risk_constraint_feasibility(tickers: List[str], risk_profile: str, 
                                     optimizer: PortfolioMVOptimizer) -> Dict[str, Any]:
    """
    Test if we can optimize a portfolio while respecting risk constraints.
    
    Returns:
        Dict with success status, optimized metrics, and constraint compliance
    """
    try:
        max_risk = get_max_risk_for_profile(risk_profile)
        
        # Get ticker metrics
        mu_dict, sigma_df = optimizer.get_ticker_metrics(
            tickers=tickers,
            annualize=True,
            min_overlap_months=24,
            strict_overlap=False
        )
        
        if not mu_dict or sigma_df is None or sigma_df.empty:
            return {
                "success": False,
                "error": "Could not get ticker metrics",
                "feasible": False
            }
        
        # Convert to arrays
        tickers_ordered = list(mu_dict.keys())
        mu_array = np.array([mu_dict.get(t, 0.0) for t in tickers_ordered])
        sigma_matrix = sigma_df.loc[tickers_ordered, tickers_ordered].values
        
        # Test 1: Try to optimize with risk constraint using efficient_risk
        try:
            ef_risk = EfficientFrontier(mu_array, sigma_matrix)
            weights_risk = ef_risk.efficient_risk(target_risk=max_risk)
            weights_risk = ef_risk.clean_weights()
            
            # Calculate metrics
            w_array = np.array([weights_risk[i] for i in range(len(tickers_ordered))])
            portfolio_return_risk = float(w_array @ mu_array)
            portfolio_variance_risk = float(w_array @ sigma_matrix @ w_array)
            portfolio_risk_risk = float(np.sqrt(max(portfolio_variance_risk, 0.0)))
            sharpe_risk = (portfolio_return_risk - optimizer.risk_free_rate) / portfolio_risk_risk if portfolio_risk_risk > 0 else 0.0
            
            risk_constraint_met = portfolio_risk_risk <= max_risk * 1.01  # Allow 1% tolerance for numerical precision
            risk_test_success = True
        except Exception as e:
            logger.warning(f"Risk constraint optimization failed: {e}")
            risk_test_success = False
            portfolio_risk_risk = None
            portfolio_return_risk = None
            sharpe_risk = None
            risk_constraint_met = False
        
        # Test 2: Try max Sharpe and check if it respects constraint
        try:
            ef_sharpe = EfficientFrontier(mu_array, sigma_matrix)
            weights_sharpe = ef_sharpe.max_sharpe(risk_free_rate=optimizer.risk_free_rate)
            weights_sharpe = ef_sharpe.clean_weights()
            
            # Calculate metrics
            w_array_sharpe = np.array([weights_sharpe[i] for i in range(len(tickers_ordered))])
            portfolio_return_sharpe = float(w_array_sharpe @ mu_array)
            portfolio_variance_sharpe = float(w_array_sharpe @ sigma_matrix @ w_array_sharpe)
            portfolio_risk_sharpe = float(np.sqrt(max(portfolio_variance_sharpe, 0.0)))
            sharpe_sharpe = (portfolio_return_sharpe - optimizer.risk_free_rate) / portfolio_risk_sharpe if portfolio_risk_sharpe > 0 else 0.0
            
            sharpe_constraint_met = portfolio_risk_sharpe <= max_risk * 1.01
            sharpe_test_success = True
        except Exception as e:
            logger.warning(f"Max Sharpe optimization failed: {e}")
            sharpe_test_success = False
            portfolio_risk_sharpe = None
            portfolio_return_sharpe = None
            sharpe_sharpe = None
            sharpe_constraint_met = False
        
        # Test 3: Try min variance (should always respect constraint if feasible)
        try:
            ef_minvar = EfficientFrontier(mu_array, sigma_matrix)
            weights_minvar = ef_minvar.min_volatility()
            weights_minvar = ef_minvar.clean_weights()
            
            # Calculate metrics
            w_array_minvar = np.array([weights_minvar[i] for i in range(len(tickers_ordered))])
            portfolio_return_minvar = float(w_array_minvar @ mu_array)
            portfolio_variance_minvar = float(w_array_minvar @ sigma_matrix @ w_array_minvar)
            portfolio_risk_minvar = float(np.sqrt(max(portfolio_variance_minvar, 0.0)))
            sharpe_minvar = (portfolio_return_minvar - optimizer.risk_free_rate) / portfolio_risk_minvar if portfolio_risk_minvar > 0 else 0.0
            
            minvar_constraint_met = portfolio_risk_minvar <= max_risk * 1.01
            minvar_test_success = True
        except Exception as e:
            logger.warning(f"Min variance optimization failed: {e}")
            minvar_test_success = False
            portfolio_risk_minvar = None
            portfolio_return_minvar = None
            sharpe_minvar = None
            minvar_constraint_met = False
        
        # Determine overall feasibility
        feasible = risk_test_success and risk_constraint_met
        
        return {
            "success": True,
            "feasible": feasible,
            "max_risk_constraint": max_risk,
            "risk_constrained_optimization": {
                "success": risk_test_success,
                "risk": portfolio_risk_risk,
                "return": portfolio_return_risk,
                "sharpe": sharpe_risk,
                "constraint_met": risk_constraint_met
            },
            "max_sharpe_optimization": {
                "success": sharpe_test_success,
                "risk": portfolio_risk_sharpe,
                "return": portfolio_return_sharpe,
                "sharpe": sharpe_sharpe,
                "constraint_met": sharpe_constraint_met
            },
            "min_variance_optimization": {
                "success": minvar_test_success,
                "risk": portfolio_risk_minvar,
                "return": portfolio_return_minvar,
                "sharpe": sharpe_minvar,
                "constraint_met": minvar_constraint_met
            }
        }
        
    except Exception as e:
        logger.error(f"Error in constraint feasibility test: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "feasible": False
        }

def test_portfolio_constraint_feasibility(risk_profile: str, num_portfolios: int = 5) -> Dict[str, Any]:
    """Test constraint feasibility for a risk profile."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing Constraint Feasibility: {risk_profile.upper()}")
    logger.info(f"{'='*80}")
    
    max_risk_constraint = get_max_risk_for_profile(risk_profile)
    logger.info(f"Max Risk Constraint: {max_risk_constraint:.2%} ({max_risk_constraint*100:.1f}%)")
    
    # Get portfolios from Redis
    portfolios = get_portfolios_from_redis(risk_profile, count=num_portfolios)
    if not portfolios:
        logger.warning(f"No portfolios found for {risk_profile}")
        return {
            "risk_profile": risk_profile,
            "max_risk_constraint": max_risk_constraint,
            "portfolios_tested": 0,
            "feasible_count": 0,
            "results": []
        }
    
    logger.info(f"Found {len(portfolios)} portfolios to test")
    
    # Initialize optimizer using the standard method
    optimizer = get_mvo_optimizer()
    
    results = []
    feasible_count = 0
    
    for i, portfolio in enumerate(portfolios, 1):
        logger.info(f"\n--- Portfolio {i}/{len(portfolios)} ---")
        
        # Extract tickers
        tickers = extract_tickers_from_portfolio(portfolio)
        if len(tickers) < 2:
            logger.warning(f"Portfolio {i} has insufficient tickers: {len(tickers)}")
            continue
        
        logger.info(f"Tickers: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''} ({len(tickers)} total)")
        
        # Test constraint feasibility
        result = test_risk_constraint_feasibility(tickers, risk_profile, optimizer)
        results.append({
            "portfolio_index": i,
            "tickers": tickers,
            "ticker_count": len(tickers),
            **result
        })
        
        if result.get("feasible", False):
            feasible_count += 1
            logger.info(f"✅ FEASIBLE: Constraints can be respected")
            
            risk_opt = result.get("risk_constrained_optimization", {})
            if risk_opt.get("success"):
                logger.info(f"   Risk-Constrained: {risk_opt.get('risk', 0):.2%} risk, "
                          f"{risk_opt.get('return', 0):.2%} return, "
                          f"Sharpe: {risk_opt.get('sharpe', 0):.2f}")
        else:
            logger.warning(f"❌ NOT FEASIBLE: Constraints cannot be respected")
            if "error" in result:
                logger.warning(f"   Error: {result['error']}")
            
            # Check individual optimization results
            risk_opt = result.get("risk_constrained_optimization", {})
            sharpe_opt = result.get("max_sharpe_optimization", {})
            
            if risk_opt.get("success"):
                logger.warning(f"   Risk-Constrained: Risk {risk_opt.get('risk', 0):.2%} "
                             f"{'✅' if risk_opt.get('constraint_met') else '❌'} constraint")
            if sharpe_opt.get("success"):
                logger.warning(f"   Max Sharpe: Risk {sharpe_opt.get('risk', 0):.2%} "
                             f"{'✅' if sharpe_opt.get('constraint_met') else '❌'} constraint")
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"SUMMARY for {risk_profile.upper()}")
    logger.info(f"{'='*80}")
    logger.info(f"Portfolios Tested: {len(results)}")
    logger.info(f"Feasible (Constraints Can Be Respected): {feasible_count}/{len(results)}")
    logger.info(f"Feasibility Rate: {feasible_count/len(results)*100:.1f}%" if results else "N/A")
    
    return {
        "risk_profile": risk_profile,
        "max_risk_constraint": max_risk_constraint,
        "portfolios_tested": len(results),
        "feasible_count": feasible_count,
        "feasibility_rate": feasible_count/len(results) if results else 0.0,
        "results": results
    }

def main():
    """Run feasibility tests for all risk profiles."""
    risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
    
    all_results = {}
    total_tested = 0
    total_feasible = 0
    
    for risk_profile in risk_profiles:
        try:
            result = test_portfolio_constraint_feasibility(risk_profile, num_portfolios=5)
            all_results[risk_profile] = result
            total_tested += result.get("portfolios_tested", 0)
            total_feasible += result.get("feasible_count", 0)
        except Exception as e:
            logger.error(f"Error testing {risk_profile}: {e}")
            import traceback
            traceback.print_exc()
    
    # Final Summary
    logger.info(f"\n{'='*80}")
    logger.info("FINAL FEASIBILITY SUMMARY - ALL RISK PROFILES")
    logger.info(f"{'='*80}")
    
    for risk_profile in risk_profiles:
        result = all_results.get(risk_profile, {})
        max_risk = result.get("max_risk_constraint", 0.0)
        tested = result.get("portfolios_tested", 0)
        feasible = result.get("feasible_count", 0)
        rate = result.get("feasibility_rate", 0.0)
        
        logger.info(f"\n{risk_profile.upper()}:")
        logger.info(f"  Max Risk Constraint: {max_risk:.2%}")
        logger.info(f"  Portfolios Tested: {tested}")
        logger.info(f"  Feasible: {feasible}/{tested}")
        logger.info(f"  Feasibility Rate: {rate*100:.1f}%")
    
    overall_rate = total_feasible / total_tested if total_tested > 0 else 0.0
    
    logger.info(f"\n{'='*80}")
    logger.info(f"OVERALL FEASIBILITY")
    logger.info(f"{'='*80}")
    logger.info(f"Total Portfolios Tested: {total_tested}")
    logger.info(f"Total Feasible: {total_feasible}")
    logger.info(f"Overall Feasibility Rate: {overall_rate*100:.1f}%")
    
    if overall_rate >= 0.8:
        logger.info(f"\n✅ FEASIBILITY CONFIRMED: {overall_rate*100:.1f}% of portfolios can respect constraints")
        logger.info("   Recommendation: Implement constraint enforcement in optimization")
    elif overall_rate >= 0.5:
        logger.warning(f"\n⚠️  PARTIAL FEASIBILITY: {overall_rate*100:.1f}% of portfolios can respect constraints")
        logger.warning("   Recommendation: Implement constraint enforcement with fallback handling")
    else:
        logger.error(f"\n❌ LOW FEASIBILITY: Only {overall_rate*100:.1f}% of portfolios can respect constraints")
        logger.error("   Recommendation: Review constraint values or optimization approach")
    
    # Save detailed results
    output_file = "constraint_feasibility_test_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "summary": {
                "total_tested": total_tested,
                "total_feasible": total_feasible,
                "overall_feasibility_rate": overall_rate,
                "feasible": overall_rate >= 0.8
            },
            "results_by_profile": all_results
        }, f, indent=2, default=str)
    
    logger.info(f"\nDetailed results saved to: {output_file}")
    
    return overall_rate >= 0.8

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
