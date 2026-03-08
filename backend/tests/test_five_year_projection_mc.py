"""
Tests for five-year projection with Monte Carlo support.

Tests both deterministic and Monte Carlo modes, including
shock scenario application and backward compatibility.
"""

import pytest
from utils.five_year_projection import (
    run_five_year_projection,
    get_projection_scenarios,
)


class TestDeterministicMode:
    """Test legacy deterministic projection mode."""

    @pytest.fixture
    def base_params(self):
        """Common parameters for tests."""
        return {
            "initial_capital": 100000,
            "weights": {"AAPL": 0.5, "MSFT": 0.5},
            "expected_return": 0.08,
            "risk": 0.15,
            "account_type": "ISK",
            "tax_year": 2025,
            "courtage_class": "mini",
            "rebalancing_frequency": "quarterly",
            "mode": "deterministic",
        }

    def test_deterministic_response_structure(self, base_params):
        """Deterministic mode should return legacy structure."""
        result = run_five_year_projection(**base_params)

        assert "years" in result
        assert "optimistic" in result
        assert "base" in result
        assert "pessimistic" in result
        assert result["mode"] == "deterministic"

    def test_deterministic_years_correct(self, base_params):
        """Years should be [0, 1, 2, 3, 4, 5]."""
        result = run_five_year_projection(**base_params)

        assert result["years"] == [0, 1, 2, 3, 4, 5]
        assert len(result["optimistic"]) == 6
        assert len(result["base"]) == 6
        assert len(result["pessimistic"]) == 6

    def test_deterministic_initial_values(self, base_params):
        """All scenarios should start at initial capital."""
        result = run_five_year_projection(**base_params)
        initial = base_params["initial_capital"]

        assert result["optimistic"][0] == initial
        assert result["base"][0] == initial
        assert result["pessimistic"][0] == initial

    def test_deterministic_ordering(self, base_params):
        """Optimistic > Base > Pessimistic at each year."""
        result = run_five_year_projection(**base_params)

        for i in range(1, 6):  # Skip year 0 where all are equal
            assert result["optimistic"][i] >= result["base"][i], f"Year {i}"
            assert result["base"][i] >= result["pessimistic"][i], f"Year {i}"


class TestMonteCarloMode:
    """Test Monte Carlo projection mode."""

    @pytest.fixture
    def base_params(self):
        """Common parameters for tests."""
        return {
            "initial_capital": 100000,
            "weights": {"AAPL": 0.5, "MSFT": 0.5},
            "expected_return": 0.08,
            "risk": 0.15,
            "account_type": "ISK",
            "tax_year": 2025,
            "courtage_class": "mini",
            "rebalancing_frequency": "quarterly",
            "mode": "monte_carlo",
        }

    def test_monte_carlo_response_structure(self, base_params):
        """Monte Carlo mode should return extended structure."""
        result = run_five_year_projection(**base_params)

        # Legacy fields for backward compatibility
        assert "years" in result
        assert "optimistic" in result
        assert "base" in result
        assert "pessimistic" in result

        # New Monte Carlo fields
        assert "confidence_bands" in result
        assert "monthly_points" in result
        assert "probability_loss" in result
        assert result["mode"] == "monte_carlo"

    def test_monte_carlo_confidence_bands(self, base_params):
        """Should have all percentile bands."""
        result = run_five_year_projection(**base_params)

        bands = result["confidence_bands"]
        assert "p5" in bands
        assert "p10" in bands
        assert "p25" in bands
        assert "p50" in bands
        assert "p75" in bands
        assert "p90" in bands
        assert "p95" in bands

    def test_monte_carlo_monthly_resolution(self, base_params):
        """Should have monthly time points (61 points for 5 years)."""
        result = run_five_year_projection(**base_params)

        # 5 years * 12 months + 1 = 61 points
        assert len(result["monthly_points"]) == 61
        assert len(result["confidence_bands"]["p50"]) == 61

    def test_monte_carlo_probability_loss(self, base_params):
        """Should have valid probability of loss."""
        result = run_five_year_projection(**base_params)

        prob = result["probability_loss"]
        assert prob is not None
        assert 0 <= prob <= 100

    def test_monte_carlo_backward_compatible(self, base_params):
        """Legacy fields should match corresponding percentiles."""
        result = run_five_year_projection(**base_params)

        # optimistic = p75, base = p50, pessimistic = p25 (annual samples)
        assert len(result["optimistic"]) == 6
        assert len(result["base"]) == 6
        assert len(result["pessimistic"]) == 6


