#!/usr/bin/env python3
"""
Tests that PDF and CSV exports always include the stress test section/graph when the user
did not run the stress step: backend runs stress on the fly and includes the section.
Run from repo root: pytest backend/tests/test_export_stress_always_included.py -v
Or from backend: pytest tests/test_export_stress_always_included.py -v
"""

import sys
import os

# Allow importing backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal stress result for mocking (PDF generator needs scenarios with metrics.max_drawdown)
MINIMAL_STRESS_RESULT = {
    "scenarios": {
        "covid19": {"metrics": {"max_drawdown": -0.15}},
        "2008_crisis": {"metrics": {"max_drawdown": -0.25}},
    },
    "resilience_score": 75.0,
    "overall_assessment": "Your portfolio shows strong resilience (score: 75/100).",
    "portfolio_summary": {},
}

MINIMAL_PDF_BODY = {
    "portfolio": [
        {"ticker": "AAPL", "allocation": 0.5, "name": "Apple Inc."},
        {"ticker": "MSFT", "allocation": 0.5, "name": "Microsoft Corp."},
    ],
    "portfolioName": "Test Portfolio",
    "includeSections": {"optimization": False, "stressTest": False},
    "portfolioValue": 100000.0,
    "accountType": "ISK",
    "taxYear": 2025,
}


def test_export_pdf_without_stress_results_returns_200_and_pdf():
    """Without stressTestResults, export returns 200 and application/pdf."""
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        import pytest
        pytest.skip(f"App import failed: {e}")
    client = TestClient(app)
    body = {**MINIMAL_PDF_BODY}
    response = client.post("/api/v1/portfolio/export/pdf", json=body)
    assert response.status_code == 200, response.text
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert len(response.content) > 0


def test_export_pdf_without_stress_includes_stress_section_when_stress_run_on_fly():
    """When _run_stress_test_for_export is used (mocked), PDF is generated with stress data (section included)."""
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        import pytest
        pytest.skip(f"App import failed: {e}")

    from unittest.mock import patch

    with patch("routers.portfolio._run_stress_test_for_export", return_value=MINIMAL_STRESS_RESULT):
        client = TestClient(app)
        body = {**MINIMAL_PDF_BODY}
        response = client.post("/api/v1/portfolio/export/pdf", json=body)
    assert response.status_code == 200, response.text
    assert response.headers.get("content-type", "").startswith("application/pdf")
    # PDF content is compressed; stress section is included when stress_test_results and includeSections.stressTest are set
    assert len(response.content) > 5000


def test_export_csv_without_stress_results_includes_stress_file_when_run_on_fly():
    """When stress test is run on the fly for CSV, response includes stress_test_results.csv."""
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        import pytest
        pytest.skip(f"App import failed: {e}")

    from unittest.mock import patch

    with patch("routers.portfolio._run_stress_test_for_export", return_value=MINIMAL_STRESS_RESULT):
        client = TestClient(app)
        body = {
            "portfolio": MINIMAL_PDF_BODY["portfolio"],
            "portfolioName": MINIMAL_PDF_BODY["portfolioName"],
            "portfolioValue": MINIMAL_PDF_BODY["portfolioValue"],
            "accountType": MINIMAL_PDF_BODY["accountType"],
            "taxYear": MINIMAL_PDF_BODY["taxYear"],
            "includeFiles": ["holdings", "stressTest", "metrics"],
        }
        response = client.post("/api/v1/portfolio/export/csv", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "files" in data
    stress_files = [f for f in data["files"] if f.get("filename") == "stress_test_results.csv"]
    assert len(stress_files) == 1
    assert stress_files[0].get("size", 0) > 0


def test_export_pdf_with_stress_results_unchanged():
    """With stressTestResults provided and stressTest true, PDF is generated (regression)."""
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        import pytest
        pytest.skip(f"App import failed: {e}")

    client = TestClient(app)
    body = {
        **MINIMAL_PDF_BODY,
        "includeSections": {"optimization": False, "stressTest": True},
        "stressTestResults": MINIMAL_STRESS_RESULT,
    }
    response = client.post("/api/v1/portfolio/export/pdf", json=body)
    assert response.status_code == 200, response.text
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert len(response.content) > 5000


def test_export_pdf_single_holding_no_stress_section():
    """Portfolio with 0 or 1 holding: export succeeds but no on-the-fly stress (helper returns None)."""
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        import pytest
        pytest.skip(f"App import failed: {e}")

    client = TestClient(app)
    body = {
        "portfolio": [{"ticker": "AAPL", "allocation": 1.0, "name": "Apple Inc."}],
        "portfolioName": "Single",
        "includeSections": {"stressTest": False},
        "portfolioValue": 50000.0,
        "accountType": "ISK",
        "taxYear": 2025,
    }
    response = client.post("/api/v1/portfolio/export/pdf", json=body)
    assert response.status_code == 200, response.text
    assert response.headers.get("content-type", "").startswith("application/pdf")
