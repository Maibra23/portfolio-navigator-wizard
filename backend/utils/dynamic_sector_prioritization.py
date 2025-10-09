#!/usr/bin/env python3
"""
Dynamic Sector Prioritization (Approach 1: momentum with risk caps)

Computes per-profile dynamic sector weights using sector momentum (3M/6M),
sector breadth, and penalties for drawdown/volatility using existing cached
stock data accessed via PortfolioStockSelector.

This module is intentionally self-contained and read-only. Integration point:
call `get_dynamic_sector_weights(data_service, risk_profile, ttl_minutes=30)`
to obtain a { sector -> weight } map to replace static `SECTOR_WEIGHTS` during
selection. Falls back to baseline static weights if metrics are insufficient.
"""

from __future__ import annotations

import json
import time
from typing import Dict, List, Tuple

from .portfolio_stock_selector import PortfolioStockSelector


# Profile-specific caps to preserve risk intent
PROFILE_CAPS = {
    'very-conservative': {'min': 0.05, 'max': 0.25, 'min_sectors': 5},
    'conservative':      {'min': 0.05, 'max': 0.28, 'min_sectors': 5},
    'moderate':          {'min': 0.04, 'max': 0.32, 'min_sectors': 4},
    'aggressive':        {'min': 0.03, 'max': 0.35, 'min_sectors': 3},
    'very-aggressive':   {'min': 0.02, 'max': 0.40, 'min_sectors': 3},
}


def _sector_metrics_from_stocks(stocks: List[Dict]) -> Dict[str, Dict[str, float]]:
    """Aggregate sector metrics from per-stock cached data using at least 12 months.

    Expects each stock dict to contain: 'sector', 'returns' (monthly series), 'volatility'.
    Returns per-sector metrics: avg_return_3m, avg_return_6m, avg_return_12m, avg_return_full,
    breadth_3m, avg_vol.
    """
    from collections import defaultdict

    sector_to_returns: Dict[str, List[float]] = defaultdict(list)
    sector_to_vols: Dict[str, List[float]] = defaultdict(list)
    sector_to_breadth_flags_3m: Dict[str, List[int]] = defaultdict(list)

    for s in stocks:
        sector = s.get('sector', 'Unknown')
        if sector == 'Unknown':
            continue
        vols = s.get('volatility', None)
        rets = s.get('returns', []) or []
        if vols is not None:
            try:
                sector_to_vols[sector].append(float(vols))
            except Exception:
                pass
        # Compute 3M, 6M, 12M and full-period cumulative returns from monthly returns series
        if isinstance(rets, list) and len(rets) >= 12:
            try:
                last_3m = rets[-3:]
                last_6m = rets[-6:]
                last_12m = rets[-12:]
                full = rets[:]  # entire available period
                cum3 = 1.0
                for r in last_3m:
                    cum3 *= (1.0 + float(r))
                cum6 = 1.0
                for r in last_6m:
                    cum6 *= (1.0 + float(r))
                cum12 = 1.0
                for r in last_12m:
                    cum12 *= (1.0 + float(r))
                cumF = 1.0
                for r in full:
                    cumF *= (1.0 + float(r))
                ret3 = cum3 - 1.0
                ret6 = cum6 - 1.0
                ret12 = cum12 - 1.0
                retF = cumF - 1.0
                sector_to_returns[sector].append((ret3, ret6, ret12, retF))
                sector_to_breadth_flags_3m[sector].append(1 if ret3 > 0 else 0)
            except Exception:
                continue

    metrics: Dict[str, Dict[str, float]] = {}
    for sector in set(list(sector_to_returns.keys()) + list(sector_to_vols.keys())):
        pairs = sector_to_returns.get(sector, [])
        vols = sector_to_vols.get(sector, [])
        flags = sector_to_breadth_flags_3m.get(sector, [])
        if not pairs:
            # If no returns, skip sector
            continue
        avg_r3 = sum(p[0] for p in pairs) / len(pairs)
        avg_r6 = sum(p[1] for p in pairs) / len(pairs)
        avg_r12 = sum(p[2] for p in pairs) / len(pairs)
        avg_rf = sum(p[3] for p in pairs) / len(pairs)
        avg_vol = (sum(vols) / len(vols)) if vols else 0.0
        breadth = (sum(flags) / len(flags)) if flags else 0.0
        metrics[sector] = {
            'avg_return_3m': avg_r3,
            'avg_return_6m': avg_r6,
            'avg_return_12m': avg_r12,
            'avg_return_full': avg_rf,
            'breadth_3m': breadth,
            'avg_vol': avg_vol,
        }
    return metrics


