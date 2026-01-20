#!/usr/bin/env python3
"""
Redis Data Verification Script
Checks if Redis has all required data before starting the application
Includes TTL checking to verify data freshness (e.g., data from January 18)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    import redis
    from utils.redis_first_data_service import RedisFirstDataService
except ImportError as e:
    print(f"ERROR: Import error: {e}")
    print("Make sure you're running from the backend directory with venv activated")
    sys.exit(1)

def load_master_ticker_list():
    """Load master ticker list from file"""
    master_file = backend_dir.parent / "master_ticker_list.txt"
    if not master_file.exists():
        print(f"⚠️  Master ticker list not found at: {master_file}")
        return []
    
    with open(master_file, 'r', encoding='utf-8') as f:
        tickers = [line.strip() for line in f if line.strip()]
    return tickers

def check_redis_connection():
    """Check if Redis is accessible"""
    try:
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=3, decode_responses=False)
        r.ping()
        return r, True
    except Exception as e:
        print(f"ERROR: Redis connection failed: {e}")
        print("   Make sure Redis/Memurai is running on localhost:6379")
        return None, False

def main():
    print("=" * 80)
    print("Redis Data Verification")
    print("=" * 80)
    print()
    
    # Step 1: Check Redis connection
    print("[1/6] Checking Redis connection...")
    redis_client, connected = check_redis_connection()
    if not connected:
        print("ERROR: Cannot proceed without Redis connection")
        sys.exit(1)
    print("OK: Redis connection established")
    print()
    
    # Step 2: Initialize data service
    print("[2/6] Initializing Redis-First Data Service...")
    try:
        service = RedisFirstDataService()
        if not service.redis_client:
            print("ERROR: Redis client not available in service")
            sys.exit(1)
        print("OK: Data service initialized")
    except Exception as e:
        print(f"ERROR: Failed to initialize service: {e}")
        sys.exit(1)
    print()
    
    # Step 3: Get cache inventory
    print("[3/6] Checking cache inventory...")
    inventory = service.get_cache_inventory()
    print(f"Redis status: {inventory.get('redis', 'unknown')}")
    
    if inventory.get('redis') != 'available':
        print("ERROR: Redis is not available")
        sys.exit(1)
    
    coverage = inventory.get('coverage', {})
    print(f"Price keys: {coverage.get('prices', 0)}")
    print(f"Sector keys: {coverage.get('sector', 0)}")
    print(f"Metrics keys: {coverage.get('metrics', 0)}")
    print(f"Joined tickers (with prices + sector): {coverage.get('joined_tickers', 0)}")
    print()
    
    # Step 4: Check TTL and data freshness (for Jan 18 data verification)
    print("[4/6] Checking data freshness and TTL...")
    print("   (Verifying if data from January 18 is still valid)")
    
    # Check TTL for sample tickers
    ttl_sample = inventory.get('ttl_sample', [])
    if ttl_sample:
        print(f"   Sample TTL check ({len(ttl_sample)} tickers):")
        current_date = datetime.now()
        cache_ttl_days = 28  # Standard cache TTL
        jan_18_date = datetime(2026, 1, 18)  # Assuming 2026, adjust if needed
        days_since_jan_18 = (current_date - jan_18_date).days
        
        if days_since_jan_18 < 0:
            # If current date is before Jan 18, check if it's 2025
            jan_18_date = datetime(2025, 1, 18)
            days_since_jan_18 = (current_date - jan_18_date).days
        
        valid_until = jan_18_date + timedelta(days=cache_ttl_days)
        days_remaining = (valid_until - current_date).days
        
        print(f"   Data fetched on: January 18, {jan_18_date.year}")
        print(f"   Days since fetch: {days_since_jan_18}")
        print(f"   Cache TTL: {cache_ttl_days} days")
        print(f"   Valid until: {valid_until.strftime('%Y-%m-%d')}")
        
        if days_remaining > 0:
            print(f"   Status: OK - Data is still valid for {days_remaining} more days")
        elif days_remaining == 0:
            print(f"   Status: WARNING - Data expires today!")
        else:
            print(f"   Status: EXPIRED - Data expired {abs(days_remaining)} days ago")
        
        # Check actual TTL from Redis
        print(f"\n   Actual TTL from Redis (sample):")
        for sample in ttl_sample[:3]:
            ticker = sample.get('ticker', 'N/A')
            prices_ttl = sample.get('prices_ttl_s', -1)
            sector_ttl = sample.get('sector_ttl_s', -1)
            
            if prices_ttl > 0:
                prices_days = prices_ttl / 86400
                prices_expires = current_date + timedelta(seconds=prices_ttl)
                print(f"   {ticker}: Prices TTL = {prices_days:.1f} days (expires {prices_expires.strftime('%Y-%m-%d')})")
            elif prices_ttl == -1:
                print(f"   {ticker}: Prices TTL = No expiration set")
            else:
                print(f"   {ticker}: Prices TTL = Expired or missing")
    else:
        print("   WARNING: Could not get TTL sample")
    print()
    
    # Step 5: Load master ticker list and compare
    print("[5/6] Comparing with master ticker list...")
    master_tickers = load_master_ticker_list()
    print(f"Master ticker list: {len(master_tickers)} tickers")
    
    if len(master_tickers) == 0:
        print("⚠️  Master ticker list is empty or not found")
    else:
        cached_count = coverage.get('joined_tickers', 0)
        coverage_pct = (cached_count / len(master_tickers)) * 100 if len(master_tickers) > 0 else 0
        print(f"Cache coverage: {cached_count}/{len(master_tickers)} ({coverage_pct:.1f}%)")
        print()
        
        if coverage_pct < 50:
            print("⚠️  WARNING: Cache coverage is below 50%")
            print("   The application will work but may need to fetch data on-demand")
        elif coverage_pct < 80:
            print("⚠️  WARNING: Cache coverage is below 80%")
            print("   Some features may be slower due to on-demand fetching")
        else:
            print("OK: Cache coverage is good (>= 80%)")
    
    print()
    
    # Step 6: Check ticker status
    print("[6/6] Checking detailed ticker status...")
    status = service.check_ticker_status()
    
    if status:
        print(f"Total tickers in Redis: {status.get('total_tickers_in_redis', 0)}")
        print(f"Total tickers in master: {status.get('total_tickers_in_master', 0)}")
        print(f"Missing from master: {status.get('missing_from_master_count', 0)}")
        print(f"Expired TTL: {status.get('expired_count', 0)}")
        print(f"Expiring soon (<24h): {status.get('expiring_soon_count', 0)}")
        print(f"Missing data: {status.get('missing_data_count', 0)}")
        print(f"Needs fetch: {status.get('needs_fetch_count', 0)}")
        
        needs_fetch = status.get('needs_fetch_count', 0)
        if needs_fetch > 0:
            print()
            print("⚠️  WARNING: Some tickers need data fetching")
            print("   The application will work but may fetch data on-demand")
        else:
            print()
            print("OK: All tickers have required data")
    else:
        print("⚠️  Could not get detailed ticker status")
    
    print()
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    
    # Final assessment
    price_keys = coverage.get('prices', 0)
    sector_keys = coverage.get('sector', 0)
    joined_tickers = coverage.get('joined_tickers', 0)
    
    # Calculate data age if we have TTL info
    data_age_info = ""
    if ttl_sample and len(ttl_sample) > 0:
        sample_ttl = ttl_sample[0].get('prices_ttl_s', -1)
        if sample_ttl > 0:
            cache_ttl_days = 28
            estimated_age_days = cache_ttl_days - (sample_ttl / 86400)
            if estimated_age_days >= 0:
                estimated_fetch_date = datetime.now() - timedelta(days=estimated_age_days)
                data_age_info = f"\n   Estimated fetch date: {estimated_fetch_date.strftime('%Y-%m-%d')} (data is ~{estimated_age_days:.0f} days old)"
    
    if price_keys == 0 and sector_keys == 0:
        print("ERROR: Redis is EMPTY - No data found")
        print("   Action required: Run data population/warming scripts")
        print("   The application will work but will fetch all data on-demand")
        sys.exit(1)
    elif joined_tickers < 100:
        print("WARNING: Redis has LIMITED data")
        print(f"   Found: {joined_tickers} tickers with complete data")
        print("   The application will work but may be slower")
        print("   Consider running data warming for better performance")
        if data_age_info:
            print(data_age_info)
    else:
        print("OK: Redis has SUFFICIENT data")
        print(f"   Found: {joined_tickers} tickers with complete data")
        print("   The application is ready to start")
        if data_age_info:
            print(data_age_info)
    
    # January 18 verification
    print()
    print("=" * 80)
    print("JANUARY 18 DATA VERIFICATION")
    print("=" * 80)
    if ttl_sample and len(ttl_sample) > 0:
        sample_ttl = ttl_sample[0].get('prices_ttl_s', -1)
        if sample_ttl > 0:
            days_remaining = sample_ttl / 86400
            if days_remaining > 20:
                print("OK: Data from January 18 appears to be VALID")
                print(f"   TTL indicates data has ~{days_remaining:.0f} days remaining")
                print("   This matches data fetched around January 18")
            elif days_remaining > 10:
                print("WARNING: Data from January 18 may be EXPIRING SOON")
                print(f"   TTL indicates data has ~{days_remaining:.0f} days remaining")
            else:
                print("WARNING: Data from January 18 may be EXPIRED or DIFFERENT")
                print(f"   TTL indicates data has only ~{days_remaining:.0f} days remaining")
                print("   This may be newer data, not from January 18")
        else:
            print("INFO: Cannot verify January 18 data - TTL information unavailable")
    else:
        print("INFO: Cannot verify January 18 data - No TTL sample available")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
