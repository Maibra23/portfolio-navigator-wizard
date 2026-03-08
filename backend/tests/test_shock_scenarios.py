"""
Tests for shock scenarios module.

Tests the predefined macroeconomic shock scenarios used for
portfolio stress projections.
"""

import pytest
from utils.shock_scenarios import (
    PREDEFINED_SCENARIOS,
    get_scenario,
    list_scenarios,
    get_scenarios_by_severity,
    create_custom_scenario,
    get_scenario_impact_summary,
)


class TestPredefinedScenarios:
    """Test predefined scenario definitions."""

    def test_predefined_scenarios_exist(self):
        """Verify predefined scenarios dict is populated."""
        assert len(PREDEFINED_SCENARIOS) > 0
        assert "mild_recession" in PREDEFINED_SCENARIOS
        assert "severe_recession" in PREDEFINED_SCENARIOS
        assert "rate_hike" in PREDEFINED_SCENARIOS

    def test_scenario_required_fields(self):
        """Each scenario should have required fields."""
        required_fields = [
            "name",
            "description",
            "return_modifier",
            "volatility_modifier",
            "duration_months",
            "year_of_shock",
            "severity",
        ]

        for scenario_id, scenario in PREDEFINED_SCENARIOS.items():
            for field in required_fields:
                assert field in scenario, (
                    f"Scenario '{scenario_id}' missing required field '{field}'"
                )

    def test_return_modifier_range(self):
        """Return modifiers should be reasonable (between -50% and +50%)."""
        for scenario_id, scenario in PREDEFINED_SCENARIOS.items():
            mod = scenario["return_modifier"]
            assert -0.5 <= mod <= 0.5, (
                f"Scenario '{scenario_id}' has unrealistic return_modifier: {mod}"
            )

    def test_volatility_modifier_positive(self):
        """Volatility modifiers should be positive (usually > 1 for shocks)."""
        for scenario_id, scenario in PREDEFINED_SCENARIOS.items():
            mod = scenario["volatility_modifier"]
            assert mod > 0, (
                f"Scenario '{scenario_id}' has non-positive volatility_modifier: {mod}"
            )

    def test_duration_reasonable(self):
        """Duration should be between 1 and 60 months."""
        for scenario_id, scenario in PREDEFINED_SCENARIOS.items():
            duration = scenario["duration_months"]
            assert 1 <= duration <= 60, (
                f"Scenario '{scenario_id}' has unrealistic duration: {duration}"
            )


class TestGetScenario:
    """Test get_scenario function."""

    def test_get_existing_scenario(self):
        """Should return scenario dict for valid name."""
        scenario = get_scenario("mild_recession")

        assert scenario is not None
        assert scenario["name"] == "Mild Recession"
        assert "id" in scenario
        assert scenario["id"] == "mild_recession"

    def test_get_nonexistent_scenario(self):
        """Should return None for invalid name."""
        scenario = get_scenario("nonexistent_scenario")
        assert scenario is None

    def test_get_scenario_returns_copy(self):
        """Should return a copy, not the original dict."""
        scenario1 = get_scenario("mild_recession")
        scenario2 = get_scenario("mild_recession")

        # Modifying one should not affect the other
        scenario1["name"] = "Modified"
        assert scenario2["name"] == "Mild Recession"

    def test_get_all_predefined_scenarios(self):
        """Should be able to get all predefined scenarios."""
        for scenario_id in PREDEFINED_SCENARIOS:
            scenario = get_scenario(scenario_id)
            assert scenario is not None
            assert scenario["id"] == scenario_id


class TestListScenarios:
    """Test list_scenarios function."""

    def test_list_returns_all_scenarios(self):
        """Should return all predefined scenarios."""
        scenarios = list_scenarios()

        assert len(scenarios) == len(PREDEFINED_SCENARIOS)

    def test_list_scenario_structure(self):
        """Each listed scenario should have display fields."""
        scenarios = list_scenarios()

        required_fields = ["id", "name", "description", "severity", "duration_months"]

        for scenario in scenarios:
            for field in required_fields:
                assert field in scenario, f"Missing field '{field}' in scenario list"

    def test_list_has_return_impact_string(self):
        """Each scenario should have formatted return impact."""
        scenarios = list_scenarios()

        for scenario in scenarios:
            assert "return_impact" in scenario
            # Should be formatted like "+5%" or "-10%"
            assert "%" in scenario["return_impact"]


