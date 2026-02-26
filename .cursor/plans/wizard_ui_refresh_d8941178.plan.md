---
name: Wizard UI Refresh
overview: A systematic UI refresh across all 8 wizard steps to create a uniform, polished, and presentable design while preserving all existing features, functions, and light/dark theming.
todos:
  - id: foundation-layout
    content: "Update PortfolioWizard.tsx: widen to max-w-5xl, upgrade progress bar to segmented stepper with step icons"
    status: pending
  - id: remove-width-overrides
    content: Remove per-step max-width and padding overrides from all 8 step components
    status: pending
  - id: unified-headers
    content: Standardize all step headers to use StepCardHeader + StepHeaderIcon
    status: pending
  - id: card-styling
    content: Apply consistent shadow-sm, top accent border, remove per-step gradient backgrounds
    status: pending
  - id: dark-mode-colors
    content: Replace all hard-coded colors (blue-600, emerald-50, purple-50, etc.) with theme-safe CSS variable alternatives
    status: pending
  - id: welcome-refresh
    content: Redesign WelcomeStep for stronger first impression while keeping feature grid and CTA
    status: pending
  - id: spacing-polish
    content: Standardize spacing, typography, and navigation button patterns across all steps
    status: pending
  - id: verify-all-steps
    content: Test all 8 steps in both light and dark themes to verify visual consistency and no regressions
    status: pending
isProject: false
---

# Portfolio Wizard UI Refresh Plan

## Current State Analysis

After reviewing all 8 wizard steps and the main orchestrator, here are the key design inconsistencies and areas for improvement:

### Layout Inconsistencies (widths)

- **WelcomeStep** / **ThankYouStep**: `max-w-4xl mx-auto` (inner card only)
- **CapitalInput**: `max-w-md mx-auto` (very narrow)
- **RiskProfiler**: `max-w-2xl mx-auto` (medium)
- **StockSelection** / **PortfolioOptimization** / **StressTest**: `max-w-6xl mx-auto p-4` (wide, with own padding)
- **FinalizePortfolio**: no outer wrapper, just `space-y-4`
- The parent `PortfolioWizard` wraps everything in `max-w-4xl`, but the inner steps then break out to `max-w-6xl` -- creating an awkward overflow situation

### Header Inconsistencies

- **StockSelection** and **PortfolioOptimization** use `StepCardHeader` (the shared component)
- **StressTest** uses raw `CardHeader` + `CardTitle` with a hardcoded blue icon color
- **FinalizePortfolio** uses raw `CardHeader` with gradient cards and inline icon boxes
- **CapitalInput** and **ThankYouStep** use `StepCardHeader` + `StepHeaderIcon` (newest pattern)
- **WelcomeStep** uses raw `CardHeader` + `CardTitle` with centered text
- **RiskProfiler** mixes `StepCardHeader` (screening) and raw `CardHeader` (questionnaire/results)

### Visual Patterns Missing

- No consistent page-level hero/header pattern across steps
- No elevation hierarchy (shadow usage is inconsistent)
- The left accent bar (`w-1 bg-gradient-to-b from-primary/30`) appears only in `StockSelection`
- FinalizePortfolio uses colored gradient cards (`bg-gradient-to-br from-primary/5`) but other steps don't
- Hard-coded colors like `text-blue-600`, `bg-emerald-50`, `bg-purple-50` break in dark mode

### Progress Bar

- The top-level progress bar in `PortfolioWizard` is minimal (1px tall, small text)
- Could benefit from step indicators or a more visual progress display

---

## Design Direction

Adopt a **uniform card-based layout** inspired by the cleanest existing patterns (CapitalInput's use of `StepCardHeader` + `StepHeaderIcon`, and PortfolioOptimization's structured tabs). The design direction is:

- **Consistent max-width**: Widen the parent container from `max-w-4xl` to `max-w-5xl` so data-heavy steps fit without breaking out. Remove per-step max-width overrides.
- **Unified step header**: Every step uses `StepCardHeader` + `StepHeaderIcon` for its primary card
- **Consistent card elevation**: Add subtle `shadow-sm` to primary cards, no shadow to nested cards
- **Accent bar**: Apply the left accent bar pattern consistently to the primary card of each step (or remove it from all)
- **Theme-safe colors**: Replace all hard-coded colors (e.g., `text-blue-600`, `bg-emerald-50`) with CSS variable-based equivalents so dark mode works correctly
- **Enhanced progress indicator**: Upgrade from the 1px bar to a segmented stepper with step labels/icons
- **Consistent spacing**: Standardize padding and gap values across all steps

---

## Implementation Steps

### Phase 1: Foundation (layout + progress bar)

1. **Update `PortfolioWizard.tsx` container**
  - Change outer container from `max-w-4xl` to `max-w-5xl`
  - Upgrade progress bar to a segmented step indicator showing step icons/labels with active/completed states
  - Keep Framer Motion transitions
