#!/usr/bin/env python3
"""
Ad-hoc test for dynamic sector prioritization (aggressive profile)

Runs the dynamic weights computation and prints the resulting sector weights.
Also demonstrates feasibility with portfolio sizes 3 and 4 by selecting top-N
sectors by weight (this does not replace the full selection pipeline).
"""

import os
import sys
import json
from typing import List, Dict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from backend.utils.dynamic_sector_prioritization import get_dynamic_sector_weights
from backend.utils.redis_first_data_service import redis_first_data_service as data_service


def purge_cache(profiles):
    rc = getattr(data_service, 'redis_client', None) or getattr(data_service, 'r', None)
    if not rc:
        return
    for p in profiles:
        try:
            rc.delete(f"sector:weights:{p}")
        except Exception:
            pass


def run_profile(risk_profile: str):
    print(f"\n=== Profile: {risk_profile} ===")
    weights = get_dynamic_sector_weights(data_service, risk_profile, ttl_minutes=15)
    if not weights:
        print("No dynamic weights available (insufficient data) — fallback to static weights recommended.")
        return None, None

    sorted_w = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
    print("Dynamic sector weights (descending):")
    for k, v in sorted_w:
        print(f"  {k:20s}  {v:6.2%}")

    for k in (3, 4):
        top = sorted_w[:k]
        coverage = sum(w for _, w in top)
        print(f"Top {k} sectors cover {coverage:.2%} of target weights:")
        for name, w in top:
            print(f"  - {name:20s} {w:6.2%}")
    return weights, sorted_w


def main():
    print("Testing dynamic sector weights using 12M + full-period momentum\n")
    profiles = ['aggressive', 'very-aggressive']
    purge_cache(profiles)

    results = {}
    for p in profiles:
        weights, sorted_w = run_profile(p)
        results[p] = {
            'weights': weights or {},
            'top3': (sorted_w or [])[:3],
            'top4': (sorted_w or [])[:4]
        }

    print("\nJSON summary:")
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()


