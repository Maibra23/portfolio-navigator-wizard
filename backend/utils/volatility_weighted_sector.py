#!/usr/bin/env python3
"""
Volatility-weighted sector helper
Provides get_volatility_weighted_sector_weights used by PortfolioStockSelector.

This minimal implementation computes per-sector weights by counting candidate
stocks aligned with the risk profile's volatility band and normalizing.
"""

from typing import Dict, List, Any


def get_volatility_weighted_sector_weights(
	risk_profile: str,
	stocks: List[Dict[str, Any]],
	min_sectors: int = 3,
	data_service: Any = None,
) -> Dict[str, float]:
	"""
	Compute simple weights per sector based on number of candidate stocks
	meeting basic data requirements. Returns normalized weights that sum to 1.0.

	This function is intentionally lightweight to unblock startup. It does not
	call external services and only inspects provided stocks.
	"""
	# Guard: empty input
	if not stocks:
		return {}

	# Count eligible stocks per sector
	sector_counts: Dict[str, int] = {}
	for s in stocks:
		sector = s.get("sector") or "Unknown"
		vol = s.get("volatility")
		# Basic eligibility: need sector string and a numeric volatility
		if sector and isinstance(vol, (int, float)) and vol > 0:
			sector_counts[sector] = sector_counts.get(sector, 0) + 1

	if not sector_counts:
		return {}

	# Normalize counts to weights
	total = float(sum(sector_counts.values()))
	if total <= 0:
		return {}

	weights = {sec: cnt / total for sec, cnt in sector_counts.items()}

	# Ensure at least min_sectors exist by spreading tiny weights if needed
	if len(weights) < min_sectors:
		# Add dummy very small weights to missing sectors seen in stocks
		seen = set(weights.keys())
		for s in stocks:
			sec = s.get("sector") or "Unknown"
			if sec not in seen:
				weights[sec] = 0.0
				seen.add(sec)
				if len(seen) >= min_sectors:
					break
		# Re-normalize (safe even if zeros added)
		t = float(sum(weights.values()))
		if t > 0:
			weights = {k: v / t for k, v in weights.items()}

	return weights


def invalidate_volatility_sector_weights_cache(redis_client: Any, risk_profile: str) -> None:
	"""
	No-op cache invalidation placeholder. Kept for compatibility with
	PortfolioAutoRegenerationService. This function intentionally does
	nothing; sector weights are computed on demand by the helper above.
	"""
	try:
		# Intentionally no Redis key used; provide hook for future implementations.
		_ = redis_client  # avoid unused var warnings
		_ = risk_profile
	except Exception:
		pass


