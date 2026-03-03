---
name: Wizard UI Refresh
overview: A systematic UI refresh across all 8 wizard steps to create a uniform, polished, and cross-platform optimized design while preserving all existing features, functions, and light/dark theming.
todos:
  - id: foundation-layout
    content: ""
    status: completed
  - id: remove-width-overrides
    content: Remove per-step max-width and padding overrides from all 8 step components
    status: completed
  - id: unified-headers
    content: Standardize all step headers to use StepCardHeader + StepHeaderIcon
    status: completed
  - id: card-styling
    content: Apply consistent shadow-sm, top accent border, remove per-step gradient backgrounds
    status: completed
  - id: dark-mode-colors
    content: Replace all hard-coded colors (blue-600, emerald-50, purple-50, etc.) with theme-safe CSS variable alternatives
    status: completed
  - id: responsive-typography
    content: Add responsive text sizing (text-sm md:text-base, text-lg md:text-xl) to headers, body text, and labels
    status: completed
  - id: touch-targets
    content: Enforce minimum 44px touch targets on all interactive elements (buttons, inputs, radio options)
    status: completed
  - id: mobile-layouts
    content: "Add sm: breakpoint grid adjustments and stack layouts for screens under 640px"
    status: completed
  - id: accessibility-pass
    content: Add missing ARIA labels, focus-visible states, and keyboard navigation to interactive components
    status: completed
  - id: welcome-refresh
    content: Redesign WelcomeStep for stronger first impression while keeping feature grid and CTA
    status: completed
  - id: spacing-polish
    content: Standardize spacing, typography, and navigation button patterns across all steps
    status: completed
  - id: verify-all-steps
    content: Test all 8 steps in both light and dark themes across mobile, tablet, and desktop viewports
    status: completed
isProject: false
---

# Portfolio Wizard UI Refresh Plan (Cross-Platform Optimized)

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

### Cross-Platform Gaps (NEW)


| Area                      | Current State                    | Gap                                                                                  |
| ------------------------- | -------------------------------- | ------------------------------------------------------------------------------------ |
| **Responsive Typography** | Fixed `text-sm`, `text-lg`, etc. | Only 1 responsive example (`text-sm md:text-base`) in entire codebase                |
| **Touch Targets**         | Inconsistent sizing              | Only `QuestionDisplay` enforces `min-h-[48px]`; most buttons rely on default padding |
| **Mobile Breakpoints**    | Heavy `md:` usage                | Minimal `sm:` breakpoint usage; layouts may break on phones                          |
| **Accessibility**         | 48 ARIA attributes in 10 files   | Missing focus states, keyboard nav, and screen reader support in most components     |
| **Viewport Logic**        | `useIsMobile()` hook exists      | Only used in 1 file (TaxFreeVisualization)                                           |


---

## Design Direction

Adopt a **uniform card-based layout** inspired by the cleanest existing patterns (CapitalInput's use of `StepCardHeader` + `StepHeaderIcon`, and PortfolioOptimization's structured tabs). The design direction is:

- **Consistent max-width**: Widen the parent container from `max-w-4xl` to `max-w-5xl` so data-heavy steps fit without breaking out. Remove per-step max-width overrides.
- **Unified step header**: Every step uses `StepCardHeader` + `StepHeaderIcon` for its primary card
- **Consistent card elevation**: Add subtle `shadow-sm` to primary cards, no shadow to nested cards
- **Accent bar**: Apply the left accent bar pattern consistently to the primary card of each step (or remove it from all)
- **Theme-safe colors**: Replace all hard-coded colors (e.g., `text-blue-600`, `bg-emerald-50`) with CSS variable-based equivalents so dark mode works correctly
- **Enhanced progress indicator**: Upgrade from the 1px bar to a segmented stepper with step labels/icons
- **Consistent spacing**: Standardize padding and gap values across all steps.

### Cross-Platform Design Additions (NEW)

- **Responsive typography scale**: Headers scale down on mobile (`text-lg md:text-xl lg:text-2xl`)
- **Touch-friendly targets**: All buttons, inputs, and interactive elements enforce `min-h-[44px]` or `min-h-[48px]`
- **Mobile-first grid patterns**: Add `sm:` breakpoint support to all grids (e.g., `grid-cols-1 sm:grid-cols-2 md:grid-cols-3`)
- **Accessibility baseline**: Focus-visible states, ARIA labels on icons/buttons, keyboard navigation

---

## Risks and Mitigations

The following friction points were identified before implementation. Each is acknowledged in the plan with a mitigation or scoped decision.


