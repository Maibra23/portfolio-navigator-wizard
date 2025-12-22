#!/usr/bin/env python3
"""
Test Constraint Enforcement in Optimization

Tests enforcing both risk and return constraints in:
1. Weights-optimized portfolios
2. Market-optimized portfolios

Compares Sharpe ratios with and without constraints.
"""

import sys
import os
import json
import logging
from typing import Dict, List, Any, Optional
import numpy as np
from pypfopt import EfficientFrontier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_portfolio_manager import RedisPortfolioManager
from utils.risk_profile_config import get_max_risk_for_profile
from utils.redis_first_data_service import redis_first_data_service
from routers.portfolio import get_mvo_optimizer

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

CONSTRAINTS = {
    'very-conservative': {'max_risk': 0.18, 'return_range': (0.04, 0.14)},
    'conservative': {'max_risk': 0.25, 'return_range': (0.12, 0.22)},
    'moderate': {'max_risk': 0.32, 'return_range': (0.18, 0.28)},
    'aggressive': {'max_risk': 0.42, 'return_range': (0.22, 0.32)},
    'very-aggressive': {'max_risk': 0.55, 'return_range': (0.26, 0.40)}
}

def get_portfolios_from_redis(risk_profile: str, count: int = 3) -> List[Dict]:
    """Get portfolios from Redis."""
    try:
        if not redis_first_data_service.redis_client:
            return []
        redis_manager = RedisPortfolioManager(redis_first_data_service.redis_client)
        return redis_manager.get_portfolio_recommendations(risk_profile, count=count) or []
    except Exception as e:
        return []

def extract_tickers(portfolio: Dict) -> List[str]:
    """Extract tickers."""
    tickers = []
    for alloc in portfolio.get('allocations', []):
        symbol = (alloc.get('symbol') or alloc.get('ticker', '')).upper()
        if symbol:
            tickers.append(symbol)
    return tickers

def optimize_with_constraints(tickers: List[str], risk_profile: str, optimizer, 
                              enforce_risk: bool = True, enforce_return: bool = True) -> Dict:
    """Optimize with constraints."""
    try:
        constraints = CONSTRAINTS[risk_profile]
        max_risk = constraints['max_risk']
        return_range = constraints['return_range']
        
        mu_dict, sigma_df = optimizer.get_ticker_metrics(
            tickers=tickers, annualize=True, min_overlap_months=24, strict_overlap=False
        )
        
        if not mu_dict or sigma_df is None or sigma_df.empty:
            return {'error': 'Could not get metrics'}
        
        tickers_ordered = list(mu_dict.keys())
        mu_array = np.array([mu_dict.get(t, 0.0) for t in tickers_ordered])
        sigma_matrix = sigma_df.loc[tickers_ordered, tickers_ordered].values
        
        result = None
        
        if enforce_risk and enforce_return:
            try:
                target_return = (return_range[0] + return_range[1]) / 2
                ef = EfficientFrontier(mu_array, sigma_matrix)
                weights = ef.efficient_return(target_return)
                weights = ef.clean_weights()
                w_array = np.array([weights[i] for i in range(len(tickers_ordered))])
                portfolio_risk = float(np.sqrt(w_array @ sigma_matrix @ w_array))
                portfolio_return = float(w_array @ mu_array)
                if portfolio_risk <= max_risk * 1.01 and return_range[0] <= portfolio_return <= return_range[1]:
                    result = {'weights': weights, 'return': portfolio_return, 'risk': portfolio_risk, 'method': 'efficient_return'}
            except:
                pass
            
            if not result:
                try:
                    ef = EfficientFrontier(mu_array, sigma_matrix)
                    weights = ef.efficient_risk(max_risk)
                    weights = ef.clean_weights()
                    w_array = np.array([weights[i] for i in range(len(tickers_ordered))])
                    portfolio_risk = float(np.sqrt(w_array @ sigma_matrix @ w_array))
                    portfolio_return = float(w_array @ mu_array)
                    result = {'weights': weights, 'return': portfolio_return, 'risk': portfolio_risk, 'method': 'efficient_risk'}
                except Exception as e:
                    return {'error': str(e)}
        elif enforce_risk:
            try:
                ef = EfficientFrontier(mu_array, sigma_matrix)
                weights = ef.efficient_risk(max_risk)
                weights = ef.clean_weights()
                w_array = np.array([weights[i] for i in range(len(tickers_ordered))])
                portfolio_risk = float(np.sqrt(w_array @ sigma_matrix @ w_array))
                portfolio_return = float(w_array @ mu_array)
                result = {'weights': weights, 'return': portfolio_return, 'risk': portfolio_risk, 'method': 'efficient_risk'}
            except Exception as e:
                return {'error': str(e)}
        else:
            try:
                ef = EfficientFrontier(mu_array, sigma_matrix)
                weights = ef.max_sharpe(risk_free_rate=optimizer.risk_free_rate)
                weights = ef.clean_weights()
                w_array = np.array([weights[i] for i in range(len(tickers_ordered))])
                portfolio_risk = float(np.sqrt(w_array @ sigma_matrix @ w_array))
                portfolio_return = float(w_array @ mu_array)
                result = {'weights': weights, 'return': portfolio_return, 'risk': portfolio_risk, 'method': 'max_sharpe'}
            except Exception as e:
                return {'error': str(e)}
        
        if result:
            sharpe = (result['return'] - optimizer.risk_free_rate) / result['risk'] if result['risk'] > 0 else 0.0
            result['sharpe'] = sharpe
        
        return result if result else {'error': 'Optimization failed'}
        
    except Exception as e:
        return {'error': str(e)}

