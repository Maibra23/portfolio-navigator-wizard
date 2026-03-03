/**
 * Semantic Color System for Dark Mode Compatibility
 *
 * This module provides theme-safe color utilities that work in both light and dark modes.
 * Use these instead of hard-coded Tailwind colors like `text-green-600` or `bg-blue-50`.
 *
 * Usage:
 *   import { colors, bgColors, borderColors, cn } from '@/utils/semanticColors';
 *   <span className={colors.positive}>+15.2%</span>
 *   <div className={cn(bgColors.info, "p-4")}>Info box</div>
 */

import { cn as clsx } from "@/lib/utils";

// Re-export cn for convenience
export { clsx as cn };

// ============================================================================
// TEXT COLORS - For text content that needs semantic meaning
// ============================================================================

export const colors = {
  // Financial indicators
  positive: "text-green-600 dark:text-green-400",
  negative: "text-red-600 dark:text-red-400",
  neutral: "text-muted-foreground",

  // Status colors
  warning: "text-amber-600 dark:text-amber-400",
  info: "text-blue-600 dark:text-blue-400",
  success: "text-emerald-600 dark:text-emerald-400",
  error: "text-red-600 dark:text-red-400",

  // Chart/data visualization colors
  primary: "text-primary",
  secondary: "text-purple-600 dark:text-purple-400",
  tertiary: "text-cyan-600 dark:text-cyan-400",
  quaternary: "text-orange-600 dark:text-orange-400",

  // Muted variants (softer contrast)
  positiveMuted: "text-green-500 dark:text-green-500",
  negativeMuted: "text-red-500 dark:text-red-500",
  warningMuted: "text-amber-500 dark:text-amber-500",
  infoMuted: "text-blue-500 dark:text-blue-500",
} as const;

// ============================================================================
// BACKGROUND COLORS - For containers, alerts, badges
// ============================================================================

export const bgColors = {
  // Financial indicators
  positive: "bg-green-50 dark:bg-green-950/40",
  negative: "bg-red-50 dark:bg-red-950/40",
  neutral: "bg-muted",

  // Status colors
  warning: "bg-amber-50 dark:bg-amber-950/40",
  info: "bg-blue-50 dark:bg-blue-950/40",
  success: "bg-emerald-50 dark:bg-emerald-950/40",
  error: "bg-red-50 dark:bg-red-950/40",

  // Semi-transparent variants (for overlays)
  positiveSubtle: "bg-green-50/70 dark:bg-green-950/30",
  negativeSubtle: "bg-red-50/70 dark:bg-red-950/30",
  warningSubtle: "bg-amber-50/70 dark:bg-amber-950/30",
  infoSubtle: "bg-blue-50/70 dark:bg-blue-950/30",

  // Chart/data visualization
  primary: "bg-primary/10",
  secondary: "bg-purple-50 dark:bg-purple-950/40",
  tertiary: "bg-cyan-50 dark:bg-cyan-950/40",
  quaternary: "bg-orange-50 dark:bg-orange-950/40",
} as const;

// ============================================================================
// BORDER COLORS - For cards, alerts, dividers
// ============================================================================

export const borderColors = {
  positive: "border-green-200 dark:border-green-800",
  negative: "border-red-200 dark:border-red-800",
  neutral: "border-border",
  warning: "border-amber-200 dark:border-amber-800",
  info: "border-blue-200 dark:border-blue-800",
  success: "border-emerald-200 dark:border-emerald-800",
  error: "border-red-200 dark:border-red-800",
  primary: "border-primary/30",
  secondary: "border-purple-200 dark:border-purple-800",
} as const;

// ============================================================================
// COMBINED STYLES - Common patterns for alerts, badges, etc.
// ============================================================================

export const alertStyles = {
  warning: "bg-amber-50/70 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200 border-amber-200 dark:border-amber-800",
  info: "bg-blue-50/70 dark:bg-blue-950/30 text-blue-800 dark:text-blue-200 border-blue-200 dark:border-blue-800",
  success: "bg-emerald-50/70 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800",
  error: "bg-red-50/70 dark:bg-red-950/30 text-red-800 dark:text-red-200 border-red-200 dark:border-red-800",
} as const;

