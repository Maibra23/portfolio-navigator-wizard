#!/usr/bin/env python3
"""
Test optimization endpoint across all risk profiles, 3 times each
Observe Sharpe ratio variation and basket composition differences
"""

import sys
import os
import json
import random
import time
from collections import defaultdict

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_first_data_service import redis_first_data_service as _rds

RISK_PROFILES = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']

def get_random_portfolio_from_redis(risk_profile: str):
    """Get a random portfolio from Redis for a risk profile"""
    if not _rds.redis_client:
        return None
    
    bucket_key = f"portfolio_bucket:{risk_profile}"
    available_portfolios = []
    
    for i in range(12):
        portfolio_key = f"{bucket_key}:{i}"
        portfolio_data = _rds.redis_client.get(portfolio_key)
        
        if portfolio_data:
            try:
                portfolio = json.loads(portfolio_data)
                allocations = portfolio.get('allocations', [])
                tickers = [a.get('symbol', '').upper() for a in allocations if a.get('symbol')]
                weights = {a.get('symbol', '').upper(): a.get('allocation', 0) / 100.0 
                          for a in allocations if a.get('symbol')}
                
                if tickers:
                    portfolio['user_tickers'] = tickers
                    portfolio['user_weights'] = weights
                    available_portfolios.append(portfolio)
            except Exception as e:
                pass
    
    if available_portfolios:
        return random.choice(available_portfolios)
    return None