def main():
    """Run tests."""
    risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
    optimizer = get_mvo_optimizer()
    
    print("="*80)
    print("CONSTRAINT ENFORCEMENT TEST")
    print("="*80)
    print()
    
    all_results = {}
    
    for risk_profile in risk_profiles:
        print("="*80)
        print(f"RISK PROFILE: {risk_profile.upper()}")
        print("="*80)
        constraints = CONSTRAINTS[risk_profile]
        print(f"Constraints: Risk ≤ {constraints['max_risk']*100:.1f}%, "
              f"Return: {constraints['return_range'][0]*100:.1f}% - {constraints['return_range'][1]*100:.1f}%")
        print()
        
        portfolios = get_portfolios_from_redis(risk_profile, count=3)
        if not portfolios:
            print(f"  ❌ No portfolios found\n")
            continue
        
        profile_results = []
        
        for i, portfolio in enumerate(portfolios, 1):
            print(f"  Portfolio {i}/3:")
            tickers = extract_tickers(portfolio)
            print(f"    Tickers: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''} ({len(tickers)} total)")
            
            # Test 1: No constraints
            nc = optimize_with_constraints(tickers, risk_profile, optimizer, False, False)
            if 'error' in nc:
                print(f"    ❌ Error: {nc['error']}\n")
                continue
            
            # Test 2: Risk only
            ro = optimize_with_constraints(tickers, risk_profile, optimizer, True, False)
            
            # Test 3: Both
            bc = optimize_with_constraints(tickers, risk_profile, optimizer, True, True)
            
            # Display
            print(f"    No Constraints:")
            print(f"      Return: {nc['return']*100:6.2f}% | Risk: {nc['risk']*100:5.2f}% | Sharpe: {nc['sharpe']:5.2f}")
            nc_risk_ok = nc['risk'] <= constraints['max_risk'] * 1.01
            nc_return_ok = constraints['return_range'][0] <= nc['return'] <= constraints['return_range'][1]
            print(f"      Compliance: Risk {'✅' if nc_risk_ok else '❌'} | Return {'✅' if nc_return_ok else '❌'}")
            
            if 'error' not in ro:
                print(f"    Risk Constraint Only:")
                print(f"      Return: {ro['return']*100:6.2f}% | Risk: {ro['risk']*100:5.2f}% | Sharpe: {ro['sharpe']:5.2f}")
                ro_risk_ok = ro['risk'] <= constraints['max_risk'] * 1.01
                ro_return_ok = constraints['return_range'][0] <= ro['return'] <= constraints['return_range'][1]
                print(f"      Compliance: Risk {'✅' if ro_risk_ok else '❌'} | Return {'✅' if ro_return_ok else '❌'}")
                print(f"      Sharpe vs No Constraints: {ro['sharpe'] - nc['sharpe']:+.3f}")
            else:
                print(f"    Risk Constraint Only: ❌ {ro.get('error', 'Failed')}")
            
            if 'error' not in bc:
                print(f"    Both Constraints:")
                print(f"      Return: {bc['return']*100:6.2f}% | Risk: {bc['risk']*100:5.2f}% | Sharpe: {bc['sharpe']:5.2f}")
                bc_risk_ok = bc['risk'] <= constraints['max_risk'] * 1.01
                bc_return_ok = constraints['return_range'][0] <= bc['return'] <= constraints['return_range'][1]
                print(f"      Compliance: Risk {'✅' if bc_risk_ok else '❌'} | Return {'✅' if bc_return_ok else '❌'}")
                print(f"      Sharpe vs No Constraints: {bc['sharpe'] - nc['sharpe']:+.3f}")
            else:
                print(f"    Both Constraints: ❌ {bc.get('error', 'Failed')}")
            
            print()
            profile_results.append({
                'portfolio': i,
                'tickers': tickers,
                'no_constraints': nc,
                'risk_only': ro,
                'both_constraints': bc
            })
        
        all_results[risk_profile] = profile_results
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"{'Profile':<20} {'Tested':<10} {'Risk-Only OK':<15} {'Both OK':<12} {'Avg Sharpe Impact'}")
    print("-"*80)
    
    for profile in risk_profiles:
        results = all_results.get(profile, [])
        if not results:
            continue
        
        risk_only_ok = sum(1 for r in results if 'error' not in r.get('risk_only', {}) and r['risk_only']['risk'] <= CONSTRAINTS[profile]['max_risk'] * 1.01)
        both_ok = sum(1 for r in results if 'error' not in r.get('both_constraints', {}) and 
                     r['both_constraints']['risk'] <= CONSTRAINTS[profile]['max_risk'] * 1.01 and
                     CONSTRAINTS[profile]['return_range'][0] <= r['both_constraints']['return'] <= CONSTRAINTS[profile]['return_range'][1])
        
        sharpe_impacts = []
        for r in results:
            if 'error' not in r.get('no_constraints', {}) and 'error' not in r.get('both_constraints', {}):
                sharpe_impacts.append(r['both_constraints']['sharpe'] - r['no_constraints']['sharpe'])
        
        avg_impact = sum(sharpe_impacts) / len(sharpe_impacts) if sharpe_impacts else 0
        
        print(f"{profile:<20} {len(results):<10} {risk_only_ok}/{len(results):<15} {both_ok}/{len(results):<12} {avg_impact:+.3f}")
    
    with open('constraint_enforcement_test_results.json', 'w') as f:
        json.dump({'constraints': CONSTRAINTS, 'results': all_results}, f, indent=2, default=str)
    
    print(f"\nResults saved to: constraint_enforcement_test_results.json")

if __name__ == "__main__":
    main()
