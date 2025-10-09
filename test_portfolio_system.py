#!/usr/bin/env python3
"""
Portfolio System Testing Suite
Tests recommendation switching and weight editing functionality
"""

import sys
import os
import json
import time
import requests
from typing import Dict, List, Any

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Test configuration
BASE_URL = "http://localhost:8000/api/portfolio"
RISK_PROFILES = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']

def test_recommendation_switching():
    """Test switching between recommendations and verify metrics alignment"""
    print("🔄 Testing recommendation switching and metrics alignment...")
    
    results = {}
    
    for risk_profile in RISK_PROFILES:
        print(f"\n📊 Testing {risk_profile}...")
        
        try:
            # Get recommendations
            response = requests.get(f"{BASE_URL}/recommendations/{risk_profile}")
            if response.status_code != 200:
                print(f"  ❌ Failed to get recommendations: {response.status_code}")
                results[risk_profile] = {'error': f'HTTP {response.status_code}'}
                continue
            
            recommendations = response.json()
            if len(recommendations) < 3:
                print(f"  ⚠️ Only {len(recommendations)} recommendations available")
            
            # Test each recommendation
            profile_results = []
            
            for i, rec in enumerate(recommendations[:3]):  # Test first 3
                print(f"    Testing recommendation {i+1}: {rec.get('name', 'Unknown')}")
                
                # Get recommendation metrics
                rec_metrics = {
                    'expectedReturn': rec.get('expectedReturn'),
                    'risk': rec.get('risk'),
                    'diversificationScore': rec.get('diversificationScore')
                }
                
                # Calculate live metrics
                allocations = rec.get('portfolio', [])
                if not allocations:
                    print(f"      ⚠️ No allocations in recommendation")
                    continue
                
                # Prepare allocation data for calculate-metrics
                allocation_data = []
                for alloc in allocations:
                    allocation_data.append({
                        'symbol': alloc.get('symbol'),
                        'allocation': alloc.get('allocation')
                    })
                
                # Call calculate-metrics endpoint
                calc_response = requests.post(
                    f"{BASE_URL}/calculate-metrics",
                    json={
                        'allocations': allocation_data,
                        'riskProfile': risk_profile
                    }
                )
                
                if calc_response.status_code != 200:
                    print(f"      ❌ Calculate-metrics failed: {calc_response.status_code}")
                    continue
                
                live_metrics = calc_response.json()
                
                # Compare metrics
                tolerance = 0.01  # 1% tolerance
                
                expected_return_match = abs(rec_metrics['expectedReturn'] - live_metrics['expectedReturn']) < tolerance
                risk_match = abs(rec_metrics['risk'] - live_metrics['risk']) < tolerance
                div_score_match = abs(rec_metrics['diversificationScore'] - live_metrics['diversificationScore']) < 5.0  # 5 point tolerance
                
                test_result = {
                    'recommendation_index': i,
                    'name': rec.get('name'),
                    'recommendation_metrics': rec_metrics,
                    'live_metrics': live_metrics,
                    'matches': {
                        'expectedReturn': expected_return_match,
                        'risk': risk_match,
                        'diversificationScore': div_score_match
                    },
                    'differences': {
                        'expectedReturn': abs(rec_metrics['expectedReturn'] - live_metrics['expectedReturn']),
                        'risk': abs(rec_metrics['risk'] - live_metrics['risk']),
                        'diversificationScore': abs(rec_metrics['diversificationScore'] - live_metrics['diversificationScore'])
                    }
                }
                
                all_match = all(test_result['matches'].values())
                status = "✅" if all_match else "❌"
                print(f"      {status} Metrics alignment: {all_match}")
                
                if not all_match:
                    print(f"        Expected Return: {rec_metrics['expectedReturn']:.4f} vs {live_metrics['expectedReturn']:.4f} (diff: {test_result['differences']['expectedReturn']:.4f})")
                    print(f"        Risk: {rec_metrics['risk']:.4f} vs {live_metrics['risk']:.4f} (diff: {test_result['differences']['risk']:.4f})")
                    print(f"        Diversification: {rec_metrics['diversificationScore']:.1f} vs {live_metrics['diversificationScore']:.1f} (diff: {test_result['differences']['diversificationScore']:.1f})")
                
                profile_results.append(test_result)
                
                # Small delay between tests
                time.sleep(0.1)
            
            results[risk_profile] = profile_results
            
        except Exception as e:
            print(f"  ❌ Error testing {risk_profile}: {e}")
            results[risk_profile] = {'error': str(e)}
    
    return results

