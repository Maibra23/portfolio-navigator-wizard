# Linear-Inspired Dark Theme Redesign - Task Breakdown

**Project Goal:** Transform the Portfolio Navigator Wizard to a minimalistic, professional dark theme inspired by Linear.app's design system.

**Timeline:** 2 Days
**Target Aesthetic:** Minimalistic, professional, dark theme with typographic precision

---

## 🎨 UNIFIED DESIGN SYSTEM

### Color Palette (Based on Linear.app Analysis)

```css
/* Dark Theme Base Colors */
--background: 222 10% 5%;           /* Near-black (#08090a equivalent) */
--foreground: 0 0% 95%;             /* Light gray text */

/* Card & Surface Colors */
--card: 222 10% 8%;                 /* Slightly lighter than background */
--card-foreground: 0 0% 95%;

/* Primary Colors (Subtle Gray Tones) */
--primary: 0 0% 85%;                /* Light gray for primary elements */
--primary-foreground: 222 10% 10%;  /* Dark text on light elements */

/* Secondary & Muted (Reduced Emphasis) */
--secondary: 220 10% 15%;           /* Dark gray */
--secondary-foreground: 0 0% 80%;
--muted: 220 10% 12%;
--muted-foreground: 0 0% 60%;       /* Medium gray for supporting text */

/* Accent (Minimal Use) */
--accent: 220 10% 18%;
--accent-foreground: 0 0% 90%;

/* Border & Input */
--border: 220 10% 18%;              /* Subtle borders */
--input: 220 10% 18%;
--ring: 0 0% 70%;                   /* Focus ring */

/* Risk Profile Colors (Muted for Dark Theme) */
--conservative: 214 50% 45%;        /* Muted blue */
--moderate: 142 40% 40%;            /* Muted green */
--aggressive: 0 50% 50%;            /* Muted red */

/* Destructive */
--destructive: 0 50% 45%;
--destructive-foreground: 0 0% 95%;
```

### Typography System (Linear-Inspired)

```css
/* Font Stack */
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", "Helvetica Neue", Arial, sans-serif;

/* Type Scale */
--text-xs: 0.75rem;      /* 12px */
--text-sm: 0.875rem;     /* 14px */
--text-base: 1rem;       /* 16px */
--text-lg: 1.125rem;     /* 18px */
--text-xl: 1.25rem;      /* 20px */
--text-2xl: 1.5rem;      /* 24px */
--text-3xl: 1.875rem;    /* 30px */
--text-4xl: 2.25rem;     /* 36px */

/* Font Weights */
--font-normal: 450;      /* Medium weight as default */
--font-medium: 500;
--font-semibold: 600;

/* Letter Spacing */
--tracking-tight: -0.01em;
--tracking-normal: 0;
--tracking-wide: 0.01em;
```

### Data Visualization Colors (Dark-Optimized)

```javascript
// Muted palette for dark backgrounds with sufficient contrast
const darkVisualizationPalette = [
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

// Chart theme
const darkChartTheme = {
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
};
```

### Spacing & Layout

```css
/* Consistent spacing scale */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */

/* Border Radius */
--radius-sm: 0.375rem;  /* 6px */
--radius: 0.5rem;       /* 8px */
--radius-lg: 0.75rem;   /* 12px */
--radius-xl: 1rem;      /* 16px */
```

---

## 📅 DAY 1: FOUNDATION & CORE COMPONENTS

### Task 1.1: Core Theme Infrastructure (2-3 hours)

**Objective:** Update CSS variables and remove gradient utilities

**Files to Modify:**
1. `frontend/src/index.css` (Lines 10-123)
2. `frontend/tailwind.config.ts` (Lines 77-84)

**Actions:**
- Replace all CSS variables with Linear-inspired dark theme values
- Remove gradient definitions (--gradient-primary, --gradient-accent, --gradient-bg)
- Update shadow definitions for dark theme
- Remove glow variants (--primary-glow, --accent-glow)
- Add typography variables (font weights, letter spacing)

**Expected Outcome:** CSS variable system ready for dark theme

---

### Task 1.2: Main Layout & Navigation (1-2 hours)

**Objective:** Update main wizard layout and navigation header

**Files to Modify:**
1. `frontend/src/components/PortfolioWizard.tsx` (Lines 207-254)

**Actions:**
- Remove gradient background class: `bg-gradient-to-br from-blue-50 to-indigo-100`
- Replace with: `bg-background`
- Update navigation header styling from white to dark
- Update progress indicator styling
- Remove hardcoded color classes (blue-600, gray-900, etc.)
- Replace with CSS variable equivalents

**Expected Outcome:** Main layout adopts dark theme with clean appearance

---

### Task 1.3: Button Component Redesign (1 hour)