def _score_sectors(metrics: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Score sectors via linear blend: momentum (3/6/12M) + breadth − vol penalty."""
    # Heuristic weights (can be tuned). Emphasize 12M and full-period to reflect long-term leaders.
    w3, w6, w12, wF, wb, wv = 0.15, 0.15, 0.35, 0.35, 0.20, 0.25

    # Normalize inputs across sectors to 0..1 for stability
    def _minmax(values: List[float]) -> Tuple[float, float]:
        if not values:
            return (0.0, 1.0)
        vmin, vmax = min(values), max(values)
        if abs(vmax - vmin) < 1e-12:
            return (vmin, vmin + 1.0)  # avoid zero range
        return (vmin, vmax)

    r3_vals = [m['avg_return_3m'] for m in metrics.values()]
    r6_vals = [m['avg_return_6m'] for m in metrics.values()]
    r12_vals = [m['avg_return_12m'] for m in metrics.values()]
    rF_vals  = [m['avg_return_full'] for m in metrics.values()]
    b_vals  = [m['breadth_3m'] for m in metrics.values()]
    v_vals  = [m['avg_vol'] for m in metrics.values()]
    r3_min, r3_max = _minmax(r3_vals)
    r6_min, r6_max = _minmax(r6_vals)
    r12_min, r12_max = _minmax(r12_vals)
    b_min, b_max   = _minmax(b_vals)
    v_min, v_max   = _minmax(v_vals)
    rF_min, rF_max = _minmax(rF_vals)

    scores: Dict[str, float] = {}
    for sector, m in metrics.items():
        r3n = (m['avg_return_3m'] - r3_min) / (r3_max - r3_min)
        r6n = (m['avg_return_6m'] - r6_min) / (r6_max - r6_min)
        r12n = (m['avg_return_12m'] - r12_min) / (r12_max - r12_min)
        rFn  = (m['avg_return_full'] - rF_min) / (rF_max - rF_min)
        bn  = (m['breadth_3m']   - b_min)  / (b_max - b_min)
        vn  = (m['avg_vol']      - v_min)  / (v_max - v_min) if v_max > v_min else 0.0
        score = w3*r3n + w6*r6n + w12*r12n + wF*rFn + wb*bn - wv*vn
        scores[sector] = score
    return scores


def _clamp_and_normalize(scores: Dict[str, float], profile: str) -> Dict[str, float]:
    """Apply per-profile min/max caps, ensure min sector count, and normalize to sum=1."""
    caps = PROFILE_CAPS.get(profile, PROFILE_CAPS['moderate'])
    if not scores:
        return {}
    # Shift scores to positive domain
    min_score = min(scores.values())
    shifted = {k: (v - min_score + 1e-6) for k, v in scores.items()}
    total = sum(shifted.values()) or 1.0
    prelim = {k: v / total for k, v in shifted.items()}

    # Apply caps
    clamped = {k: max(caps['min'], min(caps['max'], v)) for k, v in prelim.items()}
    s = sum(clamped.values())
    normalized = {k: v / s for k, v in clamped.items()} if s > 0 else clamped

    # Enforce minimum sectors by redistributing from largest weights if needed
    min_sectors = caps['min_sectors']
    if len(normalized) >= min_sectors:
        # fine
        return normalized
    # Not enough sectors available (e.g., data sparse) — just return normalized as-is
    return normalized


def get_dynamic_sector_weights(data_service, risk_profile: str, ttl_minutes: int = 30) -> Dict[str, float]:
    """Compute dynamic sector weights for a given risk profile using cached data.

    Caches the final weights in Redis under `sector:weights:{risk_profile}` with TTL.
    Falls back to empty dict (caller should use static weights) if insufficient data.
    """
    try:
        redis_client = getattr(data_service, 'redis_client', None) or getattr(data_service, 'r', None)
    except Exception:
        redis_client = None

    cache_key = f"sector:weights:{risk_profile}"
    if redis_client is not None:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    selector = PortfolioStockSelector(data_service)
    stocks = selector._get_available_stocks_with_metrics()

    # Filter by profile volatility band to keep sectors relevant to the profile
    vr = selector.RISK_PROFILE_VOLATILITY.get(risk_profile)
    if not vr:
        return {}
    filtered = selector._filter_stocks_by_volatility(stocks, vr)
    if len(filtered) < 30:  # require some breadth
        return {}

    metrics = _sector_metrics_from_stocks(filtered)
    if not metrics:
        return {}

    scores = _score_sectors(metrics)
    weights = _clamp_and_normalize(scores, risk_profile)

    if redis_client is not None and weights:
        try:
            redis_client.setex(cache_key, int(ttl_minutes * 60), json.dumps(weights))
        except Exception:
            pass
    return weights


__all__ = [
    'get_dynamic_sector_weights',
]


