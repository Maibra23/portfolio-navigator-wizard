#!/usr/bin/env python3
"""
Comprehensive Redis Content Analysis
Displays all cached data in organized tables with categories and statistics
"""

import redis
import json
import gzip
import pandas as pd
from datetime import datetime
from collections import defaultdict
from tabulate import tabulate
import sys

def analyze_redis_content():
    """Analyze all Redis content and display in organized tables"""
    
    print("🔍 COMPREHENSIVE REDIS CONTENT ANALYSIS")
    print("=" * 60)
    
    # Connect to Redis
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=False)
        r.ping()
        print("✅ Redis connection established\n")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return
    
    # Get all keys
    all_keys = r.keys("*")
    print(f"📊 Total Redis keys found: {len(all_keys)}")
    
    # Categorize keys
    key_categories = defaultdict(list)
    for key in all_keys:
        key_str = key.decode('utf-8')
        if key_str.startswith('ticker_data:prices:'):
            key_categories['price_data'].append(key_str)
        elif key_str.startswith('ticker_data:sector:'):
            key_categories['sector_data'].append(key_str)
        elif key_str.startswith('ticker_data:company_info:'):
            key_categories['company_info'].append(key_str)
        elif key_str.startswith('monthly_adj_close:'):
            key_categories['old_format'].append(key_str)
        else:
            key_categories['other'].append(key_str)
    
    # Display key categories summary
    print("\n📋 KEY CATEGORIES SUMMARY:")
    print("-" * 40)
    summary_data = []
    for category, keys in key_categories.items():
        summary_data.append([
            category.replace('_', ' ').title(),
            len(keys),
            f"{len(keys)/len(all_keys)*100:.1f}%" if all_keys else "0%"
        ])
    
    print(tabulate(summary_data, headers=['Category', 'Count', 'Percentage'], tablefmt='grid'))
    
    # Analyze each category in detail
    print("\n" + "=" * 60)
    
    # 1. PRICE DATA ANALYSIS
    if key_categories['price_data']:
        print("\n💰 PRICE DATA ANALYSIS")
        print("-" * 30)
        analyze_price_data(r, key_categories['price_data'])
    
    # 2. SECTOR DATA ANALYSIS
    if key_categories['sector_data']:
        print("\n🏢 SECTOR DATA ANALYSIS")
        print("-" * 30)
        analyze_sector_data(r, key_categories['sector_data'])
    
    # 3. COMPANY INFO ANALYSIS
    if key_categories['company_info']:
        print("\n🏛️ COMPANY INFO ANALYSIS")
        print("-" * 30)
        analyze_company_info(r, key_categories['company_info'])
    
    # 4. OLD FORMAT ANALYSIS
    if key_categories['old_format']:
        print("\n⚠️ OLD FORMAT DATA (DEPRECATED)")
        print("-" * 30)
        analyze_old_format_data(r, key_categories['old_format'])
    
    # 5. OTHER KEYS
    if key_categories['other']:
        print("\n🔧 OTHER KEYS")
        print("-" * 30)
        analyze_other_keys(r, key_categories['other'])
    
    # 6. COMPREHENSIVE TICKER LIST
    print("\n📋 COMPREHENSIVE TICKER LIST")
    print("-" * 30)
    display_comprehensive_ticker_list(r, key_categories)
    
    # 7. DATA QUALITY SUMMARY
    print("\n📊 DATA QUALITY SUMMARY")
    print("-" * 30)
    display_data_quality_summary(r, key_categories)

