"""
Basic sanity tests that don't require the full app.
These verify the test infrastructure works in CI.
"""


def test_python_works():
    """Sanity check that Python and pytest are working."""
    assert 1 + 1 == 2


def test_imports_work():
    """Verify basic imports work."""
    import json
    import os
    assert json.dumps({"test": True}) == '{"test": true}'
    assert os.path.exists(".")
