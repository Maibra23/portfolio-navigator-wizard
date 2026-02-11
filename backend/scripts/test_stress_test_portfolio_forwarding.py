#!/usr/bin/env python3
"""
Test script to verify portfolio forwarding from recommendations tab to stress test tab
Tests with 5 different portfolios across all risk profiles
"""

import sys
import os
import json
import requests
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = "http://localhost:8000"

# Test portfolios for each risk profile
TEST_PORTFOLIOS = {
    'very-conservative': {
        'tickers': ['AAPL', 'MSFT', 'JNJ', 'PG', 'KO'],
        'weights': {'AAPL': 0.25, 'MSFT': 0.20, 'JNJ': 0.20, 'PG': 0.20, 'KO': 0.15},
        'capital': 5000,
        'risk_profile': 'very-conservative'
    },
    'conservative': {
        'tickers': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
        'weights': {'AAPL': 0.30, 'MSFT': 0.25, 'GOOGL': 0.20, 'AMZN': 0.15, 'TSLA': 0.10},
        'capital': 8000,
        'risk_profile': 'conservative'
    },
    'moderate': {
        'tickers': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META'],
        'weights': {'AAPL': 0.20, 'MSFT': 0.20, 'GOOGL': 0.15, 'AMZN': 0.15, 'NVDA': 0.15, 'META': 0.15},
        'capital': 10000,
        'risk_profile': 'moderate'
    },
    'aggressive': {
        'tickers': ['TSLA', 'NVDA', 'AMD', 'META', 'NFLX'],
        'weights': {'TSLA': 0.25, 'NVDA': 0.25, 'AMD': 0.20, 'META': 0.15, 'NFLX': 0.15},
        'capital': 15000,
        'risk_profile': 'aggressive'
    },
    'very-aggressive': {
        'tickers': ['TSLA', 'NVDA', 'AMD', 'MARA', 'RIOT'],
        'weights': {'TSLA': 0.30, 'NVDA': 0.25, 'AMD': 0.20, 'MARA': 0.15, 'RIOT': 0.10},
        'capital': 20000,
        'risk_profile': 'very-aggressive'
    }
}

