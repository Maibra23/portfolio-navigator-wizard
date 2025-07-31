#!/usr/bin/env python3
"""
Test script for the enhanced data fetching system
Demonstrates Redis caching, monthly data fetching, and ticker validation
"""

import asyncio
import time
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_ticker_search():
    """Test ticker search functionality"""
    print("\n🔍 Testing ticker search...")
    try:
        # Test search for "AAPL"
        response = requests.get(f"{BASE_URL}/api/portfolio/ticker/search?q=AAPL&limit=5")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ticker search successful: {data['total_found']} results")
            for result in data['results'][:3]:
                print(f"   - {result['ticker']} (cached: {result['cached']})")
            return True
        else:
            print(f"❌ Ticker search failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ticker search error: {e}")
        return False

def test_monthly_returns():
    """Test monthly returns fetching"""
    print("\n📊 Testing monthly returns...")
    try:
        # Test AAPL monthly returns
        response = requests.get(f"{BASE_URL}/api/portfolio/returns/monthly?ticker=AAPL")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Monthly returns successful: {data['data_points']} points")
            print(f"   Source: {data['source']}")
            print(f"   Date range: {data['dates'][0]} to {data['dates'][-1]}")
            print(f"   Price range: ${data['prices'][0]:.2f} to ${data['prices'][-1]:.2f}")
            return True
        else:
            print(f"❌ Monthly returns failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Monthly returns error: {e}")
        return False

def test_returns_analysis():
    """Test comprehensive returns analysis"""
    print("\n📈 Testing returns analysis...")
    try:
        # Test AAPL analysis
        response = requests.get(f"{BASE_URL}/api/portfolio/returns/analysis?ticker=AAPL")
        if response.status_code == 200:
            data = response.json()
            stats = data['statistics']
            print(f"✅ Returns analysis successful:")
            print(f"   Annualized Return: {stats['annualized_return']:.2%}")
            print(f"   Annualized Volatility: {stats['annualized_volatility']:.2%}")
            print(f"   Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
            print(f"   Win Rate: {stats['win_rate']:.2%}")
            return True
        else:
            print(f"❌ Returns analysis failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Returns analysis error: {e}")
        return False

def test_cache_status():
    """Test cache status endpoint"""
    print("\n💾 Testing cache status...")
    try:
        response = requests.get(f"{BASE_URL}/api/portfolio/cache/status")
        if response.status_code == 200:
            data = response.json()
            system_status = data['system_status']
            print(f"✅ Cache status successful:")
            print(f"   Master tickers: {system_status['master_tickers_count']}")
            print(f"   Redis connected: {system_status['redis_connected']}")
            print(f"   Cached tickers: {system_status['cached_tickers_count']}")
            print(f"   Cache warmed: {system_status['cache_warmed']}")
            return True
        else:
            print(f"❌ Cache status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cache status error: {e}")
        return False

def test_bulk_analysis():
    """Test bulk returns analysis"""
    print("\n📊 Testing bulk analysis...")
    try:
        tickers = ["AAPL", "MSFT", "GOOGL"]
        response = requests.post(
            f"{BASE_URL}/api/portfolio/returns/bulk",
            json=tickers
        )
        if response.status_code == 200:
            data = response.json()
            summary = data['summary']
            print(f"✅ Bulk analysis successful:")
            print(f"   Requested: {summary['requested']}")
            print(f"   Successful: {summary['successful']}")
            print(f"   Failed: {summary['failed']}")
            
            for ticker, result in data['successful'].items():
                stats = result['statistics']
                print(f"   {ticker}: {stats['annualized_return']:.2%} return, {stats['annualized_volatility']:.2%} vol")
            return True
        else:
            print(f"❌ Bulk analysis failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bulk analysis error: {e}")
        return False

def test_performance():
    """Test performance of cached vs uncached requests"""
    print("\n⚡ Testing performance...")
    try:
        # Test cached request (should be fast)
        start_time = time.time()
        response1 = requests.get(f"{BASE_URL}/api/portfolio/returns/monthly?ticker=AAPL")
        cached_time = time.time() - start_time
        
        # Test another ticker (might be cached or not)
        start_time = time.time()
        response2 = requests.get(f"{BASE_URL}/api/portfolio/returns/monthly?ticker=MSFT")
        second_time = time.time() - start_time
        
        print(f"✅ Performance test:")
        print(f"   First request (AAPL): {cached_time:.3f}s")
        print(f"   Second request (MSFT): {second_time:.3f}s")
        
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            print(f"   AAPL source: {data1['source']}")
            print(f"   MSFT source: {data2['source']}")
            return True
        else:
            print(f"❌ Performance test failed")
            return False
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Enhanced Data Fetching System")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_check),
        ("Ticker Search", test_ticker_search),
        ("Monthly Returns", test_monthly_returns),
        ("Returns Analysis", test_returns_analysis),
        ("Cache Status", test_cache_status),
        ("Bulk Analysis", test_bulk_analysis),
        ("Performance", test_performance),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main() 