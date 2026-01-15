#!/usr/bin/env python3
"""
Comprehensive Performance Test for All Stress Test Scenarios
Tests each scenario separately and measures performance to identify optimization needs.
"""

import sys
import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, List, Tuple

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/portfolio"

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

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

def print_info(message: str):
    print(f"  {message}")

def print_timing(step: str, elapsed: float, threshold: float = 5.0):
    if elapsed < threshold:
        color = Colors.GREEN
        status = "✓"
    elif elapsed < threshold * 2:
        color = Colors.YELLOW
        status = "⚠"
    else:
        color = Colors.RED
        status = "✗"
    print(f"  {color}{status} {step}: {elapsed:.3f}s{Colors.RESET}")

def get_test_portfolio() -> Dict:
    """Get a standard test portfolio"""
    return {
        "tickers": ["AAPL", "MSFT", "JNJ", "PG", "V"],
        "weights": {"AAPL": 0.25, "MSFT": 0.25, "JNJ": 0.20, "PG": 0.15, "V": 0.15},
        "capital": 10000,
        "risk_profile": "moderate"
    }

def test_covid19_scenario(portfolio: Dict) -> Tuple[bool, float, Dict]:
    """Test COVID-19 scenario performance"""
    print_section("1. COVID-19 Crash Scenario")
    
    payload = {
        "tickers": portfolio["tickers"],
        "weights": portfolio["weights"],
        "scenarios": ["covid19"],
        "capital": portfolio["capital"],
        "risk_profile": portfolio["risk_profile"],
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_BASE}/stress-test", json=payload, timeout=120)
        elapsed = time.time() - start
        
        if response.status_code != 200:
            print_error(f"Failed: HTTP {response.status_code}")
            return False, elapsed, {}
        
        data = response.json()
        processing_time = data.get("processing_time_seconds", elapsed)
        
        print_timing("Total request time", elapsed)
        print_timing("Backend processing", processing_time, threshold=8.0)
        
        if "covid19" in data.get("scenarios", {}):
            metrics = data["scenarios"]["covid19"]["metrics"]
            print_success(f"Resilience score: {data.get('resilience_score', 0):.1f}/100")
            print_info(f"Max drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")
            return True, elapsed, data
        else:
            print_error("COVID-19 scenario not in response")
            return False, elapsed, data
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False, 0.0, {}

def test_2008_crisis_scenario(portfolio: Dict) -> Tuple[bool, float, Dict]:
    """Test 2008 Crisis scenario performance"""
    print_section("2. 2008 Financial Crisis Scenario")
    
    payload = {
        "tickers": portfolio["tickers"],
        "weights": portfolio["weights"],
        "scenarios": ["2008_crisis"],
        "capital": portfolio["capital"],
        "risk_profile": portfolio["risk_profile"],
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_BASE}/stress-test", json=payload, timeout=120)
        elapsed = time.time() - start
        
        if response.status_code != 200:
            print_error(f"Failed: HTTP {response.status_code}")
            return False, elapsed, {}
        
        data = response.json()
        processing_time = data.get("processing_time_seconds", elapsed)
        
        print_timing("Total request time", elapsed)
        print_timing("Backend processing", processing_time, threshold=8.0)
        
        if "2008_crisis" in data.get("scenarios", {}):
            metrics = data["scenarios"]["2008_crisis"]["metrics"]
            print_success(f"Resilience score: {data.get('resilience_score', 0):.1f}/100")
            print_info(f"Max drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")
            return True, elapsed, data
        else:
            print_error("2008 Crisis scenario not in response")
            return False, elapsed, data
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False, 0.0, {}

def test_what_if_scenario(portfolio: Dict) -> Tuple[bool, float, Dict]:
    """Test What-If scenario performance"""
    print_section("3. What-If Simulator")
    
    payload = {
        "tickers": portfolio["tickers"],
        "weights": portfolio["weights"],
        "volatility_multiplier": 2.0,
        "return_adjustment": -0.15,
        "time_horizon_months": 12,
        "capital": portfolio["capital"]
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_BASE}/what-if-scenario", json=payload, timeout=60)
        elapsed = time.time() - start
        
        if response.status_code != 200:
            print_error(f"Failed: HTTP {response.status_code}")
            return False, elapsed, {}
        
        data = response.json()
        processing_time = data.get("processing_time_seconds", elapsed)
        
        print_timing("Total request time", elapsed)
        print_timing("Backend processing", processing_time, threshold=3.0)
        
        if "monte_carlo" in data and "metrics" in data:
            print_success(f"Probability positive: {data['metrics'].get('probability_positive', 0):.1f}%")
            print_info(f"Expected return: {data['metrics'].get('expected_return', 0)*100:.2f}%")
            return True, elapsed, data
        else:
            print_error("Missing required fields in response")
            return False, elapsed, data
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False, 0.0, {}

def test_hypothetical_scenario(portfolio: Dict, scenario_type: str) -> Tuple[bool, float, Dict]:
    """Test Hypothetical scenario performance"""
    print_section(f"4. Hypothetical Scenario ({scenario_type})")
    
    payload = {
        "tickers": portfolio["tickers"],
        "weights": portfolio["weights"],
        "scenario_type": scenario_type,
        "market_decline": -0.30,
        "duration_months": 6,
        "recovery_rate": "moderate",
        "capital": portfolio["capital"]
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_BASE}/what-if-scenario", json=payload, timeout=60)
        elapsed = time.time() - start
        
        if response.status_code != 200:
            print_error(f"Failed: HTTP {response.status_code}")
            return False, elapsed, {}
        
        data = response.json()
        processing_time = data.get("processing_time_seconds", elapsed)
        
        print_timing("Total request time", elapsed)
        print_timing("Backend processing", processing_time, threshold=3.0)
        
        if "scenario_type" in data or "monte_carlo" in data:
            print_success(f"Scenario completed successfully")
            if "estimated_loss" in data:
                print_info(f"Estimated loss: {data['estimated_loss']*100:.2f}%")
            return True, elapsed, data
        else:
            print_error("Missing required fields in response")
            return False, elapsed, data
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False, 0.0, {}

