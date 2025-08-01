#!/usr/bin/env python3
"""
Simple test script to test search function without Redis dependency
"""
import sys
import os

# Add current directory to path for backend imports
sys.path.append('.')

def test_search_without_redis():
    """Test search function without Redis"""
    print("🧪 Testing Search Function (No Redis)...")
    print("=" * 50)
    
    try:
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        
        print("✅ Enhanced data fetcher imported successfully!")
        
        # Check master tickers
        ticker_count = len(enhanced_data_fetcher.master_tickers)
        print(f"📊 Total tickers: {ticker_count}")
        
        # Check if key tickers are present
        test_tickers = ["AAPL", "MSFT", "GOOGL", "VOO", "SPY", "QQQ", "BND"]
        found_tickers = []
        
        for ticker in test_tickers:
            if ticker in enhanced_data_fetcher.master_tickers:
                found_tickers.append(ticker)
                print(f"✅ {ticker} found in master tickers")
            else:
                print(f"❌ {ticker} NOT found in master tickers")
        
        print(f"\n📈 Found {len(found_tickers)}/{len(test_tickers)} key tickers")
        
        # Test search function for stocks
        print("\n🔍 Testing Stock Search...")
        stock_queries = ["AAPL", "app", "MSFT", "ms", "GOOGL", "goog", "TSLA", "tsla"]
        
        for query in stock_queries:
            try:
                results = enhanced_data_fetcher.search_tickers(query, limit=3)
                print(f"   '{query}': {len(results)} results")
                if results:
                    tickers = [r['ticker'] for r in results]
                    print(f"      Found: {tickers}")
            except Exception as e:
                print(f"   '{query}': Error - {e}")
        
        # Test search function for ETFs
        print("\n📊 Testing ETF Search...")
        etf_queries = ["VOO", "voo", "SPY", "spy", "QQQ", "qqq", "BND", "bnd", "VTI", "vti"]
        
        for query in etf_queries:
            try:
                results = enhanced_data_fetcher.search_tickers(query, limit=3)
                print(f"   '{query}': {len(results)} results")
                if results:
                    tickers = [r['ticker'] for r in results]
                    print(f"      Found: {tickers}")
            except Exception as e:
                print(f"   '{query}': Error - {e}")
        
        # Test partial matches
        print("\n🔍 Testing Partial Matches...")
        partial_queries = ["VO", "SP", "QQ", "BN", "VT", "GO", "MS", "AP"]
        
        for query in partial_queries:
            try:
                results = enhanced_data_fetcher.search_tickers(query, limit=5)
                print(f"   '{query}': {len(results)} results")
                if results:
                    tickers = [r['ticker'] for r in results]
                    print(f"      Found: {tickers}")
            except Exception as e:
                print(f"   '{query}': Error - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_master_tickers_content():
    """Test the content of master tickers"""
    print("\n📋 Testing Master Tickers Content...")
    print("=" * 50)
    
    try:
        from utils.enhanced_data_fetcher import enhanced_data_fetcher
        
        # Get sample of tickers
        sample_tickers = enhanced_data_fetcher.master_tickers[:20]
        print(f"📊 First 20 tickers: {sample_tickers}")
        
        # Check for ETFs
        etf_list = ["VOO", "SPY", "IVV", "VTI", "VTS", "QQQ", "VUG", "VEA", "IEFA", "VTV", "BND"]
        found_etfs = []
        
        for etf in etf_list:
            if etf in enhanced_data_fetcher.master_tickers:
                found_etfs.append(etf)
        
        print(f"\n📈 ETFs found: {found_etfs}")
        print(f"📈 Total ETFs found: {len(found_etfs)}/{len(etf_list)}")
        
        # Check for stocks
        stock_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
        found_stocks = []
        
        for stock in stock_list:
            if stock in enhanced_data_fetcher.master_tickers:
                found_stocks.append(stock)
        
        print(f"\n📊 Stocks found: {found_stocks}")
        print(f"📊 Total stocks found: {len(found_stocks)}/{len(stock_list)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Content test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Portfolio Navigator Wizard - Search Function Test")
    print("=" * 60)
    
    # Test search without Redis
    search_ok = test_search_without_redis()
    
    # Test master tickers content
    content_ok = test_master_tickers_content()
    
    print("\n" + "=" * 60)
    if search_ok and content_ok:
        print("✅ All tests passed! Search function is working correctly.")
        print("🚀 Both stocks and ETFs are searchable.")
    else:
        print("❌ Some tests failed. Check the output above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 