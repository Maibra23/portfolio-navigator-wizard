"""
Predefined macroeconomic shock scenarios for portfolio stress testing.

Each scenario models a specific market condition with:
- return_modifier: Additive change to expected returns (negative for adverse scenarios)
- volatility_modifier: Multiplicative change to volatility (>1 for increased uncertainty)
- duration_months: How long the shock persists
- year_of_shock: When the shock starts (default: year 1)

These scenarios are based on historical crisis characteristics and
can be applied to Monte Carlo projections to show "what-if" outcomes.
"""

from typing import Dict, List, Any, Optional


# Predefined shock scenarios based on historical crisis patterns
PREDEFINED_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "rate_hike": {
        "name": "Interest Rate Shock",
        "description": "Aggressive central bank tightening (+200bps). Impacts growth stocks and bonds.",
        "return_modifier": -0.08,  # -8% annual return impact
        "volatility_modifier": 1.5,  # 50% higher volatility
        "duration_months": 12,
        "year_of_shock": 1,
        "severity": "moderate",
        "historical_reference": "2022 Fed rate hikes",
        "sectors_most_affected": ["Technology", "Real Estate", "Utilities"],
    },

    "mild_recession": {
        "name": "Mild Recession",
        "description": "Economic contraction with GDP decline of ~2%. Typical business cycle downturn.",
        "return_modifier": -0.15,  # -15% annual return impact
        "volatility_modifier": 1.8,  # 80% higher volatility
        "duration_months": 18,
        "year_of_shock": 1,
        "severity": "moderate",
        "historical_reference": "2001 Dot-com recession",
        "sectors_most_affected": ["Consumer Discretionary", "Financials", "Industrials"],
    },

    "severe_recession": {
        "name": "Severe Recession",
        "description": "Major financial crisis with systemic risk. Similar to 2008 Global Financial Crisis.",
        "return_modifier": -0.30,  # -30% annual return impact
        "volatility_modifier": 2.5,  # 150% higher volatility
        "duration_months": 24,
        "year_of_shock": 1,
        "severity": "severe",
        "historical_reference": "2008 Financial Crisis",
        "sectors_most_affected": ["Financials", "Real Estate", "Consumer Discretionary"],
    },

    "stagflation": {
        "name": "Stagflation",
        "description": "High inflation combined with economic stagnation. Difficult environment for most assets.",
        "return_modifier": -0.10,  # -10% annual return impact
        "volatility_modifier": 2.0,  # 100% higher volatility
        "duration_months": 24,
        "year_of_shock": 1,
        "severity": "moderate",
        "historical_reference": "1970s stagflation",
        "sectors_most_affected": ["Consumer Staples", "Growth Stocks", "Bonds"],
    },

    "tech_correction": {
        "name": "Tech Sector Correction",
        "description": "Sharp decline in technology stocks. Other sectors relatively resilient.",
        "return_modifier": -0.20,  # -20% annual return impact (weighted by tech exposure)
        "volatility_modifier": 2.0,  # 100% higher volatility
        "duration_months": 6,
        "year_of_shock": 1,
        "severity": "moderate",
        "historical_reference": "2022 Tech correction",
        "sectors_most_affected": ["Technology", "Communication Services"],
    },

    "pandemic_shock": {
        "name": "Pandemic Shock",
        "description": "Sudden economic shutdown with rapid recovery. V-shaped pattern.",
        "return_modifier": -0.25,  # -25% initial shock
        "volatility_modifier": 3.0,  # 200% higher volatility
        "duration_months": 4,  # Short but intense
        "year_of_shock": 1,
        "severity": "severe",
        "historical_reference": "COVID-19 March 2020",
        "sectors_most_affected": ["Travel", "Hospitality", "Energy"],
        "recovery_pattern": "v_shaped",
    },

    "currency_crisis": {
        "name": "Currency Crisis",
        "description": "Major currency devaluation affecting international investments.",
        "return_modifier": -0.12,  # -12% annual return impact
        "volatility_modifier": 1.8,
        "duration_months": 12,
        "year_of_shock": 1,
        "severity": "moderate",
        "historical_reference": "1997 Asian Financial Crisis",
        "sectors_most_affected": ["International Stocks", "Emerging Markets"],
    },

    "deflation": {
        "name": "Deflationary Spiral",
        "description": "Persistent deflation leading to economic contraction. Japan-style scenario.",
        "return_modifier": -0.05,  # -5% annual return impact
        "volatility_modifier": 1.3,  # 30% higher volatility
        "duration_months": 36,  # Long duration
        "year_of_shock": 1,
        "severity": "moderate",
        "historical_reference": "Japan 1990s",
        "sectors_most_affected": ["Banks", "Real Estate", "Consumer"],
    },
}