2. **Remove per-step width overrides**
  - `StockSelection.tsx` line 2269: `max-w-6xl mx-auto p-4` -> remove width/padding wrapper (parent handles it)
  - `PortfolioOptimization.tsx` line 3060: same treatment
  - `StressTest.tsx` line 333: same treatment
  - `CapitalInput.tsx` line 54: `max-w-md mx-auto` -> remove (use parent width, the card itself can be narrower)
  - `RiskProfiler.tsx` lines 2110/2128/2314/2336/2468: `max-w-2xl mx-auto` -> remove
  - `WelcomeStep.tsx` line 57: `max-w-4xl mx-auto` -> remove

### Phase 2: Unified headers

1. **Standardize all step headers to use `StepCardHeader` + `StepHeaderIcon`**
  - **WelcomeStep**: Replace raw `CardHeader`/`CardTitle` with `StepCardHeader` using a `TrendingUp` icon
  - **StressTest**: Replace raw `CardHeader` with `StepCardHeader` + `StepHeaderIcon` (use `Shield` icon)
  - **RiskProfiler questionnaire view**: Replace raw `CardHeader` with `StepCardHeader`
  - **FinalizePortfolio**: Already has a tabs structure; add a `StepCardHeader` hero above the tabs

### Phase 3: Card styling consistency

1. **Standardize card elevation and accent patterns**
  - Add `shadow-sm` to all primary step cards uniformly (the outermost Card in each step)
  - Choose one pattern for visual emphasis: either the left accent bar OR a subtle top gradient, and apply it to all primary cards consistently. Recommendation: remove the accent bar and use a very subtle `border-t-2 border-primary/30` top border for visual anchoring.
  - Remove per-step gradient backgrounds from FinalizePortfolio's hero cards (they look different from every other step)
2. **Fix dark-mode-unsafe colors**
  - Replace `text-blue-600` / `bg-blue-50` / `bg-emerald-50` / `bg-purple-50` etc. with theme-safe alternatives using CSS variables (e.g., `bg-primary/10 text-primary`, `bg-muted`, or new CSS variable-based utility classes)
  - Key files: `PortfolioBuilder.tsx` (metrics grid, lines 720-748), `StressTest.tsx` (header icon), `FinalizePortfolio.tsx` (gradient cards)

### Phase 4: Welcome page enhancement

1. **Redesign WelcomeStep for a stronger first impression**
  - Use `StepCardHeader` with a larger icon
  - Improve the feature grid: add subtle hover animation, slightly larger icon containers
  - Make the "What You'll Learn" section more visually distinct with a subtle left border or icon
  - Make the CTA button larger and more prominent

### Phase 5: Polish and spacing

1. **Standardize spacing and typography across all steps**
  - Ensure all steps use `space-y-4` for section gaps
  - Ensure all card headers use `pb-2` consistently (via `StepCardHeader`)
  - Ensure navigation buttons (Next/Previous) follow a consistent pattern: Previous on left (outline), Next on right (primary)
  - Ensure tabs use the same grid layout pattern (already consistent in most places)

---

## Files to Modify


| File                                                                                    | Changes                                                                        |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `[PortfolioWizard.tsx](frontend/src/components/PortfolioWizard.tsx)`                    | Widen container, upgrade progress indicator                                    |
| `[WelcomeStep.tsx](frontend/src/components/wizard/WelcomeStep.tsx)`                     | Use StepCardHeader, visual refresh                                             |
| `[RiskProfiler.tsx](frontend/src/components/wizard/RiskProfiler.tsx)`                   | Standardize headers, remove width overrides                                    |
| `[CapitalInput.tsx](frontend/src/components/wizard/CapitalInput.tsx)`                   | Remove width override                                                          |
| `[StockSelection.tsx](frontend/src/components/wizard/StockSelection.tsx)`               | Remove width/padding override, standardize header                              |
| `[PortfolioOptimization.tsx](frontend/src/components/wizard/PortfolioOptimization.tsx)` | Remove width/padding override                                                  |
| `[StressTest.tsx](frontend/src/components/wizard/StressTest.tsx)`                       | Use StepCardHeader+StepHeaderIcon, remove width override, fix hardcoded colors |
| `[FinalizePortfolio.tsx](frontend/src/components/wizard/FinalizePortfolio.tsx)`         | Add unified header, remove gradient cards, fix colors                          |
| `[ThankYouStep.tsx](frontend/src/components/wizard/ThankYouStep.tsx)`                   | Remove width override                                                          |
| `[PortfolioBuilder.tsx](frontend/src/components/wizard/PortfolioBuilder.tsx)`           | Fix dark-mode-unsafe colors in metrics grid                                    |
| `[StepCardHeader.tsx](frontend/src/components/wizard/StepCardHeader.tsx)`               | Minor tweaks if needed for new accent pattern                                  |
| `[index.css](frontend/src/index.css)`                                                   | Optional: add utility classes for theme-safe accent colors                     |


## What Will NOT Change

- All existing features and functionality remain intact
- All API calls and state management untouched
- Light/dark theme switching preserved (improved with color fixes)
- Framer Motion step transitions preserved
- Tab structures within steps preserved
- All existing components (charts, tables, forms) preserved

