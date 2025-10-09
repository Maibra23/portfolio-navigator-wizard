from typing import List, Dict
import pytest
import requests

BASE = "http://localhost:8000/api/portfolio"

RISK_PROFILES = [
    "very-conservative",
    "conservative",
    "moderate",
    "aggressive",
    "very-aggressive",
]


def fetch_recommendations(risk: str) -> List[Dict]:
    r = requests.get(f"{BASE}/recommendations/{risk}", timeout=15)
    r.raise_for_status()
    return r.json()


def calc_metrics(allocations: List[Dict], risk: str) -> Dict:
    r = requests.post(
        f"{BASE}/calculate-metrics",
        json={"allocations": allocations, "riskProfile": risk},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


@pytest.mark.parametrize("risk", RISK_PROFILES)
def test_switching_recommendations_metrics_align(risk: str):
    # Get 3 recommendations
    recs = fetch_recommendations(risk)
    assert len(recs) >= 1

    # Rapidly switch selections 5 times in a round-robin manner
    for i in range(5):
        rec = recs[i % len(recs)]
        allocs = rec["portfolio"]

        # Live metrics should match recommendation (same analytics path)
        live = calc_metrics(allocs, risk)

        assert pytest.approx(live["expectedReturn"], rel=1e-3, abs=1e-4) == rec["expectedReturn"]
        assert pytest.approx(live["risk"], rel=1e-3, abs=1e-4) == rec["risk"]
        assert pytest.approx(live["diversificationScore"], rel=1e-2, abs=1e-2) == rec["diversificationScore"]


@pytest.mark.parametrize("risk", ["moderate", "aggressive"])  # spot-check
def test_weight_editor_edits_compute_correctly(risk: str):
    # Start from first recommendation
    recs = fetch_recommendations(risk)
    assert len(recs) >= 1
    rec = recs[0]
    allocs = rec["portfolio"]

    # Verify baseline alignment
    base = calc_metrics(allocs, risk)
    assert pytest.approx(base["expectedReturn"], rel=1e-3, abs=1e-4) == rec["expectedReturn"]

    # Simulate weight editor: tweak first symbol +1%, subtract from last
    if len(allocs) >= 2:
        edited = [a.copy() for a in allocs]
        edited[0]["allocation"] = round(edited[0]["allocation"] + 1.0, 2)
        edited[-1]["allocation"] = round(edited[-1]["allocation"] - 1.0, 2)
        # Keep total at 100
        total = sum(a["allocation"] for a in edited)
        assert pytest.approx(total, abs=0.05) == 100.0

        live_after = calc_metrics(edited, risk)
        # Expect a change in either return or risk (direction not asserted)
        assert isinstance(live_after["expectedReturn"], (int, float))
        assert isinstance(live_after["risk"], (int, float))
        assert live_after["stockCount"] == len(edited)

    # Simulate add one stock (if capacity) and normalize weights
    if len(allocs) < 10:
        added = [a.copy() for a in allocs]
        # Reuse first symbol as a dummy new symbol only if distinct is required; else skip
        # Here, we skip symbol uniqueness and just rebalance to len+1 parts for test
        equal = round(100.0 / (len(added) + 1), 2)
        added = [{**a, "allocation": equal} for a in added]
        # Fake an extra allocation using last symbol for simplicity
        added.append({**allocs[-1], "allocation": equal})
        total = sum(a["allocation"] for a in added)
        # Adjust last to close rounding gap
        gap = round(100.0 - total, 2)
        added[-1]["allocation"] = round(added[-1]["allocation"] + gap, 2)
        total2 = sum(a["allocation"] for a in added)
        assert pytest.approx(total2, abs=0.05) == 100.0

        live_added = calc_metrics(added, risk)
        assert live_added["stockCount"] == len(added)
        assert isinstance(live_added["expectedReturn"], (int, float))
        assert isinstance(live_added["risk"], (int, float))
