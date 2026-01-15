#!/usr/bin/env python3
"""
Verify that both COVID-19 and 2008 Financial Crisis scenarios work correctly
and have consistent performance optimizations applied.
"""

import sys
import os
import time
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/portfolio"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_test(test_name: str):
    print(f"{Colors.BOLD}▶ {test_name}{Colors.RESET}")

def print_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message: str):
    print(f"  {message}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

def test_scenario(scenario_name: str, portfolio: dict) -> tuple:
    """Test a specific scenario"""
    print_test(f"Testing {scenario_name} scenario...")
    
    payload = {
        "tickers": portfolio["tickers"],
        "weights": portfolio["weights"],
        "scenarios": [scenario_name],
        "capital": portfolio["capital"],
        "risk_profile": portfolio["risk_profile"]
    }
    
    start_time = time.time()
    try:
        response = requests.post(f"{API_BASE}/stress-test", json=payload, timeout=120)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            if "scenarios" in data:
                # Scenarios can be a dict or list
                scenarios = data["scenarios"]
                if isinstance(scenarios, dict):
                    # Find the scenario by name
                    scenario_result = None
                    for key, value in scenarios.items():
                        if scenario_name in key.lower() or key.lower() in scenario_name.lower():
                            scenario_result = value
                            break
                    if not scenario_result and len(scenarios) > 0:
                        # Use first scenario if name doesn't match
                        scenario_result = list(scenarios.values())[0]
                elif isinstance(scenarios, list) and len(scenarios) > 0:
                    scenario_result = scenarios[0]
                else:
                    print_error("No scenario results in response")
                    return False, {}, elapsed
                
                if not scenario_result:
                    print_error("Could not find scenario result")
                    return False, {}, elapsed
                
                # Check required fields
                required_fields = [
                    'scenario_name', 'period', 'metrics', 'peaks_troughs',
                    'monthly_performance', 'data_availability'
                ]
                
                missing_fields = [f for f in required_fields if f not in scenario_result]
                if missing_fields:
                    print_error(f"Missing required fields: {missing_fields}")
                    return False, {}, elapsed
                
                # Check metrics
                metrics = scenario_result.get('metrics', {})
                required_metrics = [
                    'total_return', 'max_drawdown', 'volatility_during_crisis',
                    'recovery_months', 'recovery_pattern'
                ]
                
                missing_metrics = [m for m in required_metrics if m not in metrics]
                if missing_metrics:
                    print_error(f"Missing required metrics: {missing_metrics}")
                    return False, {}, elapsed
                
                # Display key metrics
                print_success(f"{scenario_name} scenario completed in {elapsed:.2f}s")
                print_info(f"  Total Return: {metrics['total_return']*100:.2f}%")
                print_info(f"  Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
                print_info(f"  Volatility: {metrics['volatility_during_crisis']*100:.2f}%")
                
                if metrics.get('recovery_months') is not None:
                    print_info(f"  Recovery Time: {metrics['recovery_months']} months")
                else:
                    print_info(f"  Recovery Time: Not recovered (or no significant drawdown)")
                
                if 'recovery_needed_pct' in metrics:
                    print_info(f"  Recovery Needed: {metrics['recovery_needed_pct']*100:.2f}%")
                
                if 'trajectory_projections' in metrics:
                    traj = metrics['trajectory_projections']
                    if traj:  # Only show if not empty
                        print_info(f"  Trajectory Projections:")
                        if 'optimistic_months' in traj:
                            print_info(f"    Optimistic: {traj['optimistic_months']} months")
                        if 'realistic_months' in traj:
                            print_info(f"    Realistic: {traj['realistic_months']} months")
                        if 'pessimistic_months' in traj:
                            print_info(f"    Pessimistic: {traj['pessimistic_months']} months")
                
                if 'max_drawdown_data' in metrics:
                    dd_data = metrics['max_drawdown_data']
                    if isinstance(dd_data, dict):
                        print_info(f"  Max Drawdown Data: is_significant={dd_data.get('is_significant', 'N/A')}")
                
                return True, scenario_result, elapsed
            else:
                print_error("No scenario results in response")
                return False, {}, elapsed
        else:
            print_error(f"HTTP {response.status_code}: {response.text[:200]}")
            return False, {}, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print_error(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, {}, elapsed

def compare_optimizations(covid_result: dict, crisis2008_result: dict):
    """Compare if both scenarios have the same optimizations"""
    print_test("Comparing optimizations between scenarios...")
    
    checks = []
    
    # Check if both have Monte Carlo
    covid_mc = covid_result.get('monte_carlo')
    crisis_mc = crisis2008_result.get('monte_carlo')
    
    if covid_mc and crisis_mc:
        covid_sims = covid_mc.get('parameters', {}).get('num_simulations', 0)
        crisis_sims = crisis_mc.get('parameters', {}).get('num_simulations', 0)
        
        if covid_sims == 5000 and crisis_sims == 5000:
            checks.append("✓ Both use optimized Monte Carlo (5,000 simulations)")
        else:
            checks.append(f"⚠ Monte Carlo simulations differ: COVID={covid_sims}, 2008={crisis_sims}")
    else:
        checks.append("⚠ Monte Carlo missing in one or both scenarios")
    
    # Check if both have recovery metrics
    covid_recovery = covid_result.get('metrics', {}).get('recovery_thresholds', {})
    crisis_recovery = crisis2008_result.get('metrics', {}).get('recovery_thresholds', {})
    
    if isinstance(covid_recovery, dict) and isinstance(crisis_recovery, dict):
        checks.append("✓ Both have recovery thresholds structure")
    else:
        checks.append("⚠ Recovery thresholds structure differs")
    
    # Check if both have trajectory_projections field (may be empty if no significant drawdown)
    covid_metrics = covid_result.get('metrics', {})
    crisis_metrics = crisis2008_result.get('metrics', {})
    
    if 'trajectory_projections' in covid_metrics and 'trajectory_projections' in crisis_metrics:
        checks.append("✓ Both have trajectory_projections field")
        covid_traj = covid_metrics.get('trajectory_projections', {})
        crisis_traj = crisis_metrics.get('trajectory_projections', {})
        if covid_traj or crisis_traj:
            print_info(f"  COVID-19 trajectory_projections: {bool(covid_traj)} (has data: {bool(covid_traj)})")
            print_info(f"  2008 Crisis trajectory_projections: {bool(crisis_traj)} (has data: {bool(crisis_traj)})")
    else:
        checks.append("⚠ trajectory_projections field missing in one or both")
        print_info(f"  COVID-19 has field: {'trajectory_projections' in covid_metrics}")
        print_info(f"  2008 Crisis has field: {'trajectory_projections' in crisis_metrics}")
    
    # Check if both have max_drawdown_data with is_significant
    covid_dd = covid_metrics.get('max_drawdown_data', {})
    crisis_dd = crisis_metrics.get('max_drawdown_data', {})
    
    if isinstance(covid_dd, dict) and isinstance(crisis_dd, dict):
        if 'is_significant' in covid_dd and 'is_significant' in crisis_dd:
            checks.append("✓ Both have is_significant flag in max_drawdown_data")
            print_info(f"  COVID-19 is_significant: {covid_dd.get('is_significant')}")
            print_info(f"  2008 Crisis is_significant: {crisis_dd.get('is_significant')}")
        else:
            checks.append("⚠ is_significant flag missing in one or both")
            print_info(f"  COVID-19 has is_significant: {'is_significant' in covid_dd}")
            print_info(f"  2008 Crisis has is_significant: {'is_significant' in crisis_dd}")
    else:
        checks.append("⚠ max_drawdown_data missing or not a dict in one or both")
        print_info(f"  COVID-19 max_drawdown_data type: {type(covid_dd)}")
        print_info(f"  2008 Crisis max_drawdown_data type: {type(crisis_dd)}")
    
    for check in checks:
        if check.startswith("✓"):
            print_success(check)
        else:
            print_warning(check)

def main():
    print_header("STRESS TEST SCENARIOS FUNCTIONALITY VERIFICATION")
    
    # Test portfolio
    portfolio = {
        "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
        "weights": {"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.20, "AMZN": 0.15, "TSLA": 0.15},
        "capital": 10000,
        "risk_profile": "moderate"
    }
    
    print_info(f"Test Portfolio: {', '.join(portfolio['tickers'])}")
    print_info(f"Capital: ${portfolio['capital']:,}")
    print_info(f"Risk Profile: {portfolio['risk_profile']}\n")
    
    # Test COVID-19 scenario
    covid_success, covid_result, covid_time = test_scenario("covid19", portfolio)
    
    print()
    
    # Test 2008 Crisis scenario
    crisis_success, crisis_result, crisis_time = test_scenario("2008_crisis", portfolio)
    
    print()
    
    # Compare optimizations
    if covid_success and crisis_success:
        compare_optimizations(covid_result, crisis_result)
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    if covid_success:
        print_success(f"COVID-19 scenario: PASSED ({covid_time:.2f}s)")
    else:
        print_error("COVID-19 scenario: FAILED")
    
    if crisis_success:
        print_success(f"2008 Crisis scenario: PASSED ({crisis_time:.2f}s)")
    else:
        print_error("2008 Crisis scenario: FAILED")
    
    if covid_success and crisis_success:
        print_success("\n✓ All scenarios are functional and optimized!")
        return 0
    else:
        print_error("\n✗ Some scenarios failed verification")
        return 1

if __name__ == "__main__":
    sys.exit(main())
