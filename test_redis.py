#!/usr/bin/env python3
"""
Test script to verify Redis connection and enhanced data fetcher
"""
import sys
import os

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
    """Test the enhanced data fetcher"""
    print("\n🧪 Testing Enhanced Data Fetcher...")
    print("=" * 40)
    
    try:
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        
        print("✅ Enhanced data fetcher imported successfully!")
        
        # Test ticker store
        ticker_count = len(enhanced_data_fetcher.master_tickers)
        print(f"📊 Master tickers loaded: {ticker_count}")
        
        # Test search functionality
        test_queries = ["AAPL", "app", "MSFT", "ms", "GOOGL", "goog"]
        
        for query in test_queries:
            results = enhanced_data_fetcher.search_tickers(query, limit=5)
            print(f"🔍 Search '{query}': Found {len(results)} results")
            if results:
                tickers = [r['ticker'] for r in results]
                print(f"   Tickers: {tickers}")
        
        # Test cache status
        cache_status = enhanced_data_fetcher.get_cache_status()
        print(f"💾 Cache status: {cache_status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced data fetcher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🧪 Portfolio Navigator Wizard - Redis & Data Fetcher Test")
    print("=" * 60)
    
    # Test Redis
    redis_ok = test_redis_connection()
    
    # Test enhanced data fetcher
    fetcher_ok = test_enhanced_data_fetcher()
    
    print("\n" + "=" * 60)
    if redis_ok and fetcher_ok:
        print("✅ All tests passed! Backend is ready to run.")
        print("🚀 You can now start the backend server with:")
        print("   cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000")
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