| Plan Item                                    | Risk          | What Could Happen                                                                                                             | Mitigation / Decision                                                                                                                                                                                                                                                              |
| -------------------------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Width change (max-w-4xl to max-w-5xl)        | Low           | Charts/tables in PortfolioOptimization and StressTest are already at max-w-6xl; they will fit properly instead of overflowing | No change. Proceed as planned.                                                                                                                                                                                                                                                     |
| Progress bar to segmented stepper            | Medium        | New JSX structure, icon imports, active/completed state styling; more code to maintain                                        | **Scoped down**: Implement an **enhanced progress bar** (taller bar, step count, optional small step dots) instead of a full icon-and-label stepper. Avoid adding 8 step icons and connector lines to limit maintenance. If a full stepper is desired later, do it as a follow-up. |
| Remove gradient cards from FinalizePortfolio | Low           | Purely cosmetic                                                                                                               | Proceed. Replace with flat card + subtle border so it matches other steps.                                                                                                                                                                                                         |
| Dark mode color replacements                 | Low (tedious) | Straightforward find-replace but 30+ instances across files                                                                   | **Batch by file** in Phase 3: do PortfolioBuilder, StressTest, FinalizePortfolio, then grep for remaining `text-*-[0-9]`, `bg-*-[0-9]` in wizard components. Use a single theme-safe palette (e.g. primary/muted/success/destructive) to avoid drift.                              |
| WelcomeStep "stronger first impression"      | Medium        | Subjective scope; could lead to iteration on "what looks better"                                                              | **Scope to concrete, bounded changes only**: (1) Use StepCardHeader + StepHeaderIcon. (2) One subtle hover on feature tiles (e.g. scale or border). (3) Single CTA size bump. (4) No open-ended "redesign." If more is needed, treat as a separate, later task.                    |
| **Responsive typography (NEW)**              | Low           | More CSS classes to maintain                                                                                                  | Apply systematically: headers get `text-lg md:text-xl`, body gets `text-sm md:text-base`. Create a reference in this plan for consistency.                                                                                                                                         |
| **Touch targets (NEW)**                      | Low           | May increase vertical space on desktop                                                                                        | Use `min-h-[44px]` (iOS guideline) rather than fixed height. Desktop users won't notice; mobile users gain usability.                                                                                                                                                              |
| **Accessibility (NEW)**                      | Medium        | Adds attributes to many elements                                                                                              | Focus on interactive elements only: buttons, inputs, tabs, radio groups. Skip decorative icons. Use `focus-visible:` ring pattern from existing components.                                                                                                                        |


---

## Implementation Steps

### Phase 1: Foundation (layout + progress bar)

1. **Update `PortfolioWizard.tsx` container**
  - Change outer container from `max-w-4xl` to `max-w-5xl`
  - Upgrade progress bar to a segmented step indicator showing step icons/labels with active/completed states
  - Add responsive padding: `px-4 md:px-6`
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

### Phase 4: Cross-Platform Optimization (NEW)

1. **Responsive typography**
  - Apply responsive text classes systematically:
    - Step titles: `text-xl md:text-2xl`
    - Section headers: `text-base md:text-lg`
    - Body text: `text-sm md:text-base`
    - Labels/captions: `text-xs md:text-sm`
  - Key files: All step components, `StepCardHeader.tsx`
2. **Touch target enforcement**
  - Add `min-h-[44px]` to:
    - All `<Button>` instances in wizard steps
    - All radio/checkbox options (QuestionDisplay already has this)
    - Tab triggers in FinalizePortfolio
  - Ensure adequate padding for touch: `py-3` minimum on interactive elements
3. **Mobile layout adjustments**
  - Add `sm:` breakpoints to all grid layouts:
    - Current: `grid-cols-1 md:grid-cols-2` → New: `grid-cols-1 sm:grid-cols-2 md:grid-cols-3`
  - Stack navigation buttons vertically on mobile: `flex flex-col sm:flex-row`
  - Key files: `WelcomeStep.tsx`, `RiskProfiler.tsx`, `FinalizePortfolio.tsx`
4. **Accessibility improvements**
  - Add `aria-label` to icon-only buttons
  - Add `focus-visible:ring-2 focus-visible:ring-primary` to custom interactive elements
  - Ensure all form inputs have associated labels
  - Add `role="tablist"` and `role="tab"` where custom tabs are used
  - Key files: `QuestionDisplay.tsx`, `StepHeaderIcon.tsx`, `FinalizePortfolio.tsx`

### Phase 5: Welcome page enhancement

1. **Redesign WelcomeStep for a stronger first impression**
  - Use `StepCardHeader` with a larger icon
  - Improve the feature grid: add subtle hover animation, slightly larger icon containers
  - Make the "What You'll Learn" section more visually distinct with a subtle left border or icon
  - Make the CTA button larger and more prominent
  - Add responsive typography to hero text