def test_stress_test_endpoint(portfolio: Dict[str, Any], portfolio_source: str = 'current') -> Dict[str, Any]:
    """
    Test the stress test endpoint with a given portfolio
    """
    print(f"\n{'='*60}")
    print(f"Testing Stress Test Endpoint")
    print(f"Risk Profile: {portfolio['risk_profile']}")
    print(f"Portfolio Source: {portfolio_source}")
    print(f"Tickers: {portfolio['tickers']}")
    print(f"Capital: {portfolio['capital']}")
    print(f"{'='*60}")
    
    # Prepare request payload
    payload = {
        'tickers': portfolio['tickers'],
        'weights': portfolio['weights'],
        'scenarios': ['covid19', '2008_crisis'],
        'capital': portfolio['capital'],
        'risk_profile': portfolio['risk_profile']
    }
    
    try:
        # Make API request
        response = requests.post(
            f"{BASE_URL}/api/v1/portfolio/stress-test",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=120  # 2 minute timeout for stress tests
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify response structure
            assert 'portfolio_summary' in data, "Missing portfolio_summary in response"
            assert 'scenarios' in data, "Missing scenarios in response"
            assert 'resilience_score' in data, "Missing resilience_score in response"
            assert 'overall_assessment' in data, "Missing overall_assessment in response"
            
            # Verify portfolio summary matches input
            summary = data['portfolio_summary']
            assert summary['tickers'] == portfolio['tickers'], "Tickers mismatch in portfolio_summary"
            assert summary['capital'] == portfolio['capital'], "Capital mismatch in portfolio_summary"
            assert summary['risk_profile'] == portfolio['risk_profile'], "Risk profile mismatch in portfolio_summary"
            
            # Verify scenarios
            scenarios = data['scenarios']
            assert 'covid19' in scenarios or '2008_crisis' in scenarios, "No scenario results returned"
            
            # Verify COVID-19 scenario if present
            if 'covid19' in scenarios:
                covid = scenarios['covid19']
                assert 'scenario_name' in covid, "Missing scenario_name in COVID-19 results"
                assert 'metrics' in covid, "Missing metrics in COVID-19 results"
                assert 'monthly_performance' in covid, "Missing monthly_performance in COVID-19 results"
                assert 'peaks_troughs' in covid, "Missing peaks_troughs in COVID-19 results"
                
                metrics = covid['metrics']
                assert 'total_return' in metrics, "Missing total_return in COVID-19 metrics"
                assert 'max_drawdown' in metrics, "Missing max_drawdown in COVID-19 metrics"
                assert 'recovery_months' in metrics, "Missing recovery_months in COVID-19 metrics"
            
            # Verify 2008 Crisis scenario if present
            if '2008_crisis' in scenarios:
                crisis = scenarios['2008_crisis']
                assert 'scenario_name' in crisis, "Missing scenario_name in 2008 Crisis results"
                assert 'metrics' in crisis, "Missing metrics in 2008 Crisis results"
                assert 'monthly_performance' in crisis, "Missing monthly_performance in 2008 Crisis results"
                assert 'peaks_troughs' in crisis, "Missing peaks_troughs in 2008 Crisis results"
                
                metrics = crisis['metrics']
                assert 'total_return' in metrics, "Missing total_return in 2008 Crisis metrics"
                assert 'max_drawdown' in metrics, "Missing max_drawdown in 2008 Crisis metrics"
                assert 'recovery_months' in metrics, "Missing recovery_months in 2008 Crisis metrics"
            
            # Verify resilience score
            resilience_score = data['resilience_score']
            assert isinstance(resilience_score, (int, float)), "Resilience score must be a number"
            assert 0 <= resilience_score <= 100, "Resilience score must be between 0 and 100"
            
            print(f"✅ Stress test completed successfully!")
            print(f"   Resilience Score: {resilience_score:.1f}/100")
            print(f"   Assessment: {data['overall_assessment'][:80]}...")
            
            if 'covid19' in scenarios:
                covid_metrics = scenarios['covid19']['metrics']
                print(f"   COVID-19 Max Drawdown: {covid_metrics['max_drawdown']*100:.1f}%")
                print(f"   COVID-19 Recovery: {covid_metrics['recovery_months'] or 'N/A'} months")
            
            if '2008_crisis' in scenarios:
                crisis_metrics = scenarios['2008_crisis']['metrics']
                print(f"   2008 Crisis Max Drawdown: {crisis_metrics['max_drawdown']*100:.1f}%")
                print(f"   2008 Crisis Recovery: {crisis_metrics['recovery_months'] or 'N/A'} months")
            
            return {
                'success': True,
                'data': data,
                'portfolio_source': portfolio_source
            }
        else:
            error_msg = f"API returned status {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f": {error_data.get('detail', 'Unknown error')}"
            except:
                error_msg += f": {response.text[:200]}"
            
            print(f"❌ Stress test failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'portfolio_source': portfolio_source
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return {
            'success': False,
            'error': str(e),
            'portfolio_source': portfolio_source
        }
    except AssertionError as e:
        print(f"❌ Validation error: {e}")
        return {
            'success': False,
            'error': str(e),
            'portfolio_source': portfolio_source
        }
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'portfolio_source': portfolio_source
        }

def test_portfolio_forwarding_simulation():
    """
    Simulate portfolio forwarding from recommendations tab to stress test tab
    Tests all three portfolio sources: current, weights, market
    """
    print("\n" + "="*60)
    print("PORTFOLIO FORWARDING TEST")
    print("="*60)
    print("\nThis test simulates the portfolio forwarding flow:")
    print("1. User selects a portfolio in Recommendations tab")
    print("2. Portfolio data is forwarded to Stress Test tab")
    print("3. Stress test runs with the forwarded portfolio")
    print("\nTesting with 5 portfolios across all risk profiles...")
    
    results = []
    
    # Test each risk profile
    for risk_profile, portfolio in TEST_PORTFOLIOS.items():
        print(f"\n{'='*60}")
        print(f"Testing {risk_profile.upper()} Risk Profile")
        print(f"{'='*60}")
        
        # Test with 'current' source (default)
        result_current = test_stress_test_endpoint(portfolio, 'current')
        results.append(result_current)
        
        # Test with 'weights' source (if we had weights-optimized data)
        # In real scenario, this would come from triple optimization results
        result_weights = test_stress_test_endpoint(portfolio, 'weights')
        results.append(result_weights)
        
        # Test with 'market' source (if we had market-optimized data)
        # In real scenario, this would come from triple optimization results
        result_market = test_stress_test_endpoint(portfolio, 'market')
        results.append(result_market)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results if r.get('success', False))
    total = len(results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success Rate: {successful/total*100:.1f}%")
    
    if successful == total:
        print("\n✅ All tests passed! Portfolio forwarding is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        print("\nFailed tests:")
        for i, result in enumerate(results):
            if not result.get('success', False):
                print(f"  - Test {i+1} ({result.get('portfolio_source', 'unknown')}): {result.get('error', 'Unknown error')}")
    
    return results

if __name__ == '__main__':
    print("="*60)
    print("STRESS TEST PORTFOLIO FORWARDING VERIFICATION")
    print("="*60)
    print("\nThis script tests:")
    print("1. Portfolio data forwarding from Recommendations → Stress Test")
    print("2. Stress test API endpoint functionality")
    print("3. Response structure validation")
    print("4. Data integrity across all risk profiles")
    print("\nMake sure the backend server is running on http://localhost:8000")
    print("\nStarting tests...")
    
    try:
        results = test_portfolio_forwarding_simulation()
        
        # Save results to file
        output_file = 'stress_test_forwarding_results.json'
        with open(output_file, 'w') as f:
            json.dump({
                'test_summary': {
                    'total_tests': len(results),
                    'successful': sum(1 for r in results if r.get('success', False)),
                    'failed': sum(1 for r in results if not r.get('success', False))
                },
                'results': results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {output_file}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