def analyze_price_data(r, price_keys):
    """Analyze price data keys"""
    if not price_keys:
        print("No price data found")
        return
    
    # Extract tickers
    tickers = [key.replace('ticker_data:prices:', '') for key in price_keys]
    
    # Sample analysis
    sample_tickers = tickers[:5]
    sample_data = []
    
    for ticker in sample_tickers:
        try:
            key = f"ticker_data:prices:{ticker}"
            raw_data = r.get(key)
            if raw_data:
                data_dict = json.loads(gzip.decompress(raw_data).decode())
                data_points = len(data_dict)
                first_date = min(data_dict.keys()) if data_dict else "N/A"
                last_date = max(data_dict.keys()) if data_dict else "N/A"
                sample_data.append([ticker, data_points, first_date, last_date])
        except Exception as e:
            sample_data.append([ticker, f"Error: {e}", "N/A", "N/A"])
    
    print(f"📈 Total tickers with price data: {len(tickers)}")
    print(f"📅 Sample data (first 5 tickers):")
    print(tabulate(sample_data, headers=['Ticker', 'Data Points', 'First Date', 'Last Date'], tablefmt='grid'))
    
    # Date range analysis
    all_dates = set()
    for ticker in tickers[:10]:  # Sample first 10 for date analysis
        try:
            key = f"ticker_data:prices:{ticker}"
            raw_data = r.get(key)
            if raw_data:
                data_dict = json.loads(gzip.decompress(raw_data).decode())
                all_dates.update(data_dict.keys())
        except:
            continue
    
    if all_dates:
        sorted_dates = sorted(all_dates)
        print(f"\n📅 Date range in sample: {sorted_dates[0]} to {sorted_dates[-1]}")
        print(f"📊 Total unique dates: {len(all_dates)}")

def analyze_sector_data(r, sector_keys):
    """Analyze sector data keys"""
    if not sector_keys:
        print("No sector data found")
        return
    
    # Extract tickers
    tickers = [key.replace('ticker_data:sector:', '') for key in sector_keys]
    
    # Sector distribution
    sector_counts = defaultdict(int)
    industry_counts = defaultdict(int)
    exchange_counts = defaultdict(int)
    
    sample_data = []
    
    for ticker in tickers[:10]:  # Sample first 10
        try:
            key = f"ticker_data:sector:{ticker}"
            raw_data = r.get(key)
            if raw_data:
                sector_info = json.loads(raw_data.decode())
                sector = sector_info.get('sector', 'Unknown')
                industry = sector_info.get('industry', 'Unknown')
                exchange = sector_info.get('exchange', 'Unknown')
                country = sector_info.get('country', 'Unknown')
                
                sector_counts[sector] += 1
                industry_counts[industry] += 1
                exchange_counts[exchange] += 1
                
                sample_data.append([ticker, sector, industry, exchange, country])
        except Exception as e:
            sample_data.append([ticker, f"Error: {e}", "N/A", "N/A", "N/A"])
    
    print(f"🏢 Total tickers with sector data: {len(tickers)}")
    print(f"📊 Sample sector data (first 10 tickers):")
    print(tabulate(sample_data, headers=['Ticker', 'Sector', 'Industry', 'Exchange', 'Country'], tablefmt='grid'))
    
    # Top sectors
    print(f"\n🏆 Top 5 Sectors:")
    top_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    sector_table = [[sector, count] for sector, count in top_sectors]
    print(tabulate(sector_table, headers=['Sector', 'Count'], tablefmt='grid'))

def analyze_company_info(r, company_keys):
    """Analyze company info keys"""
    if not company_keys:
        print("No company info found")
        return
    
    # Extract tickers
    tickers = [key.replace('ticker_data:company_info:', '') for key in company_keys]
    
    print(f"🏛️ Total tickers with company info: {len(tickers)}")
    
    # Sample company names
    sample_data = []
    for ticker in tickers[:10]:
        try:
            key = f"ticker_data:company_info:{ticker}"
            raw_data = r.get(key)
            if raw_data:
                company_info = json.loads(raw_data.decode())
                company_name = company_info.get('name', 'Unknown')
                sample_data.append([ticker, company_name])
        except Exception as e:
            sample_data.append([ticker, f"Error: {e}"])
    
    print(f"📊 Sample company names (first 10 tickers):")
    print(tabulate(sample_data, headers=['Ticker', 'Company Name'], tablefmt='grid'))

def analyze_old_format_data(r, old_keys):
    """Analyze old format data"""
    if not old_keys:
        print("No old format data found")
        return
    
    # Extract tickers
    tickers = [key.replace('monthly_adj_close:', '') for key in old_keys]
    
    print(f"⚠️ Total tickers in old format: {len(tickers)}")
    print(f"📋 Old format tickers: {', '.join(tickers[:20])}{'...' if len(tickers) > 20 else ''}")
    print("💡 Note: These are deprecated and should be cleaned up")

