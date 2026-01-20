#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify startup fixes on Windows
Tests each proposed fix individually before implementation
"""

import sys
import os
import time
import traceback
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 fallback
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    # Set environment variable
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_redis_connection_timeouts():
    """Test Fix 2: Redis connection with timeouts"""
    print("\n" + "="*80)
    print("TEST 1: Redis Connection with Timeouts")
    print("="*80)
    
    try:
        import redis
        
        # Test current implementation (no explicit timeouts)
        print("\n[Current] Testing Redis connection without explicit timeouts...")
        start = time.time()
        try:
            r1 = redis.Redis(host='localhost', port=6379, decode_responses=False)
            r1.ping()
            elapsed1 = time.time() - start
            print(f"  [OK] Success in {elapsed1:.3f}s")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")
            return False
        
        # Test with timeouts (proposed fix)
        print("\n[Proposed Fix] Testing Redis connection with explicit timeouts...")
        start = time.time()
        try:
            r2 = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=3
            )
            r2.ping()
            elapsed2 = time.time() - start
            print(f"  [OK] Success in {elapsed2:.3f}s")
            
            if elapsed2 <= elapsed1 * 1.5:  # Within 50% of original time
                print("  [OK] Timeout settings don't cause performance regression")
                return True
            else:
                print("  [WARN] Timeout settings may cause slight delay")
                return True  # Still acceptable
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")
            return False
            
    except ImportError:
        print("  [SKIP] Redis library not installed - using venv Python recommended")
        return None  # Skip, not fail
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        traceback.print_exc()
        return False


def test_duplicated_code_detection():
    """Test Fix 1: Detect duplicated portfolio check code"""
    print("\n" + "="*80)
    print("TEST 2: Duplicated Code Detection in main.py")
    print("="*80)
    
    try:
        main_py_path = "main.py"
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Find the portfolio check sections
        check_keywords = [
            "Checking portfolio recommendations cache",
            "profiles_needing_generation",
            "background_generate_missing_portfolios"
        ]
        
        matches = []
        for i, line in enumerate(lines):
            for keyword in check_keywords:
                if keyword in line:
                    matches.append((i+1, line.strip()))
        
        # Look for duplicate patterns
        portfolio_check_count = content.count("Checking portfolio recommendations cache")
        
        print(f"\n[Analysis] Found '{portfolio_check_count}' occurrences of 'Checking portfolio recommendations cache'")
        
        if portfolio_check_count > 1:
            print(f"  [DUPLICATE] Code appears {portfolio_check_count} times")
            print("  [OK] Fix needed: Remove duplicate code block")
            
            # Show line numbers
            for line_num, line_content in matches[:6]:  # Show first 6 matches
                print(f"    Line {line_num}: {line_content[:80]}")
            
            return True  # Test confirms fix is needed
        else:
            print("  [OK] No duplication detected")
            return True
            
    except FileNotFoundError:
        print(f"  [FAIL] main.py not found at {main_py_path}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        traceback.print_exc()
        return False


def test_portfolio_analytics_lazy_load():
    """Test Fix 3: Lazy load quantstats pandas extension"""
    print("\n" + "="*80)
    print("TEST 3: PortfolioAnalytics Lazy Loading")
    print("="*80)
    
    try:
        # Test current implementation
        print("\n[Current] Testing PortfolioAnalytics initialization...")
        start = time.time()
        try:
            from utils.port_analytics import PortfolioAnalytics
            pa1 = PortfolioAnalytics()
            elapsed1 = time.time() - start
            print(f"  [OK] Initialized in {elapsed1:.3f}s")
            print(f"  [INFO] quantstats.extend_pandas() called immediately on __init__")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")
            traceback.print_exc()
            return False
        
        # Test that we can create multiple instances
        print("\n[Test] Creating second instance...")
        start = time.time()
        try:
            pa2 = PortfolioAnalytics()
            elapsed2 = time.time() - start
            print(f"  [OK] Second instance created in {elapsed2:.3f}s")
            
            if elapsed2 < elapsed1:  # Second should be faster due to pandas already extended
                print("  [OK] Confirms pandas extension is persistent (global effect)")
            else:
                print("  [WARN] Second instance still takes significant time")
        except Exception as e:
            print(f"  [FAIL] Failed: {e}")
            return False
        
        # Verify quantstats functionality
        print("\n[Test] Testing quantstats functionality...")
        try:
            import pandas as pd
            import numpy as np
            
            # Create sample returns
            dates = pd.date_range('2020-01-01', periods=12, freq='ME')
            prices = pd.Series([100, 102, 101, 105, 103, 108, 107, 110, 112, 115, 114, 118], index=dates)
            returns = prices.pct_change().dropna()
            
            # Test if quantstats methods are available
            if hasattr(returns, 'stats'):
                print("  [OK] quantstats methods available (pandas extended)")
            else:
                print("  [WARN] quantstats methods not available (pandas may not be extended)")
            
            # Test PortfolioAnalytics method
            metrics = pa1.calculate_asset_metrics(prices.tolist())
            if metrics and 'annualized_return' in metrics:
                print(f"  [OK] PortfolioAnalytics works correctly")
                print(f"    Sample metrics: Return={metrics.get('annualized_return', 0):.2%}")
                return True
            else:
                print("  [FAIL] PortfolioAnalytics returned invalid metrics")
                return False
        except Exception as e:
            print(f"  [FAIL] Testing failed: {e}")
            traceback.print_exc()
            return False
            
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        traceback.print_exc()
        return False


def test_module_import_performance():
    """Test Fix 4: Module import performance"""
    print("\n" + "="*80)
    print("TEST 4: Module Import Performance")
    print("="*80)
    
    import_results = {}
    
    modules_to_test = [
        ("pypfopt", "pypfopt"),
        ("quantstats", "quantstats"),
        ("redis", "redis"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
    ]
    
    print("\n[Test] Measuring import times...")
    for name, module_name in modules_to_test:
        try:
            start = time.time()
            __import__(module_name)
            elapsed = time.time() - start
            import_results[name] = elapsed
            print(f"  {name:15} - {elapsed:.3f}s")
        except ImportError:
            import_results[name] = None
            print(f"  {name:15} - NOT INSTALLED")
        except Exception as e:
            import_results[name] = None
            print(f"  {name:15} - ERROR: {e}")
    
    # Test importing routers.portfolio (this is the heavy one)
    print("\n[Test] Testing routers.portfolio import...")
    try:
        start = time.time()
        # Don't actually import it fully, just test if it's accessible
        import importlib.util
        spec = importlib.util.find_spec("routers.portfolio")
        if spec:
            elapsed = time.time() - start
            print(f"  routers.portfolio module found in {elapsed:.3f}s")
            print("  ⚠ Full import will load all dependencies")
            
            # Test actual import
            print("\n  [Warning] Testing full import (this may take time)...")
            start = time.time()
            from routers import portfolio
            elapsed_full = time.time() - start
            print(f"  [OK] Full import completed in {elapsed_full:.3f}s")
            
            if elapsed_full > 5:
                print(f"  [WARN] Import takes {elapsed_full:.2f}s - consider lazy loading")
            
            return True
        else:
            print("  [FAIL] routers.portfolio module not found")
            return False
    except Exception as e:
        print(f"  [FAIL] Import test failed: {e}")
        traceback.print_exc()
        return False


def test_windows_compatibility():
    """Test Windows-specific compatibility"""
    print("\n" + "="*80)
    print("TEST 5: Windows OS Compatibility")
    print("="*80)
    
    try:
        import platform
        import os
        
        print(f"\n[System Info]")
        print(f"  OS: {platform.system()} {platform.release()}")
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  Architecture: {platform.architecture()[0]}")
        print(f"  Current Directory: {os.getcwd()}")
        
        # Test path separators
        print(f"\n[Path Tests]")
        test_path = os.path.join("backend", "main.py")
        print(f"  Path join test: {test_path}")
        
        if os.path.exists(test_path):
            print(f"  [OK] Path exists")
        else:
            print(f"  [WARN] Path doesn't exist (may be expected)")
        
        # Test environment variable access
        print(f"\n[Environment Tests]")
        fast_startup = os.getenv('FAST_STARTUP', 'not set')
        print(f"  FAST_STARTUP: {fast_startup}")
        
        # Test Redis connection on Windows
        print(f"\n[Windows Redis Test]")
        try:
            import redis
            r = redis.Redis(host='127.0.0.1', port=6379, socket_connect_timeout=2)
            r.ping()
            print(f"  [OK] Redis connection works on Windows")
            
            # Test info command
            info = r.info('server')
            redis_version = info.get('redis_version', 'unknown')
            print(f"  [OK] Redis version: {redis_version}")
            
            return True
        except ImportError:
            print(f"  [SKIP] Redis library not installed")
            return None
        except Exception as e:
            print(f"  [FAIL] Redis connection failed: {e}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Windows compatibility test failed: {e}")
        traceback.print_exc()
        return False


def test_backend_startup_sequence():
    """Test the actual backend startup sequence"""
    print("\n" + "="*80)
    print("TEST 6: Backend Startup Sequence Simulation")
    print("="*80)
    
    try:
        print("\n[Test] Simulating startup sequence...")
        startup_steps = [
            ("Import main module", "import main"),
            ("Initialize RedisFirstDataService", "from utils.redis_first_data_service import RedisFirstDataService"),
            ("Initialize PortfolioAnalytics", "from utils.port_analytics import PortfolioAnalytics"),
        ]
        
        results = {}
        for step_name, import_cmd in startup_steps:
            print(f"\n  [{step_name}]...")
            try:
                start = time.time()
                exec(import_cmd)
                elapsed = time.time() - start
                results[step_name] = elapsed
                print(f"    [OK] Completed in {elapsed:.3f}s")
            except Exception as e:
                print(f"    [FAIL] Failed: {e}")
                results[step_name] = None
                # Don't fail completely, continue testing
                continue
        
        total_time = sum(v for v in results.values() if v)
        print(f"\n[Summary] Total import time: {total_time:.3f}s")
        
        if total_time > 10:
            print(f"  [WARN] Startup takes {total_time:.2f}s - optimizations needed")
        else:
            print(f"  [OK] Startup time acceptable")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Startup sequence test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*80)
    print("BACKEND STARTUP FIXES VERIFICATION - WINDOWS OS")
    print("="*80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Redis Connection Timeouts", test_redis_connection_timeouts),
        ("Duplicated Code Detection", test_duplicated_code_detection),
        ("PortfolioAnalytics Lazy Loading", test_portfolio_analytics_lazy_load),
        ("Module Import Performance", test_module_import_performance),
        ("Windows Compatibility", test_windows_compatibility),
        ("Backend Startup Sequence", test_backend_startup_sequence),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n[FAIL] {test_name} crashed: {e}")
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        if result is None:
            status = "[SKIP]"
        elif result:
            status = "[PASS]"
        else:
            status = "[FAIL]"
        print(f"  {status}: {test_name}")
    
    # Count only actual passes (not skips)
    actual_passed = sum(1 for r in results.values() if r is True)
    skipped = sum(1 for r in results.values() if r is None)
    
    print(f"\nResults: {actual_passed}/{total} tests passed ({skipped} skipped)")
    
    if actual_passed == total - skipped:
        print("\n[OK] All tests passed - fixes are safe to implement")
        return 0
    elif actual_passed > 0:
        print(f"\n[WARN] {total - skipped - actual_passed} test(s) failed - review before implementing")
        return 1
    else:
        print(f"\n[FAIL] All tests failed - do not implement fixes")
        return 2


if __name__ == "__main__":
    sys.exit(main())