### Phase 6: Polish and spacing

1. **Standardize spacing and typography across all steps**
  - Ensure all steps use `space-y-4` for section gaps
  - Ensure all card headers use `pb-2` consistently (via `StepCardHeader`)
  - Ensure navigation buttons (Next/Previous) follow a consistent pattern: Previous on left (outline), Next on right (primary)
  - Ensure tabs use the same grid layout pattern (already consistent in most places)

### Phase 7: Cross-Platform Testing (NEW)

1. **Test all 8 steps across viewports**
  - Mobile (375px, 414px) - iPhone SE, iPhone 14
  - Tablet (768px, 1024px) - iPad Mini, iPad Pro
  - Desktop (1280px, 1920px) - Laptop, Monitor
2. **Test both themes (light/dark) at each viewport**
3. **Test keyboard navigation** through entire wizard flow
4. **Test with screen reader** (VoiceOver/NVDA) for accessibility

---

## Responsive Typography Reference

Use these patterns consistently across all wizard components:


| Element        | Mobile (default)                | Tablet (md:) | Desktop (lg:) |
| -------------- | ------------------------------- | ------------ | ------------- |
| Page title     | `text-xl`                       | `text-2xl`   | `text-3xl`    |
| Step title     | `text-lg`                       | `text-xl`    | `text-2xl`    |
| Section header | `text-base font-semibold`       | `text-lg`    | `text-lg`     |
| Body text      | `text-sm`                       | `text-base`  | `text-base`   |
| Labels         | `text-xs`                       | `text-sm`    | `text-sm`     |
| Helper text    | `text-xs text-muted-foreground` | same         | same          |


---

## Files to Modify


| File                                                                                    | Changes                                                                        |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `[PortfolioWizard.tsx](frontend/src/components/PortfolioWizard.tsx)`                    | Widen container, upgrade progress indicator, responsive padding                |
| `[WelcomeStep.tsx](frontend/src/components/wizard/WelcomeStep.tsx)`                     | Use StepCardHeader, visual refresh, responsive typography, mobile grid         |
| `[RiskProfiler.tsx](frontend/src/components/wizard/RiskProfiler.tsx)`                   | Standardize headers, remove width overrides, responsive text                   |
| `[CapitalInput.tsx](frontend/src/components/wizard/CapitalInput.tsx)`                   | Remove width override, touch target sizing                                     |
| `[StockSelection.tsx](frontend/src/components/wizard/StockSelection.tsx)`               | Remove width/padding override, standardize header                              |
| `[PortfolioOptimization.tsx](frontend/src/components/wizard/PortfolioOptimization.tsx)` | Remove width/padding override, touch targets on tabs                           |
| `[StressTest.tsx](frontend/src/components/wizard/StressTest.tsx)`                       | Use StepCardHeader+StepHeaderIcon, remove width override, fix hardcoded colors |
| `[FinalizePortfolio.tsx](frontend/src/components/wizard/FinalizePortfolio.tsx)`         | Add unified header, remove gradient cards, fix colors, tab accessibility       |
| `[ThankYouStep.tsx](frontend/src/components/wizard/ThankYouStep.tsx)`                   | Remove width override, responsive typography                                   |
| `[PortfolioBuilder.tsx](frontend/src/components/wizard/PortfolioBuilder.tsx)`           | Fix dark-mode-unsafe colors in metrics grid                                    |
| `[StepCardHeader.tsx](frontend/src/components/wizard/StepCardHeader.tsx)`               | Add responsive typography, ensure focus-visible states                         |
| `[QuestionDisplay.tsx](frontend/src/components/wizard/QuestionDisplay.tsx)`             | Verify touch targets (already has min-h-[48px]), add missing ARIA              |
| `[index.css](frontend/src/index.css)`                                                   | Optional: add utility classes for theme-safe accent colors                     |


## What Will NOT Change

- All existing features and functionality remain intact
- All API calls and state management untouched
- Light/dark theme switching preserved (improved with color fixes)
- Framer Motion step transitions preserved
- Tab structures within steps preserved
- All existing components (charts, tables, forms) preserved
- Recharts ResponsiveContainer usage (already good for responsive charts)

## Cross-Platform Checklist (NEW)

Before marking complete, verify:

- All steps render correctly at 375px width (iPhone SE)
- All steps render correctly at 768px width (tablet)
- All interactive elements have min 44px touch targets
- All steps pass WCAG 2.1 AA color contrast in both themes
- Keyboard navigation works through entire wizard flow
- No horizontal scroll at any viewport width
- Charts resize properly (Recharts ResponsiveContainer)
- Navigation buttons accessible on mobile (not clipped)

