#!/usr/bin/env python3
"""
Comprehensive test script for the full ticker implementation
"""
import sys
import os
import time
import requests
import json

# Add backend to path
sys.path.append('backend')

def test_redis_connection():
    """Test Redis connection"""
    print("🧪 Testing Redis Connection...")
    print("=" * 40)
    
    try:
        import redis
        
        # Test basic Redis connection
        r = redis.Redis(host='localhost', port=6379, decode_responses=False, socket_timeout=5)
        r.ping()
        print("✅ Redis connection successful!")
        
        # Test basic operations
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        if value == b'test_value':
            print("✅ Redis read/write operations working!")
        else:
            print("❌ Redis read/write operations failed!")
        
        # Clean up
        r.delete('test_key')
        
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("💡 Make sure Redis is running: redis-server")
        return False

def test_enhanced_data_fetcher():
    """Test the enhanced data fetcher with full ticker list"""
    print("\n🧪 Testing Enhanced Data Fetcher (Full Ticker Mode)...")
    print("=" * 40)
    
    try:
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        
        print("✅ Enhanced data fetcher imported successfully!")
        
        # Test ticker store
        ticker_count = len(enhanced_data_fetcher.master_tickers)
        print(f"📊 Master tickers loaded: {ticker_count}")
        
        # Check if we have a good number of tickers
        if ticker_count < 200:
            print("⚠️  Warning: Low ticker count. You may be in fast startup mode.")
            print("💡 To get full ticker list, set FAST_STARTUP=false")
        elif ticker_count >= 400:
            print("✅ Excellent! Full ticker list loaded successfully.")
        else:
            print("✅ Good ticker count loaded.")
        
        # Test search functionality with various queries
        test_queries = [
            ("AAPL", "Exact ticker"),
            ("app", "Partial lowercase"),
            ("APP", "Partial uppercase"),
            ("MSFT", "Exact ticker"),
            ("ms", "Partial lowercase"),
            ("GOOGL", "Exact ticker"),
            ("goog", "Partial lowercase"),
            ("TSLA", "Exact ticker"),
            ("tsl", "Partial lowercase"),
            ("NVDA", "Exact ticker"),
            ("nvd", "Partial lowercase")
        ]
        
        print("\n🔍 Testing search functionality...")
        for query, description in test_queries:
            results = enhanced_data_fetcher.search_tickers(query, limit=5)
            print(f"   {description} '{query}': Found {len(results)} results")
            if results:
                tickers = [r['ticker'] for r in results]
                print(f"      Tickers: {tickers}")
        
        # Test cache status
        cache_status = enhanced_data_fetcher.get_cache_status()
        print(f"\n💾 Cache status: {cache_status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced data fetcher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test the API endpoints"""
    print("\n🧪 Testing API Endpoints...")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Wait for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(3)
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed: {data}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
    
    # Test 2: Ticker search
    print("\n2. Testing ticker search API...")
    test_queries = ["AAPL", "app", "MSFT", "ms", "GOOGL", "goog"]
    
    for query in test_queries:
        try:
            response = requests.get(f"{base_url}/api/portfolio/ticker/search?q={query}&limit=5", timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"   ✅ Search '{query}': Found {len(results)} results")
                if results:
                    tickers = [r['ticker'] for r in results]
                    print(f"      Tickers: {tickers}")
            else:
                print(f"   ❌ Search '{query}' failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Search '{query}' error: {e}")
    
    # Test 3: Cache status
    print("\n3. Testing cache status API...")
    try:
        response = requests.get(f"{base_url}/api/portfolio/cache/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            status = data.get('system_status', {})
            print(f"   ✅ Cache status: {status.get('master_count', 0)} master tickers, {status.get('cached_count', 0)} cached")
            print(f"      Redis status: {status.get('redis_status', 'unknown')}")
        else:
            print(f"   ❌ Cache status failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cache status error: {e}")

def main():
    """Main test function"""
    print("🧪 Portfolio Navigator Wizard - Full Implementation Test")
    print("=" * 60)
    
    # Test Redis
    redis_ok = test_redis_connection()
    
    # Test enhanced data fetcher
    fetcher_ok = test_enhanced_data_fetcher()
    
    print("\n" + "=" * 60)
    if redis_ok and fetcher_ok:
        print("✅ All tests passed! Backend is ready to run.")
        print("🚀 You can now start the backend server with:")
        print("   chmod +x start_backend_full_tickers.sh && ./start_backend_full_tickers.sh")
        print("\n🌐 After starting the server, test the API endpoints.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        if not redis_ok:
            print("💡 To fix Redis issues:")
            print("   1. Install Redis: brew install redis (macOS) or sudo apt install redis-server (Ubuntu)")
            print("   2. Start Redis: redis-server")
            print("   3. Test Redis: redis-cli ping")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 