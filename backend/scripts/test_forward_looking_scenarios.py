#!/usr/bin/env python3
"""
Test forward-looking hypothetical scenarios with different parameters.
Validates that all scenario types produce logical and accurate results.
"""
import requests
import sys
from typing import Any, Dict, Tuple

API_BASE = "http://127.0.0.1:8000/api/v1/portfolio"

# Portfolio used for all tests (must exist in cache for sector impact)
PORTFOLIO = {
    "tickers": ["AAPL", "MSFT"],
    "weights": {"AAPL": 0.5, "MSFT": 0.5},
    "capital": 10000,
}


def call_what_if(
    scenario_type: str,
    market_decline: float,
    duration_months: int = 6,
    recovery_rate: str = "moderate",
) -> Tuple[bool, str, Dict[str, Any]]:
    """Call what-if-scenario endpoint. market_decline as decimal e.g. -0.30 for -30%."""
    payload = {
        **PORTFOLIO,
        "scenario_type": scenario_type,
        "market_decline": market_decline,
        "duration_months": duration_months,
        "recovery_rate": recovery_rate,
    }
    try:
        r = requests.post(f"{API_BASE}/what-if-scenario", json=payload, timeout=60)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}", {}
        return True, "", r.json()
    except requests.exceptions.RequestException as e:
        return False, str(e), {}


def validate_response(data: Dict[str, Any], scenario_type: str, market_decline: float) -> Tuple[bool, list]:
    """Check response for logical and accurate structure. Returns (ok, list of error messages)."""
    errors = []
    capital = PORTFOLIO["capital"]

    if data.get("scenario_type") != scenario_type:
        errors.append(f"scenario_type: expected {scenario_type}, got {data.get('scenario_type')}")

    est = data.get("estimated_loss")
    if est is None:
        errors.append("missing estimated_loss")
    elif not isinstance(est, (int, float)):
        errors.append(f"estimated_loss must be number, got {type(est)}")
    elif est > 0 or est < -1:
        errors.append(f"estimated_loss must be in [-1, 0], got {est}")

    cap_risk = data.get("capital_at_risk")
    if cap_risk is not None and est is not None:
        expected_cap = round(capital * abs(est), 2)
        if abs(cap_risk - expected_cap) > 0.02:
            errors.append(f"capital_at_risk: expected ~{expected_cap}, got {cap_risk}")

    rec = data.get("estimated_recovery_months")
    if rec is not None and (not isinstance(rec, (int, float)) or rec < 0):
        errors.append(f"estimated_recovery_months must be non-negative number, got {rec}")

    params = data.get("parameters", {})
    if isinstance(params, dict):
        if params.get("market_decline") is not None and abs(params["market_decline"] - market_decline) > 1e-6:
            errors.append(f"parameters.market_decline: expected {market_decline}, got {params['market_decline']}")
    else:
        errors.append("parameters should be a dict")

    mc = data.get("monte_carlo")
    if not mc:
        errors.append("missing monte_carlo")
    elif not isinstance(mc.get("histogram_data"), list):
        errors.append("monte_carlo.histogram_data must be a list")
    elif len(mc.get("histogram_data") or []) == 0:
        errors.append("monte_carlo.histogram_data is empty")

    return (len(errors) == 0, errors)


def run_tests() -> bool:
    """Run all scenario and parameter combinations. Return True if all pass."""
    print("Forward-Looking Scenarios – parameter and logic checks")
    print("=" * 60)

    # Health check
    try:
        r = requests.get("http://127.0.0.1:8000/health", timeout=15)
        if r.status_code != 200:
            print("FAIL: Backend health check returned", r.status_code)
            return False
    except requests.exceptions.RequestException as e:
        print("FAIL: Backend not reachable at http://127.0.0.1:8000 –", e)
        return False

    scenarios = [
        ("tech_crash", -0.30, 6, "moderate"),
        ("tech_crash", -0.40, 12, "slow"),
        ("inflation", -0.25, 6, "moderate"),
        ("inflation", -0.20, 3, "fast"),
        ("geopolitical", -0.35, 9, "moderate"),
        ("geopolitical", -0.25, 6, "fast"),
        ("recession", -0.30, 12, "slow"),
        ("recession", -0.25, 6, "moderate"),
    ]

    all_ok = True
    for scenario_type, market_decline, duration_months, recovery_rate in scenarios:
        label = f"{scenario_type} decline={market_decline*100:.0f}% dur={duration_months}mo rec={recovery_rate}"
        ok, err_msg, data = call_what_if(scenario_type, market_decline, duration_months, recovery_rate)
        if not ok:
            print(f"FAIL {label}: {err_msg}")
            all_ok = False
            continue
        valid, errs = validate_response(data, scenario_type, market_decline)
        if not valid:
            print(f"FAIL {label}: validation errors: {errs}")
            all_ok = False
            continue
        est = data.get("estimated_loss", 0) * 100
        cap_risk = data.get("capital_at_risk", 0)
        rec = data.get("estimated_recovery_months", 0)
        print(f"OK   {label} -> loss={est:.1f}% capital_at_risk={cap_risk:.0f} recovery={rec}mo")

    # Sanity: steeper decline => more negative (worse) loss (same scenario)
    print()
    print("Consistency: steeper decline => larger loss (tech_crash)")
    ok1, _, d1 = call_what_if("tech_crash", -0.20, 6, "moderate")
    ok2, _, d2 = call_what_if("tech_crash", -0.50, 6, "moderate")
    if ok1 and ok2:
        l1 = d1.get("estimated_loss") or 0
        l2 = d2.get("estimated_loss") or 0
        if l2 >= l1:
            print(f"FAIL: -50% decline loss ({l2}) should be more negative than -20% loss ({l1})")
            all_ok = False
        else:
            print(f"OK: -50% loss ({l2:.3f}) < -20% loss ({l1:.3f})")
    else:
        all_ok = False

    # Slow recovery => longer recovery months (same decline)
    print()
    print("Consistency: slow recovery => longer recovery months")
    ok1, _, d1 = call_what_if("recession", -0.30, 6, "fast")
    ok2, _, d2 = call_what_if("recession", -0.30, 6, "slow")
    if ok1 and ok2:
        r1 = d1.get("estimated_recovery_months") or 0
        r2 = d2.get("estimated_recovery_months") or 0
        if r2 < r1:
            print(f"FAIL: slow recovery ({r2}mo) should be >= fast ({r1}mo)")
            all_ok = False
        else:
            print(f"OK: slow={r2}mo >= fast={r1}mo")
    else:
        all_ok = False

    print("=" * 60)
    print("PASS" if all_ok else "FAIL")
    return all_ok


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