def analyze_other_keys(r, other_keys):
    """Analyze other keys"""
    if not other_keys:
        print("No other keys found")
        return
    
    print(f"🔧 Total other keys: {len(other_keys)}")
    for key in other_keys[:10]:
        print(f"  - {key}")
    if len(other_keys) > 10:
        print(f"  ... and {len(other_keys) - 10} more")

def display_comprehensive_ticker_list(r, key_categories):
    """Display comprehensive ticker list with data availability"""
    
    # Get all unique tickers
    all_tickers = set()
    
    # From price data
    price_tickers = {key.replace('ticker_data:prices:', '') for key in key_categories['price_data']}
    all_tickers.update(price_tickers)
    
    # From sector data
    sector_tickers = {key.replace('ticker_data:sector:', '') for key in key_categories['sector_data']}
    all_tickers.update(sector_tickers)
    
    # From company info
    company_tickers = {key.replace('ticker_data:company_info:', '') for key in key_categories['company_info']}
    all_tickers.update(company_tickers)
    
    # From old format
    old_tickers = {key.replace('monthly_adj_close:', '') for key in key_categories['old_format']}
    all_tickers.update(old_tickers)
    
    sorted_tickers = sorted(all_tickers)
    
    print(f"📋 Total unique tickers: {len(sorted_tickers)}")
    
    # Create availability matrix
    availability_data = []
    for ticker in sorted_tickers[:20]:  # Show first 20
        has_price = ticker in price_tickers
        has_sector = ticker in sector_tickers
        has_company = ticker in company_tickers
        has_old = ticker in old_tickers
        
        availability_data.append([
            ticker,
            "✅" if has_price else "❌",
            "✅" if has_sector else "❌",
            "✅" if has_company else "❌",
            "⚠️" if has_old else "✅"
        ])
    
    print(f"📊 Data availability (first 20 tickers):")
    print(tabulate(availability_data, headers=['Ticker', 'Price', 'Sector', 'Company', 'Format'], tablefmt='grid'))
    
    if len(sorted_tickers) > 20:
        print(f"\n... and {len(sorted_tickers) - 20} more tickers")
    
    # Summary statistics
    print(f"\n📈 AVAILABILITY SUMMARY:")
    print(f"  • Tickers with price data: {len(price_tickers)}")
    print(f"  • Tickers with sector data: {len(sector_tickers)}")
    print(f"  • Tickers with company info: {len(company_tickers)}")
    print(f"  • Tickers in old format: {len(old_tickers)}")

def display_data_quality_summary(r, key_categories):
    """Display data quality summary"""
    
    print("📊 DATA QUALITY SUMMARY:")
    print("-" * 30)
    
    # Calculate coverage
    price_tickers = {key.replace('ticker_data:prices:', '') for key in key_categories['price_data']}
    sector_tickers = {key.replace('ticker_data:sector:', '') for key in key_categories['sector_data']}
    company_tickers = {key.replace('ticker_data:company_info:', '') for key in key_categories['company_info']}
    
    all_tickers = price_tickers | sector_tickers | company_tickers
    
    if all_tickers:
        price_coverage = len(price_tickers) / len(all_tickers) * 100
        sector_coverage = len(sector_tickers) / len(all_tickers) * 100
        company_coverage = len(company_tickers) / len(all_tickers) * 100
        
        quality_data = [
            ["Price Data", len(price_tickers), f"{price_coverage:.1f}%"],
            ["Sector Data", len(sector_tickers), f"{sector_coverage:.1f}%"],
            ["Company Info", len(company_tickers), f"{company_coverage:.1f}%"],
            ["Total Unique", len(all_tickers), "100%"]
        ]
        
        print(tabulate(quality_data, headers=['Data Type', 'Count', 'Coverage'], tablefmt='grid'))
    
    # Memory usage estimation
    total_memory = 0
    for key in r.keys("*"):
        try:
            memory = r.memory_usage(key)
            if memory:
                total_memory += memory
        except:
            continue
    
    print(f"\n💾 Estimated memory usage: {total_memory / (1024*1024):.2f} MB")
    
    # TTL information
    print(f"\n⏰ Cache TTL: 28 days (672 hours)")
    print(f"🔄 Auto-refresh: Enabled when coverage < 80%")

if __name__ == "__main__":
    try:
        analyze_redis_content()
    except KeyboardInterrupt:
        print("\n\n⏹️ Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc() 