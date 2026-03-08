"""
Tests for Monte Carlo projection engine.

Tests the GBM-based Monte Carlo simulation for portfolio projections,
including path generation, tax drag application, and shock scenarios.
"""

import pytest
import numpy as np
from utils.monte_carlo_projection import MonteCarloProjector, monte_carlo_projector


class TestMonteCarloProjector:
    """Test suite for MonteCarloProjector class."""

    @pytest.fixture
    def projector(self):
        """Create a fresh projector instance."""
        return MonteCarloProjector()

    @pytest.fixture
    def base_params(self):
        """Common parameters for tests."""
        return {
            "initial_capital": 100000,
            "annual_expected_return": 0.08,
            "annual_volatility": 0.15,
            "years": 5,
            "num_simulations": 1000,
            "monthly_steps": True,
        }

    def test_simulate_paths_shape(self, projector, base_params):
        """Verify output dict has correct keys and list lengths."""
        result = projector.simulate_paths(**base_params)

        # Check required keys exist
        assert "time_points" in result
        assert "percentiles" in result
        assert "mean_path" in result
        assert "probability_loss" in result
        assert "statistics" in result

        # Check time points length (5 years * 12 months + 1 = 61 points)
        expected_points = 5 * 12 + 1
        assert len(result["time_points"]) == expected_points

        # Check all percentile paths have correct length
        for pct_key in ["p5", "p10", "p25", "p50", "p75", "p90", "p95"]:
            assert pct_key in result["percentiles"]
            assert len(result["percentiles"][pct_key]) == expected_points

        # Check mean path length
        assert len(result["mean_path"]) == expected_points

    def test_simulate_paths_initial_value(self, projector, base_params):
        """All percentile paths should start at initial_capital."""
        result = projector.simulate_paths(**base_params)
        initial = base_params["initial_capital"]

        # All paths start at initial capital
        for pct_key in result["percentiles"]:
            assert abs(result["percentiles"][pct_key][0] - initial) < 0.01

        assert abs(result["mean_path"][0] - initial) < 0.01

    def test_simulate_paths_monotonic_percentiles(self, projector, base_params):
        """At each time point, p5 < p25 < p50 < p75 < p95."""
        result = projector.simulate_paths(**base_params)
        pcts = result["percentiles"]

        for i in range(len(result["time_points"])):
            # Skip time 0 where all values are equal
            if i == 0:
                continue

            assert pcts["p5"][i] <= pcts["p10"][i], f"p5 > p10 at index {i}"
            assert pcts["p10"][i] <= pcts["p25"][i], f"p10 > p25 at index {i}"
            assert pcts["p25"][i] <= pcts["p50"][i], f"p25 > p50 at index {i}"
            assert pcts["p50"][i] <= pcts["p75"][i], f"p50 > p75 at index {i}"
            assert pcts["p75"][i] <= pcts["p90"][i], f"p75 > p90 at index {i}"
            assert pcts["p90"][i] <= pcts["p95"][i], f"p90 > p95 at index {i}"

    def test_simulate_paths_deterministic_seed(self, projector, base_params):
        """Same seed produces identical results."""
        params_with_seed = {**base_params, "seed": 42}

        result1 = projector.simulate_paths(**params_with_seed)
        result2 = projector.simulate_paths(**params_with_seed)

        # Percentiles should be identical
        for pct_key in result1["percentiles"]:
            np.testing.assert_array_almost_equal(
                result1["percentiles"][pct_key],
                result2["percentiles"][pct_key],
                decimal=6
            )

    def test_simulate_paths_zero_volatility(self, projector):
        """With zero volatility, all paths converge to deterministic growth."""
        result = projector.simulate_paths(
            initial_capital=100000,
            annual_expected_return=0.08,
            annual_volatility=0.001,  # Near-zero volatility
            years=5,
            num_simulations=100,
            monthly_steps=True,
            seed=42
        )

        # With near-zero volatility, all percentiles should be very close
        final_p5 = result["percentiles"]["p5"][-1]
        final_p95 = result["percentiles"]["p95"][-1]

        # Allow 5% spread due to minimum volatility guard
        spread = (final_p95 - final_p5) / final_p5
        assert spread < 0.1, f"Spread too large for near-zero volatility: {spread}"

    def test_simulate_paths_can_lose_money(self, projector):
        """With high volatility and low return, probability_loss > 0."""
        result = projector.simulate_paths(
            initial_capital=100000,
            annual_expected_return=0.02,  # Low return
            annual_volatility=0.30,  # High volatility
            years=5,
            num_simulations=5000,
            monthly_steps=True,
            seed=42
        )

        # Should have meaningful probability of loss
        assert result["probability_loss"] > 5, (
            f"Expected significant loss probability, got {result['probability_loss']}%"
        )

    def test_simulate_paths_annual_steps(self, projector):
        """Test with annual (not monthly) steps."""
        result = projector.simulate_paths(
            initial_capital=100000,
            annual_expected_return=0.08,
            annual_volatility=0.15,
            years=5,
            num_simulations=1000,
            monthly_steps=False,  # Annual steps
            seed=42
        )

        # Should have 6 time points (0, 1, 2, 3, 4, 5)
        assert len(result["time_points"]) == 6
        assert result["time_points"] == [0, 1, 2, 3, 4, 5]

    def test_simulate_paths_with_tax_drag(self, projector):
        """Tax-adjusted paths should be lower than non-tax-adjusted."""
        # First run without tax
        base_result = projector.simulate_paths(
            initial_capital=100000,
            annual_expected_return=0.10,
            annual_volatility=0.15,
            years=5,
            num_simulations=1000,
            seed=42
        )

        # Run with tax drag
        tax_result = projector.simulate_paths_with_tax_drag(
            initial_capital=100000,
            annual_expected_return=0.10,
            annual_volatility=0.15,
            account_type="ISK",
            tax_year=2025,
            courtage_class="mini",
            weights={"AAPL": 0.5, "MSFT": 0.5},
            years=5,
            num_simulations=1000,
            seed=42
        )

        # Tax-adjusted final values should be lower
        base_median_final = base_result["percentiles"]["p50"][-1]
        tax_median_final = tax_result["percentiles"]["p50"][-1]

        assert tax_median_final < base_median_final, (
            f"Tax-adjusted ({tax_median_final}) should be less than base ({base_median_final})"
        )

    def test_apply_shock_scenario(self, projector, base_params):
        """Shocked paths should diverge from base paths during shock period."""
        base_result = projector.simulate_paths(**base_params, seed=42)

        shock_scenario = {
            "year_of_shock": 1,
            "return_modifier": -0.20,
            "volatility_modifier": 2.0,
            "duration_months": 12,
            "description": "Test shock"
        }

        shocked_result = projector.apply_shock_scenario(
            base_result=base_result,
            shock_scenario=shock_scenario,
            initial_capital=base_params["initial_capital"]
        )

        # Shocked final values should be lower
        base_median_final = base_result["percentiles"]["p50"][-1]
        shocked_median_final = shocked_result["percentiles"]["p50"][-1]

        assert shocked_median_final < base_median_final, (
            f"Shocked ({shocked_median_final}) should be less than base ({base_median_final})"
        )

        # Check shock period metadata
        assert "shock_period" in shocked_result
        assert shocked_result["shock_period"]["start_month"] == 12  # Year 1 start

    def test_statistics_keys(self, projector, base_params):
        """Statistics dict should contain expected keys."""
        result = projector.simulate_paths(**base_params)

        expected_keys = ["mean_final", "median_final", "std_final", "min_final", "max_final"]
        for key in expected_keys:
            assert key in result["statistics"], f"Missing statistics key: {key}"

    def test_probability_values_valid(self, projector, base_params):
        """Probability values should be between 0 and 100."""
        result = projector.simulate_paths(**base_params)

        assert 0 <= result["probability_loss"] <= 100
        assert 0 <= result["probability_loss_20pct"] <= 100

    def test_fallback_on_error(self, projector):
        """Should return fallback result on invalid input."""
        result = projector.simulate_paths(
            initial_capital=-100,  # Invalid negative capital
            annual_expected_return=0.08,
            annual_volatility=0.15,
            years=5,
            num_simulations=1000,
        )

        # Should get a valid result structure even with bad input
        # (the implementation guards against negative capital)
        assert "time_points" in result
        assert "percentiles" in result


class TestModuleLevelInstance:
    """Test the module-level monte_carlo_projector instance."""

    def test_instance_exists(self):
        """Module-level instance should be available."""
        assert monte_carlo_projector is not None
        assert isinstance(monte_carlo_projector, MonteCarloProjector)

    def test_instance_functional(self):
        """Module-level instance should be functional."""
        result = monte_carlo_projector.simulate_paths(
            initial_capital=100000,
            annual_expected_return=0.08,
            annual_volatility=0.15,
            years=5,
            num_simulations=100,
            seed=42
        )

        assert "percentiles" in result
        assert len(result["percentiles"]["p50"]) == 61
