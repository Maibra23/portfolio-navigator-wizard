#!/usr/bin/env python3
"""
Test the optimization endpoint with a random portfolio from aggressive risk profile
"""

import sys
import os
import json
import random

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_first_data_service import redis_first_data_service as _rds

def get_random_portfolio_from_redis(risk_profile: str):
    """Get a random portfolio from Redis for a risk profile"""
    if not _rds.redis_client:
        print("❌ Redis client not available")
        return None
    
    bucket_key = f"portfolio_bucket:{risk_profile}"
    available_portfolios = []
    
    # Load all portfolios from Redis
    for i in range(12):  # PORTFOLIOS_PER_PROFILE = 12
        portfolio_key = f"{bucket_key}:{i}"
        portfolio_data = _rds.redis_client.get(portfolio_key)
        
        if portfolio_data:
            try:
                portfolio = json.loads(portfolio_data)
                allocations = portfolio.get('allocations', [])
                # Extract tickers and weights
                tickers = [a.get('symbol', '').upper() for a in allocations if a.get('symbol')]
                weights = {a.get('symbol', '').upper(): a.get('allocation', 0) / 100.0 
                          for a in allocations if a.get('symbol')}
                
                if tickers:
                    portfolio['user_tickers'] = tickers
                    portfolio['user_weights'] = weights
                    available_portfolios.append(portfolio)
            except Exception as e:
                print(f"⚠️ Error parsing portfolio {i} for {risk_profile}: {e}")
    
    if available_portfolios:
        selected = random.choice(available_portfolios)
        return selected
    return None

def test_optimization_endpoint():
    """Test the optimization endpoint"""
    import requests
    import time
    
    # Get random portfolio
    print("📥 Fetching random portfolio from Redis (aggressive profile)...")
    portfolio = get_random_portfolio_from_redis('aggressive')
    
    if not portfolio:
        print("❌ No portfolio found")
        return
    
    user_tickers = portfolio.get('user_tickers', [])
    user_weights = portfolio.get('user_weights', {})
    risk_profile = portfolio.get('riskProfile', 'aggressive')
    
    print(f"\n✅ Selected portfolio:")
    print(f"   Risk Profile: {risk_profile}")
    print(f"   Tickers ({len(user_tickers)}): {user_tickers}")
    print(f"   Weights: {user_weights}")
    
    # Prepare request
    request_data = {
        "user_tickers": user_tickers,
        "user_weights": user_weights,
        "risk_profile": risk_profile,
        "optimization_type": "max_sharpe",
        "max_eligible_tickers": 20,
        "include_efficient_frontier": True,
        "include_random_portfolios": True,
        "num_frontier_points": 20,
        "num_random_portfolios": 200,
        "use_combined_strategy": True,
        "attempt_market_exploration": True
    }
    
    # Call endpoint
    print(f"\n🚀 Calling optimization endpoint...")
    print(f"   Endpoint: http://localhost:8000/api/v1/portfolio/optimization/triple")
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/portfolio/optimization/triple",
            json=request_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n" + "=" * 80)
            print("OPTIMIZATION RESULTS")
            print("=" * 80)
            
            # Current Portfolio
            current = result.get('current_portfolio', {})
            current_metrics = current.get('metrics', {})
            print(f"\n📊 CURRENT PORTFOLIO:")
            print(f"   Tickers: {current.get('tickers', [])}")
            print(f"   Expected Return: {current_metrics.get('expected_return', 0):.2%}")
            print(f"   Risk: {current_metrics.get('risk', 0):.2%}")
            print(f"   Sharpe Ratio: {current_metrics.get('sharpe_ratio', 0):.2f}")
            
            # Weights-Optimized Portfolio
            weights_opt = result.get('weights_optimized_portfolio', {})
            if weights_opt:
                weights_portfolio = weights_opt.get('optimized_portfolio', {})
                weights_metrics = weights_portfolio.get('metrics', {})
                print(f"\n📊 WEIGHTS-OPTIMIZED PORTFOLIO:")
                print(f"   Tickers: {weights_portfolio.get('tickers', [])}")
                print(f"   Expected Return: {weights_metrics.get('expected_return', 0):.2%}")
                print(f"   Risk: {weights_metrics.get('risk', 0):.2%}")
                print(f"   Sharpe Ratio: {weights_metrics.get('sharpe_ratio', 0):.2f}")
            
            # Market-Optimized Portfolio
            market_opt = result.get('market_optimized_portfolio')
            if market_opt:
                market_portfolio = market_opt.get('optimized_portfolio', {})
                market_metrics = market_portfolio.get('metrics', {})
                print(f"\n📊 MARKET-OPTIMIZED PORTFOLIO:")
                print(f"   Tickers: {market_portfolio.get('tickers', [])}")
                print(f"   Basket Size: {len(market_portfolio.get('tickers', []))} tickers")
                print(f"   Expected Return: {market_metrics.get('expected_return', 0):.2%}")
                print(f"   Risk: {market_metrics.get('risk', 0):.2%}")
                print(f"   Sharpe Ratio: {market_metrics.get('sharpe_ratio', 0):.2f}")
            else:
                print(f"\n⚠️ MARKET-OPTIMIZED PORTFOLIO: Not available (market exploration failed)")
            
            # Comparison
            comparison = result.get('comparison', {})
            print(f"\n📊 COMPARISON:")
            print(f"   Recommendation: {result.get('optimization_metadata', {}).get('recommendation', 'N/A')}")
            print(f"   Processing Time: {result.get('optimization_metadata', {}).get('processing_time_seconds', 0):.2f}s")
            print(f"   Market Exploration: {'✅ Success' if result.get('optimization_metadata', {}).get('market_exploration_successful') else '❌ Failed'}")
            
            if comparison:
                print(f"\n   Metrics Comparison:")
                for key, value in comparison.items():
                    if isinstance(value, dict):
                        print(f"   {key}:")
                        for k, v in value.items():
                            if isinstance(v, (int, float)):
                                if 'return' in k.lower() or 'risk' in k.lower():
                                    print(f"      {k}: {v:.2%}")
                                else:
                                    print(f"      {k}: {v:.2f}")
                            else:
                                print(f"      {k}: {v}")
                    else:
                        print(f"   {key}: {value}")
            
            return result
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend. Is the server running on http://localhost:8000?")
        print("   Please start the backend server first.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_optimization_endpoint()

