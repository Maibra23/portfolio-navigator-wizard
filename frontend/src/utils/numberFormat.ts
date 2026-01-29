/**
 * Global number formatting for user-facing values.
 * Rule: maximum 2 decimal places, prefer 1 where appropriate.
 */

/**
 * Normalize a return/risk value that may be stored as decimal (0.12) or percentage (12).
 * Backend and caches sometimes return percentage (e.g. 9.83 for 9.83%); we treat values > 1 as percentage.
 */
export function asPercentDecimal(value: number | null | undefined): number {
  if (value == null || typeof value !== 'number' || !isFinite(value)) return 0;
  if (value > 1) return value / 100; // already percentage
  return value;
}

/**
 * Format a decimal rate (0.12 = 12%) for display. Uses at most 2 decimals, prefers 1 when .0.
 */
export function formatPercent(value: number | null | undefined): string {
  const decimal = asPercentDecimal(value);
  const pct = decimal * 100;
  if (!isFinite(pct)) return 'N/A';
  if (Math.abs(pct) >= 100) return `${Math.round(pct)}%`;
  const one = pct.toFixed(1);
  const two = pct.toFixed(2);
  const chosen = one === two ? one : two;
  const trimmed = chosen.replace(/\.?0+$/, '');
  return (trimmed || '0') + '%';
}

/**
 * Format a plain number with max 2 decimals, prefer 1 where appropriate.
 */
export function formatNumber(value: number | null | undefined, options?: { minDecimals?: number; maxDecimals?: number }): string {
  if (value == null || typeof value !== 'number' || !isFinite(value)) return 'N/A';
  const maxDecimals = options?.maxDecimals ?? 2;
  const minDecimals = options?.minDecimals ?? 0;
  const s = value.toFixed(maxDecimals);
  if (maxDecimals <= 0) return s;
  let trimmed = s;
  for (let d = maxDecimals; d > minDecimals; d--) {
    const t = value.toFixed(d);
    if (parseFloat(t) === value) trimmed = t;
    else break;
  }
  return trimmed;
}