**Objective:** Remove gradients, simplify variants

**Files to Modify:**
1. `frontend/src/components/ui/button.tsx` (Lines 7-38)

**Actions:**
- Remove `gradient` variant
- Update `conservative`, `moderate`, `aggressive` variants for dark theme
- Simplify hover states (remove opacity animations)
- Update default variant styling
- Remove shadow utilities

**Expected Outcome:** Minimalist button component matching Linear aesthetic

---

### Task 1.4: Card Component Updates (1 hour)

**Objective:** Update card styling for dark theme

**Files to Modify:**
1. `frontend/src/components/ui/card.tsx`
2. All wizard step components that use cards

**Actions:**
- Update Card component default classes
- Add subtle borders instead of shadows
- Increase border radius for modern look
- Test card appearance in all contexts

**Expected Outcome:** Elegant card components with subtle depth

---

### Task 1.5: Welcome Step Redesign (1 hour)

**Objective:** Update first wizard step to match new aesthetic

**Files to Modify:**
1. `frontend/src/components/wizard/WelcomeStep.tsx` (Lines 44-112)

**Actions:**
- Remove gradient icon background (Line 47)
- Replace with solid dark background
- Update feature card styling (Lines 59-72)
- Remove accent color highlights
- Update typography hierarchy
- Remove gradient button (Line 100)

**Expected Outcome:** Clean, minimal welcome screen

---

## 📅 DAY 2: COMPLEX COMPONENTS & VISUALIZATIONS

### Task 2.1: Data Visualization Theme Update (2-3 hours)

**Objective:** Update all chart components for dark backgrounds

**Files to Modify:**
1. `frontend/src/components/wizard/EfficientFrontierChart.tsx` (Lines 48-73)
2. `frontend/src/components/wizard/Portfolio3PartVisualization.tsx` (Lines 33-86)
3. `frontend/src/components/wizard/FiveYearProjectionChart.tsx`
4. `frontend/src/components/wizard/RiskReturnChart.tsx`
5. `frontend/src/components/wizard/SectorDistributionChart.tsx`

**Actions:**
- Replace `visualizationTheme` object with dark theme values
- Update `vividPalette` to dark-optimized colors
- Adjust grid colors for visibility
- Update axis styling (lines, ticks, labels)
- Test contrast for all data points
- Update tooltip backgrounds and text colors
- Ensure accessibility (WCAG AA contrast ratios)

**Expected Outcome:** Professional, readable charts on dark backgrounds

---

### Task 2.2: Risk Profiler Components (2-3 hours)

**Objective:** Update risk assessment UI components

**Files to Modify:**
1. `frontend/src/components/wizard/RiskProfiler.tsx`
2. `frontend/src/components/wizard/ResultsPage.tsx` (Lines 62-100)
3. `frontend/src/components/wizard/CategoryCard.tsx`
4. `frontend/src/components/wizard/RiskSpectrum.tsx`
5. `frontend/src/components/wizard/TwoDimensionalMap.tsx`
6. `frontend/src/components/wizard/FlagAlerts.tsx`

**Actions:**
- Remove gradient backgrounds from category cards
- Update risk profile color indicators for dark theme
- Adjust flag alert styling
- Update spectrum visualization colors
- Modify 2D map colors and backgrounds
- Test all risk categories (very-conservative to very-aggressive)

**Expected Outcome:** Cohesive risk profiling experience in dark theme

---

### Task 2.3: Capital Input & Stock Selection (1-2 hours)

**Objective:** Update input forms and stock selection interface

**Files to Modify:**
1. `frontend/src/components/wizard/CapitalInput.tsx` (Lines 44-122)
2. `frontend/src/components/wizard/StockSelection.tsx`
3. `frontend/src/components/ui/input.tsx`
4. `frontend/src/components/ui/label.tsx`

**Actions:**
- Remove gradient icon backgrounds
- Update input field styling for dark theme
- Adjust placeholder colors
- Update validation message colors
- Modify stock selection tab interface
- Update search result styling

**Expected Outcome:** Clean, functional forms in dark theme

---

### Task 2.4: Portfolio Optimization Interface (2 hours)

**Objective:** Update optimization step with efficient frontier visualization

**Files to Modify:**
1. `frontend/src/components/wizard/PortfolioOptimization.tsx`
2. `frontend/src/components/wizard/EfficientFrontierChart.tsx`

**Actions:**
- Update tab interface styling
- Modify efficient frontier chart colors
- Adjust scatter plot point colors
- Update legend styling
- Modify zoom controls appearance
- Update reference area colors

**Expected Outcome:** Professional optimization interface

---

### Task 2.5: Stress Test & Finalize Portfolio (1-2 hours)

