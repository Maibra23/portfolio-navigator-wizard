#!/usr/bin/env python3
"""
Volatility-Weighted Sector Prioritization System

Main idea: prefer sectors whose realized volatility aligns with the
risk-profile's target band. Uses dynamic sector volatility computed
from cached stock metrics; falls back to static profiles if data is sparse.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import os


# Fallback static sector volatilities (annualized) when data is sparse
STATIC_SECTOR_VOL = {
    'Utilities': 0.15,
    'Consumer Defensive': 0.16,  # Staples
    'Healthcare': 0.18,
    'Real Estate': 0.20,
    'Financial Services': 0.22,
    'Industrials': 0.24,
    'Basic Materials': 0.26,     # Materials
    'Communication Services': 0.28,
    'Consumer Cyclical': 0.30,   # Discretionary
    'Energy': 0.35,
    'Technology': 0.38
}


PROFILE_VOL_BANDS = {
    'very-conservative': (0.05, 0.18),
    'conservative': (0.15, 0.25),
    'moderate': (0.22, 0.32),
    'aggressive': (0.28, 0.45),
    'very-aggressive': (0.38, 1.00)
}


PROFILE_FLOORS = {
    'moderate': {
        'Technology': 0.05,
        'Communication Services': 0.04
    },
    'aggressive': {
        'Technology': 0.10,
        'Communication Services': 0.08
    },
    'very-aggressive': {
        'Technology': 0.12,
        'Communication Services': 0.10
    }
}


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    m = n // 2
    if n % 2 == 1:
        return s[m]
    return 0.5 * (s[m-1] + s[m])


def compute_dynamic_sector_volatility(stocks: List[Dict]) -> Dict[str, float]:
    """Compute per-sector median volatility from stock list.
    Expects each stock to have 'sector' and 'volatility'.
    """
    by_sector: Dict[str, List[float]] = defaultdict(list)
    for s in stocks:
        sec = s.get('sector', 'Unknown')
        vol = s.get('volatility', None)
        if sec and sec != 'Unknown' and isinstance(vol, (int, float)) and vol > 0:
            by_sector[sec].append(float(vol))
    result = {}
    for sec, vols in by_sector.items():
        if len(vols) >= 10:  # coverage guard
            result[sec] = _median(vols)
    return result


def score_sectors_by_band_alignment(profile: str, sector_vols: Dict[str, float]) -> Dict[str, float]:
    """Score sectors by distance to the risk-profile volatility band midpoint.
    In-band sectors use a gentle quadratic penalty around the midpoint.
    Out-of-band sectors get a stronger linear penalty by distance to nearest bound.
    """
    vmin, vmax = PROFILE_VOL_BANDS.get(profile, (0.22, 0.32))
    vmid = 0.5 * (vmin + vmax)
    vrange = max(1e-6, (vmax - vmin))

    scores: Dict[str, float] = {}
    for sector, sv in sector_vols.items():
        if vmin <= sv <= vmax:
            # quadratic around midpoint; alpha configurable via env
            alpha = float(os.environ.get('SECTOR_MID_ALPHA', '0.30'))
            distance = abs(sv - vmid) / vrange
            score = 1.0 - alpha * (distance ** 2)
        else:
            # linear penalty by distance to nearest bound
            if sv < vmin:
                dist = (vmin - sv)
            else:
                dist = (sv - vmax)
            score = max(0.05, 1.0 - 2.0 * dist)
        scores[sector] = max(0.0, score)
    # normalize
    total = sum(scores.values()) or 1.0
    return {k: v / total for k, v in scores.items()}


def apply_floors_and_normalize(weights: Dict[str, float], profile: str, min_sectors: int) -> Dict[str, float]:
    floors = PROFILE_FLOORS.get(profile, {})
    # apply floors
    adjusted = dict(weights)
    for sec, floor in floors.items():
        adjusted[sec] = max(floor, adjusted.get(sec, 0.0))
    # ensure diversity: keep top min_sectors by weight
    if len(adjusted) > min_sectors:
        # keep all but renormalize
        pass
    # normalize
    s = sum(adjusted.values()) or 1.0
    return {k: v / s for k, v in adjusted.items()}


def _apply_regime_nudges(weights: Dict[str, float], profile: str) -> Dict[str, float]:
    """Optional regime nudges via env REGIME_FLAG in {risk_on, risk_off, neutral}."""
    regime = os.environ.get('REGIME_FLAG', 'neutral').lower()
    if regime not in ('risk_on', 'risk_off'):
        return weights
    growth = ('Technology', 'Communication Services', 'Consumer Cyclical')
    defensive = ('Utilities', 'Consumer Defensive', 'Healthcare')
    nudged = dict(weights)
    delta = 0.02  # 2% nudges
    if regime == 'risk_on':
        for s in growth:
            if s in nudged:
                nudged[s] += delta
    else:
        for s in defensive:
            if s in nudged:
                nudged[s] += delta
    # renormalize
    ssum = sum(nudged.values()) or 1.0
    return {k: v / ssum for k, v in nudged.items()}


def get_volatility_weighted_sector_weights(profile: str, stocks: List[Dict], min_sectors: int = 3, data_service: Optional[object] = None) -> Dict[str, float]:
    """Main entry: compute sector weights for a risk profile using dynamic vol.
    Falls back to STATIC_SECTOR_VOL when coverage is insufficient.
    """
    # Try Redis cache first
    cache_key = f"sector:weights:volsys:{profile}"
    redis_client = None
    if data_service is not None:
        try:
            redis_client = getattr(data_service, 'redis_client', None) or getattr(data_service, 'r', None)
        except Exception:
            redis_client = None
    if redis_client is not None:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception:
            pass

    dyn = compute_dynamic_sector_volatility(stocks)
    # merge with static for missing sectors
    merged: Dict[str, float] = dict(STATIC_SECTOR_VOL)
    merged.update(dyn)
    scores = score_sectors_by_band_alignment(profile, merged)
    weights = apply_floors_and_normalize(scores, profile, min_sectors)
    weights = _apply_regime_nudges(weights, profile)
    # Cache with TTL (30-60 min), TTL is activated/cleared by auto-regeneration service
    if redis_client is not None:
        try:
            import json
            ttl_seconds = int(os.environ.get('SECTOR_WEIGHTS_TTL_SECONDS', '3600'))
            redis_client.setex(cache_key, ttl_seconds, json.dumps(weights))
        except Exception:
            pass
    return weights


def invalidate_volatility_sector_weights_cache(redis_client, risk_profile: Optional[str] = None):
    """Allow auto-regeneration to clear cached weights so they refresh on next access."""
    try:
        if risk_profile:
            redis_client.delete(f"sector:weights:volsys:{risk_profile}")
        else:
            # best-effort scan
            for key in redis_client.scan_iter(match="sector:weights:volsys:*"):
                redis_client.delete(key)
    except Exception:
        pass


__all__ = [
    'get_volatility_weighted_sector_weights',
    'invalidate_volatility_sector_weights_cache',
]


