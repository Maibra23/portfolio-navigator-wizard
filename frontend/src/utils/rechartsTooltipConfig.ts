/**
 * Shared Recharts Tooltip and cursor configuration.
 * High-visibility, theme-proof tooltips across all charts.
 */

import type { ThemeType } from "@/lib/themeConfig";
import { getChartTheme } from "@/utils/chartThemes";

/** Cursor style: visible dashed crosshair */
export const RECHARTS_CURSOR = {
  strokeDasharray: "2 2",
  strokeOpacity: 0.6,
} as const;

/**
 * Theme-aware tooltip shadow: visible but soft so it doesn't stand in the way.
 */
function getTooltipShadow(theme: ThemeType): string {
  return theme === "dark"
    ? "0 2px 10px rgba(0,0,0,0.4)"
    : "0 2px 8px rgba(0,0,0,0.1)";
}

/**
 * Recharts Tooltip props: clear and visible, compact so they don't block the chart.
 * Theme-proof; use theme from useTheme().
 */
export function getRechartsTooltipProps(theme: ThemeType) {
  const chartTheme = getChartTheme(theme);
  const themeWithTooltip = chartTheme as typeof chartTheme & {
    tooltip?: { background: string; border: string; text: string };
  };
  const tooltip = themeWithTooltip.tooltip ?? {
    background: chartTheme.cardBackground,
    border: chartTheme.border,
    text: chartTheme.text.primary,
  };
  return {
    allowEscapeViewBox: { x: true, y: true },
    offset: 14,
    wrapperStyle: { pointerEvents: "none" as const },
    contentStyle: {
      padding: "6px 10px",
      fontSize: "11px",
      maxWidth: "180px",
      background: tooltip.background,
      border: `1px solid ${tooltip.border}`,
      borderRadius: "6px",
      boxShadow: getTooltipShadow(theme),
      color: tooltip.text,
    },
    itemStyle: { color: tooltip.text },
    labelStyle: { color: tooltip.text },
    cursor: RECHARTS_CURSOR,
  };
}

/**
 * Cursor prop when chart is in "selecting" state (e.g. box zoom drag).
 * Use cursor={isSelecting ? false : RECHARTS_CURSOR} so crosshair is hidden during drag.
 */
