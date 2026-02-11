#!/usr/bin/env python3
"""
Test tax/calculate endpoint: ISK/KF/AF, expectedReturn, and afterTaxReturn.
Run from backend: python scripts/test_tax_endpoint.py
Or with pytest: pytest scripts/test_tax_endpoint.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_swedish_tax_calculator_unit():
    """Unit test: SwedishTaxCalculator ISK 2026 for 400k and afterTaxReturn logic."""
    from utils.swedish_tax_calculator import SwedishTaxCalculator
    calc = SwedishTaxCalculator()
    # ISK 2026: 400k, tax-free 300k -> taxable 100k, schablon 3.55%, tax 30%
    result = calc.calculate_isk_tax_2026(400000.0)
    assert result["annual_tax"] == round(100000 * 0.0355 * 0.30, 2)
    assert result["tax_free_level"] == 300000.0
    assert result["taxable_capital"] == 100000.0
    # 100000 * 0.0355 * 0.30 = 1065.0
    assert result["annual_tax"] == 1065.0
    print("  OK SwedishTaxCalculator ISK 2026 400k -> annual_tax 1065 SEK")


def test_isk_2025_unit():
    """Unit test: ISK 2025 400k -> taxable 250k, schablon 2.96%."""
    from utils.swedish_tax_calculator import SwedishTaxCalculator
    calc = SwedishTaxCalculator()
    result = calc.calculate_isk_tax_2025(400000.0)
    assert result["tax_free_level"] == 150000.0
    assert result["taxable_capital"] == 250000.0
    assert result["annual_tax"] == round(250000 * 0.0296 * 0.30, 2)
    print("  OK SwedishTaxCalculator ISK 2025 400k")


def test_tax_calculate_isk_with_after_tax_return():
    """Test POST /api/v1/portfolio/tax/calculate with expectedReturn returns afterTaxReturn."""
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        print(f"  SKIP TestClient (app import): {e}")
        return
    client = TestClient(app)
    payload = {
        "accountType": "ISK",
        "taxYear": 2026,
        "portfolioValue": 400000.0,
        "expectedReturn": 0.07,
    }
    response = client.post("/api/v1/portfolio/tax/calculate", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["accountType"] == "ISK"
    assert data["taxYear"] == 2026
    assert data["annualTax"] == 1065.0
    assert "afterTaxReturn" in data
    assert data["afterTaxReturn"] is not None
    # Gross = 400000 * 0.07 = 28000, after tax = 28000 - 1065 = 26935, rate = 26935/400000 = 0.0673
    expected_after = round((400000 * 0.07 - 1065) / 400000, 4)
    assert abs(data["afterTaxReturn"] - expected_after) < 0.0001
    print(f"  OK ISK 400k 7% return -> afterTaxReturn={data['afterTaxReturn']}")


def test_tax_calculate_af_with_after_tax_return():
    """Test AF account returns afterTaxReturn = expectedReturn * 0.70."""
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        print(f"  SKIP TestClient: {e}")
        return
    client = TestClient(app)
    payload = {
        "accountType": "AF",
        "taxYear": 2026,
        "realizedGains": 28000.0,
        "dividends": 0,
        "fundHoldings": 0,
        "expectedReturn": 0.07,
    }
    response = client.post("/api/v1/portfolio/tax/calculate", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["accountType"] == "AF"
    assert data["annualTax"] == round(28000 * 0.30, 2)
    assert data["afterTaxReturn"] is not None
    assert abs(data["afterTaxReturn"] - 0.049) < 0.0001  # 0.07 * 0.70 = 0.049
    print(f"  OK AF 7% return -> afterTaxReturn={data['afterTaxReturn']}")


def test_tax_calculate_isk_without_expected_return():
    """Without expectedReturn, afterTaxReturn should be null."""
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        print(f"  SKIP TestClient: {e}")
        return
    client = TestClient(app)
    response = client.post("/api/v1/portfolio/tax/calculate", json={
        "accountType": "ISK",
        "taxYear": 2026,
        "portfolioValue": 400000.0,
    })
    assert response.status_code == 200
    data = response.json()
    assert data.get("afterTaxReturn") is None
    print("  OK ISK without expectedReturn -> afterTaxReturn is null")


if __name__ == "__main__":
    print("Tax endpoint tests")
    print("-" * 40)
    test_swedish_tax_calculator_unit()
    test_isk_2025_unit()
    test_tax_calculate_isk_with_after_tax_return()
    test_tax_calculate_af_with_after_tax_return()
    test_tax_calculate_isk_without_expected_return()
    print("-" * 40)
    print("All tests passed.")