def get_scenario(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a predefined shock scenario by name.

    Args:
        name: Scenario identifier (e.g., "mild_recession", "tech_correction")

    Returns:
        Scenario dict if found, None otherwise
    """
    scenario = PREDEFINED_SCENARIOS.get(name)
    if scenario:
        # Return a copy to prevent mutation
        return {**scenario, "id": name}
    return None


def list_scenarios() -> List[Dict[str, Any]]:
    """
    Get all available shock scenarios.

    Returns:
        List of scenario dicts with id, name, description, and severity
    """
    scenarios = []
    for scenario_id, scenario in PREDEFINED_SCENARIOS.items():
        scenarios.append({
            "id": scenario_id,
            "name": scenario["name"],
            "description": scenario["description"],
            "severity": scenario["severity"],
            "duration_months": scenario["duration_months"],
            "return_impact": f"{scenario['return_modifier'] * 100:+.0f}%",
        })
    return scenarios


def get_scenarios_by_severity(severity: str) -> List[Dict[str, Any]]:
    """
    Filter scenarios by severity level.

    Args:
        severity: "mild", "moderate", or "severe"

    Returns:
        List of matching scenarios
    """
    return [
        {**scenario, "id": name}
        for name, scenario in PREDEFINED_SCENARIOS.items()
        if scenario.get("severity") == severity
    ]


def create_custom_scenario(
    name: str,
    description: str,
    return_modifier: float,
    volatility_modifier: float,
    duration_months: int,
    year_of_shock: int = 1
) -> Dict[str, Any]:
    """
    Create a custom shock scenario.

    Args:
        name: Display name for the scenario
        description: Explanation of the scenario
        return_modifier: Additive change to returns (e.g., -0.15 for -15%)
        volatility_modifier: Multiplicative change to volatility (e.g., 1.5)
        duration_months: How long the shock lasts
        year_of_shock: When shock starts (1 = beginning of year 1)

    Returns:
        Custom scenario dict
    """
    # Validate inputs
    if return_modifier > 0.5:
        return_modifier = 0.5  # Cap at +50%
    if return_modifier < -0.5:
        return_modifier = -0.5  # Cap at -50%

    if volatility_modifier < 0.5:
        volatility_modifier = 0.5  # Minimum 50% of base
    if volatility_modifier > 5.0:
        volatility_modifier = 5.0  # Maximum 500% of base

    if duration_months < 1:
        duration_months = 1
    if duration_months > 60:
        duration_months = 60  # Max 5 years

    if year_of_shock < 1:
        year_of_shock = 1
    if year_of_shock > 5:
        year_of_shock = 5

    # Determine severity based on parameters
    impact_score = abs(return_modifier) * volatility_modifier
    if impact_score > 0.5:
        severity = "severe"
    elif impact_score > 0.2:
        severity = "moderate"
    else:
        severity = "mild"

    return {
        "id": "custom",
        "name": name,
        "description": description,
        "return_modifier": return_modifier,
        "volatility_modifier": volatility_modifier,
        "duration_months": duration_months,
        "year_of_shock": year_of_shock,
        "severity": severity,
        "historical_reference": "Custom scenario",
        "sectors_most_affected": [],
        "is_custom": True,
    }


def get_scenario_impact_summary(scenario: Dict[str, Any], initial_capital: float) -> Dict[str, Any]:
    """
    Calculate a summary of expected scenario impact.

    Args:
        scenario: Shock scenario dict
        initial_capital: Starting portfolio value

    Returns:
        Dict with estimated impact metrics
    """
    return_mod = scenario.get("return_modifier", 0)
    duration = scenario.get("duration_months", 12)

    # Simplified impact calculation
    # Assumes the shock compounds over the duration
    cumulative_impact = (1 + return_mod / 12) ** duration - 1

    estimated_loss = initial_capital * abs(cumulative_impact) if cumulative_impact < 0 else 0
    estimated_final = initial_capital * (1 + cumulative_impact)

    return {
        "scenario_name": scenario.get("name", "Unknown"),
        "cumulative_return_impact": round(cumulative_impact * 100, 1),
        "estimated_loss": round(estimated_loss, 2),
        "estimated_final_value": round(max(0, estimated_final), 2),
        "duration_months": duration,
        "severity": scenario.get("severity", "unknown"),
    }