class TestGetScenariosBySeverity:
    """Test filtering scenarios by severity."""

    def test_filter_moderate(self):
        """Should return moderate severity scenarios."""
        scenarios = get_scenarios_by_severity("moderate")

        assert len(scenarios) > 0
        for scenario in scenarios:
            assert scenario["severity"] == "moderate"

    def test_filter_severe(self):
        """Should return severe severity scenarios."""
        scenarios = get_scenarios_by_severity("severe")

        assert len(scenarios) > 0
        for scenario in scenarios:
            assert scenario["severity"] == "severe"

    def test_filter_nonexistent_severity(self):
        """Should return empty list for unknown severity."""
        scenarios = get_scenarios_by_severity("extreme")
        assert len(scenarios) == 0


class TestCreateCustomScenario:
    """Test custom scenario creation."""

    def test_create_basic_custom_scenario(self):
        """Should create a valid custom scenario."""
        scenario = create_custom_scenario(
            name="Test Shock",
            description="A test shock scenario",
            return_modifier=-0.10,
            volatility_modifier=1.5,
            duration_months=12,
            year_of_shock=1
        )

        assert scenario["name"] == "Test Shock"
        assert scenario["return_modifier"] == -0.10
        assert scenario["volatility_modifier"] == 1.5
        assert scenario["duration_months"] == 12
        assert scenario["is_custom"] is True

    def test_custom_scenario_caps_return_modifier(self):
        """Should cap return modifier at +/- 50%."""
        scenario = create_custom_scenario(
            name="Extreme",
            description="Extreme scenario",
            return_modifier=-0.80,  # Too extreme
            volatility_modifier=1.5,
            duration_months=12,
        )

        assert scenario["return_modifier"] == -0.5  # Capped

    def test_custom_scenario_caps_volatility_modifier(self):
        """Should cap volatility modifier at 0.5 to 5.0."""
        scenario_low = create_custom_scenario(
            name="Low Vol",
            description="Low volatility",
            return_modifier=-0.10,
            volatility_modifier=0.1,  # Too low
            duration_months=12,
        )
        assert scenario_low["volatility_modifier"] == 0.5  # Minimum

        scenario_high = create_custom_scenario(
            name="High Vol",
            description="High volatility",
            return_modifier=-0.10,
            volatility_modifier=10.0,  # Too high
            duration_months=12,
        )
        assert scenario_high["volatility_modifier"] == 5.0  # Maximum

    def test_custom_scenario_caps_duration(self):
        """Should cap duration at 1 to 60 months."""
        scenario = create_custom_scenario(
            name="Long",
            description="Long scenario",
            return_modifier=-0.10,
            volatility_modifier=1.5,
            duration_months=100,  # Too long
        )

        assert scenario["duration_months"] == 60  # Capped

    def test_custom_scenario_severity_calculation(self):
        """Severity should be calculated based on impact."""
        # Mild scenario
        mild = create_custom_scenario(
            name="Mild",
            description="Mild",
            return_modifier=-0.05,
            volatility_modifier=1.2,
            duration_months=6,
        )
        assert mild["severity"] in ["mild", "moderate"]

        # Severe scenario
        severe = create_custom_scenario(
            name="Severe",
            description="Severe",
            return_modifier=-0.40,
            volatility_modifier=2.5,
            duration_months=24,
        )
        assert severe["severity"] == "severe"


class TestGetScenarioImpactSummary:
    """Test impact summary calculation."""

    def test_impact_summary_structure(self):
        """Should return expected impact summary fields."""
        scenario = get_scenario("mild_recession")
        summary = get_scenario_impact_summary(scenario, 100000)

        expected_fields = [
            "scenario_name",
            "cumulative_return_impact",
            "estimated_loss",
            "estimated_final_value",
            "duration_months",
            "severity",
        ]

        for field in expected_fields:
            assert field in summary, f"Missing field '{field}' in impact summary"

    def test_impact_summary_values(self):
        """Impact values should be reasonable."""
        scenario = get_scenario("mild_recession")
        summary = get_scenario_impact_summary(scenario, 100000)

        # Loss should be positive for negative return modifier
        assert summary["estimated_loss"] > 0

        # Final value should be less than initial for negative shock
        assert summary["estimated_final_value"] < 100000

    def test_impact_summary_with_positive_modifier(self):
        """Should handle positive return modifiers."""
        scenario = {
            "name": "Bull Market",
            "return_modifier": 0.10,
            "duration_months": 12,
            "severity": "positive",
        }
        summary = get_scenario_impact_summary(scenario, 100000)

        # Should show no loss for positive modifier
        assert summary["estimated_loss"] == 0
        assert summary["estimated_final_value"] > 100000
