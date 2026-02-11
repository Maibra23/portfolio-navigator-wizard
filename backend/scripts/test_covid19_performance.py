#!/usr/bin/env python3
"""
COVID-19 Stress Test Performance Analysis
Tests the 2020 COVID-19 Crash scenario with an optimized moderate portfolio
and measures timing at each step to identify bottlenecks.
"""

import sys
import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1/portfolio"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")

def print_section(text: str):
    print(f"\n{Colors.CYAN}{Colors.BOLD}▶ {text}{Colors.RESET}")

def print_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message: str):
    print(f"  {message}")

def print_timing(step: str, elapsed: float, details: str = ""):
    color = Colors.GREEN if elapsed < 2.0 else Colors.YELLOW if elapsed < 5.0 else Colors.RED
    print(f"  {color}⏱️  {step}: {elapsed:.3f}s{Colors.RESET}", end="")
    if details:
        print(f" {details}")
    else:
        print()

def get_optimized_moderate_portfolio() -> tuple[Dict, float]:
    """Get optimized moderate portfolio from triple optimization endpoint"""
    print_section("Step 1: Getting Optimized Moderate Portfolio")
    
    # Use a typical moderate portfolio
    user_tickers = ["AAPL", "MSFT", "JNJ", "PG", "V"]
    user_weights = {"AAPL": 0.25, "MSFT": 0.25, "JNJ": 0.20, "PG": 0.15, "V": 0.15}
    
    payload = {
        "user_tickers": user_tickers,
        "user_weights": user_weights,
        "risk_profile": "moderate",
        "optimization_type": "max_sharpe",
        "max_eligible_tickers": 20,
        "include_efficient_frontier": False,
        "include_random_portfolios": False,
        "use_combined_strategy": True,
        "attempt_market_exploration": True
    }
    
    try:
        start = time.time()
        print_info(f"Requesting optimization for {len(user_tickers)} tickers...")
        response = requests.post(f"{API_BASE}/optimization/triple", json=payload, timeout=60)
        elapsed = time.time() - start
        print_timing("Optimization request", elapsed)
        
        if response.status_code != 200:
            print_error(f"Optimization failed: HTTP {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return None, elapsed
        
        data = response.json()
        
        # Prefer market-optimized, then weights-optimized, then current
        portfolio = None
        source = None
        for key in ["market_optimized_portfolio", "weights_optimized_portfolio", "current_portfolio"]:
            if data.get(key) and data[key].get("weights"):
                portfolio = data[key]
                source = key.replace("_portfolio", "").replace("_", " ")
                break
        
        if not portfolio:
            print_error("No valid portfolio found in optimization response")
            return None, elapsed
        
        weights = portfolio["weights"]
        print_success(f"Got {source} portfolio with {len(weights)} tickers")
        print_info(f"Tickers: {', '.join(list(weights.keys())[:5])}{'...' if len(weights) > 5 else ''}")
        
        return {
            "tickers": list(weights.keys()),
            "weights": weights,
            "capital": 10000,
            "risk_profile": "moderate",
            "source": source
        }, elapsed
        
    except Exception as e:
        print_error(f"Error getting optimized portfolio: {e}")
        import traceback
        traceback.print_exc()
        return None, 0.0

def run_covid19_stress_test(portfolio: Dict) -> tuple[bool, Dict, float]:
    """Run COVID-19 stress test and measure timing"""
    print_section("Step 2: Running COVID-19 Stress Test")
    
    payload = {
        "tickers": portfolio["tickers"],
        "weights": portfolio["weights"],
        "scenarios": ["covid19"],
        "capital": portfolio["capital"],
        "risk_profile": portfolio["risk_profile"],
    }
    
    try:
        start = time.time()
        print_info(f"Requesting stress test for {len(portfolio['tickers'])} tickers...")
        response = requests.post(f"{API_BASE}/stress-test", json=payload, timeout=120)
        elapsed = time.time() - start
        print_timing("Stress test request", elapsed)
        
        if response.status_code != 200:
            print_error(f"Stress test failed: HTTP {response.status_code}")
            print_info(f"Response: {response.text[:300]}")
            return False, {}, elapsed
        
        data = response.json()
        
        # Extract timing from response if available
        processing_time = data.get("processing_time_seconds", elapsed)
        
        if "covid19" not in data.get("scenarios", {}):
            print_error("COVID-19 scenario not in response")
            return False, data, elapsed
        
        scenario_data = data["scenarios"]["covid19"]
        metrics = scenario_data.get("metrics", {})
        
        print_success(f"Stress test completed")
        print_info(f"Processing time (backend): {processing_time:.3f}s")
        print_info(f"Total return: {metrics.get('total_return', 0)*100:.2f}%")
        print_info(f"Max drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")
        print_info(f"Resilience score: {data.get('resilience_score', 0):.1f}/100")
        
        return True, data, elapsed
        
    except Exception as e:
        print_error(f"Error running stress test: {e}")
        import traceback
        traceback.print_exc()
        return False, {}, 0.0

def analyze_performance(optimization_time: float, stress_test_time: float, total_time: float):
    """Analyze performance and provide recommendations"""
    print_section("Performance Analysis")
    
    print_info(f"Optimization time: {optimization_time:.3f}s ({optimization_time/total_time*100:.1f}%)")
    print_info(f"Stress test time: {stress_test_time:.3f}s ({stress_test_time/total_time*100:.1f}%)")
    print_info(f"Total time: {total_time:.3f}s")
    
    print_section("Optimization Opportunities")
    
    if stress_test_time > 10.0:
        print_info("🔴 Stress test is slow (>10s). Potential optimizations:")
        print_info("   1. Cache portfolio value calculations")
        print_info("   2. Parallelize data retrieval for multiple tickers")
        print_info("   3. Reduce Monte Carlo simulations (currently 10,000)")
        print_info("   4. Skip normal period calculation if not needed")
        print_info("   5. Batch Redis data requests")
    
    if stress_test_time > 5.0 and stress_test_time <= 10.0:
        print_info("🟡 Stress test is moderate (5-10s). Consider:")
        print_info("   1. Cache crisis period calculations")
        print_info("   2. Optimize Monte Carlo simulation")
        print_info("   3. Parallelize correlation calculations")
    
    if stress_test_time <= 5.0:
        print_success("Stress test performance is good (≤5s)")
    
    if optimization_time > 5.0:
        print_info("🟡 Optimization is slow (>5s). Consider:")
        print_info("   1. Cache eligible tickers list")
        print_info("   2. Optimize market exploration")
        print_info("   3. Reduce efficient frontier points if not needed")

def review_code_steps():
    """Review code steps for optimization opportunities"""
    print_section("Code Review - Optimization Opportunities")
    
    opportunities = [
        {
            "area": "Data Retrieval",
            "issue": "Multiple calls to get_monthly_data() for same tickers",
            "solution": "Batch requests or cache results within request",
            "file": "backend/utils/stress_test_analyzer.py",
            "lines": "209-251"
        },
        {
            "area": "Portfolio Value Calculation",
            "issue": "calculate_portfolio_values_over_period called multiple times",
            "solution": "Cache results for same (tickers, weights, period) combinations",
            "file": "backend/utils/stress_test_analyzer.py",
            "lines": "743-745, 784-786"
        },
        {
            "area": "Monte Carlo Simulation",
            "issue": "10,000 iterations may be excessive",
            "solution": "Reduce to 5,000 or make configurable, use vectorized operations",
            "file": "backend/utils/stress_test_analyzer.py",
            "lines": "806-811"
        },
        {
            "area": "Normal Period Calculation",
            "issue": "Calculated separately for each scenario",
            "solution": "Cache normal period data or calculate once per portfolio",
            "file": "backend/utils/stress_test_analyzer.py",
            "lines": "779-786"
        },
        {
            "area": "Date Filtering",
            "issue": "filter_prices_by_date_range called for each ticker",
            "solution": "Filter once per ticker, reuse filtered data",
            "file": "backend/utils/stress_test_analyzer.py",
            "lines": "233-237"
        },
        {
            "area": "Correlation Calculation",
            "issue": "Pairwise correlations calculated sequentially",
            "solution": "Use vectorized numpy operations for all pairs at once",
            "file": "backend/utils/stress_test_analyzer.py",
            "lines": "482-609"
        }
    ]
    
    for i, opp in enumerate(opportunities, 1):
        print_info(f"{i}. {opp['area']}")
        print_info(f"   Issue: {opp['issue']}")
        print_info(f"   Solution: {opp['solution']}")
        print_info(f"   Location: {opp['file']} (lines {opp['lines']})")
        print()

def main():
    print_header("COVID-19 STRESS TEST PERFORMANCE ANALYSIS")
    print(f"Testing: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    total_start = time.time()
    
    # Step 1: Get optimized portfolio
    portfolio, optimization_time = get_optimized_moderate_portfolio()
    if not portfolio:
        print_error("Failed to get optimized portfolio. Exiting.")
        return 1
    
    print()
    
    # Step 2: Run stress test
    success, results, stress_test_time = run_covid19_stress_test(portfolio)
    if not success:
        print_error("Stress test failed. Exiting.")
        return 1
    
    print()
    
    # Step 3: Performance analysis
    total_time = time.time() - total_start
    analyze_performance(optimization_time, stress_test_time, total_time)
    
    print()
    
    # Step 4: Code review
    review_code_steps()
    
    # Summary
    print_header("SUMMARY")
    print_success(f"Total test time: {total_time:.3f}s")
    print_success(f"Optimization: {optimization_time:.3f}s")
    print_success(f"Stress test: {stress_test_time:.3f}s")
    
    if results:
        resilience = results.get("resilience_score", 0)
        print_success(f"Resilience score: {resilience:.1f}/100")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