def analyze_performance(results: Dict[str, Tuple[bool, float, Dict]]):
    """Analyze performance results and provide recommendations"""
    print_header("PERFORMANCE ANALYSIS & OPTIMIZATION RECOMMENDATIONS")
    
    recommendations = []
    
    # COVID-19 Scenario
    if "covid19" in results:
        success, elapsed, data = results["covid19"]
        if success:
            if elapsed > 10.0:
                recommendations.append({
                    "scenario": "COVID-19",
                    "current_time": elapsed,
                    "issue": f"Slow performance ({elapsed:.1f}s)",
                    "optimizations": [
                        "Already optimized: Monte Carlo reduced to 5,000 iterations",
                        "Already optimized: Portfolio value caching implemented",
                        "Consider: Further reduce Monte Carlo to 3,000 if acceptable",
                        "Consider: Cache sector impact calculations"
                    ]
                })
            else:
                print_success(f"COVID-19: Performance acceptable ({elapsed:.1f}s)")
    
    # 2008 Crisis Scenario
    if "2008_crisis" in results:
        success, elapsed, data = results["2008_crisis"]
        if success:
            if elapsed > 10.0:
                recommendations.append({
                    "scenario": "2008 Crisis",
                    "current_time": elapsed,
                    "issue": f"Slow performance ({elapsed:.1f}s)",
                    "optimizations": [
                        "Already optimized: Monte Carlo reduced to 5,000 iterations",
                        "Already optimized: Portfolio value caching implemented",
                        "Consider: Correlation breakdown calculation is expensive",
                        "Consider: Cache correlation calculations"
                    ]
                })
            else:
                print_success(f"2008 Crisis: Performance acceptable ({elapsed:.1f}s)")
    
    # What-If Scenario
    if "what_if" in results:
        success, elapsed, data = results["what_if"]
        if success:
            if elapsed > 5.0:
                recommendations.append({
                    "scenario": "What-If Simulator",
                    "current_time": elapsed,
                    "issue": f"Needs optimization ({elapsed:.1f}s)",
                    "optimizations": [
                        "⚠️ CRITICAL: Reduce Monte Carlo from 10,000 to 5,000 iterations",
                        "Optimize: Sequential price data retrieval (batch requests)",
                        "Consider: Cache baseline metrics calculation"
                    ]
                })
            else:
                print_success(f"What-If: Performance acceptable ({elapsed:.1f}s)")
    
    # Hypothetical Scenarios
    for scenario_type in ["tech_crash", "recession"]:
        key = f"hypothetical_{scenario_type}"
        if key in results:
            success, elapsed, data = results[key]
            if success:
                if elapsed > 5.0:
                    recommendations.append({
                        "scenario": f"Hypothetical ({scenario_type})",
                        "current_time": elapsed,
                        "issue": f"Needs optimization ({elapsed:.1f}s)",
                        "optimizations": [
                            "⚠️ CRITICAL: Reduce Monte Carlo from 10,000 to 5,000 iterations",
                            "Optimize: Sequential price data retrieval (batch requests)",
                            "Consider: Cache baseline metrics calculation"
                        ]
                    })
                else:
                    print_success(f"Hypothetical ({scenario_type}): Performance acceptable ({elapsed:.1f}s)")
    
    # Print recommendations
    if recommendations:
        print_section("Optimization Recommendations")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['scenario']} - {rec['issue']}")
            for opt in rec['optimizations']:
                print(f"   {opt}")
    else:
        print_success("All scenarios have acceptable performance!")

def main():
    print_header("COMPREHENSIVE STRESS TEST PERFORMANCE ANALYSIS")
    print(f"Testing: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    portfolio = get_test_portfolio()
    print_info(f"Test Portfolio: {', '.join(portfolio['tickers'])}")
    print_info(f"Capital: {portfolio['capital']} SEK")
    print_info(f"Risk Profile: {portfolio['risk_profile']}\n")
    
    results = {}
    
    # Test COVID-19
    success, elapsed, data = test_covid19_scenario(portfolio)
    results["covid19"] = (success, elapsed, data)
    time.sleep(1)
    
    # Test 2008 Crisis
    success, elapsed, data = test_2008_crisis_scenario(portfolio)
    results["2008_crisis"] = (success, elapsed, data)
    time.sleep(1)
    
    # Test What-If
    success, elapsed, data = test_what_if_scenario(portfolio)
    results["what_if"] = (success, elapsed, data)
    time.sleep(1)
    
    # Test Hypothetical scenarios
    for scenario_type in ["tech_crash", "recession"]:
        success, elapsed, data = test_hypothetical_scenario(portfolio, scenario_type)
        results[f"hypothetical_{scenario_type}"] = (success, elapsed, data)
        time.sleep(1)
    
    # Analyze performance
    analyze_performance(results)
    
    # Summary
    print_header("SUMMARY")
    total_tests = len(results)
    passed = sum(1 for success, _, _ in results.values() if success)
    
    print_info(f"Tests run: {total_tests}")
    print_success(f"Passed: {passed}")
    print_error(f"Failed: {total_tests - passed}")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return 0 if passed == total_tests else 1

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