def test_weight_editing():
    """Test weight editing functionality"""
    print("\n✏️ Testing weight editing functionality...")
    
    results = {}
    
    # Test with moderate risk profile
    risk_profile = 'moderate'
    
    try:
        # Get a recommendation
        response = requests.get(f"{BASE_URL}/recommendations/{risk_profile}")
        if response.status_code != 200:
            return {'error': f'Failed to get recommendations: {response.status_code}'}
        
        recommendations = response.json()
        if not recommendations:
            return {'error': 'No recommendations available'}
        
        base_rec = recommendations[0]
        base_allocations = base_rec.get('portfolio', [])
        
        if len(base_allocations) < 3:
            return {'error': 'Not enough allocations to test'}
        
        print(f"  📊 Base portfolio: {base_rec.get('name')}")
        
        # Test 1: Modify existing allocations
        print("    Test 1: Modifying existing allocations...")
        modified_allocations = []
        for i, alloc in enumerate(base_allocations):
            # Adjust allocations slightly
            new_allocation = alloc['allocation']
            if i == 0:
                new_allocation += 5  # Increase first by 5%
            elif i == 1:
                new_allocation -= 3  # Decrease second by 3%
            elif i == 2:
                new_allocation -= 2  # Decrease third by 2%
            
            modified_allocations.append({
                'symbol': alloc['symbol'],
                'allocation': max(0, new_allocation)  # Ensure non-negative
            })
        
        # Calculate metrics for modified portfolio
        calc_response = requests.post(
            f"{BASE_URL}/calculate-metrics",
            json={
                'allocations': modified_allocations,
                'riskProfile': risk_profile
            }
        )
        
        if calc_response.status_code == 200:
            modified_metrics = calc_response.json()
            print("      ✅ Modified allocation metrics calculated successfully")
            results['weight_modification'] = {
                'success': True,
                'base_allocations': base_allocations,
                'modified_allocations': modified_allocations,
                'modified_metrics': modified_metrics
            }
        else:
            print(f"      ❌ Failed to calculate modified metrics: {calc_response.status_code}")
            results['weight_modification'] = {'success': False, 'error': f'HTTP {calc_response.status_code}'}
        
        # Test 2: Add a new stock
        print("    Test 2: Adding a new stock...")
        
        # Add AAPL if not already present
        symbols_in_portfolio = [alloc['symbol'] for alloc in base_allocations]
        new_symbol = 'AAPL' if 'AAPL' not in symbols_in_portfolio else 'MSFT'
        
        # Reduce existing allocations to make room
        reduced_allocations = []
        total_reduction = 15  # Reduce by 15% total to make room for new stock
        reduction_per_stock = total_reduction / len(base_allocations)
        
        for alloc in base_allocations:
            reduced_allocations.append({
                'symbol': alloc['symbol'],
                'allocation': alloc['allocation'] - reduction_per_stock
            })
        
        # Add new stock
        reduced_allocations.append({
            'symbol': new_symbol,
            'allocation': total_reduction
        })
        
        # Calculate metrics for portfolio with new stock
        calc_response = requests.post(
            f"{BASE_URL}/calculate-metrics",
            json={
                'allocations': reduced_allocations,
                'riskProfile': risk_profile
            }
        )
        
        if calc_response.status_code == 200:
            new_stock_metrics = calc_response.json()
            print(f"      ✅ Added {new_symbol} successfully, metrics calculated")
            results['add_stock'] = {
                'success': True,
                'new_symbol': new_symbol,
                'allocations_with_new_stock': reduced_allocations,
                'metrics_with_new_stock': new_stock_metrics
            }
        else:
            print(f"      ❌ Failed to calculate metrics with new stock: {calc_response.status_code}")
            results['add_stock'] = {'success': False, 'error': f'HTTP {calc_response.status_code}'}
        
        # Test 3: Remove a stock
        print("    Test 3: Removing a stock...")
        
        if len(base_allocations) > 3:  # Only test if we have more than 3 stocks
            # Remove the last stock and redistribute its allocation
            removed_stock = base_allocations[-1]
            remaining_allocations = base_allocations[:-1]
            
            # Redistribute the removed stock's allocation proportionally
            total_remaining = sum(alloc['allocation'] for alloc in remaining_allocations)
            redistribution_factor = (total_remaining + removed_stock['allocation']) / total_remaining
            
            redistributed_allocations = []
            for alloc in remaining_allocations:
                redistributed_allocations.append({
                    'symbol': alloc['symbol'],
                    'allocation': alloc['allocation'] * redistribution_factor
                })
            
            # Calculate metrics for portfolio with removed stock
            calc_response = requests.post(
                f"{BASE_URL}/calculate-metrics",
                json={
                    'allocations': redistributed_allocations,
                    'riskProfile': risk_profile
                }
            )
            
            if calc_response.status_code == 200:
                removed_stock_metrics = calc_response.json()
                print(f"      ✅ Removed {removed_stock['symbol']} successfully, metrics calculated")
                results['remove_stock'] = {
                    'success': True,
                    'removed_symbol': removed_stock['symbol'],
                    'allocations_after_removal': redistributed_allocations,
                    'metrics_after_removal': removed_stock_metrics
                }
            else:
                print(f"      ❌ Failed to calculate metrics after stock removal: {calc_response.status_code}")
                results['remove_stock'] = {'success': False, 'error': f'HTTP {calc_response.status_code}'}
        else:
            print("      ⚠️ Skipping remove stock test (not enough stocks)")
            results['remove_stock'] = {'skipped': True, 'reason': 'Not enough stocks'}
        
    except Exception as e:
        print(f"  ❌ Error during weight editing tests: {e}")
        results['error'] = str(e)
    
    return results

