#!/usr/bin/env python3
"""
Test script to verify search functionality works correctly
after fixing the frontend URL issues
"""
import requests
import time
import sys

def test_search_endpoint():
    """Test the search endpoint directly"""
    print("🧪 Testing Search Endpoint...")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Test queries
    test_queries = [
        ("AAPL", "Apple Inc."),
        ("MSFT", "Microsoft"),
        ("GOOGL", "Alphabet"),
        ("TSLA", "Tesla"),
        ("NVDA", "NVIDIA"),
        ("app", "Partial search"),
        ("ms", "Partial search"),
        ("goog", "Partial search")
    ]
    
    for query, description in test_queries:
        try:
            print(f"\n🔍 Testing: {description} ('{query}')")
            response = requests.get(
                f"{base_url}/api/portfolio/ticker/search",
                params={"q": query, "limit": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"   ✅ Status: {response.status_code}")
                print(f"   📊 Found: {len(results)} results")
                if results:
                    tickers = [r['ticker'] for r in results]
                    print(f"   🎯 Tickers: {tickers}")
                else:
                    print("   ⚠️  No results found")
            else:
                print(f"   ❌ Status: {response.status_code}")
                print(f"   📝 Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed - Backend not running")
            return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    return True

def test_backend_health():
    """Test if backend is running and healthy"""
    print("\n🏥 Testing Backend Health...")
    print("=" * 40)
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend is healthy")
            print(f"📊 Ticker count: {data.get('ticker_count', 0)}")
            print(f"💾 Cached tickers: {data.get('cached_tickers', 0)}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend not reachable: {e}")
        return False

def test_ticker_count():
    """Test if we have sufficient tickers loaded"""
    print("\n📊 Testing Ticker Count...")
    print("=" * 40)
    
    try:
        response = requests.get("http://localhost:8000/api/portfolio/tickers/master", timeout=10)
        if response.status_code == 200:
            data = response.json()
            total_tickers = data.get('total_tickers', 0)
            sp500_count = data.get('sp500_count', 0)
            nasdaq100_count = data.get('nasdaq100_count', 0)
            
            print(f"📈 Total tickers: {total_tickers}")
            print(f"📊 S&P 500: {sp500_count}")
            print(f"📊 Nasdaq 100: {nasdaq100_count}")
            
            if total_tickers >= 400:
                print("✅ Excellent! Full ticker list loaded")
                return True
            elif total_tickers >= 200:
                print("✅ Good ticker count loaded")
                return True
            else:
                print("⚠️  Low ticker count - may be in fast startup mode")
                return False
        else:
            print(f"❌ Failed to get ticker count: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting ticker count: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Search Functionality Test")
    print("=" * 50)
    print("This test verifies that search works correctly after URL fixes")
    print("=" * 50)
    
    # Wait for backend to be ready
    print("⏳ Waiting for backend to be ready...")
    time.sleep(2)
    
    # Test backend health
    health_ok = test_backend_health()
    if not health_ok:
        print("\n❌ Backend is not running. Please start it first:")
        print("   make dev          # For fast mode")
        print("   make full-dev     # For full ticker mode")
        return
    
    # Test ticker count
    ticker_ok = test_ticker_count()
    
    # Test search functionality
    search_ok = test_search_endpoint()
    
    print("\n" + "=" * 50)
    if search_ok and ticker_ok:
        print("✅ All tests passed! Search functionality is working correctly.")
        print("🚀 You can now use the frontend search without issues.")
    elif search_ok and not ticker_ok:
        print("⚠️  Search works but ticker count is low.")
        print("💡 Consider using 'make full-dev' for complete ticker coverage.")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    print("=" * 50)

if __name__ == "__main__":
    main() 