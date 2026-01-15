#!/usr/bin/env python3
"""
Verify all stress test scenarios are properly implemented
Checks code structure without requiring server to be running
"""

import re
import sys
import os

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def check_file(filepath, checks):
    """Check a file for various conditions"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        results = {}
        for name, pattern, required in checks:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            results[name] = {
                'found': len(matches) > 0,
                'count': len(matches),
                'required': required,
                'pass': len(matches) >= required if required else len(matches) > 0
            }
        return results
    except Exception as e:
        print(f"{RED}Error reading {filepath}: {e}{RESET}")
        return {}

def main():
    print(f"{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}Stress Test Scenarios Verification{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_file = os.path.join(base_path, 'frontend/src/components/wizard/StressTest.tsx')
    backend_file = os.path.join(base_path, 'backend/routers/portfolio.py')
    
    all_passed = True
    
    # Check Frontend
    print(f"{BOLD}Frontend Component Checks:{RESET}\n")
    frontend_checks = [
        ('loadingProgress state', r'const \[loadingProgress', 1),
        ('loadingStep state', r'const \[loadingStep', 1),
        ('setLoadingProgress', r'setLoadingProgress', 1),
        ('setLoadingStep', r'setLoadingStep', 1),
        ('COVID-19 scenario', r'covid19', 5),
        ('2008 Crisis scenario', r'2008_crisis', 5),
        ('What-If scenario', r'what-if|whatIf', 3),
        ('Hypothetical scenarios', r'hypothetical|scenario_type', 3),
        ('Monte Carlo display', r'monte.?carlo|monte_carlo', 3),
        ('Timeline events', r'crisisEvents', 1),
        ('Comparison view', r'showComparison', 2),
        ('Export functionality', r'handleExportResults|Export', 2),
    ]
    
    frontend_results = check_file(frontend_file, frontend_checks)
    for name, result in frontend_results.items():
        status = f"{GREEN}✓{RESET}" if result['pass'] else f"{RED}✗{RESET}"
        print(f"  {status} {name}: {result['count']} found (required: {result['required']})")
        if not result['pass']:
            all_passed = False
    
    print()
    
    # Check Backend
    print(f"{BOLD}Backend API Checks:{RESET}\n")
    backend_checks = [
        ('Stress test endpoint', r'@router\.post\(["\']/stress-test', 1),
        ('What-If endpoint', r'@router\.post\(["\']/what-if-scenario', 1),
        ('Hypothetical handler', r'_handle_hypothetical_scenario|scenario_type', 2),
        ('COVID-19 analysis', r'analyze_covid19_scenario', 1),
        ('2008 Crisis analysis', r'analyze_2008_crisis_scenario', 1),
        ('Monte Carlo integration', r'run_monte_carlo_simulation', 2),
        ('Advanced risk metrics', r'calculate_advanced_risk_metrics', 1),
    ]
    
    backend_results = check_file(backend_file, backend_checks)
    for name, result in backend_results.items():
        status = f"{GREEN}✓{RESET}" if result['pass'] else f"{RED}✗{RESET}"
        print(f"  {status} {name}: {result['count']} found (required: {result['required']})")
        if not result['pass']:
            all_passed = False
    
    print()
    
    # Summary
    print(f"{BOLD}{BLUE}{'='*70}{RESET}")
    if all_passed:
        print(f"{GREEN}{BOLD}✓ All checks passed!{RESET}")
    else:
        print(f"{RED}{BOLD}✗ Some checks failed{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
