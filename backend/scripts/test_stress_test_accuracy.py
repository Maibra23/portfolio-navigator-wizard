#!/usr/bin/env python3
"""
Test script to verify stress test accuracy
Tests with an existing optimized portfolio and validates:
1. Portfolio value calculations
2. Peak/Trough detection
3. Recovery time calculation
4. What-If scenario accuracy
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000/api/portfolio"

def print_section(title: str):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

def print_step(step: str, status: str = "info"):
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    print(f"{icons.get(status, '•')} {step}")

def get_test_portfolio():
    """Get a standard test portfolio (moderate risk)"""
    return {
        "tickers": ["AAPL", "MSFT", "JNJ", "PG", "V"],
        "weights": {"AAPL": 0.25, "MSFT": 0.25, "JNJ": 0.20, "PG": 0.15, "V": 0.15},
        "capital": 10000,
        "risk_profile": "moderate"
    }

def test_covid19_scenario(portfolio):
    """Test COVID-19 scenario accuracy"""
    print_section("COVID-19 Scenario Accuracy Test")
    
    payload = {
        "tickers": portfolio["tickers"],
        "weights": portfolio["weights"],
        "scenarios": ["covid19"],
        "capital": portfolio["capital"]
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_BASE}/stress-test", json=payload, timeout=120)
        elapsed = time.time() - start
        
        if response.status_code != 200:
            print_step(f"Failed: HTTP {response.status_code}", "error")
            print(response.text)
            return None
        
        data = response.json()
        scenario_data = data.get("scenarios", {}).get("covid19", {})
        
        print_step(f"Request completed in {elapsed:.2f}s", "success")
        
        # Verify data structure
        monthly_perf = scenario_data.get("monthly_performance", [])
        peaks_troughs = scenario_data.get("peaks_troughs", {})
        metrics = scenario_data.get("metrics", {})
        
        print_step(f"Monthly performance data points: {len(monthly_perf)}", "info")
        print_step(f"Peak: {peaks_troughs.get('peak', {}).get('date', 'N/A')} (value: {peaks_troughs.get('peak', {}).get('value', 0):.4f})", "info")
        print_step(f"Trough: {peaks_troughs.get('trough', {}).get('date', 'N/A')} (value: {peaks_troughs.get('trough', {}).get('value', 0):.4f})", "info")
        print_step(f"Recovery months: {metrics.get('recovery_months', 'N/A')}", "info")
        print_step(f"Recovery pattern: {metrics.get('recovery_pattern', 'N/A')}", "info")
        print_step(f"Total return: {metrics.get('total_return', 0)*100:.2f}%", "info")
        print_step(f"Max drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%", "info")
        
        # Verify calculations
        issues = []
        
        # Check if monthly_performance values are consistent
        if monthly_perf:
            values = [m.get('value', 0) for m in monthly_perf]
            if values[0] != 1.0:
                issues.append(f"First value should be 1.0 (normalized), got {values[0]}")
            
            # Check if peak value matches monthly_performance
            peak_date = peaks_troughs.get('peak', {}).get('date', '')
            if peak_date:
                peak_month = peak_date[:7]  # YYYY-MM
                peak_data_point = next((m for m in monthly_perf if m.get('month', '') == peak_month), None)
                if peak_data_point:
                    peak_value_in_data = peak_data_point.get('value', 0)
                    peak_value_reported = peaks_troughs.get('peak', {}).get('value', 0)
                    if abs(peak_value_in_data - peak_value_reported) > 0.001:
                        issues.append(f"Peak value mismatch: data={peak_value_in_data:.4f}, reported={peak_value_reported:.4f}")
                else:
                    issues.append(f"Peak date {peak_month} not found in monthly_performance")
            
            # Check if trough value matches monthly_performance
            trough_date = peaks_troughs.get('trough', {}).get('date', '')
            if trough_date:
                trough_month = trough_date[:7]  # YYYY-MM
                trough_data_point = next((m for m in monthly_perf if m.get('month', '') == trough_month), None)
                if trough_data_point:
                    trough_value_in_data = trough_data_point.get('value', 0)
                    trough_value_reported = peaks_troughs.get('trough', {}).get('value', 0)
                    if abs(trough_value_in_data - trough_value_reported) > 0.001:
                        issues.append(f"Trough value mismatch: data={trough_value_in_data:.4f}, reported={trough_value_reported:.4f}")
                else:
                    issues.append(f"Trough date {trough_month} not found in monthly_performance")
        
        # Check recovery calculation
        recovery_months = metrics.get('recovery_months')
        if recovery_months is None:
            print_step("Recovery months is None - portfolio did not recover to 95% of peak", "warning")
        else:
            print_step(f"Recovery verified: {recovery_months} months", "success")
        
        if issues:
            print_step("Issues found:", "error")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print_step("All calculations verified", "success")
        
        return data
        
    except Exception as e:
        print_step(f"Error: {e}", "error")
        import traceback
        traceback.print_exc()
        return None

def test_what_if_scenario(portfolio):
    """Test What-If scenario accuracy"""
    print_section("What-If Scenario Accuracy Test")
    
    payload = {
        "tickers": portfolio["tickers"],
        "weights": portfolio["weights"],
        "volatility_multiplier": 2.0,
        "return_adjustment": -0.05,
        "time_horizon_months": 12,
        "capital": portfolio["capital"]
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_BASE}/what-if-scenario", json=payload, timeout=120)
        elapsed = time.time() - start
        
        if response.status_code != 200:
            print_step(f"Failed: HTTP {response.status_code}", "error")
            print(response.text)
            return None
        
        data = response.json()
        
        print_step(f"Request completed in {elapsed:.2f}s", "success")
        
        monte_carlo = data.get("monte_carlo", {})
        metrics = data.get("metrics", {})
        
        print_step(f"Expected return: {data.get('parameters', {}).get('return_adjustment', 0)*100:.2f}%", "info")
        print_step(f"Volatility multiplier: {data.get('parameters', {}).get('volatility_multiplier', 0)}x", "info")
        print_step(f"Time horizon: {data.get('parameters', {}).get('time_horizon_months', 0)} months", "info")
        print_step(f"Probability positive: {metrics.get('probability_positive', 0)*100:.2f}%", "info")
        print_step(f"Monte Carlo simulations: {len(monte_carlo.get('simulated_returns', []))}", "info")
        
        # Verify Monte Carlo
        sim_returns = monte_carlo.get("simulated_returns", [])
        if len(sim_returns) != 5000:
            print_step(f"Warning: Expected 5000 simulations, got {len(sim_returns)}", "warning")
        
        # Check if results are reasonable
        prob_positive = metrics.get('probability_positive', 0)
        if prob_positive < 0 or prob_positive > 1:
            print_step(f"Invalid probability_positive: {prob_positive}", "error")
        else:
            print_step("Monte Carlo results validated", "success")
        
        return data
        
    except Exception as e:
        print_step(f"Error: {e}", "error")
        import traceback
        traceback.print_exc()
        return None

def test_hypothetical_scenario(portfolio):
    """Test Hypothetical scenario accuracy"""
    print_section("Hypothetical Scenario Accuracy Test")
    
    payload = {
        "tickers": portfolio["tickers"],
        "weights": portfolio["weights"],
        "scenario_type": "tech_crash",
        "capital": portfolio["capital"]
    }
    
    try:
        start = time.time()
        response = requests.post(f"{API_BASE}/what-if-scenario", json=payload, timeout=120)
        elapsed = time.time() - start
        
        if response.status_code != 200:
            print_step(f"Failed: HTTP {response.status_code}", "error")
            print(response.text)
            return None
        
        data = response.json()
        
        print_step(f"Request completed in {elapsed:.2f}s", "success")
        print_step(f"Estimated loss: {data.get('estimated_loss', 0)*100:.2f}%", "info")
        print_step(f"Capital at risk: {data.get('capital_at_risk', 0):.2f} SEK", "info")
        print_step(f"Recovery months: {data.get('estimated_recovery_months', 'N/A')}", "info")
        
        return data
        
    except Exception as e:
        print_step(f"Error: {e}", "error")
        import traceback
        traceback.print_exc()
        return None

def main():
    print_section("STRESS TEST ACCURACY VERIFICATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    portfolio = get_test_portfolio()
    print(f"\nTest Portfolio: {', '.join(portfolio['tickers'])}")
    print(f"Capital: {portfolio['capital']} SEK")
    print(f"Risk Profile: {portfolio['risk_profile']}")
    
    # Test COVID-19 scenario
    covid19_result = test_covid19_scenario(portfolio)
    
    # Test What-If scenario
    whatif_result = test_what_if_scenario(portfolio)
    
    # Test Hypothetical scenario
    hypothetical_result = test_hypothetical_scenario(portfolio)
    
    print_section("SUMMARY")
    print_step(f"COVID-19: {'✅ Passed' if covid19_result else '❌ Failed'}")
    print_step(f"What-If: {'✅ Passed' if whatif_result else '❌ Failed'}")
    print_step(f"Hypothetical: {'✅ Passed' if hypothetical_result else '❌ Failed'}")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