def test_repeated_switching():
    """Test repeated switching between recommendations"""
    print("\n🔄 Testing repeated recommendation switching...")
    
    risk_profile = 'moderate'  # Use moderate for testing
    switch_count = 10  # Number of switches to test
    
    try:
        # Get recommendations
        response = requests.get(f"{BASE_URL}/recommendations/{risk_profile}")
        if response.status_code != 200:
            return {'error': f'Failed to get recommendations: {response.status_code}'}
        
        recommendations = response.json()
        if len(recommendations) < 2:
            return {'error': 'Need at least 2 recommendations for switching test'}
        
        print(f"  🔄 Performing {switch_count} switches between recommendations...")
        
        switch_results = []
        
        for i in range(switch_count):
            # Alternate between first two recommendations
            rec_index = i % 2
            rec = recommendations[rec_index]
            
            # Calculate live metrics
            allocations = rec.get('portfolio', [])
            allocation_data = [{'symbol': alloc['symbol'], 'allocation': alloc['allocation']} for alloc in allocations]
            
            calc_response = requests.post(
                f"{BASE_URL}/calculate-metrics",
                json={
                    'allocations': allocation_data,
                    'riskProfile': risk_profile
                }
            )
            
            if calc_response.status_code == 200:
                live_metrics = calc_response.json()
                
                # Check alignment
                expected_return_diff = abs(rec['expectedReturn'] - live_metrics['expectedReturn'])
                risk_diff = abs(rec['risk'] - live_metrics['risk'])
                
                switch_results.append({
                    'switch_number': i + 1,
                    'recommendation_index': rec_index,
                    'recommendation_name': rec.get('name'),
                    'expected_return_diff': expected_return_diff,
                    'risk_diff': risk_diff,
                    'aligned': expected_return_diff < 0.01 and risk_diff < 0.01
                })
                
                if (i + 1) % 5 == 0:  # Progress update every 5 switches
                    aligned_count = sum(1 for r in switch_results if r['aligned'])
                    print(f"    Progress: {i + 1}/{switch_count} switches, {aligned_count} aligned")
            
            else:
                switch_results.append({
                    'switch_number': i + 1,
                    'recommendation_index': rec_index,
                    'error': f'HTTP {calc_response.status_code}',
                    'aligned': False
                })
            
            # Small delay between switches
            time.sleep(0.05)
        
        # Analyze results
        aligned_count = sum(1 for r in switch_results if r.get('aligned', False))
        success_rate = (aligned_count / switch_count) * 100
        
        print(f"  📊 Results: {aligned_count}/{switch_count} switches aligned ({success_rate:.1f}%)")
        
        return {
            'switch_count': switch_count,
            'aligned_count': aligned_count,
            'success_rate': success_rate,
            'switch_results': switch_results
        }
        
    except Exception as e:
        print(f"  ❌ Error during repeated switching test: {e}")
        return {'error': str(e)}

