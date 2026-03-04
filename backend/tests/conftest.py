"""
Pytest configuration for backend tests.
Handles graceful skipping when app dependencies (Redis, etc.) are unavailable.
"""

import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_app: mark test as requiring full app (skip if unavailable)"
    )


@pytest.fixture(scope="session")
def app_available():
    """Check if the FastAPI app can be imported (requires Redis, etc.)."""
    try:
        from main import app
        return True
    except Exception:
        return False


@pytest.fixture
def test_client(app_available):
    """Provide a TestClient, skipping if app is unavailable."""
    if not app_available:
        pytest.skip("App not available (missing Redis or dependencies)")

    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)