def test_optimization(risk_profile: str, iteration: int):
    """Test optimization for a risk profile"""
    import requests
    
    # Get random portfolio
    portfolio = get_random_portfolio_from_redis(risk_profile)
    
    if not portfolio:
        return None
    
    user_tickers = portfolio.get('user_tickers', [])
    user_weights = portfolio.get('user_weights', {})
    
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
    
    try:
        response = requests.post(
            "http://localhost:8000/api/portfolio/optimization/triple",
            json=request_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract key metrics
            current = result.get('current_portfolio', {})
            current_metrics = current.get('metrics', {})
            
            weights_opt = result.get('weights_optimized_portfolio', {})
            weights_metrics = {}
            if weights_opt:
                weights_portfolio = weights_opt.get('optimized_portfolio', {})
                weights_metrics = weights_portfolio.get('metrics', {})
            
            market_opt = result.get('market_optimized_portfolio')
            market_metrics = {}
            market_tickers = []
            basket_size = 0
            if market_opt:
                market_portfolio = market_opt.get('optimized_portfolio', {})
                market_metrics = market_portfolio.get('metrics', {})
                market_tickers = market_portfolio.get('tickers', [])
                basket_size = len(market_tickers)
            
            return {
                'risk_profile': risk_profile,
                'iteration': iteration,
                'user_tickers': user_tickers,
                'current': {
                    'return': current_metrics.get('expected_return', 0),
                    'risk': current_metrics.get('risk', 0),
                    'sharpe': current_metrics.get('sharpe_ratio', 0)
                },
                'weights_opt': {
                    'return': weights_metrics.get('expected_return', 0),
                    'risk': weights_metrics.get('risk', 0),
                    'sharpe': weights_metrics.get('sharpe_ratio', 0)
                },
                'market_opt': {
                    'return': market_metrics.get('expected_return', 0),
                    'risk': market_metrics.get('risk', 0),
                    'sharpe': market_metrics.get('sharpe_ratio', 0),
                    'tickers': market_tickers,
                    'basket_size': basket_size
                },
                'recommendation': result.get('optimization_metadata', {}).get('recommendation', 'N/A'),
                'market_success': result.get('optimization_metadata', {}).get('market_exploration_successful', False)
            }
        else:
            return {'error': f"HTTP {response.status_code}: {response.text[:100]}"}
            
    except requests.exceptions.ConnectionError:
        return {'error': 'Backend not running'}
    except Exception as e:
        return {'error': str(e)}

def main():
    print("=" * 80)
    print("OPTIMIZATION TEST: All Risk Profiles (3 iterations each)")
    print("=" * 80)
    print()
    
    all_results = defaultdict(list)
    
    # Test each risk profile 3 times
    for risk_profile in RISK_PROFILES:
        print(f"\n{'='*80}")
        print(f"Testing Risk Profile: {risk_profile.upper()}")
        print(f"{'='*80}")
        
        for iteration in range(1, 4):
            print(f"\n  Iteration {iteration}/3...")
            result = test_optimization(risk_profile, iteration)
            
            if result and 'error' not in result:
                all_results[risk_profile].append(result)
                
                # Display results
                print(f"    ✅ Current: Sharpe={result['current']['sharpe']:.2f}, Return={result['current']['return']:.2%}, Risk={result['current']['risk']:.2%}")
                print(f"    ✅ Weights-Opt: Sharpe={result['weights_opt']['sharpe']:.2f}, Return={result['weights_opt']['return']:.2%}, Risk={result['weights_opt']['risk']:.2%}")
                if result['market_opt']['basket_size'] > 0:
                    print(f"    ✅ Market-Opt: Sharpe={result['market_opt']['sharpe']:.2f}, Return={result['market_opt']['return']:.2%}, Risk={result['market_opt']['risk']:.2%}, Basket={result['market_opt']['basket_size']} tickers")
                    print(f"       Tickers: {result['market_opt']['tickers'][:5]}...")
                else:
                    print(f"    ❌ Market-Opt: Failed")
                print(f"    📊 Recommendation: {result['recommendation']}")
                
                # Small delay to ensure variation
                time.sleep(0.5)
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result'
                print(f"    ❌ Error: {error_msg}")
    
    # Summary Analysis
    print("\n" + "=" * 80)
    print("SUMMARY ANALYSIS")
    print("=" * 80)
    
    for risk_profile in RISK_PROFILES:
        if risk_profile not in all_results or len(all_results[risk_profile]) == 0:
            continue
        
        results = all_results[risk_profile]
        print(f"\n📊 {risk_profile.upper()}:")
        print(f"   Total iterations: {len(results)}")
        
        # Market-optimized analysis
        market_sharpes = [r['market_opt']['sharpe'] for r in results if r['market_opt']['basket_size'] > 0]
        market_basket_sizes = [r['market_opt']['basket_size'] for r in results if r['market_opt']['basket_size'] > 0]
        market_tickers_sets = [set(r['market_opt']['tickers']) for r in results if r['market_opt']['basket_size'] > 0]
        
        if market_sharpes:
            print(f"\n   Market-Optimized Portfolio:")
            print(f"      Sharpe Ratios: {[f'{s:.2f}' for s in market_sharpes]}")
            print(f"      Average Sharpe: {sum(market_sharpes)/len(market_sharpes):.2f}")
            print(f"      Min Sharpe: {min(market_sharpes):.2f}")
            print(f"      Max Sharpe: {max(market_sharpes):.2f}")
            print(f"      Sharpe Variation: {max(market_sharpes) - min(market_sharpes):.2f}")
            
            print(f"\n      Basket Sizes: {market_basket_sizes}")
            print(f"      Average Basket Size: {sum(market_basket_sizes)/len(market_basket_sizes):.1f}")
            
            # Ticker composition variation
            if len(market_tickers_sets) >= 2:
                similarities = []
                for i in range(len(market_tickers_sets)):
                    for j in range(i+1, len(market_tickers_sets)):
                        set1 = market_tickers_sets[i]
                        set2 = market_tickers_sets[j]
                        overlap = len(set1 & set2)
                        union = len(set1 | set2)
                        similarity = overlap / union if union > 0 else 0
                        similarities.append(similarity)
                
                if similarities:
                    print(f"\n      Ticker Composition Similarity:")
                    print(f"         Similarities: {[f'{s:.1%}' for s in similarities]}")
                    print(f"         Average Similarity: {sum(similarities)/len(similarities):.1%}")
                    print(f"         Min Similarity: {min(similarities):.1%}")
                    print(f"         Max Similarity: {max(similarities):.1%}")
            
            # Check if Sharpe is high
            avg_sharpe = sum(market_sharpes) / len(market_sharpes)
            if avg_sharpe > 2.0:
                print(f"\n      ⚠️  WARNING: Average Sharpe ratio ({avg_sharpe:.2f}) is HIGH (>2.0)")
            elif avg_sharpe > 1.5:
                print(f"\n      ⚠️  NOTE: Average Sharpe ratio ({avg_sharpe:.2f}) is moderately high (>1.5)")
            else:
                print(f"\n      ✅ Average Sharpe ratio ({avg_sharpe:.2f}) is reasonable")
        
        # Current vs Weights-Opt comparison
        current_sharpes = [r['current']['sharpe'] for r in results]
        weights_sharpes = [r['weights_opt']['sharpe'] for r in results]
        
        print(f"\n   Current Portfolio:")
        print(f"      Average Sharpe: {sum(current_sharpes)/len(current_sharpes):.2f}")
        print(f"   Weights-Optimized Portfolio:")
        print(f"      Average Sharpe: {sum(weights_sharpes)/len(weights_sharpes):.2f}")
    
    # Overall Summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    
    all_market_sharpes = []
    all_basket_sizes = []
    
    for risk_profile in RISK_PROFILES:
        if risk_profile in all_results:
            for result in all_results[risk_profile]:
                if result['market_opt']['basket_size'] > 0:
                    all_market_sharpes.append(result['market_opt']['sharpe'])
                    all_basket_sizes.append(result['market_opt']['basket_size'])
    
    if all_market_sharpes:
        print(f"\n📊 Market-Optimized Portfolios (All Profiles):")
        print(f"   Total successful optimizations: {len(all_market_sharpes)}")
        print(f"   Average Sharpe Ratio: {sum(all_market_sharpes)/len(all_market_sharpes):.2f}")
        print(f"   Min Sharpe: {min(all_market_sharpes):.2f}")
        print(f"   Max Sharpe: {max(all_market_sharpes):.2f}")
        print(f"   Sharpe Range: {max(all_market_sharpes) - min(all_market_sharpes):.2f}")
        
        high_sharpe_count = sum(1 for s in all_market_sharpes if s > 2.0)
        print(f"\n   Sharpe Ratio Analysis:")
        print(f"      Sharpe > 2.0: {high_sharpe_count}/{len(all_market_sharpes)} ({high_sharpe_count/len(all_market_sharpes):.1%})")
        print(f"      Sharpe > 1.5: {sum(1 for s in all_market_sharpes if s > 1.5)}/{len(all_market_sharpes)}")
        print(f"      Sharpe <= 1.5: {sum(1 for s in all_market_sharpes if s <= 1.5)}/{len(all_market_sharpes)}")
        
        print(f"\n   Basket Size Analysis:")
        print(f"      Average Basket Size: {sum(all_basket_sizes)/len(all_basket_sizes):.1f}")
        print(f"      Min Basket Size: {min(all_basket_sizes)}")
        print(f"      Max Basket Size: {max(all_basket_sizes)}")
        print(f"      Basket Size Range: {min(all_basket_sizes)}-{max(all_basket_sizes)} tickers")
        
        # Variation assessment
        if max(all_market_sharpes) - min(all_market_sharpes) > 0.5:
            print(f"\n   ✅ GOOD VARIATION: Sharpe ratios vary significantly across runs")
        else:
            print(f"\n   ⚠️  LIMITED VARIATION: Sharpe ratios are similar across runs")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    main()

