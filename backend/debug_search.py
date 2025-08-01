#!/usr/bin/env python3
"""
Debug script to test the search function
"""
import sys
import os

# Add current directory to path for backend imports
sys.path.append('.')

def debug_search_function():
    """Debug the search function"""
    print("🔍 Debugging Search Function...")
    print("=" * 40)
    
    try:
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        
        print("✅ Enhanced data fetcher imported successfully!")
        
        # Check master tickers
        ticker_count = len(enhanced_data_fetcher.master_tickers)
        print(f"📊 Total tickers: {ticker_count}")
        
        # Check if key tickers are present
        test_tickers = ["AAPL", "MSFT", "GOOGL", "VOO", "SPY", "QQQ"]
        for ticker in test_tickers:
            if ticker in enhanced_data_fetcher.master_tickers:
                print(f"✅ {ticker} found in master tickers")
            else:
                print(f"❌ {ticker} NOT found in master tickers")
        
        # Test search function directly
        print("\n🔍 Testing search function...")
        test_queries = ["AAPL", "app", "MSFT", "ms", "GOOGL", "goog", "VOO", "voo", "SPY", "spy"]
        
        for query in test_queries:
            print(f"\n--- Testing query: '{query}' ---")
            try:
                results = enhanced_data_fetcher.search_tickers(query, limit=5)
                print(f"   Results: {len(results)} found")
                if results:
                    for result in results:
                        print(f"      {result['ticker']} (cached: {result['cached']})")
                else:
                    print("      No results found")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Test Redis connection
        print(f"\n🔍 Redis status: {enhanced_data_fetcher.r is not None}")
        if enhanced_data_fetcher.r:
            try:
                enhanced_data_fetcher.r.ping()
                print("✅ Redis connection working")
            except Exception as e:
                print(f"❌ Redis connection failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_search():
    """Test a simplified search approach"""
    print("\n🧪 Testing Simple Search...")
    print("=" * 40)
    
    try:
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        
        # Test the simplest possible search
        q = "AAPL"
        print(f"Searching for: '{q}'")
        
        # Direct search in master_tickers
        direct_matches = [t for t in enhanced_data_fetcher.master_tickers if q in t]
        print(f"Direct matches: {direct_matches}")
        
        # Test the actual search function
        results = enhanced_data_fetcher.search_tickers(q, limit=5)
        print(f"Search function results: {results}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main debug function"""
    print("🔍 Portfolio Navigator Wizard - Search Function Debug")
    print("=" * 60)
    
    # Debug search function
    debug_ok = debug_search_function()
    
    # Test simple search
    simple_ok = test_simple_search()
    
    print("\n" + "=" * 60)
    if debug_ok and simple_ok:
        print("✅ Debug completed successfully.")
    else:
        print("❌ Debug found issues. Check the output above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 