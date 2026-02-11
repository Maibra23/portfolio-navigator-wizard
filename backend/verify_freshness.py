#!/usr/bin/env python3
"""Quick verification of freshness values"""
import json
import sys
import urllib.request

try:
    url = "http://localhost:8000/api/v1/portfolio/ticker-table/data"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
    
    tickers = data.get('tickers', [])
    print(f"✅ Total tickers: {len(tickers)}")
    print("\n📊 Sample freshness values:")
    print("-" * 70)
    for t in tickers[:10]:
        ticker = t.get('ticker', 'N/A')
        freshness = t.get('dataFreshness', 'N/A')
        last_date = t.get('lastDate', 'N/A')
        print(f"  {ticker:15} | Freshness: {freshness:15} | Last Date: {last_date}")
    
    print("\n📈 Freshness distribution:")
    print("-" * 70)
    from collections import Counter
    dist = Counter([t.get('dataFreshness', 'unknown') for t in tickers])
    for k, v in sorted(dist.items()):
        print(f"  {k:15}: {v:4} tickers")
    
    # Check for errors
    unknown_count = dist.get('unknown', 0)
    error_count = dist.get('error', 0)
    
    print("\n✅ Verification Results:")
    print("-" * 70)
    if unknown_count == 0 and error_count == 0:
        print("  ✅ No 'unknown' or 'error' freshness values found!")
    else:
        print(f"  ⚠️  Found {unknown_count} 'unknown' and {error_count} 'error' values")
        if unknown_count > 0 or error_count > 0:
            print("\n  Tickers with issues:")
            for t in tickers:
                if t.get('dataFreshness') in ['unknown', 'error']:
                    print(f"    - {t.get('ticker')}: {t.get('dataFreshness')} (last_date: {t.get('lastDate')})")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