**Objective:** Update final wizard steps

**Files to Modify:**
1. `frontend/src/components/wizard/StressTest.tsx`
2. `frontend/src/components/wizard/FinalizePortfolio.tsx`
3. `frontend/src/components/wizard/FinalAnalysisComponents.tsx`
4. `frontend/src/components/wizard/PortfolioComparisonTable.tsx`

**Actions:**
- Update stress test scenario cards
- Modify metric display cards
- Update comparison table styling
- Adjust Monte Carlo simulation visualization
- Update tax calculation interface
- Test all four tabs (Builder, Optimize, Analysis, Tax)

**Expected Outcome:** Complete wizard with consistent dark theme

---

### Task 2.6: Typography & Consistency Pass (1-2 hours)

**Objective:** Ensure consistent typography throughout

**Files to Audit:**
- All 27 wizard components
- All 45 UI components (spot check)

**Actions:**
- Verify font weights are consistent
- Check heading hierarchy
- Ensure proper letter spacing
- Verify color contrast (text on backgrounds)
- Check for any remaining hardcoded colors
- Test responsive behavior

**Expected Outcome:** Typographically consistent application

---

### Task 2.7: Final QA & Polish (1-2 hours)

**Objective:** Test all wizard flows and fix edge cases

**Actions:**
- Walk through entire wizard from start to finish
- Test all 7 steps with real data
- Verify all interactive elements (buttons, tabs, inputs)
- Check loading states and error states
- Test dark mode toggle (if implemented)
- Fix any visual inconsistencies
- Take screenshots for documentation

**Expected Outcome:** Production-ready dark theme

---

## 🎯 SUCCESS CRITERIA

### Visual Quality
- [ ] No bright gradients or colorful accents
- [ ] Consistent use of subtle grays and muted tones
- [ ] Professional typographic hierarchy
- [ ] Readable data visualizations
- [ ] Sufficient contrast for accessibility (WCAG AA)

### Technical Quality
- [ ] All CSS variables properly updated
- [ ] No hardcoded colors in components
- [ ] Consistent spacing throughout
- [ ] No visual regressions
- [ ] All 7 wizard steps functional

### User Experience
- [ ] Clear visual hierarchy
- [ ] Smooth transitions between steps
- [ ] Readable text at all sizes
- [ ] Intuitive navigation
- [ ] Professional appearance

---

## 📝 NOTES FOR IMPLEMENTERS

### Key Principles
1. **Subtlety over Drama:** Use tonal variations instead of color explosions
2. **Typography First:** Let text hierarchy create visual interest
3. **Consistency:** Apply patterns uniformly across all components
4. **Accessibility:** Always check contrast ratios for text and data

### Common Patterns to Remove
- `bg-gradient-to-*` classes
- `bg-gradient-primary` / `bg-gradient-accent`
- `shadow-elegant` / `shadow-card` (replace with subtle borders)
- Bright color values (blue-600, green-600, etc.)
- `hover:opacity-90` on gradient buttons

### Common Patterns to Add
- `bg-card` for elevated surfaces
- `border border-border` for subtle separation
- `text-foreground`, `text-muted-foreground` for text hierarchy
- `rounded-lg` or `rounded-xl` for modern feel
- Consistent `gap-*` and `space-y-*` utilities

### Testing Checklist
- [ ] Light text on dark backgrounds is readable
- [ ] Charts display data clearly
- [ ] Forms are usable and inputs are visible
- [ ] Risk profile categories are distinguishable
- [ ] All wizard steps are navigable
- [ ] No console errors or warnings
- [ ] Performance is acceptable (no lag from style changes)

---

## 🔗 REFERENCE LINKS

- Linear.app Landing: https://linear.app/
- Linear.app Features: https://linear.app/features
- Linear.app Method: https://linear.app/method

**Design Characteristics to Emulate:**
- Near-black backgrounds (#08090a)
- Subtle grayscale gradients for depth
- Medium font-weight as default (450-500)
- Precise letter-spacing (-0.01em to 0.01em)
- Modular spacing system
- Hierarchy through type scale and tonal contrast
- Minimal use of color accents
- Professional, premium aesthetic

---

## 🚀 IMPLEMENTATION ORDER

**Recommended Sequence:**
1. Start with Task 1.1 (CSS variables) - this enables everything else
2. Work through Day 1 tasks sequentially
3. Day 2: Tackle visualizations first (most complex)
4. End with typography pass and QA

**Alternative Approach:**
- Use Cursor AI agents to parallelize Day 2 tasks
- Run visualization updates and component updates simultaneously
- Merge and test in final QA pass

---

**Document Version:** 1.0
**Last Updated:** 2026-02-04
**Owner:** Portfolio Navigator Wizard Team