def main():
    """Main test execution"""
    print("🧪 Portfolio System Testing Suite")
    print("=" * 50)
    
    # Check if backend is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend health check failed")
            return False
    except requests.exceptions.RequestException:
        print("❌ Backend is not running or not accessible")
        print("   Please start the backend with: make run-backend")
        return False
    
    print("✅ Backend is running and accessible")
    
    # Run tests
    test_results = {}
    
    # Test 1: Recommendation switching and metrics alignment
    test_results['recommendation_switching'] = test_recommendation_switching()
    
    # Test 2: Weight editing functionality
    test_results['weight_editing'] = test_weight_editing()
    
    # Test 3: Repeated switching
    test_results['repeated_switching'] = test_repeated_switching()
    
    # Generate summary report
    print("\n📊 Test Summary Report")
    print("=" * 30)
    
    # Recommendation switching summary
    switching_results = test_results['recommendation_switching']
    if isinstance(switching_results, dict) and 'error' not in switching_results:
        total_tests = 0
        passed_tests = 0
        
        for risk_profile, results in switching_results.items():
            if isinstance(results, list):
                for result in results:
                    if 'matches' in result:
                        total_tests += 1
                        if all(result['matches'].values()):
                            passed_tests += 1
        
        switching_success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"🔄 Recommendation Switching: {passed_tests}/{total_tests} tests passed ({switching_success_rate:.1f}%)")
    else:
        print("🔄 Recommendation Switching: ❌ Failed")
    
    # Weight editing summary
    weight_results = test_results['weight_editing']
    weight_tests_passed = 0
    weight_tests_total = 0
    
    for test_name, result in weight_results.items():
        if test_name != 'error' and isinstance(result, dict):
            weight_tests_total += 1
            if result.get('success', False):
                weight_tests_passed += 1
    
    if weight_tests_total > 0:
        weight_success_rate = (weight_tests_passed / weight_tests_total * 100)
        print(f"✏️ Weight Editing: {weight_tests_passed}/{weight_tests_total} tests passed ({weight_success_rate:.1f}%)")
    else:
        print("✏️ Weight Editing: ❌ Failed")
    
    # Repeated switching summary
    repeated_results = test_results['repeated_switching']
    if 'success_rate' in repeated_results:
        print(f"🔄 Repeated Switching: {repeated_results['success_rate']:.1f}% success rate")
    else:
        print("🔄 Repeated Switching: ❌ Failed")
    
    # Save detailed results
    with open('PORTFOLIO_SYSTEM_TEST_RESULTS.json', 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to PORTFOLIO_SYSTEM_TEST_RESULTS.json")
    
    # Overall assessment
    overall_success = (
        switching_success_rate > 90 if 'switching_success_rate' in locals() else False
    ) and (
        weight_success_rate > 80 if 'weight_success_rate' in locals() else False
    ) and (
        repeated_results.get('success_rate', 0) > 90
    )
    
    if overall_success:
        print("\n🎉 All tests passed! Portfolio system is working correctly.")
        return True
    else:
        print("\n⚠️ Some tests failed. Please review the detailed results.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
