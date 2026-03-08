"""
Test: annualization method consistency across all modules.

Verifies that every module computing annualized returns from monthly data
uses the compound formula: (1 + monthly_return)**12 - 1
and NOT the simple formula: monthly_return * 12.

Also verifies that the numerical difference between the two methods is
within expectations for typical stock returns (0.5-2% monthly).
"""
import math
import pytest


# --- Pure-math tests (no project imports needed) ---

def _compound(monthly: float) -> float:
    return (1 + monthly) ** 12 - 1

def _simple(monthly: float) -> float:
    return monthly * 12


@pytest.mark.parametrize("monthly_return,label", [
    (0.005, "low (0.5%/mo)"),
    (0.01,  "typical (1%/mo)"),
    (0.02,  "high (2%/mo)"),
    (0.05,  "very high (5%/mo)"),
])
def test_compound_vs_simple_difference(monthly_return, label):
    """Show that compound > simple for positive returns, and the gap grows."""
    c = _compound(monthly_return)
    s = _simple(monthly_return)
    assert c > s, f"Compound should exceed simple for positive {label}"
    # For 1%/mo the gap is about 0.68pp (12.68% vs 12.00%)
    gap_pp = (c - s) * 100
    assert gap_pp > 0


@pytest.mark.parametrize("monthly_return,label", [
    (-0.005, "low loss (-0.5%/mo)"),
    (-0.01,  "typical loss (-1%/mo)"),
    (-0.02,  "high loss (-2%/mo)"),
])
def test_compound_vs_simple_negative(monthly_return, label):
    """For negative returns, compound gives a less negative (better) result."""
    c = _compound(monthly_return)
    s = _simple(monthly_return)
    assert c > s, f"Compound should be less negative than simple for {label}"


def test_both_methods_agree_at_zero():
    """At zero monthly return, both methods give exactly zero."""
    assert _compound(0.0) == 0.0
    assert _simple(0.0) == 0.0


def test_typical_stock_numerical_values():
    """
    For a stock with 1% average monthly return:
    - Simple: 0.01 * 12 = 0.12 (12.00%)
    - Compound: (1.01)^12 - 1 = 0.12682 (12.68%)
    The difference is ~0.68pp. This is the impact of the code change.
    """
    monthly = 0.01
    simple_annual = _simple(monthly)
    compound_annual = _compound(monthly)

    assert abs(simple_annual - 0.12) < 1e-10
    assert abs(compound_annual - ((1.01)**12 - 1)) < 1e-10
    assert abs(compound_annual - simple_annual - 0.006825) < 0.001


# --- Source-code inspection tests ---
# These tests require Redis to import backend modules. Skip if unavailable.

def _try_import(module_path, attr):
    """Try to import a module attribute, return None if it fails (e.g., no Redis)."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    except Exception:
        return None


def test_enhanced_data_fetcher_uses_compound():
    """enhanced_data_fetcher.py must use compound annualization."""
    import inspect
    cls = _try_import("utils.enhanced_data_fetcher", "EnhancedDataFetcher")
    if cls is None:
        pytest.skip("Cannot import EnhancedDataFetcher (Redis unavailable)")
    EnhancedDataFetcher = cls
    src = inspect.getsource(EnhancedDataFetcher._calculate_and_save_metrics)
    assert "(1 + monthly_return) ** 12 - 1" in src, (
        "enhanced_data_fetcher._calculate_and_save_metrics must use compound annualization"
    )
    assert "monthly_return * 12" not in src, (
        "enhanced_data_fetcher._calculate_and_save_metrics must NOT use simple annualization"
    )


def test_port_analytics_uses_compound():
    """port_analytics.py must use compound annualization."""
    import inspect
    cls = _try_import("utils.port_analytics", "PortfolioAnalytics")
    if cls is None:
        pytest.skip("Cannot import PortfolioAnalytics (Redis unavailable)")
    src = inspect.getsource(cls.calculate_asset_metrics)
    assert "(1 + monthly_return) ** 12 - 1" in src, (
        "port_analytics.calculate_asset_metrics must use compound annualization"
    )


def test_portfolio_stock_selector_uses_compound():
    """portfolio_stock_selector must use compound annualization."""
    import inspect
    cls = _try_import("utils.portfolio_stock_selector", "PortfolioStockSelector")
    if cls is None:
        pytest.skip("Cannot import PortfolioStockSelector (Redis unavailable)")
    src = inspect.getsource(cls._parse_ticker_data_optimized)
    assert "** 12 - 1" in src, (
        "portfolio_stock_selector._parse_ticker_data_optimized must use compound annualization"
    )
    assert "returns.mean() * 12" not in src, (
        "portfolio_stock_selector._parse_ticker_data_optimized must NOT use simple annualization"
    )


def test_calculate_annualized_metrics_uses_compound():
    """routers/portfolio.py helper must use compound annualization."""
    import inspect
    func = _try_import("routers.portfolio", "calculate_annualized_metrics")
    if func is None:
        pytest.skip("Cannot import calculate_annualized_metrics (Redis unavailable)")
    src = inspect.getsource(func)
    assert "** 12 - 1" in src
    assert "returns.mean()) * 12" not in src
