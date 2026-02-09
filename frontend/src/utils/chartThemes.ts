/**
 * Theme-Aware Chart Colors and Themes
 *
 * Provides dynamic color palettes and chart configurations that adapt
 * to the currently selected theme (Classic or Dark).
 */

import { ThemeType } from '@/lib/themeConfig';

/**
 * Get chart colors based on current theme
 */
export const getChartTheme = (theme: ThemeType) => {
  if (theme === 'dark') {
    return {
      // Background colors for dark theme
      canvas: '#08090a',
      cardBackground: '#14151a',

      // Border and grid colors
      border: 'rgba(255, 255, 255, 0.08)',
      grid: 'rgba(255, 255, 255, 0.06)',

      // Axis styling
      axes: {
        line: 'rgba(255, 255, 255, 0.1)',
        tick: 'rgba(255, 255, 255, 0.5)',
        label: 'rgba(255, 255, 255, 0.7)',
      },

      // Text colors
      text: {
        primary: 'rgba(255, 255, 255, 0.9)',
        secondary: 'rgba(255, 255, 255, 0.6)',
        subtle: 'rgba(255, 255, 255, 0.4)',
      },

      // Tooltip styling
      tooltip: {
        background: '#1a1b21',
        border: 'rgba(255, 255, 255, 0.15)',
        text: '#ffffff',
      },
    };
  }

  // Classic/Light theme
  return {
    // Background colors for light theme
    canvas: '#fafbfc',
    cardBackground: '#ffffff',

    // Border and grid colors
    border: 'rgba(0, 0, 0, 0.08)',
    grid: 'rgba(0, 0, 0, 0.05)',

    // Axis styling
    axes: {
      line: 'rgba(0, 0, 0, 0.15)',
      tick: 'rgba(0, 0, 0, 0.5)',
      label: 'rgba(0, 0, 0, 0.7)',
    },

    // Text colors
    text: {
      primary: 'rgba(0, 0, 0, 0.9)',
      secondary: 'rgba(0, 0, 0, 0.6)',
      subtle: 'rgba(0, 0, 0, 0.4)',
    },

    // Tooltip styling
    tooltip: {
      background: '#ffffff',
      border: 'rgba(0, 0, 0, 0.15)',
      text: '#000000',
    },
  };
};

/**
 * Data visualization color palette
 * These colors work well on both light and dark backgrounds
 */
export const getVisualizationPalette = (theme: ThemeType) => {
  if (theme === 'dark') {
    // Muted, softer colors for dark backgrounds
    return [
      '#4ade80', // Soft green
      '#f87171', // Soft red
      '#60a5fa', // Soft blue
      '#fbbf24', // Soft amber
      '#a78bfa', // Soft purple
      '#fb923c', // Soft orange
      '#22d3ee', // Soft cyan
      '#f472b6', // Soft pink
      '#84cc16', // Soft lime
      '#06b6d4', // Soft teal
    ];
  }

  // Vibrant colors for light backgrounds
  return [
    '#10b981', // Green
    '#ef4444', // Red
    '#3b82f6', // Blue
    '#f59e0b', // Amber
    '#8b5cf6', // Purple
    '#f97316', // Orange
    '#06b6d4', // Cyan
    '#ec4899', // Pink
    '#84cc16', // Lime
    '#14b8a6', // Teal
  ];
};

/**
 * Risk profile colors that adapt to theme
 */
export const getRiskColors = (theme: ThemeType) => {
  if (theme === 'dark') {
    return {
      conservative: '#5b8fd6',   // Muted blue
      moderate: '#5ba86b',       // Muted green
      aggressive: '#d67373',     // Muted red
      veryConservative: '#7ea8e5',
      veryAggressive: '#e55757',
    };
  }

  return {
    conservative: '#3b82f6',   // Bright blue
    moderate: '#10b981',       // Bright green
    aggressive: '#ef4444',     // Bright red
    veryConservative: '#60a5fa',
    veryAggressive: '#f87171',
  };
};

