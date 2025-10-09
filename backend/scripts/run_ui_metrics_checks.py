import json
import math
from urllib import request as urlrequest

BASE = "http://localhost:8000/api/portfolio"

RISK_PROFILES = [
    "very-conservative",
    "conservative",
    "moderate",
    "aggressive",
    "very-aggressive",
]


def http_get_json(url: str):
    with urlrequest.urlopen(url, timeout=20) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


def http_post_json(url: str, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urlrequest.urlopen(req, timeout=30) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


def approx_equal(a: float, b: float, rel=1e-3, abs_tol=1e-4) -> bool:
    if a is None or b is None:
        return False
    if any(map(lambda x: math.isnan(x) or math.isinf(x), [a, b])):
        return False
    return abs(a - b) <= max(rel * max(abs(a), abs(b)), abs_tol)


def run_switch_checks() -> dict:
    results = {rp: {"switch_pass": True, "cases": 0, "fails": 0} for rp in RISK_PROFILES}
    for rp in RISK_PROFILES:
        recs = http_get_json(f"{BASE}/recommendations/{rp}")
        if not recs:
            results[rp]["switch_pass"] = False
            continue
        for i in range(5):
            rec = recs[i % len(recs)]
            allocs = rec.get("portfolio", [])
            live = http_post_json(f"{BASE}/calculate-metrics", {"allocations": allocs, "riskProfile": rp})
            results[rp]["cases"] += 1
            if not (
                approx_equal(live.get("expectedReturn"), rec.get("expectedReturn"))
                and approx_equal(live.get("risk"), rec.get("risk"))
                and approx_equal(live.get("diversificationScore"), rec.get("diversificationScore"), rel=1e-2, abs_tol=1e-2)
            ):
                results[rp]["fails"] += 1
                results[rp]["switch_pass"] = False
    return results


def run_weight_editor_checks() -> dict:
    results = {rp: {"weight_pass": True, "cases": 0, "fails": 0} for rp in ["moderate", "aggressive"]}
    for rp in results.keys():
        recs = http_get_json(f"{BASE}/recommendations/{rp}")
        if not recs:
            results[rp]["weight_pass"] = False
            continue
        rec = recs[0]
        allocs = rec.get("portfolio", [])
        # baseline
        base = http_post_json(f"{BASE}/calculate-metrics", {"allocations": allocs, "riskProfile": rp})
        if not approx_equal(base.get("expectedReturn"), rec.get("expectedReturn")):
            results[rp]["weight_pass"] = False
            results[rp]["fails"] += 1
        results[rp]["cases"] += 1
        # tweak +1/-1 if possible
        if len(allocs) >= 2:
            edited = [dict(a) for a in allocs]
            edited[0]["allocation"] = round(edited[0]["allocation"] + 1.0, 2)
            edited[-1]["allocation"] = round(edited[-1]["allocation"] - 1.0, 2)
            live_after = http_post_json(f"{BASE}/calculate-metrics", {"allocations": edited, "riskProfile": rp})
            ok = (
                isinstance(live_after.get("expectedReturn"), (int, float))
                and isinstance(live_after.get("risk"), (int, float))
                and live_after.get("stockCount") == len(edited)
            )
            results[rp]["cases"] += 1
            if not ok:
                results[rp]["weight_pass"] = False
                results[rp]["fails"] += 1
    return results


def main():
    switch = run_switch_checks()
    weight = run_weight_editor_checks()
    summary = {"switch": switch, "weight": weight}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()


