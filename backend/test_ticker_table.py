#!/usr/bin/env python3
"""
Test script for ticker table functionality
"""

import json
import gzip
from utils.enhanced_data_fetcher import enhanced_data_fetcher
import redis

def test_ticker_table_data():
    """Test the ticker table data generation"""
    
    print("🧪 Testing Ticker Table Data Generation")
    print("=" * 50)
    
    # Get all tickers
    all_tickers = enhanced_data_fetcher.all_tickers
    print(f"📊 Total tickers: {len(all_tickers)}")
    
    # Initialize Redis connection
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
    
    ticker_data = []
    successful = 0
    missing = 0
    errors = 0
    
    # Test first 10 tickers
    test_tickers = all_tickers[:10]
    
    for ticker in test_tickers:
        try:
            # Get price data
            price_key = f"ticker_data:prices:{ticker}"
            price_raw = r.get(price_key)
            
            # Get sector/company data
            sector_key = f"ticker_data:sector:{ticker}"
            sector_raw = r.get(sector_key)
            
            if price_raw and sector_raw:
                # Parse price data
                price_dict = json.loads(gzip.decompress(price_raw).decode())
                prices = list(price_dict.values())
                dates = list(price_dict.keys())
                
                # Parse sector data
                sector_info = json.loads(sector_raw.decode())
                
                # Calculate data points and date range
                data_points = len(prices)
                first_date = dates[0] if dates else "N/A"
                last_date = dates[-1] if dates else "N/A"
                last_price = prices[-1] if prices else 0
                
                ticker_info = {
                    "ticker": ticker,
                    "companyName": sector_info.get("companyName", ticker),
                    "sector": sector_info.get("sector", "Unknown"),
                    "industry": sector_info.get("industry", "Unknown"),
                    "exchange": sector_info.get("exchange", "Unknown"),
                    "country": sector_info.get("country", "Unknown"),
                    "dataPoints": data_points,
                    "firstDate": first_date,
                    "lastDate": last_date,
                    "lastPrice": round(last_price, 2) if last_price else 0,
                    "status": "active"
                }
                
                ticker_data.append(ticker_info)
                successful += 1
                
                print(f"✅ {ticker}: {sector_info.get('companyName', ticker)} - {sector_info.get('sector', 'Unknown')} - ${last_price:.2f}")
                
            else:
                missing += 1
                print(f"❌ {ticker}: Missing data")
                
        except Exception as e:
            errors += 1
            print(f"💥 {ticker}: Error - {e}")
    
    print("\n📊 Test Results:")
    print(f"✅ Successful: {successful}")
    print(f"❌ Missing: {missing}")
    print(f"💥 Errors: {errors}")
    
    if ticker_data:
        print("\n📋 Sample Data:")
        sample = ticker_data[0]
        for key, value in sample.items():
            print(f"  {key}: {value}")
    
    return ticker_data

if __name__ == "__main__":
    test_ticker_table_data() 