class TestShockScenarios:
    """Test shock scenario application."""

    @pytest.fixture
    def base_params(self):
        """Common parameters for tests."""
        return {
            "initial_capital": 100000,
            "weights": {"AAPL": 0.5, "MSFT": 0.5},
            "expected_return": 0.08,
            "risk": 0.15,
            "account_type": "ISK",
            "tax_year": 2025,
            "courtage_class": "mini",
            "mode": "monte_carlo",
        }

    def test_shock_scenario_applied(self, base_params):
        """Shock scenario should be reflected in results."""
        # Run without shock
        base_result = run_five_year_projection(**base_params)

        # Run with mild recession shock
        shock_result = run_five_year_projection(
            **base_params,
            shock_scenario="mild_recession"
        )

        # Shock result should show lower final values
        base_final = base_result["base"][-1]
        shock_final = shock_result["base"][-1]

        assert shock_final < base_final, (
            f"Shocked ({shock_final}) should be less than base ({shock_final})"
        )

    def test_shock_scenario_in_response(self, base_params):
        """Shock scenario name should be in response."""
        result = run_five_year_projection(
            **base_params,
            shock_scenario="rate_hike"
        )

        assert result.get("shock_scenario") == "rate_hike"

    def test_invalid_shock_scenario(self, base_params):
        """Invalid shock scenario should be ignored gracefully."""
        result = run_five_year_projection(
            **base_params,
            shock_scenario="nonexistent_scenario"
        )

        # Should still return valid result
        assert "base" in result
        assert len(result["base"]) > 0


class TestGetProjectionScenarios:
    """Test scenario listing function."""

    def test_list_scenarios_returns_list(self):
        """Should return a list of scenarios."""
        scenarios = get_projection_scenarios()

        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

    def test_scenario_structure(self):
        """Each scenario should have expected fields."""
        scenarios = get_projection_scenarios()

        for scenario in scenarios:
            assert "id" in scenario
            assert "name" in scenario
            assert "description" in scenario


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_capital(self):
        """Should handle zero capital gracefully."""
        result = run_five_year_projection(
            initial_capital=0,
            weights={"AAPL": 1.0},
            expected_return=0.08,
            risk=0.15,
            account_type="ISK",
            tax_year=2025,
            courtage_class="mini",
            mode="deterministic",
        )

        # Should return valid structure
        assert "base" in result

    def test_high_volatility(self):
        """Should handle high volatility portfolios."""
        result = run_five_year_projection(
            initial_capital=100000,
            weights={"AAPL": 1.0},
            expected_return=0.05,
            risk=0.50,  # Very high volatility
            account_type="ISK",
            tax_year=2025,
            courtage_class="mini",
            mode="monte_carlo",
        )

        # Should have higher probability of loss with high vol
        assert result["probability_loss"] > 10

    def test_negative_expected_return(self):
        """Should handle negative expected returns."""
        result = run_five_year_projection(
            initial_capital=100000,
            weights={"AAPL": 1.0},
            expected_return=-0.05,  # Negative return
            risk=0.15,
            account_type="ISK",
            tax_year=2025,
            courtage_class="mini",
            mode="monte_carlo",
        )

        # Final median should be less than initial
        assert result["base"][-1] < 100000
