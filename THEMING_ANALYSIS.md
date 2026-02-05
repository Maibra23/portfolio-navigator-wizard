# Portfolio Navigator Wizard - Theming Analysis & Migration Guide

**Document Purpose:** Single source of truth for migrating the project to a new dark theme
**Analysis Date:** 2026-02-04
**Target Aesthetic:** Linear.app-inspired minimalist dark UI

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Identified Challenges](#2-identified-challenges)
3. [Hardcoded Color Inventory](#3-hardcoded-color-inventory)
4. [Proposed Theming Solution](#4-proposed-theming-solution)
5. [Integration Plan](#5-integration-plan)
6. [Agent Task Delegation](#6-agent-task-delegation)
7. [Appendices](#7-appendices)

---

## 1. Executive Summary

### Current State
The Portfolio Navigator Wizard uses a hybrid styling approach with:
- **Tailwind CSS** with CSS variables for the design system
- **Extensive hardcoded colors** throughout 25+ component files
- **Multiple visualization theme objects** duplicated across chart components
- **Inconsistent color patterns** mixing Tailwind classes, hex values, and rgba values

### Scale of Changes Required
| Category | Count | Complexity |
|----------|-------|------------|
| Files with hardcoded Tailwind colors | 25+ | Medium |
| Files with hardcoded hex colors | 15+ | High |
| Files with rgba/inline styles | 12+ | High |
| Visualization theme objects | 4 | Medium |
| UI components using gradients | 12 | Low |
| Total unique color values | 80+ | - |

### Key Findings
1. **No centralized color system** - Colors are defined in multiple places
2. **Duplicate visualization themes** - Same theme object copied across 4+ files
3. **Mixed color formats** - Tailwind classes, hex, rgba, HSL all used inconsistently
4. **Light theme assumptions** - Many components assume light backgrounds

---

## 2. Identified Challenges

### 2.1 Styling Inconsistencies

#### Challenge 1: Fragmented Color Definitions
**Description:** Colors are defined in multiple locations without a single source of truth.

**Affected Locations:**
- `frontend/src/index.css` - CSS variables (partial)
- `frontend/src/components/wizard/EfficientFrontierChart.tsx` - visualizationTheme object
- `frontend/src/components/wizard/Portfolio3PartVisualization.tsx` - visualizationTheme object
- `frontend/src/components/wizard/PortfolioOptimization.tsx` - visualizationTheme object
- `frontend/src/components/wizard/PortfolioComparisonTable.tsx` - visualizationTheme object
- `frontend/src/components/wizard/RiskSpectrum.tsx` - riskZones array with colors
- `frontend/src/components/wizard/scoring-engine.ts` - getCategoryColor function

**Impact:** Changing a color requires updates in multiple files, leading to inconsistencies.

---

#### Challenge 2: Hardcoded Tailwind Color Classes
**Description:** Components use hardcoded Tailwind color classes (e.g., `blue-600`, `gray-200`) instead of semantic CSS variables.

**Files Affected:**
| File | Hardcoded Classes Count |
|------|------------------------|
| `PortfolioWizard.tsx` | 15+ |
| `StressTest.tsx` | 80+ |
| `StockSelection.tsx` | 40+ |
| `PortfolioOptimization.tsx` | 60+ |
| `RiskProfiler.tsx` | 20+ |
| `FinalAnalysisComponents.tsx` | 30+ |
| `RecommendationsTabReview.tsx` | 25+ |
| `PortfolioBuilder.tsx` | 20+ |
| `CategoryCard.tsx` | 10+ |
| `FlagAlerts.tsx` | 15+ |
| `ConfirmationModal.tsx` | 10+ |
| `TwoDimensionalMap.tsx` | 15+ |
| `CapitalInput.tsx` | 5+ |
| `WelcomeStep.tsx` | 5+ |
| `NotFound.tsx` | 5+ |
| `TickerInfo.tsx` | 15+ |

**Impact:** Theme changes require find-and-replace across 400+ individual color class instances.

---

#### Challenge 3: Inline Style Color Values
**Description:** Many components use inline `style` props with hardcoded hex/rgba values.

**Files with Inline Styles:**
- `PortfolioOptimization.tsx` - 100+ inline style color values
- `EfficientFrontierChart.tsx` - 50+ inline style color values
- `StressTest.tsx` - 60+ inline style color values
- `FinalAnalysisComponents.tsx` - 30+ inline style color values
- `PortfolioComparisonTable.tsx` - 20+ inline style color values
- `TwoDimensionalMap.tsx` - 15+ inline style color values
- `ResultsPage.tsx` - 10+ inline style color values
- `RiskSpectrum.tsx` - 10+ inline style color values

**Impact:** These cannot be changed via CSS variables and require code changes.

---

#### Challenge 4: Chart/Visualization Specific Colors
**Description:** Recharts components require color values as props, not CSS classes.

**Chart Components:**
- `EfficientFrontierChart.tsx` - Scatter plots, lines, reference areas
- `Portfolio3PartVisualization.tsx` - Pie charts, scatter plots
- `FiveYearProjectionChart.tsx` - Line charts
- `StressTest.tsx` - Multiple chart types
- `RiskReturnChart.tsx` - Mixed charts
- `SectorDistributionChart.tsx` - Bar charts, pie charts
- `TwoAssetChart.tsx` - Correlation charts
- `TwoDimensionalMap.tsx` - Risk quadrant visualization

**Impact:** Chart colors must be passed as JS variables, requiring a theme-aware color system.

---

#### Challenge 5: Gradient Dependencies
**Description:** Multiple components rely on gradient backgrounds that don't translate well to dark themes.

**Files Using Gradients:**
| File | Gradient Usage |
|------|----------------|
| `PortfolioWizard.tsx:207` | `bg-gradient-to-br from-blue-50 to-indigo-100` |
| `WelcomeStep.tsx:47` | `bg-gradient-primary` |
| `CapitalInput.tsx:48` | `bg-gradient-primary` |
| `RecommendationsTabReview.tsx:254` | `bg-gradient-to-br from-blue-50 to-indigo-50` |
| `RecommendationsTabReview.tsx:391` | `bg-gradient-to-br from-indigo-50 to-purple-50` |
| `StockSelection.tsx:1760` | `bg-gradient-to-r from-blue-50 to-purple-50` |
| `StockSelection.tsx:1997` | `bg-gradient-to-br from-slate-50 to-blue-50` |
| `CategoryCard.tsx:164` | `bg-gradient-to-r from-blue-50 to-indigo-50` |
| `RiskProfiler.tsx:1531` | `bg-gradient-to-r from-green-50 to-blue-50` |
| `PortfolioOptimization.tsx:2301` | `bg-gradient-to-r from-blue-50 to-purple-50` |
| `PortfolioOptimization.tsx:4073` | `bg-gradient-to-r from-blue-50 to-indigo-50` |
| `ResultsPage.tsx:150` | `bg-gradient-to-r from-blue-600 to-indigo-600` |

**Impact:** Gradients must be removed or replaced with solid dark colors.

---

#### Challenge 6: Semantic Color Inconsistency
**Description:** Same semantic meaning uses different colors across components.

**Examples:**
| Semantic Meaning | Color Variations Used |
|-----------------|----------------------|
| Success/Positive | `green-600`, `green-500`, `#22c55e`, `#16a34a`, `#10b981`, `#008000` |
| Error/Negative | `red-600`, `red-500`, `#ef4444`, `#dc2626`, `#FF0000` |
| Primary/Action | `blue-600`, `blue-500`, `#3b82f6`, `#2563eb`, `#1e40af`, `#60a5fa` |
| Warning | `amber-600`, `orange-600`, `#f59e0b`, `#ea580c`, `#FFA500` |
| Neutral | `gray-600`, `gray-500`, `gray-200`, `#6b7280`, `#9ca3af`, `#64748b` |

**Impact:** No consistent mapping between semantic intent and actual colors.

---

### 2.2 Architecture Issues

#### Issue 1: Duplicated Visualization Theme
The same `visualizationTheme` object is copied across 4 files:

```javascript
// Duplicated in: EfficientFrontierChart.tsx, Portfolio3PartVisualization.tsx,
// PortfolioOptimization.tsx, PortfolioComparisonTable.tsx

const visualizationTheme = {
  canvas: '#FAFAF4',
  cardBackground: '#FFFFFF',
  border: 'rgba(90, 90, 82, 0.12)',
  grid: 'rgba(200, 200, 195, 0.8)',
  axes: {
    line: 'rgba(94, 94, 86, 0.28)',
    tick: 'rgba(75, 75, 68, 0.82)',
    label: '#3B3B33',
  },
  text: {
    primary: '#2F2F29',
    secondary: '#6D6D62',
    subtle: 'rgba(90, 90, 82, 0.65)',
  },
  // ... more properties
};
```

**Impact:** Any theme change requires updating 4 files identically.

---

#### Issue 2: No Theme Context
**Description:** The application lacks a React context for providing theme colors to components.

**Current State:**
- No `ThemeProvider` or theme context
- No `useTheme` hook for accessing colors
- Components import colors locally or use hardcoded values

**Impact:** Cannot dynamically switch themes or provide dark mode.

---

#### Issue 3: Mixed CSS Variable Adoption
**Description:** Some components use CSS variables, others use hardcoded values.

**CSS Variable Usage:**
- `index.css` defines: `--primary`, `--secondary`, `--background`, etc.
- `button.tsx` uses: `bg-primary`, `text-primary-foreground` ✅
- `card.tsx` uses: `bg-card`, `text-card-foreground` ✅
- `PortfolioWizard.tsx` uses: `blue-600`, `gray-200` ❌
- `StressTest.tsx` uses: `#3b82f6`, `#22c55e` ❌

**Impact:** Partial adoption means CSS variable changes only affect some components.

---

## 3. Hardcoded Color Inventory

### 3.1 Tailwind Color Classes by Category

#### Blue Colors (Primary Actions, Information)
| Class | Files Using | Purpose |
|-------|-------------|---------|
| `blue-50` | PortfolioWizard, StressTest, StockSelection, etc. | Light backgrounds |
| `blue-100` | FinalizePortfolio, PortfolioOptimization | Subtle backgrounds |
| `blue-200` | StressTest, StockSelection, FlagAlerts | Borders, light accents |
| `blue-300` | StressTest, FinalAnalysisComponents | Hover states |
| `blue-400` | StressTest, FlagAlerts | Medium accents |
| `blue-500` | NotFound, RiskReturnChart, SectorChart | Primary actions |
| `blue-600` | PortfolioWizard, StressTest, RiskSpectrum, etc. | Primary buttons, icons |
| `blue-700` | PortfolioWizard, StressTest, StockSelection | Hover states, text |
| `blue-800` | StressTest, StockSelection, FinalAnalysis | Dark text |
| `blue-900` | RecommendationsTabReview, StockSelection | Very dark text |

#### Green Colors (Success, Positive Values)
| Class | Files Using | Purpose |
|-------|-------------|---------|
| `green-50` | PortfolioBuilder, RiskProfiler, StressTest | Success backgrounds |
| `green-100` | PortfolioOptimization | Subtle success |
| `green-200` | PortfolioBuilder, StressTest | Success borders |
| `green-500` | StressTest | Progress indicators |
| `green-600` | TickerInfo, CapitalInput, PortfolioBuilder | Positive values, text |

#### Red Colors (Error, Negative Values)
| Class | Files Using | Purpose |
|-------|-------------|---------|
| `red-50` | PortfolioBuilder | Error backgrounds |
| `red-200` | PortfolioBuilder | Error borders |
| `red-500` | PortfolioBuilder | Error indicators |
| `red-600` | TickerInfo, PortfolioBuilder | Negative values, text |

#### Gray Colors (Neutral, Borders, Text)
| Class | Files Using | Purpose |
|-------|-------------|---------|
| `gray-50` | TickerInfo | Hover backgrounds |
| `gray-100` | NotFound, TickerInfo, FinalAnalysis | Light backgrounds |
| `gray-200` | PortfolioWizard, PortfolioBuilder, StressTest | Borders |
| `gray-300` | PortfolioComparisonTable, PortfolioOptimization | Borders |
| `gray-400` | RiskProfiler | Placeholder text |
| `gray-500` | PortfolioWizard, FinalAnalysis, PortfolioOpt | Secondary text |
| `gray-600` | NotFound, StressTest, PortfolioOptimization | Text |
| `gray-700` | PortfolioWizard | Text |
| `gray-900` | PortfolioWizard, RiskProfiler | Headings |

#### Other Colors
| Class | Files Using | Purpose |
|-------|-------------|---------|
| `amber-50` | PortfolioBuilder | Warning backgrounds |
| `amber-400` | PortfolioBuilder | Warning borders |
| `amber-600` | PortfolioBuilder | Warning icons, text |
| `amber-800` | PortfolioBuilder | Warning text |
| `indigo-50` | PortfolioWizard, RecommendationsTabReview | Gradient component |
| `indigo-100` | PortfolioWizard | Gradient component |
| `indigo-600` | RecommendationsTabReview, ResultsPage | Primary gradient |
| `purple-50` | RecommendationsTabReview, StockSelection | Gradient component |
| `slate-50` | StockSelection | Card backgrounds |
| `slate-900` | StockSelection | Tooltip backgrounds |
| `white` | PortfolioWizard, StockSelection, StressTest | Backgrounds, text |

---

### 3.2 Hex Color Inventory

#### Primary Blue Shades
| Hex Code | Usage | Files |
|----------|-------|-------|
| `#1e40af` | Deep blue, chart dots | TwoDimensionalMap, PortfolioOptimization |
| `#1e3a8a` | Very deep blue | PortfolioOptimization |
| `#2563eb` | Vibrant blue, charts | Portfolio3Part, PortfolioOptimization |
| `#3b82f6` | Standard blue, charts | 15+ files |
| `#60a5fa` | Light blue, risk spectrum | RiskSpectrum, TwoDimensionalMap |
| `#93c5fd` | Very light blue | Various |
| `#BFDBFE` | Border blue | PortfolioOptimization |
| `#EFF6FF` | Background blue | PortfolioOptimization |

#### Green Shades
| Hex Code | Usage | Files |
|----------|-------|-------|
| `#008000` | Legacy green | scoring-engine.ts |
| `#10b981` | Emerald green, charts | 10+ files |
| `#15803d` | Dark green stroke | PortfolioOptimization |
| `#16a34a` | Vibrant green, palette | Portfolio3Part |
| `#22c55e` | Standard green, charts | 15+ files |
| `#82ca9d` | Soft green | RiskReturnChart |
| `#86efac` | Light green, heatmap | Portfolio3Part |

#### Red/Orange Shades
| Hex Code | Usage | Files |
|----------|-------|-------|
| `#dc2626` | Vibrant red, palette | Portfolio3Part, PortfolioOptimization |
| `#ef4444` | Standard red, charts | 20+ files |
| `#991b1b` | Dark red stroke | PortfolioOptimization |
| `#FF0000` | Legacy red | scoring-engine.ts |
| `#f59e0b` | Amber, warnings | 10+ files |
| `#ea580c` | Orange, palette | Portfolio3Part |
| `#fb923c` | Soft orange | Portfolio3Part |
| `#FFA500` | Legacy orange | scoring-engine.ts |

#### Purple/Pink Shades
| Hex Code | Usage | Files |
|----------|-------|-------|
| `#7e22ce` | Deep purple | StressTest |
| `#9333ea` | Purple, CML line | 10+ files |
| `#a855f7` | Medium purple | StressTest |
| `#be185d` | Vibrant pink | Portfolio3Part |
| `#f472b6` | Soft pink | Portfolio3Part |
| `#e9d5ff` | Light purple border | StressTest |
| `#faf5ff` | Very light purple bg | StressTest |

#### Gray/Neutral Shades
| Hex Code | Usage | Files |
|----------|-------|-------|
| `#2F2F29` | Text primary | visualizationTheme |
| `#3B3B33` | Axis labels | visualizationTheme |
| `#4b5563` | Text | PortfolioOptimization |
| `#64748b` | Chart elements | 10+ files |
| `#6b7280` | Reference lines | TwoDimensionalMap |
| `#6D6D62` | Text secondary | visualizationTheme |
| `#94a3b8` | Muted elements | 8+ files |
| `#9ca3af` | Gray accents | 5+ files |
| `#cbd5e1` | Light gray points | 6+ files |
| `#e5e7eb` | Grid lines | 10+ files |

#### Cyan/Teal Shades
| Hex Code | Usage | Files |
|----------|-------|-------|
| `#0891b2` | Vibrant cyan | Portfolio3Part |
| `#0e7490` | Vibrant teal | Portfolio3Part, PortfolioOptimization |
| `#06b6d4` | Soft cyan | Portfolio3Part |
| `#22d3ee` | Soft cyan variant | Portfolio3Part |

#### Background/Canvas Colors
| Hex Code | Usage | Files |
|----------|-------|-------|
| `#FAFAF4` | Canvas background | visualizationTheme (4 files) |
| `#FFFFFF` | Card background | visualizationTheme (4 files) |
| `#fff` | White, strokes | Multiple chart components |

#### Special/Legacy Colors
| Hex Code | Usage | Files |
|----------|-------|-------|
| `#00008B` | Dark blue | scoring-engine.ts |
| `#ADD8E6` | Light blue | scoring-engine.ts |
| `#8884d8` | Default Recharts | RiskReturnChart, SectorChart |
| `#ff7300` | Recharts orange | RiskReturnChart |
| `#0088FE` | Sector chart palette | SectorDistributionChart |
| `#00C49F` | Sector chart palette | SectorDistributionChart |
| `#FFBB28` | Sector chart palette | SectorDistributionChart |
| `#FF8042` | Sector chart palette | SectorDistributionChart |

---

### 3.3 RGBA Color Inventory

#### Visualization Theme Colors
| RGBA Value | Usage | Files |
|------------|-------|-------|
| `rgba(90, 90, 82, 0.12)` | Border | visualizationTheme |
| `rgba(90, 90, 82, 0.65)` | Subtle text | visualizationTheme |
| `rgba(94, 94, 86, 0.28)` | Axis line | visualizationTheme |
| `rgba(75, 75, 68, 0.82)` | Axis tick | visualizationTheme |
| `rgba(59, 59, 51, 0.8)` | Legend | visualizationTheme |
| `rgba(200, 200, 195, 0.8)` | Grid | visualizationTheme |
| `rgba(226, 226, 221, 0.7)` | Grid variant | Portfolio3Part |

#### Risk Quadrant Colors
| RGBA Value | Usage | Files |
|------------|-------|-------|
| `rgba(34, 197, 94, 0.15)` | Green quadrant (high-high) | TwoDimensionalMap, ResultsPage |
| `rgba(34, 197, 94, 0.35)` | Green reference area | TwoDimensionalMap |
| `rgba(234, 179, 8, 0.15)` | Yellow quadrant (low-high) | TwoDimensionalMap, ResultsPage |
| `rgba(245, 158, 11, 0.35)` | Yellow reference area | TwoDimensionalMap |
| `rgba(59, 130, 246, 0.15)` | Blue quadrant (high-low) | TwoDimensionalMap, ResultsPage |
| `rgba(59, 130, 246, 0.35)` | Blue reference area | TwoDimensionalMap |
| `rgba(107, 114, 128, 0.15)` | Gray quadrant (low-low) | TwoDimensionalMap, ResultsPage |
| `rgba(156, 163, 175, 0.35)` | Gray reference area | TwoDimensionalMap |
| `rgba(30, 64, 175, 0.15)` | User position halo | TwoDimensionalMap |

#### Heatmap/Correlation Colors
| RGBA Value | Usage | Files |
|------------|-------|-------|
| `rgba(148, 163, 184, 0.25)` | NaN value | Portfolio3Part |
| `rgba(220, 38, 38, 0.4-0.9)` | Strong negative | Portfolio3Part |
| `rgba(251, 146, 60, 0.35-0.75)` | Moderate negative | Portfolio3Part |
| `rgba(253, 224, 71, 0.25-0.55)` | Weak correlation | Portfolio3Part |
| `rgba(134, 239, 172, 0.35-0.75)` | Moderate positive | Portfolio3Part |
| `rgba(34, 197, 94, 0.45-0.95)` | Strong positive | Portfolio3Part |
| `rgba(130, 188, 176, 0.25)` | Self correlation | Portfolio3Part |

#### Shadow Colors
| RGBA Value | Usage | Files |
|------------|-------|-------|
| `rgba(59,130,246,0.5)` | Blue shadow narrow | RiskSpectrum |
| `rgba(59,130,246,0.6)` | Blue shadow medium | RiskSpectrum |
| `rgba(59,130,246,0.7)` | Blue shadow wide | RiskSpectrum |
| `rgba(59,130,246,0.4)` | Blue shadow outer | RiskSpectrum |

---

### 3.4 Color Usage by Semantic Purpose

#### Status Indicators
| Purpose | Current Colors | Recommended Token |
|---------|---------------|-------------------|
| Success | `green-600`, `#22c55e`, `#10b981`, `#16a34a` | `--color-success` |
| Error | `red-600`, `#ef4444`, `#dc2626` | `--color-error` |
| Warning | `amber-600`, `#f59e0b`, `#ea580c` | `--color-warning` |
| Info | `blue-600`, `#3b82f6`, `#2563eb` | `--color-info` |

#### Risk Profile Colors
| Profile | Current Colors | Recommended Token |
|---------|---------------|-------------------|
| Very Conservative | `#1e40af`, `#00008B` | `--color-risk-very-conservative` |
| Conservative | `#60a5fa`, `#ADD8E6` | `--color-risk-conservative` |
| Moderate | `#10b981`, `#008000` | `--color-risk-moderate` |
| Aggressive | `#f59e0b`, `#FFA500` | `--color-risk-aggressive` |
| Very Aggressive | `#ef4444`, `#FF0000` | `--color-risk-very-aggressive` |

#### Portfolio Comparison
| Element | Current Colors | Recommended Token |
|---------|---------------|-------------------|
| Current Portfolio | `#ef4444` | `--color-portfolio-current` |
| Weights Optimized | `#3b82f6` | `--color-portfolio-weights` |
| Market Optimized | `#22c55e` | `--color-portfolio-market` |

#### Chart Elements
| Element | Current Colors | Recommended Token |
|---------|---------------|-------------------|
| Grid Lines | `#e5e7eb`, `rgba(200,200,195,0.8)` | `--color-chart-grid` |
| Axis Lines | `rgba(94,94,86,0.28)` | `--color-chart-axis` |
| Axis Ticks | `rgba(75,75,68,0.82)` | `--color-chart-tick` |
| Axis Labels | `#3B3B33` | `--color-chart-label` |
| Random Points | `#cbd5e1`, `#94a3b8` | `--color-chart-random` |
| Efficient Frontier | `#64748b` | `--color-chart-frontier` |
| CML Line | `#9333ea` | `--color-chart-cml` |

---

## 4. Proposed Theming Solution

### 4.1 Token-Based Color System

#### Core Design Principles
1. **Single Source of Truth:** All colors defined in one location
2. **Semantic Naming:** Colors named by purpose, not appearance
3. **Theme-Aware:** Support for light and dark themes
4. **JS Accessible:** Colors available to chart components via JavaScript

#### Token Categories

```css
/* === BASE TOKENS (Primitives) === */
/* These are the raw color values, not used directly in components */

:root {
  /* Gray Scale */
  --gray-50: 210 20% 98%;
  --gray-100: 210 15% 95%;
  --gray-200: 214 12% 90%;
  --gray-300: 214 10% 80%;
  --gray-400: 215 10% 65%;
  --gray-500: 215 12% 50%;
  --gray-600: 215 15% 35%;
  --gray-700: 215 18% 25%;
  --gray-800: 220 20% 15%;
  --gray-900: 222 25% 8%;
  --gray-950: 222 30% 5%;

  /* Blue Scale */
  --blue-50: 214 100% 97%;
  --blue-100: 214 95% 93%;
  --blue-200: 214 90% 85%;
  --blue-300: 214 85% 75%;
  --blue-400: 214 80% 60%;
  --blue-500: 214 75% 50%;
  --blue-600: 214 70% 45%;
  --blue-700: 214 65% 35%;
  --blue-800: 214 60% 25%;
  --blue-900: 214 55% 18%;

  /* Green Scale */
  --green-50: 142 80% 95%;
  --green-100: 142 75% 90%;
  --green-200: 142 70% 80%;
  --green-300: 142 65% 65%;
  --green-400: 142 60% 50%;
  --green-500: 142 55% 40%;
  --green-600: 142 50% 35%;
  --green-700: 142 45% 28%;
  --green-800: 142 40% 20%;
  --green-900: 142 35% 15%;

  /* Red Scale */
  --red-50: 0 85% 97%;
  --red-100: 0 80% 92%;
  --red-200: 0 75% 85%;
  --red-300: 0 70% 70%;
  --red-400: 0 65% 55%;
  --red-500: 0 60% 50%;
  --red-600: 0 55% 45%;
  --red-700: 0 50% 38%;
  --red-800: 0 45% 30%;
  --red-900: 0 40% 22%;

  /* Amber Scale */
  --amber-50: 45 95% 95%;
  --amber-100: 45 90% 88%;
  --amber-200: 45 85% 78%;
  --amber-300: 45 80% 65%;
  --amber-400: 45 75% 55%;
  --amber-500: 45 70% 48%;
  --amber-600: 45 65% 40%;
  --amber-700: 45 60% 32%;
  --amber-800: 45 55% 25%;
  --amber-900: 45 50% 18%;

  /* Purple Scale */
  --purple-50: 270 80% 97%;
  --purple-100: 270 75% 92%;
  --purple-200: 270 70% 82%;
  --purple-300: 270 65% 70%;
  --purple-400: 270 60% 58%;
  --purple-500: 270 55% 50%;
  --purple-600: 270 50% 42%;
  --purple-700: 270 45% 35%;
  --purple-800: 270 40% 28%;
  --purple-900: 270 35% 20%;
}
```

```css
/* === SEMANTIC TOKENS (Light Theme) === */
:root {
  /* Background */
  --background: var(--gray-50);
  --background-secondary: var(--gray-100);
  --background-tertiary: var(--gray-200);

  /* Foreground */
  --foreground: var(--gray-900);
  --foreground-secondary: var(--gray-600);
  --foreground-tertiary: var(--gray-500);
  --foreground-muted: var(--gray-400);

  /* Card */
  --card: 0 0% 100%;
  --card-foreground: var(--gray-900);

  /* Border */
  --border: var(--gray-200);
  --border-secondary: var(--gray-300);

  /* Primary (Actions) */
  --primary: var(--blue-600);
  --primary-foreground: 0 0% 100%;
  --primary-hover: var(--blue-700);
  --primary-muted: var(--blue-100);

  /* Status Colors */
  --success: var(--green-500);
  --success-foreground: 0 0% 100%;
  --success-muted: var(--green-100);

  --error: var(--red-500);
  --error-foreground: 0 0% 100%;
  --error-muted: var(--red-100);

  --warning: var(--amber-500);
  --warning-foreground: var(--gray-900);
  --warning-muted: var(--amber-100);

  --info: var(--blue-500);
  --info-foreground: 0 0% 100%;
  --info-muted: var(--blue-100);

  /* Risk Profile Colors */
  --risk-very-conservative: var(--blue-800);
  --risk-conservative: var(--blue-500);
  --risk-moderate: var(--green-500);
  --risk-aggressive: var(--amber-500);
  --risk-very-aggressive: var(--red-500);

  /* Portfolio Colors */
  --portfolio-current: var(--red-500);
  --portfolio-weights: var(--blue-500);
  --portfolio-market: var(--green-500);

  /* Chart Colors */
  --chart-canvas: var(--gray-50);
  --chart-grid: var(--gray-200);
  --chart-axis: var(--gray-400);
  --chart-tick: var(--gray-600);
  --chart-label: var(--gray-800);
  --chart-random: var(--gray-300);
  --chart-frontier: var(--gray-500);
  --chart-cml: var(--purple-500);
}
```

```css
/* === SEMANTIC TOKENS (Dark Theme) === */
.dark {
  /* Background */
  --background: var(--gray-950);
  --background-secondary: var(--gray-900);
  --background-tertiary: var(--gray-800);

  /* Foreground */
  --foreground: var(--gray-50);
  --foreground-secondary: var(--gray-300);
  --foreground-tertiary: var(--gray-400);
  --foreground-muted: var(--gray-500);

  /* Card */
  --card: var(--gray-900);
  --card-foreground: var(--gray-50);

  /* Border */
  --border: var(--gray-800);
  --border-secondary: var(--gray-700);

  /* Primary (Actions) */
  --primary: var(--gray-100);
  --primary-foreground: var(--gray-900);
  --primary-hover: var(--gray-200);
  --primary-muted: var(--gray-800);

  /* Status Colors (Muted for dark theme) */
  --success: 142 50% 45%;
  --success-foreground: var(--gray-50);
  --success-muted: 142 30% 15%;

  --error: 0 55% 50%;
  --error-foreground: var(--gray-50);
  --error-muted: 0 30% 18%;

  --warning: 45 65% 50%;
  --warning-foreground: var(--gray-900);
  --warning-muted: 45 30% 18%;

  --info: 214 60% 50%;
  --info-foreground: var(--gray-50);
  --info-muted: 214 30% 18%;

  /* Risk Profile Colors (Muted) */
  --risk-very-conservative: 214 50% 45%;
  --risk-conservative: 214 45% 55%;
  --risk-moderate: 142 45% 45%;
  --risk-aggressive: 45 55% 50%;
  --risk-very-aggressive: 0 50% 50%;

  /* Portfolio Colors */
  --portfolio-current: 0 55% 55%;
  --portfolio-weights: 214 55% 55%;
  --portfolio-market: 142 50% 50%;

  /* Chart Colors */
  --chart-canvas: var(--gray-950);
  --chart-grid: 220 10% 15%;
  --chart-axis: 220 10% 25%;
  --chart-tick: 220 10% 50%;
  --chart-label: 220 10% 70%;
  --chart-random: 220 10% 35%;
  --chart-frontier: 220 10% 45%;
  --chart-cml: 270 45% 55%;
}
```

---

### 4.2 JavaScript Theme Provider

Create a centralized theme configuration that can be imported by chart components.

#### File: `frontend/src/config/theme.ts`

```typescript
/**
 * Centralized theme configuration
 * Single source of truth for all colors in the application
 */

export type ThemeMode = 'light' | 'dark';

// Chart-specific color palette (for Recharts)
export const chartPalette = {
  light: [
    '#16a34a', // Green
    '#dc2626', // Red
    '#2563eb', // Blue
    '#ca8a04', // Gold
    '#9333ea', // Purple
    '#ea580c', // Orange
    '#0891b2', // Cyan
    '#be185d', // Pink
    '#65a30d', // Lime
    '#0e7490', // Teal
  ],
  dark: [
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
  ],
};

// Visualization theme (for chart components)
export const getVisualizationTheme = (mode: ThemeMode = 'light') => {
  if (mode === 'dark') {
    return {
      canvas: '#0c0d0e',
      cardBackground: '#14151a',
      border: 'rgba(255, 255, 255, 0.08)',
      grid: 'rgba(255, 255, 255, 0.06)',
      axes: {
        line: 'rgba(255, 255, 255, 0.1)',
        tick: 'rgba(255, 255, 255, 0.5)',
        label: 'rgba(255, 255, 255, 0.7)',
      },
      text: {
        primary: 'rgba(255, 255, 255, 0.9)',
        secondary: 'rgba(255, 255, 255, 0.6)',
        subtle: 'rgba(255, 255, 255, 0.4)',
      },
      spacing: {
        cardPadding: '28px',
        sectionGap: '28px',
      },
      radius: '18px',
      hoverFadeOpacity: 0.4,
      legend: {
        fontSize: 12,
        color: 'rgba(255, 255, 255, 0.7)',
      },
    };
  }

  // Light theme (current default)
  return {
    canvas: '#FAFAF4',
    cardBackground: '#FFFFFF',
    border: 'rgba(90, 90, 82, 0.12)',
    grid: 'rgba(200, 200, 195, 0.8)',
    axes: {
      line: 'rgba(94, 94, 86, 0.28)',
      tick: 'rgba(75, 75, 68, 0.82)',
      label: '#3B3B33',
    },
    text: {
      primary: '#2F2F29',
      secondary: '#6D6D62',
      subtle: 'rgba(90, 90, 82, 0.65)',
    },
    spacing: {
      cardPadding: '28px',
      sectionGap: '28px',
    },
    radius: '18px',
    hoverFadeOpacity: 0.4,
    legend: {
      fontSize: 12,
      color: 'rgba(59, 59, 51, 0.8)',
    },
  };
};

// Risk profile colors
export const getRiskColors = (mode: ThemeMode = 'light') => ({
  'very-conservative': mode === 'dark' ? '#3b82f6' : '#1e40af',
  'conservative': mode === 'dark' ? '#60a5fa' : '#3b82f6',
  'moderate': mode === 'dark' ? '#4ade80' : '#10b981',
  'aggressive': mode === 'dark' ? '#fbbf24' : '#f59e0b',
  'very-aggressive': mode === 'dark' ? '#f87171' : '#ef4444',
});

// Portfolio comparison colors
export const getPortfolioColors = (mode: ThemeMode = 'light') => ({
  current: mode === 'dark' ? '#f87171' : '#ef4444',
  weights: mode === 'dark' ? '#60a5fa' : '#3b82f6',
  market: mode === 'dark' ? '#4ade80' : '#22c55e',
});

// Status colors
export const getStatusColors = (mode: ThemeMode = 'light') => ({
  success: mode === 'dark' ? '#4ade80' : '#22c55e',
  error: mode === 'dark' ? '#f87171' : '#ef4444',
  warning: mode === 'dark' ? '#fbbf24' : '#f59e0b',
  info: mode === 'dark' ? '#60a5fa' : '#3b82f6',
});

// Percentile/scenario colors
export const getPercentileColors = (mode: ThemeMode = 'light') => ({
  p5: mode === 'dark' ? '#f87171' : '#ef4444',   // Worst case
  p25: mode === 'dark' ? '#fbbf24' : '#f59e0b',  // Pessimistic
  p50: mode === 'dark' ? '#60a5fa' : '#3b82f6',  // Expected
  p75: mode === 'dark' ? '#4ade80' : '#22c55e',  // Optimistic
  p95: mode === 'dark' ? '#34d399' : '#10b981',  // Best case
});

// Quadrant colors (for TwoDimensionalMap)
export const getQuadrantColors = (mode: ThemeMode = 'light') => ({
  'high-high': {
    fill: mode === 'dark' ? 'rgba(74, 222, 128, 0.2)' : 'rgba(34, 197, 94, 0.35)',
    border: mode === 'dark' ? '#4ade80' : '#10b981',
    background: mode === 'dark' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(34, 197, 94, 0.15)',
  },
  'low-high': {
    fill: mode === 'dark' ? 'rgba(251, 191, 36, 0.2)' : 'rgba(245, 158, 11, 0.35)',
    border: mode === 'dark' ? '#fbbf24' : '#eab308',
    background: mode === 'dark' ? 'rgba(251, 191, 36, 0.1)' : 'rgba(234, 179, 8, 0.15)',
  },
  'high-low': {
    fill: mode === 'dark' ? 'rgba(96, 165, 250, 0.2)' : 'rgba(59, 130, 246, 0.35)',
    border: mode === 'dark' ? '#60a5fa' : '#3b82f6',
    background: mode === 'dark' ? 'rgba(96, 165, 250, 0.1)' : 'rgba(59, 130, 246, 0.15)',
  },
  'low-low': {
    fill: mode === 'dark' ? 'rgba(156, 163, 175, 0.2)' : 'rgba(156, 163, 175, 0.35)',
    border: mode === 'dark' ? '#9ca3af' : '#9ca3af',
    background: mode === 'dark' ? 'rgba(156, 163, 175, 0.1)' : 'rgba(107, 114, 128, 0.15)',
  },
});
```

---

### 4.3 React Theme Context

#### File: `frontend/src/contexts/ThemeContext.tsx`

```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  ThemeMode,
  getVisualizationTheme,
  getRiskColors,
  getPortfolioColors,
  getStatusColors,
  getPercentileColors,
  getQuadrantColors,
  chartPalette,
} from '@/config/theme';

interface ThemeContextValue {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
  visualization: ReturnType<typeof getVisualizationTheme>;
  riskColors: ReturnType<typeof getRiskColors>;
  portfolioColors: ReturnType<typeof getPortfolioColors>;
  statusColors: ReturnType<typeof getStatusColors>;
  percentileColors: ReturnType<typeof getPercentileColors>;
  quadrantColors: ReturnType<typeof getQuadrantColors>;
  chartPalette: string[];
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<ThemeMode>('dark'); // Default to dark for new theme

  useEffect(() => {
    // Apply dark class to document
    if (mode === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [mode]);

  const toggleMode = () => setMode(m => m === 'light' ? 'dark' : 'light');

  const value: ThemeContextValue = {
    mode,
    setMode,
    toggleMode,
    visualization: getVisualizationTheme(mode),
    riskColors: getRiskColors(mode),
    portfolioColors: getPortfolioColors(mode),
    statusColors: getStatusColors(mode),
    percentileColors: getPercentileColors(mode),
    quadrantColors: getQuadrantColors(mode),
    chartPalette: chartPalette[mode],
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
```

---

### 4.4 Integration with Existing Stack

#### Tailwind Configuration Update

```typescript
// tailwind.config.ts
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // All colors now reference CSS variables
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',

        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },

        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
          hover: 'hsl(var(--primary-hover))',
          muted: 'hsl(var(--primary-muted))',
        },

        // Status colors
        success: {
          DEFAULT: 'hsl(var(--success))',
          foreground: 'hsl(var(--success-foreground))',
          muted: 'hsl(var(--success-muted))',
        },
        error: {
          DEFAULT: 'hsl(var(--error))',
          foreground: 'hsl(var(--error-foreground))',
          muted: 'hsl(var(--error-muted))',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning))',
          foreground: 'hsl(var(--warning-foreground))',
          muted: 'hsl(var(--warning-muted))',
        },
        info: {
          DEFAULT: 'hsl(var(--info))',
          foreground: 'hsl(var(--info-foreground))',
          muted: 'hsl(var(--info-muted))',
        },

        // Risk profile colors
        risk: {
          'very-conservative': 'hsl(var(--risk-very-conservative))',
          'conservative': 'hsl(var(--risk-conservative))',
          'moderate': 'hsl(var(--risk-moderate))',
          'aggressive': 'hsl(var(--risk-aggressive))',
          'very-aggressive': 'hsl(var(--risk-very-aggressive))',
        },

        // Portfolio colors
        portfolio: {
          current: 'hsl(var(--portfolio-current))',
          weights: 'hsl(var(--portfolio-weights))',
          market: 'hsl(var(--portfolio-market))',
        },

        // Border
        border: {
          DEFAULT: 'hsl(var(--border))',
          secondary: 'hsl(var(--border-secondary))',
        },

        // Foreground variants
        muted: {
          DEFAULT: 'hsl(var(--foreground-muted))',
          foreground: 'hsl(var(--foreground-secondary))',
        },
      },
    },
  },
} satisfies Config;
```

---

## 5. Integration Plan

### 5.1 Phase Overview

| Phase | Focus | Duration | Risk |
|-------|-------|----------|------|
| Phase 1 | Core Infrastructure | 2-3 hours | Low |
| Phase 2 | UI Components | 2-3 hours | Low |
| Phase 3 | Layout & Navigation | 1-2 hours | Low |
| Phase 4 | Wizard Steps (Simple) | 2-3 hours | Medium |
| Phase 5 | Visualization Components | 3-4 hours | High |
| Phase 6 | Complex Wizard Steps | 3-4 hours | High |
| Phase 7 | Testing & Polish | 2-3 hours | Low |

**Total Estimated Effort:** 15-22 hours (2 days)

---

### 5.2 Phase 1: Core Infrastructure

**Objective:** Establish the theming foundation

**Files to Create:**
1. `frontend/src/config/theme.ts` - Theme configuration
2. `frontend/src/contexts/ThemeContext.tsx` - Theme provider

**Files to Modify:**
1. `frontend/src/index.css` - CSS variables (complete rewrite)
2. `frontend/tailwind.config.ts` - Color configuration
3. `frontend/src/App.tsx` - Add ThemeProvider

**Order of Operations:**
1. Create `theme.ts` with all color configurations
2. Create `ThemeContext.tsx` with provider and hook
3. Update `index.css` with new CSS variable system
4. Update `tailwind.config.ts` to use new color tokens
5. Wrap App with ThemeProvider
6. Verify no build errors

**Verification:**
- Application builds without errors
- Dark class applied to document
- CSS variables accessible via DevTools

---

### 5.3 Phase 2: UI Components

**Objective:** Update shadcn/ui components to use theme tokens

**Files to Modify:**
| File | Changes |
|------|---------|
| `components/ui/button.tsx` | Remove gradient variant, update colors |
| `components/ui/card.tsx` | Update shadow, border styles |
| `components/ui/input.tsx` | Update focus ring, border colors |
| `components/ui/alert.tsx` | Update variant colors |
| `components/ui/badge.tsx` | Update variant colors |
| `components/ui/progress.tsx` | Update indicator color |
| `components/ui/tabs.tsx` | Update active state colors |

**Order of Operations:**
1. Update `button.tsx` (most critical)
2. Update `card.tsx` (used everywhere)
3. Update remaining UI components
4. Test each component in isolation

**Verification:**
- All button variants work in dark mode
- Cards have proper contrast
- Form inputs are usable

---

### 5.4 Phase 3: Layout & Navigation

**Objective:** Update main layout components

**Files to Modify:**
| File | Line(s) | Change |
|------|---------|--------|
| `PortfolioWizard.tsx` | 207 | Remove gradient, use `bg-background` |
| `PortfolioWizard.tsx` | 209-225 | Update header to dark theme |
| `PortfolioWizard.tsx` | 229-249 | Update progress indicator |
| `NotFound.tsx` | All | Update page styling |
| `Index.tsx` | If any | Update page wrapper |

**Order of Operations:**
1. Update PortfolioWizard layout (main container)
2. Update navigation header
3. Update progress indicator
4. Update NotFound page
5. Test navigation flow

**Verification:**
- Main layout is dark
- Navigation is readable
- Progress indicator works
- 404 page is styled

---

### 5.5 Phase 4: Wizard Steps (Simple)

**Objective:** Update simple wizard steps

**Files to Modify:**
| File | Complexity | Key Changes |
|------|------------|-------------|
| `WelcomeStep.tsx` | Low | Remove gradients, update colors |
| `CapitalInput.tsx` | Low | Remove gradient, update form |
| `FlagAlerts.tsx` | Low | Update alert colors |
| `ConfirmationModal.tsx` | Low | Update modal styling |

**Order of Operations:**
1. Update `WelcomeStep.tsx`
2. Update `CapitalInput.tsx`
3. Update `FlagAlerts.tsx`
4. Update `ConfirmationModal.tsx`
5. Test wizard flow through step 3

**Verification:**
- Welcome step displays correctly
- Capital input form is usable
- Alerts are visible
- Modals have proper contrast

---

### 5.6 Phase 5: Visualization Components

**Objective:** Update all chart components to use theme context

**Files to Modify:**
| File | Changes Required |
|------|-----------------|
| `EfficientFrontierChart.tsx` | Use `useTheme()`, update 50+ colors |
| `Portfolio3PartVisualization.tsx` | Use `useTheme()`, update 80+ colors |
| `FiveYearProjectionChart.tsx` | Update chart colors |
| `RiskReturnChart.tsx` | Update chart colors |
| `SectorDistributionChart.tsx` | Update palette colors |
| `TwoAssetChart.tsx` | Update chart colors |
| `TwoDimensionalMap.tsx` | Use quadrant colors |
| `RiskSpectrum.tsx` | Use risk colors |

**Order of Operations:**
1. Update `EfficientFrontierChart.tsx` first (used in optimization)
2. Update `Portfolio3PartVisualization.tsx` (used in stock selection)
3. Update `TwoDimensionalMap.tsx` (used in risk profiler)
4. Update `RiskSpectrum.tsx` (used in risk profiler)
5. Update remaining chart components
6. Test all visualizations

**Critical Changes:**
```typescript
// Before
const visualizationTheme = { canvas: '#FAFAF4', ... };

// After
import { useTheme } from '@/contexts/ThemeContext';

const { visualization } = useTheme();
// Use visualization.canvas, visualization.grid, etc.
```

**Verification:**
- All charts render on dark background
- Data points are visible
- Grid lines are subtle but present
- Axis labels are readable
- Tooltips are styled correctly

---

### 5.7 Phase 6: Complex Wizard Steps

**Objective:** Update remaining wizard steps with heavy color usage

**Files to Modify:**
| File | Estimated Changes | Complexity |
|------|------------------|------------|
| `StressTest.tsx` | 150+ | High |
| `PortfolioOptimization.tsx` | 200+ | High |
| `StockSelection.tsx` | 100+ | High |
| `RiskProfiler.tsx` | 50+ | Medium |
| `FinalizePortfolio.tsx` | 30+ | Medium |
| `FinalAnalysisComponents.tsx` | 80+ | High |
| `PortfolioComparisonTable.tsx` | 40+ | Medium |
| `RecommendationsTabReview.tsx` | 50+ | Medium |
| `PortfolioBuilder.tsx` | 40+ | Medium |
| `CategoryCard.tsx` | 20+ | Low |
| `ResultsPage.tsx` | 30+ | Medium |

**Order of Operations:**
1. Update `RiskProfiler.tsx` (Step 2)
2. Update `StockSelection.tsx` (Step 4)
3. Update `PortfolioOptimization.tsx` (Step 5) - Most complex
4. Update `StressTest.tsx` (Step 6) - Second most complex
5. Update `FinalizePortfolio.tsx` and related components (Step 7)
6. Test complete wizard flow

**Verification:**
- Complete wizard flow works
- All steps display correctly in dark mode
- Charts and visualizations are consistent
- Forms and inputs are usable
- Risk categories are distinguishable

---

### 5.8 Phase 7: Testing & Polish

**Objective:** Comprehensive testing and final adjustments

**Tasks:**
1. **Full Wizard Test:** Complete wizard from start to finish
2. **Contrast Check:** Verify WCAG AA compliance
3. **Edge Cases:** Test error states, loading states, empty states
4. **Responsive Test:** Check mobile and tablet layouts
5. **Browser Test:** Verify Chrome, Firefox, Safari
6. **Performance:** Ensure no render performance issues
7. **Final Polish:** Fix any visual inconsistencies

**Verification Checklist:**
- [ ] All 7 wizard steps functional
- [ ] All visualizations readable
- [ ] All forms usable
- [ ] All buttons have proper states
- [ ] No hardcoded colors remain (grep verification)
- [ ] WCAG AA contrast met
- [ ] No console errors
- [ ] Performance acceptable

---

## 6. Agent Task Delegation

### 6.1 Agent Overview

| Agent | Responsibility | Complexity | Est. Time |
|-------|---------------|------------|-----------|
| Agent 1: Foundation | Core infrastructure, CSS variables | Medium | 3 hours |
| Agent 2: Components | UI components, shadcn updates | Low | 2 hours |
| Agent 3: Layout | Main layout, navigation, simple steps | Low | 2 hours |
| Agent 4: Charts | All visualization components | High | 4 hours |
| Agent 5: Wizard | Complex wizard steps | High | 5 hours |
| Agent 6: QA | Testing, polish, verification | Medium | 2 hours |

---

### 6.2 Agent 1: Foundation Agent

**Responsibility:** Establish theming infrastructure

**Tasks:**
1. Create `frontend/src/config/theme.ts`
2. Create `frontend/src/contexts/ThemeContext.tsx`
3. Update `frontend/src/index.css` with complete CSS variable system
4. Update `frontend/tailwind.config.ts`
5. Update `frontend/src/App.tsx` to include ThemeProvider

**Files to Create:**
- `frontend/src/config/theme.ts`
- `frontend/src/contexts/ThemeContext.tsx`

**Files to Modify:**
- `frontend/src/index.css`
- `frontend/tailwind.config.ts`
- `frontend/src/App.tsx`

**Boundaries:**
- DO NOT modify any component files
- DO NOT change any functionality
- ONLY establish infrastructure

**Expected Output:**
- Working dark theme toggle
- All CSS variables defined
- ThemeProvider wrapping app
- Build passes with no errors

**Context Files for Cursor:**
```
frontend/src/index.css
frontend/tailwind.config.ts
frontend/src/App.tsx
THEMING_ANALYSIS.md (Section 4)
```

**Cursor Prompt:**
```
Create the theming infrastructure for a Linear.app-inspired dark theme.

Tasks:
1. Create frontend/src/config/theme.ts with:
   - chartPalette (light/dark arrays)
   - getVisualizationTheme() function
   - getRiskColors(), getPortfolioColors(), getStatusColors()
   - getPercentileColors(), getQuadrantColors()

2. Create frontend/src/contexts/ThemeContext.tsx with:
   - ThemeProvider component
   - useTheme hook
   - Mode toggle functionality

3. Update frontend/src/index.css with:
   - Base color primitives (gray, blue, green, red, amber, purple scales)
   - Semantic tokens for light theme
   - Semantic tokens for dark theme (.dark class)
   - Remove existing gradient definitions

4. Update frontend/tailwind.config.ts with:
   - New color token references
   - Status color definitions
   - Risk profile colors
   - Portfolio colors

5. Update frontend/src/App.tsx to wrap with ThemeProvider

Use the color values from THEMING_ANALYSIS.md Section 4.
Default to dark mode.
```

---

### 6.3 Agent 2: Components Agent

**Responsibility:** Update shadcn/ui components

**Tasks:**
1. Update `button.tsx` - Remove gradient, update variants
2. Update `card.tsx` - Update shadow/border
3. Update `input.tsx` - Update focus styles
4. Update `alert.tsx` - Update variants
5. Update `badge.tsx` - Update variants
6. Update `progress.tsx` - Update colors
7. Update `tabs.tsx` - Update active states

**Files to Modify:**
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/card.tsx`
- `frontend/src/components/ui/input.tsx`
- `frontend/src/components/ui/alert.tsx`
- `frontend/src/components/ui/badge.tsx`
- `frontend/src/components/ui/progress.tsx`
- `frontend/src/components/ui/tabs.tsx`

**Boundaries:**
- ONLY modify files in `components/ui/`
- DO NOT modify wizard components
- Use CSS variable classes only

**Expected Output:**
- All UI components work in dark mode
- No hardcoded colors in UI components
- Proper hover/focus states

**Context Files for Cursor:**
```
frontend/src/components/ui/button.tsx
frontend/src/components/ui/card.tsx
frontend/src/index.css (updated)
THEMING_ANALYSIS.md (Section 3.1 - Tailwind classes)
```

**Cursor Prompt:**
```
Update the shadcn/ui components to use the new dark theme CSS variables.

For button.tsx:
1. Remove the "gradient" variant completely
2. Update default variant to use CSS variables
3. Simplify hover states (no opacity animations)
4. Update conservative/moderate/aggressive variants to use --risk-* variables

For card.tsx:
1. Replace "shadow-sm" with "border border-border"
2. Ensure bg-card is used
3. Update CardTitle styling

For input.tsx:
1. Update focus ring colors
2. Ensure proper contrast in dark mode

For alert.tsx:
1. Update destructive variant for dark mode
2. Add success/warning/info variants

For badge.tsx:
1. Update color variants
2. Add risk-profile variants

Use only CSS variable classes (bg-background, text-foreground, border-border, etc.)
DO NOT use hardcoded Tailwind color classes (blue-600, gray-200, etc.)
```

---

### 6.4 Agent 3: Layout Agent

**Responsibility:** Update layout and simple wizard steps

**Tasks:**
1. Update `PortfolioWizard.tsx` - Main layout
2. Update `NotFound.tsx` - 404 page
3. Update `WelcomeStep.tsx` - Step 1
4. Update `CapitalInput.tsx` - Step 3
5. Update `ConfirmationModal.tsx`
6. Update `FlagAlerts.tsx`

**Files to Modify:**
- `frontend/src/components/PortfolioWizard.tsx`
- `frontend/src/pages/NotFound.tsx`
- `frontend/src/components/wizard/WelcomeStep.tsx`
- `frontend/src/components/wizard/CapitalInput.tsx`
- `frontend/src/components/wizard/ConfirmationModal.tsx`
- `frontend/src/components/wizard/FlagAlerts.tsx`

**Boundaries:**
- Remove ALL gradient classes
- Replace ALL hardcoded color classes with CSS variables
- DO NOT modify chart components

**Expected Output:**
- Dark themed main layout
- Working navigation
- Steps 1 and 3 display correctly

**Context Files for Cursor:**
```
frontend/src/components/PortfolioWizard.tsx
frontend/src/components/wizard/WelcomeStep.tsx
frontend/src/components/wizard/CapitalInput.tsx
frontend/src/index.css (updated)
THEMING_ANALYSIS.md (Section 3.1)
```

**Cursor Prompt:**
```
Update the layout and simple wizard components for the dark theme.

For PortfolioWizard.tsx:
1. Line 207: Replace "bg-gradient-to-br from-blue-50 to-indigo-100" with "bg-background"
2. Lines 209-225: Update header - replace "bg-white border-gray-200" with "bg-card border-border"
3. Replace all blue-600, gray-* classes with CSS variable equivalents
4. Update step indicator to use primary colors

For WelcomeStep.tsx:
1. Remove "bg-gradient-primary" (line 47)
2. Update feature cards to use bg-card and border-border
3. Remove gradient button styling
4. Replace all hardcoded colors

For CapitalInput.tsx:
1. Remove gradient icon background
2. Update validation colors to use --success and --error
3. Update info box styling

For NotFound.tsx:
1. Update to use bg-background and text-foreground
2. Update link colors

Replace patterns:
- bg-gradient-* → bg-secondary or bg-card
- text-blue-* → text-primary or text-foreground
- text-gray-* → text-muted-foreground
- bg-white → bg-card
- border-gray-* → border-border
```

---

### 6.5 Agent 4: Charts Agent

**Responsibility:** Update all visualization components

**Tasks:**
1. Update `EfficientFrontierChart.tsx`
2. Update `Portfolio3PartVisualization.tsx`
3. Update `TwoDimensionalMap.tsx`
4. Update `RiskSpectrum.tsx`
5. Update `FiveYearProjectionChart.tsx`
6. Update `RiskReturnChart.tsx`
7. Update `SectorDistributionChart.tsx`
8. Update `TwoAssetChart.tsx`
9. Update `scoring-engine.ts` (getCategoryColor)

**Files to Modify:**
- `frontend/src/components/wizard/EfficientFrontierChart.tsx`
- `frontend/src/components/wizard/Portfolio3PartVisualization.tsx`
- `frontend/src/components/wizard/TwoDimensionalMap.tsx`
- `frontend/src/components/wizard/RiskSpectrum.tsx`
- `frontend/src/components/wizard/FiveYearProjectionChart.tsx`
- `frontend/src/components/wizard/RiskReturnChart.tsx`
- `frontend/src/components/wizard/SectorDistributionChart.tsx`
- `frontend/src/components/wizard/TwoAssetChart.tsx`
- `frontend/src/components/wizard/scoring-engine.ts`

**Boundaries:**
- Import and use `useTheme` hook
- Replace local visualizationTheme with theme context
- Replace all hardcoded hex/rgba colors

**Expected Output:**
- All charts render correctly on dark background
- Consistent color palette across all charts
- Data remains visible and accessible

**Context Files for Cursor:**
```
frontend/src/components/wizard/EfficientFrontierChart.tsx
frontend/src/components/wizard/Portfolio3PartVisualization.tsx
frontend/src/contexts/ThemeContext.tsx
frontend/src/config/theme.ts
THEMING_ANALYSIS.md (Section 3.2, 3.3)
```

**Cursor Prompt:**
```
Update all visualization components to use the centralized theme system.

For each chart component:
1. Add import: import { useTheme } from '@/contexts/ThemeContext';
2. Get theme values: const { visualization, chartPalette, portfolioColors } = useTheme();
3. Remove the local visualizationTheme object
4. Replace all hardcoded colors with theme values

Specific mappings:
- visualizationTheme.canvas → visualization.canvas
- visualizationTheme.grid → visualization.grid
- '#ef4444' (red) → portfolioColors.current
- '#3b82f6' (blue) → portfolioColors.weights
- '#22c55e' (green) → portfolioColors.market
- '#e5e7eb' (grid) → visualization.grid
- vividPalette → chartPalette

For TwoDimensionalMap.tsx:
- Use getQuadrantColors() for quadrant fills and borders
- Update reference area colors

For RiskSpectrum.tsx:
- Use getRiskColors() for the risk zones

For scoring-engine.ts:
- Update getCategoryColor() to accept theme mode parameter

Ensure all tooltips have dark backgrounds and light text.
Test that data points are visible against dark canvas.
```

---

### 6.6 Agent 5: Wizard Agent

**Responsibility:** Update complex wizard steps

**Tasks:**
1. Update `RiskProfiler.tsx`
2. Update `StockSelection.tsx`
3. Update `PortfolioOptimization.tsx`
4. Update `StressTest.tsx`
5. Update `FinalizePortfolio.tsx`
6. Update `FinalAnalysisComponents.tsx`
7. Update `PortfolioComparisonTable.tsx`
8. Update `PortfolioBuilder.tsx`
9. Update `CategoryCard.tsx`
10. Update `ResultsPage.tsx`
11. Update `RecommendationsTabReview.tsx`

**Files to Modify:**
- All files listed above in `frontend/src/components/wizard/`

**Boundaries:**
- Replace ALL hardcoded Tailwind classes
- Replace ALL inline style colors
- Import useTheme where needed for dynamic colors
- Maintain all existing functionality

**Expected Output:**
- Complete wizard flow works in dark mode
- All forms usable
- All indicators visible
- Consistent visual language

**Context Files for Cursor:**
```
frontend/src/components/wizard/StressTest.tsx
frontend/src/components/wizard/PortfolioOptimization.tsx
frontend/src/components/wizard/StockSelection.tsx
frontend/src/contexts/ThemeContext.tsx
THEMING_ANALYSIS.md (Section 3.1, 3.2, 3.3)
```

**Cursor Prompt:**
```
Update the complex wizard step components for the dark theme.

Common replacements needed:
- bg-blue-50, bg-blue-100 → bg-info-muted
- bg-green-50 → bg-success-muted
- bg-red-50 → bg-error-muted
- bg-amber-50 → bg-warning-muted
- text-blue-600, text-blue-700 → text-info
- text-green-600 → text-success
- text-red-600 → text-error
- border-blue-200 → border-info/30
- border-green-200 → border-success/30
- border-red-200 → border-error/30
- bg-gray-100, bg-gray-200 → bg-secondary
- text-gray-500, text-gray-600 → text-muted-foreground
- bg-white → bg-card

For inline styles with hex colors:
- Import useTheme hook
- Get colors from context
- Replace style={{ color: '#3b82f6' }} with style={{ color: portfolioColors.weights }}

For status indicators:
- Use statusColors from theme context
- if (positive) use statusColors.success
- if (negative) use statusColors.error

For selection states:
- Selected: border-primary bg-primary-muted
- Unselected: border-border bg-background

Remove all gradient-to-* classes.
Ensure loading spinners use primary colors.
Test all interactive states (hover, focus, selected, disabled).
```

---

### 6.7 Agent 6: QA Agent

**Responsibility:** Testing, verification, and final polish

**Tasks:**
1. Run grep to verify no hardcoded colors remain
2. Complete wizard flow test
3. WCAG contrast verification
4. Edge case testing
5. Cross-browser testing
6. Final visual polish

**Verification Commands:**
```bash
# Check for remaining hardcoded Tailwind colors
grep -r "blue-[0-9]" frontend/src --include="*.tsx" | wc -l
grep -r "gray-[0-9]" frontend/src --include="*.tsx" | wc -l
grep -r "green-[0-9]" frontend/src --include="*.tsx" | wc -l
grep -r "red-[0-9]" frontend/src --include="*.tsx" | wc -l

# Check for hardcoded hex colors in TSX files
grep -r "#[0-9a-fA-F]\{6\}" frontend/src --include="*.tsx" | wc -l

# Should be 0 or minimal for each
```

**Expected Output:**
- Zero or minimal hardcoded colors
- All flows working
- Accessibility verified
- List of any remaining issues

**Context Files for Cursor:**
```
All updated files
THEMING_ANALYSIS.md (Section 5.8 - Verification Checklist)
```

**Cursor Prompt:**
```
Perform final QA verification for the theme migration.

1. Run grep commands to find any remaining hardcoded colors:
   - Tailwind color classes (blue-*, gray-*, green-*, red-*)
   - Hex values (#XXXXXX)
   - rgba() values not in theme

2. For each remaining instance:
   - Assess if it should be replaced
   - If yes, replace with appropriate CSS variable
   - If no, document why it's acceptable

3. Test complete wizard flow:
   - Start from Step 1 (Welcome)
   - Complete through Step 7 (Finalize)
   - Verify each step displays correctly
   - Check all interactive elements work

4. Verify contrast ratios:
   - Primary text on background: 4.5:1 minimum
   - Secondary text: 3:1 minimum
   - Chart labels: 3:1 minimum
   - Button text: 4.5:1 minimum

5. Test edge cases:
   - Error states
   - Loading states
   - Empty states
   - Very long content
   - Mobile viewport

6. Document any remaining issues that need attention.

Provide a final report with:
- Remaining hardcoded color count
- List of any unfixed issues
- Suggestions for future improvements
```

---

## 7. Appendices

### 7.1 File-to-Agent Mapping

| File | Agent |
|------|-------|
| `index.css` | Agent 1 |
| `tailwind.config.ts` | Agent 1 |
| `App.tsx` | Agent 1 |
| `config/theme.ts` | Agent 1 |
| `contexts/ThemeContext.tsx` | Agent 1 |
| `ui/button.tsx` | Agent 2 |
| `ui/card.tsx` | Agent 2 |
| `ui/input.tsx` | Agent 2 |
| `ui/alert.tsx` | Agent 2 |
| `ui/badge.tsx` | Agent 2 |
| `ui/progress.tsx` | Agent 2 |
| `ui/tabs.tsx` | Agent 2 |
| `PortfolioWizard.tsx` | Agent 3 |
| `NotFound.tsx` | Agent 3 |
| `WelcomeStep.tsx` | Agent 3 |
| `CapitalInput.tsx` | Agent 3 |
| `ConfirmationModal.tsx` | Agent 3 |
| `FlagAlerts.tsx` | Agent 3 |
| `EfficientFrontierChart.tsx` | Agent 4 |
| `Portfolio3PartVisualization.tsx` | Agent 4 |
| `TwoDimensionalMap.tsx` | Agent 4 |
| `RiskSpectrum.tsx` | Agent 4 |
| `FiveYearProjectionChart.tsx` | Agent 4 |
| `RiskReturnChart.tsx` | Agent 4 |
| `SectorDistributionChart.tsx` | Agent 4 |
| `TwoAssetChart.tsx` | Agent 4 |
| `scoring-engine.ts` | Agent 4 |
| `RiskProfiler.tsx` | Agent 5 |
| `StockSelection.tsx` | Agent 5 |
| `PortfolioOptimization.tsx` | Agent 5 |
| `StressTest.tsx` | Agent 5 |
| `FinalizePortfolio.tsx` | Agent 5 |
| `FinalAnalysisComponents.tsx` | Agent 5 |
| `PortfolioComparisonTable.tsx` | Agent 5 |
| `PortfolioBuilder.tsx` | Agent 5 |
| `CategoryCard.tsx` | Agent 5 |
| `ResultsPage.tsx` | Agent 5 |
| `RecommendationsTabReview.tsx` | Agent 5 |

### 7.2 Color Token Quick Reference

```
Background:      bg-background, bg-secondary, bg-card
Text:            text-foreground, text-muted-foreground
Border:          border-border, border-secondary
Primary:         bg-primary, text-primary, border-primary
Success:         bg-success, text-success, bg-success-muted
Error:           bg-error, text-error, bg-error-muted
Warning:         bg-warning, text-warning, bg-warning-muted
Info:            bg-info, text-info, bg-info-muted
Risk:            text-risk-conservative, text-risk-aggressive, etc.
Portfolio:       text-portfolio-current, text-portfolio-weights, text-portfolio-market
```

### 7.3 Gradient Replacement Guide

| Original | Replacement |
|----------|-------------|
| `bg-gradient-to-br from-blue-50 to-indigo-100` | `bg-background` |
| `bg-gradient-primary` | `bg-secondary` |
| `bg-gradient-to-r from-blue-50 to-purple-50` | `bg-info-muted` |
| `bg-gradient-to-r from-green-50 to-blue-50` | `bg-success-muted` |
| `bg-gradient-to-r from-blue-600 to-indigo-600` | `bg-primary` |

---

**Document Version:** 1.0
**Last Updated:** 2026-02-04
**Total Hardcoded Colors Identified:** 400+
**Estimated Migration Effort:** 15-22 hours
