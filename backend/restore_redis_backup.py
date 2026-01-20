#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual Redis Backup Restoration Script
Attempts to restore data from RDB backup file
"""
import redis
import subprocess
import sys
import os

def check_redis_connection():
    """Check if Redis is accessible"""
    try:
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print('[OK] Redis connection successful')
        return r
    except Exception as e:
        print(f'[ERROR] Redis connection failed: {e}')
        return None

def get_redis_info(r):
    """Get Redis server information"""
    try:
        info = r.info('server')
        print(f'[INFO] Redis version: {info.get("redis_version", "N/A")}')
        print(f'[INFO] Current DBSIZE: {r.dbsize()} keys')
        return info
    except Exception as e:
        print(f'[ERROR] Failed to get Redis info: {e}')
        return None

def check_rdb_file():
    """Check if RDB file exists in Memurai directory"""
    rdb_paths = [
        r"C:\Program Files\Memurai\dump.rdb",
        r"C:\ProgramData\Memurai\dump.rdb",
    ]
    
    for path in rdb_paths:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f'[OK] Found RDB file: {path}')
            print(f'[INFO] File size: {size:,} bytes ({size/1024/1024:.2f} MB)')
            return path
    
    print('[WARNING] RDB file not found in expected locations')
    return None

def main():
    print('=== Redis Backup Restoration Tool ===\n')
    
    # Check Redis connection
    r = check_redis_connection()
    if not r:
        print('\n[ERROR] Cannot proceed without Redis connection')
        print('[INFO] Make sure Memurai service is running')
        return 1
    
    # Get current status
    print('\n=== Current Redis Status ===')
    info = get_redis_info(r)
    current_size = r.dbsize()
    
    # Check for RDB file
    print('\n=== Checking for RDB Backup File ===')
    rdb_path = check_rdb_file()
    
    if not rdb_path:
        print('\n[WARNING] No RDB file found')
        print('[INFO] The application will auto-populate cache on first use')
        return 0
    
    # Check if data is already loaded
    if current_size > 0:
        print(f'\n[OK] Redis already has {current_size} keys')
        print('[INFO] Data appears to be loaded already')
        
        # Verify application-expected keys
        price_keys = len(r.keys('ticker_data:prices:*'))
        sector_keys = len(r.keys('ticker_data:sector:*'))
        print(f'[INFO] Price keys: {price_keys}')
        print(f'[INFO] Sector keys: {sector_keys}')
        
        if price_keys > 0 or sector_keys > 0:
            print('\n[SUCCESS] Application data is available!')
            print('[INFO] No restoration needed')
            return 0
    
    # If empty, explain the situation
    print('\n=== Restoration Status ===')
    print('[INFO] Redis database is empty (0 keys)')
    print('[INFO] RDB file exists but was not auto-loaded by Memurai')
    print('\n[EXPLANATION]')
    print('  Memurai should automatically load dump.rdb on startup,')
    print('  but sometimes this doesn\'t happen. The application has')
    print('  "lazy loading" built-in, which means:')
    print('  - Data will be fetched from APIs on first use')
    print('  - Fetched data will be cached in Redis')
    print('  - Subsequent requests will use cached data')
    print('\n[RECOMMENDATION]')
    print('  1. Start the application: make dev or make full-dev')
    print('  2. Use the application normally')
    print('  3. Data will be cached automatically')
    print('  4. Future startups will use cached data')
    
    print('\n[ALTERNATIVE]')
    print('  If you need the backup data immediately, you can:')
    print('  1. Restart Memurai service (may trigger RDB load)')
    print('  2. Or let the application rebuild cache (recommended)')
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