export const badgeStyles = {
  positive: "bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800",
  negative: "bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800",
  warning: "bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800",
  info: "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800",
  neutral: "bg-muted text-muted-foreground border-border",
} as const;

// ============================================================================
// ICON COLORS - For lucide-react icons
// ============================================================================

export const iconColors = {
  positive: "text-green-600 dark:text-green-400",
  negative: "text-red-600 dark:text-red-400",
  warning: "text-amber-600 dark:text-amber-400",
  info: "text-blue-600 dark:text-blue-400",
  success: "text-emerald-600 dark:text-emerald-400",
  neutral: "text-muted-foreground",
  primary: "text-primary",
} as const;

// ============================================================================
// HOVER STATES - Interactive element colors
// ============================================================================

export const hoverStyles = {
  warning: "hover:bg-amber-100/50 dark:hover:bg-amber-900/30",
  info: "hover:bg-blue-100/50 dark:hover:bg-blue-900/30",
  success: "hover:bg-emerald-100/50 dark:hover:bg-emerald-900/30",
  error: "hover:bg-red-100/50 dark:hover:bg-red-900/30",
  neutral: "hover:bg-muted/80",
} as const;

// ============================================================================
// FOCUS RING STYLES - For accessibility
// ============================================================================

export const focusRingStyles = {
  warning: "focus:ring-2 focus:ring-amber-400 dark:focus:ring-amber-600",
  info: "focus:ring-2 focus:ring-blue-400 dark:focus:ring-blue-600",
  success: "focus:ring-2 focus:ring-emerald-400 dark:focus:ring-emerald-600",
  error: "focus:ring-2 focus:ring-red-400 dark:focus:ring-red-600",
  primary: "focus:ring-2 focus:ring-primary",
} as const;

// ============================================================================
// CHART COLORS - For Recharts and data visualization
// ============================================================================

export const chartColors = {
  light: {
    positive: "#16a34a", // green-600
    negative: "#dc2626", // red-600
    primary: "hsl(var(--primary))",
    secondary: "#9333ea", // purple-600
    tertiary: "#0891b2", // cyan-600
    quaternary: "#ea580c", // orange-600
    grid: "#e5e7eb", // gray-200
    text: "#374151", // gray-700
  },
  dark: {
    positive: "#4ade80", // green-400
    negative: "#f87171", // red-400
    primary: "hsl(var(--primary))",
    secondary: "#c084fc", // purple-400
    tertiary: "#22d3ee", // cyan-400
    quaternary: "#fb923c", // orange-400
    grid: "#374151", // gray-700
    text: "#d1d5db", // gray-300
  },
} as const;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get the appropriate text color class for a numeric value
 * Positive numbers get green, negative get red, zero/null get neutral
 */
export function getValueColor(value: number | null | undefined): string {
  if (value === null || value === undefined) return colors.neutral;
  if (value > 0) return colors.positive;
  if (value < 0) return colors.negative;
  return colors.neutral;
}

/**
 * Get the appropriate background color class for a numeric value
 */
export function getValueBgColor(value: number | null | undefined): string {
  if (value === null || value === undefined) return bgColors.neutral;
  if (value > 0) return bgColors.positive;
  if (value < 0) return bgColors.negative;
  return bgColors.neutral;
}

/**
 * Get chart color based on current theme
 * Use this with Recharts: fill={getChartColor('positive', isDark)}
 */
export function getChartColor(
  colorKey: keyof typeof chartColors.light,
  isDark: boolean
): string {
  return isDark ? chartColors.dark[colorKey] : chartColors.light[colorKey];
}

/**
 * Generate a complete alert style string
 */
export function getAlertStyle(type: keyof typeof alertStyles): string {
  return alertStyles[type];
}

/**
 * Generate a complete badge style string
 */
export function getBadgeStyle(type: keyof typeof badgeStyles): string {
  return badgeStyles[type];
}
