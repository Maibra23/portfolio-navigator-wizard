#!/usr/bin/env python3
"""
Test Script for Strategy Comparison System
Tests the new strategy-based portfolio generation and comparison endpoints
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/portfolio"

def test_strategy_buckets_generation():
    """Test generating strategy portfolio buckets"""
    print("🧪 Testing Strategy Portfolio Buckets Generation...")
    
    try:
        response = requests.post(f"{API_BASE}/strategy-buckets/generate")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Strategy buckets generated successfully!")
            print(f"   - Pure strategies: {data['buckets_created']['pure_strategies']}")
            print(f"   - Personalized strategies: {data['buckets_created']['personalized_strategies']}")
            print(f"   - Portfolios per bucket: {data['portfolios_per_bucket']}")
            print(f"   - Total portfolios: {data['total_portfolios']}")
            return True
        else:
            print(f"❌ Failed to generate strategy buckets: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing strategy buckets generation: {e}")
        return False

def test_strategy_buckets_status():
    """Test getting strategy portfolio buckets status"""
    print("\n🧪 Testing Strategy Portfolio Buckets Status...")
    
    try:
        response = requests.get(f"{API_BASE}/strategy-buckets/status")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Strategy buckets status retrieved successfully!")
            print(f"   - Total buckets: {data['total_buckets']}")
            print(f"   - Total portfolios: {data['total_portfolios']}")
            
            # Check pure strategies
            print("\n   Pure Strategies:")
            for strategy, status in data['pure_strategies'].items():
                print(f"     - {strategy}: {'✅' if status['exists'] else '❌'}")
            
            # Check personalized strategies
            print("\n   Personalized Strategies:")
            for profile, strategies in data['personalized_strategies'].items():
                print(f"     - {profile}:")
                for strategy, status in strategies.items():
                    print(f"       - {strategy}: {'✅' if status['exists'] else '❌'}")
            
            return True
        else:
            print(f"❌ Failed to get strategy buckets status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing strategy buckets status: {e}")
        return False

def test_strategy_comparison(strategy, risk_profile):
    """Test generating strategy comparison portfolios"""
    print(f"\n🧪 Testing Strategy Comparison: {strategy} for {risk_profile}...")
    
    try:
        payload = {
            "strategy": strategy,
            "risk_profile": risk_profile
        }
        
        response = requests.post(
            f"{API_BASE}/recommendations/strategy-comparison",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Strategy comparison generated successfully!")
            
            # Display pure strategy portfolio
            pure = data['pure_strategy']
            print(f"\n   Pure Strategy Portfolio:")
            print(f"     - Name: {pure['name']}")
            print(f"     - Expected Return: {pure['expectedReturn']:.1%}")
            print(f"     - Risk: {pure['risk']:.1%}")
            print(f"     - Diversification: {pure['diversificationScore']:.0f}%")
            print(f"     - Assets: {len(pure['allocations'])}")
            
            if 'riskWarning' in pure:
                warning = pure['riskWarning']
                print(f"     - ⚠️ Risk Warning: {warning['message']}")
                print(f"       Details: {warning['details']}")
                print(f"       Recommendation: {warning['recommendation']}")
            
            # Display personalized strategy portfolio
            personalized = data['personalized_strategy']
            print(f"\n   Personalized Strategy Portfolio:")
            print(f"     - Name: {personalized['name']}")
            print(f"     - Expected Return: {personalized['expectedReturn']:.1%}")
            print(f"     - Risk: {personalized['risk']:.1%}")
            print(f"     - Diversification: {personalized['diversificationScore']:.0f}%")
            print(f"     - Assets: {len(personalized['allocations'])}")
            
            return True
        else:
            print(f"❌ Failed to generate strategy comparison: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing strategy comparison: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Strategy Comparison System Test")
    print("=" * 50)
    
    # Test 1: Generate strategy buckets
    if not test_strategy_buckets_generation():
        print("\n❌ Strategy buckets generation failed. Stopping tests.")
        return
    
    # Wait a moment for generation to complete
    print("\n⏳ Waiting for strategy buckets to be generated...")
    time.sleep(2)
    
    # Test 2: Check strategy buckets status
    if not test_strategy_buckets_status():
        print("\n❌ Strategy buckets status check failed. Stopping tests.")
        return
    
    # Test 3: Test strategy comparisons for different combinations
    test_combinations = [
        ('diversification', 'conservative'),
        ('risk', 'moderate'),
        ('return', 'aggressive')
    ]
    
    print("\n🧪 Testing Strategy Comparisons...")
    for strategy, risk_profile in test_combinations:
        if not test_strategy_comparison(strategy, risk_profile):
            print(f"❌ Strategy comparison test failed for {strategy} + {risk_profile}")
        else:
            print(f"✅ Strategy comparison test passed for {strategy} + {risk_profile}")
    
    print("\n🎉 Strategy Comparison System Test Complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()