/**
 * Portfolio comparison colors
 */
export const getPortfolioColors = (theme: ThemeType) => {
  if (theme === 'dark') {
    return {
      current: '#60a5fa',        // Soft blue
      weightsOptimized: '#4ade80', // Soft green
      marketOptimized: '#a78bfa',  // Soft purple
    };
  }

  return {
    current: '#3b82f6',        // Blue
    weightsOptimized: '#10b981', // Green
    marketOptimized: '#8b5cf6',  // Purple
  };
};

/**
 * Gradient colors for charts (for Classic theme)
 */
export const getGradientColors = (theme: ThemeType) => {
  if (theme === 'dark') {
    // No gradients in dark theme
    return null;
  }

  return {
    primary: ['#3b82f6', '#60a5fa'],
    accent: ['#10b981', '#34d399'],
    warning: ['#f59e0b', '#fbbf24'],
    danger: ['#ef4444', '#f87171'],
  };
};

/**
 * Get CSS variable value from document
 * Useful for getting theme colors at runtime
 */
export const getCSSVariable = (variable: string): string => {
  if (typeof window === 'undefined') return '';
  return getComputedStyle(document.documentElement)
    .getPropertyValue(variable)
    .trim();
};

/**
 * Get HSL color from CSS variable and convert to hex
 */
export const getThemeColor = (variable: string): string => {
  const hsl = getCSSVariable(variable);
  if (!hsl) return '#000000';

  // Convert HSL to hex (simplified - assumes HSL format like "214 84% 56%")
  const [h, s, l] = hsl.split(/\s+/).map(v => parseFloat(v));

  // HSL to RGB conversion
  const hue = h / 360;
  const sat = s / 100;
  const lum = l / 100;

  const hue2rgb = (p: number, q: number, t: number) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };

  let r, g, b;
  if (sat === 0) {
    r = g = b = lum;
  } else {
    const q = lum < 0.5 ? lum * (1 + sat) : lum + sat - lum * sat;
    const p = 2 * lum - q;
    r = hue2rgb(p, q, hue + 1 / 3);
    g = hue2rgb(p, q, hue);
    b = hue2rgb(p, q, hue - 1 / 3);
  }

  const toHex = (x: number) => {
    const hex = Math.round(x * 255).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
};

/**
 * Complete Recharts theme configuration
 */
export const getRechartsTheme = (theme: ThemeType) => {
  const chartTheme = getChartTheme(theme);

  return {
    // Cartesian grid styling
    cartesianGrid: {
      stroke: chartTheme.grid,
      strokeDasharray: '3 3',
    },

    // Axis styling
    xAxis: {
      stroke: chartTheme.axes.line,
      tick: { fill: chartTheme.axes.label, fontSize: 12 },
      axisLine: { stroke: chartTheme.axes.line },
      tickLine: { stroke: chartTheme.axes.tick },
    },

    yAxis: {
      stroke: chartTheme.axes.line,
      tick: { fill: chartTheme.axes.label, fontSize: 12 },
      axisLine: { stroke: chartTheme.axes.line },
      tickLine: { stroke: chartTheme.axes.tick },
    },

    // Tooltip styling
    tooltip: {
      contentStyle: {
        backgroundColor: chartTheme.tooltip.background,
        border: `1px solid ${chartTheme.tooltip.border}`,
        borderRadius: '8px',
        color: chartTheme.tooltip.text,
      },
      itemStyle: {
        color: chartTheme.tooltip.text,
      },
      labelStyle: {
        color: chartTheme.tooltip.text,
        fontWeight: 600,
      },
    },

    // Legend styling
    legend: {
      wrapperStyle: {
        color: chartTheme.text.primary,
      },
    },
  };
};

export default {
  getChartTheme,
  getVisualizationPalette,
  getRiskColors,
  getPortfolioColors,
  getGradientColors,
  getThemeColor,
  getRechartsTheme,
};
