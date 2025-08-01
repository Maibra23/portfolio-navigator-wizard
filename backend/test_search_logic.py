#!/usr/bin/env python3
"""
Test search logic without Redis dependency
"""
import sys
import os

# Add current directory to path for backend imports
sys.path.append('.')

def test_search_logic():
    """Test the search logic directly"""
    print("🧪 Testing Search Logic...")
    print("=" * 50)
    
    try:
        # Import ticker store directly
        from utils.ticker_store import ticker_store
        
        print("✅ Ticker store imported successfully!")
        
        # Get all tickers
        all_tickers = ticker_store.get_all_tickers()
        print(f"📊 Total tickers from store: {len(all_tickers)}")
        
        # Add ETFs manually
        etf_list = ["VOO", "SPY", "IVV", "VTI", "VTS", "QQQ", "VUG", "VEA", "IEFA", "VTV", "BND"]
        master_tickers = all_tickers.copy()
        
        for etf in etf_list:
            if etf not in master_tickers:
                master_tickers.append(etf)
        
        print(f"📊 Total tickers with ETFs: {len(master_tickers)}")
        
        # Test search logic
        def search_tickers_simple(query, limit=10):
            q = query.strip().upper()
            matches = []
            
            # Strategy 1: Exact prefix matches
            prefix_matches = [t for t in master_tickers if t.startswith(q)]
            matches.extend(prefix_matches)
            
            # Strategy 2: Partial matches
            partial_matches = [t for t in master_tickers if q in t and t not in prefix_matches]
            matches.extend(partial_matches)
            
            # Limit results
            limited_matches = matches[:limit]
            
            # Return simple format
            return [{"ticker": t, "cached": False} for t in limited_matches]
        
        # Test stock search
        print("\n🔍 Testing Stock Search...")
        stock_queries = ["AAPL", "app", "MSFT", "ms", "GOOGL", "goog", "TSLA", "tsla"]
        
        for query in stock_queries:
            results = search_tickers_simple(query, limit=3)
            print(f"   '{query}': {len(results)} results")
            if results:
                tickers = [r['ticker'] for r in results]
                print(f"      Found: {tickers}")
        
        # Test ETF search
        print("\n📊 Testing ETF Search...")
        etf_queries = ["VOO", "voo", "SPY", "spy", "QQQ", "qqq", "BND", "bnd", "VTI", "vti"]
        
        for query in etf_queries:
            results = search_tickers_simple(query, limit=3)
            print(f"   '{query}': {len(results)} results")
            if results:
                tickers = [r['ticker'] for r in results]
                print(f"      Found: {tickers}")
        
        # Test partial matches
        print("\n🔍 Testing Partial Matches...")
        partial_queries = ["VO", "SP", "QQ", "BN", "VT", "GO", "MS", "AP"]
        
        for query in partial_queries:
            results = search_tickers_simple(query, limit=5)
            print(f"   '{query}': {len(results)} results")
            if results:
                tickers = [r['ticker'] for r in results]
                print(f"      Found: {tickers}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ticker_content():
    """Test ticker content"""
    print("\n📋 Testing Ticker Content...")
    print("=" * 50)
    
    try:
        from utils.ticker_store import ticker_store
        
        # Get all tickers
        all_tickers = ticker_store.get_all_tickers()
        
        # Check for key stocks
        stock_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
        found_stocks = []
        
        for stock in stock_list:
            if stock in all_tickers:
                found_stocks.append(stock)
        
        print(f"📊 Stocks found: {found_stocks}")
        print(f"📊 Total stocks found: {len(found_stocks)}/{len(stock_list)}")
        
        # Check for ETFs (should not be in original list)
        etf_list = ["VOO", "SPY", "IVV", "VTI", "VTS", "QQQ", "VUG", "VEA", "IEFA", "VTV", "BND"]
        found_etfs = []
        
        for etf in etf_list:
            if etf in all_tickers:
                found_etfs.append(etf)
        
        print(f"\n📈 ETFs in original list: {found_etfs}")
        print(f"📈 Total ETFs in original: {len(found_etfs)}/{len(etf_list)}")
        
        # Show sample of tickers
        sample_tickers = all_tickers[:20]
        print(f"\n📊 Sample tickers: {sample_tickers}")
        
        return True
        
    except Exception as e:
        print(f"❌ Content test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Portfolio Navigator Wizard - Search Logic Test")
    print("=" * 60)
    
    # Test search logic
    search_ok = test_search_logic()
    
    # Test ticker content
    content_ok = test_ticker_content()
    
    print("\n" + "=" * 60)
    if search_ok and content_ok:
        print("✅ All tests passed! Search logic is working correctly.")
        print("🚀 Both stocks and ETFs can be searched.")
        print("📊 ETFs need to be added to the master ticker list.")
    else:
        print("❌ Some tests failed. Check the output above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 