# Cursor AI Prompts for Linear-Inspired Dark Theme Redesign

**Instructions:** Copy and paste these prompts into Cursor AI with the specified files added as context. Each prompt is designed for a specific task from the implementation plan.

---

## 🎨 DAY 1 PROMPTS

### Prompt 1.1: Core Theme Infrastructure

**Context Files to Add:**
- `frontend/src/index.css`
- `frontend/tailwind.config.ts`
- `THEME_REDESIGN_TASKS.md` (Lines 12-88)

**Prompt:**
```
Update the CSS variables in index.css to implement a Linear.app-inspired dark theme. Use the color palette and typography system defined in THEME_REDESIGN_TASKS.md (Color Palette section).

Requirements:
1. Replace all :root CSS variables with dark theme values (near-black background, light gray text)
2. Remove gradient definitions (--gradient-primary, --gradient-accent, --gradient-bg)
3. Remove glow variants (--primary-glow, --accent-glow)
4. Update shadow definitions to be subtle for dark theme
5. Update the .dark class variables consistently
6. Remove gradient utilities from tailwind.config.ts (lines 77-84)
7. Keep the HSL format for all colors

Expected result: A cohesive dark theme foundation that matches Linear.app's aesthetic (near-black #08090a base, subtle grays, minimal accent colors).
```

---

### Prompt 1.2: Main Layout & Navigation

**Context Files to Add:**
- `frontend/src/components/PortfolioWizard.tsx`
- `frontend/src/index.css` (newly updated)
- `THEME_REDESIGN_TASKS.md` (Lines 139-165)

**Prompt:**
```
Update the PortfolioWizard component to use the new dark theme by removing gradient backgrounds and hardcoded colors.

Changes needed:
1. Line 207: Remove "bg-gradient-to-br from-blue-50 to-indigo-100", replace with "bg-background"
2. Lines 209-225: Update navigation header from white background to dark theme
   - Remove "bg-white border-b border-gray-200"
   - Use "bg-card border-b border-border" instead
3. Lines 212-213: Update TrendingUp icon and heading colors to use CSS variables
4. Lines 232-242: Update step indicator styling to use theme colors instead of hardcoded blue-600, gray-900, etc.
5. Line 249: Update Progress component styling if needed

Maintain all functionality - only update visual styling. The result should be a clean, minimalist dark interface matching Linear.app's aesthetic.
```

---

### Prompt 1.3: Button Component Redesign

**Context Files to Add:**
- `frontend/src/components/ui/button.tsx`
- `THEME_REDESIGN_TASKS.md` (Lines 167-187)

**Prompt:**
```
Simplify the Button component to match Linear.app's minimalist aesthetic by removing gradient variants and excessive styling.

Required changes:
1. Remove the "gradient" variant completely (line 21)
2. Update the default variant to be more subtle
3. Simplify conservative, moderate, aggressive variants:
   - Use muted versions of risk colors
   - Remove hover opacity animations
   - Use simple hover:bg-*/90 patterns
4. Remove any shadow utilities
5. Ensure all variants work with dark theme

The result should be clean, minimal buttons that rely on subtle color changes rather than dramatic gradients or shadows. Test all variants to ensure they're visible on dark backgrounds.
```

---

### Prompt 1.4: Card Component Updates

**Context Files to Add:**
- `frontend/src/components/ui/card.tsx`
- `THEME_REDESIGN_TASKS.md` (Lines 189-204)

**Prompt:**
```
Update the Card component for the dark theme with subtle borders instead of heavy shadows.

Modifications:
1. Update Card component (lines 8-18): Change "shadow-sm" to "border-border/50"
2. Consider increasing border radius for modern look: "rounded-lg" to "rounded-xl"
3. Ensure card background uses CSS variable (bg-card)
4. Update CardHeader to use consistent spacing
5. Ensure CardTitle uses appropriate typography scale

Result should be elegant cards with subtle depth through borders and background contrast, not shadows. Cards should feel premium and minimal like Linear.app.
```

---

### Prompt 1.5: Welcome Step Redesign

**Context Files to Add:**
- `frontend/src/components/wizard/WelcomeStep.tsx`
- `frontend/src/components/ui/button.tsx` (updated)
- `frontend/src/components/ui/card.tsx` (updated)
- `THEME_REDESIGN_TASKS.md` (Lines 206-226)

**Prompt:**
```
Redesign the WelcomeStep component to match the new minimalist dark theme, removing all gradient backgrounds and colorful accents.

Required changes:
1. Line 47: Remove "bg-gradient-primary" from icon container, replace with "bg-secondary"
2. Lines 59-72: Update feature cards:
   - Change "bg-muted/50 hover:bg-muted" to simpler variants
   - Remove colorful icon backgrounds (line 64)
   - Use subtle borders instead of background changes for hover states
3. Line 74: Update "What You'll Learn" section:
   - Change "bg-accent/10" and "text-accent" to muted colors
   - Replace colored dots with subtle indicators
4. Line 100: Remove "bg-gradient-primary hover:opacity-90"
   - Replace with standard button variant

The result should be a clean, professional welcome screen with clear typography hierarchy and minimal use of color. Focus on elegance through spacing and typography, not bright colors.
```

---

### Prompt 2.3A: Capital Input Step

**Context Files to Add:**
- `frontend/src/components/wizard/CapitalInput.tsx`
- `frontend/src/components/ui/input.tsx`
- `THEME_REDESIGN_TASKS.md` (Lines 300-323)

**Prompt:**
```
Update the CapitalInput component for the dark theme, focusing on form usability and visual clarity.

Changes needed:
1. Line 48: Remove "bg-gradient-primary" from icon, replace with "bg-secondary"
2. Lines 63-76: Update input field:
   - Ensure input background is visible on dark theme
   - Adjust placeholder color for readability
   - Update focus ring to match theme
3. Lines 78-85: Update validation messages:
   - Replace "text-green-600" with "text-accent"
   - Replace "text-orange-600" with "text-destructive"
4. Lines 95-103: Update guidelines box to use muted background

Also update input.tsx component if needed to ensure proper dark theme styling. The form should be highly usable with clear visual feedback for user input.
```

---

### Prompt 2.2A: Risk Profiler Components (Part 1)

**Context Files to Add:**
- `frontend/src/components/wizard/CategoryCard.tsx`
- `frontend/src/components/wizard/RiskSpectrum.tsx`
- `THEME_REDESIGN_TASKS.md` (Lines 266-298)

**Prompt:**
```
Update the risk profiler visual components (CategoryCard and RiskSpectrum) for the dark theme while maintaining clear differentiation between risk categories.

For CategoryCard.tsx:
1. Remove any gradient backgrounds
2. Update risk category color indicators to muted versions suitable for dark backgrounds
3. Use subtle borders and background differences to create hierarchy
4. Ensure category names are prominent and readable

For RiskSpectrum.tsx:
1. Update the spectrum visualization colors for dark theme
2. Ensure the user's position on the spectrum is clearly visible
3. Update confidence band visualization
4. Use muted colors that still provide clear risk level indication

Risk categories (very-conservative, conservative, moderate, aggressive, very-aggressive) should remain distinguishable but use muted tones that fit the minimalist aesthetic. Reference the risk profile colors from THEME_REDESIGN_TASKS.md.
```

---

## 🎨 DAY 2 PROMPTS

### Prompt 2.1: Data Visualization Theme (Part 1 - Core Charts)

**Context Files to Add:**
- `frontend/src/components/wizard/EfficientFrontierChart.tsx`
- `frontend/src/components/wizard/Portfolio3PartVisualization.tsx`
- `THEME_REDESIGN_TASKS.md` (Lines 89-110, 228-265)

**Prompt:**
```
Update the visualization theme for dark backgrounds in EfficientFrontierChart and Portfolio3PartVisualization components.

For both files, replace the visualizationTheme object (around lines 48-73 in EfficientFrontierChart, lines 33-86 in Portfolio3PartVisualization) with dark-optimized values:

```javascript
const darkVisualizationTheme = {
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
  legend: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
  },
};
```

Also update the vividPalette (in Portfolio3PartVisualization) with dark-optimized colors:
```javascript
const darkOptimizedPalette = [
  '#4ade80', '#f87171', '#60a5fa', '#fbbf24', '#a78bfa',
  '#fb923c', '#22d3ee', '#f472b6', '#84cc16', '#06b6d4',
];
```

Test the charts to ensure:
- Data points are clearly visible
- Grid lines are subtle but present
- Text labels are readable
- Tooltips have dark backgrounds
- Color contrast meets accessibility standards
```

---

### Prompt 2.1B: Data Visualization Theme (Part 2 - Additional Charts)

**Context Files to Add:**
- `frontend/src/components/wizard/FiveYearProjectionChart.tsx`
- `frontend/src/components/wizard/RiskReturnChart.tsx`
- `frontend/src/components/wizard/SectorDistributionChart.tsx`
- `frontend/src/components/wizard/TwoAssetChart.tsx`
- `THEME_REDESIGN_TASKS.md` (Lines 228-265)

**Prompt:**
```
Apply the same dark visualization theme to the remaining chart components (FiveYearProjectionChart, RiskReturnChart, SectorDistributionChart, TwoAssetChart).

For each component:
1. Find the chart configuration or theme object
2. Update colors, grid lines, and axes for dark backgrounds
3. Use the darkVisualizationTheme values from THEME_REDESIGN_TASKS.md
4. Update any hardcoded color values to dark-optimized alternatives
5. Ensure chart backgrounds are dark
6. Update tooltip styling

Use this color palette for data series:
['#4ade80', '#f87171', '#60a5fa', '#fbbf24', '#a78bfa', '#fb923c', '#22d3ee', '#f472b6', '#84cc16', '#06b6d4']

Test each chart to ensure data is clearly visible and meets accessibility contrast requirements. The charts should look professional on dark backgrounds.
```

---

### Prompt 2.2B: Risk Profiler Components (Part 2 - Results & Visualizations)

**Context Files to Add:**
- `frontend/src/components/wizard/ResultsPage.tsx`
- `frontend/src/components/wizard/TwoDimensionalMap.tsx`
- `frontend/src/components/wizard/FlagAlerts.tsx`
- `frontend/src/components/wizard/RiskProfiler.tsx`
- `THEME_REDESIGN_TASKS.md` (Lines 266-298)

**Prompt:**
```
Complete the risk profiler dark theme by updating the results display, 2D risk map, and flag alerts.

For ResultsPage.tsx (lines 62-100):
1. Update quadrantStyle colors (lines 56-59) to be muted for dark theme
2. Ensure flag alerts are prominent but not jarring
3. Update card styling to match dark theme
4. Ensure risk breakdown visualization uses appropriate colors

For TwoDimensionalMap.tsx:
1. Update quadrant background colors for dark theme
2. Ensure the user's position is clearly marked
3. Update axis labels and grid for visibility
4. Use muted colors that still differentiate quadrants

For FlagAlerts.tsx:
1. Update alert styling for dark backgrounds
2. Ensure warnings are visible but not overwhelming
3. Use appropriate icon colors
4. Maintain urgency while fitting the minimalist aesthetic

All risk-related visualizations should remain functional and clear while adopting the new dark, minimal aesthetic.
```

---

### Prompt 2.3B: Stock Selection Step

**Context Files to Add:**
- `frontend/src/components/wizard/StockSelection.tsx`
- `frontend/src/components/wizard/TwoAssetChart.tsx` (if not already updated)
- `THEME_REDESIGN_TASKS.md` (Lines 300-323)

**Prompt:**
```
Update the StockSelection component and its associated visualizations for the dark theme.

Required changes:
1. Update tab interface styling to use theme colors
2. Update stock search input and results styling
3. Ensure selected stocks are highlighted appropriately
4. Update curated picks cards to use muted backgrounds
5. Update TwoAssetChart (if not done in 2.1B) for dark theme
6. Update Portfolio3PartVisualization integration
7. Ensure badges and stock symbols are readable

The stock selection interface should feel professional and elegant. Search results should be clear, and interactive elements should provide appropriate visual feedback. Maintain all functionality while updating visual appearance.
```

---

### Prompt 2.4: Portfolio Optimization Interface

**Context Files to Add:**
- `frontend/src/components/wizard/PortfolioOptimization.tsx`
- `frontend/src/components/wizard/EfficientFrontierChart.tsx` (updated)
- `THEME_REDESIGN_TASKS.md` (Lines 325-350)

**Prompt:**
```
Update the PortfolioOptimization component to match the dark minimalist theme.

Changes needed:
1. Update tab interface for strategy selection
2. Update strategy cards (Risk Parity, Mean-Variance, MVO) styling
3. Ensure EfficientFrontierChart integration works with dark theme
4. Update legend styling and interactivity
5. Update zoom and control buttons styling
6. Ensure source selection (current/weights/market) is clear
7. Update any remaining hardcoded colors

The optimization interface should feel professional and data-focused. The efficient frontier should be the visual centerpiece, with controls and information being supportive but not distracting. Maintain the sophisticated financial analysis feel while adopting the minimal dark aesthetic.
```

---

### Prompt 2.5: Final Steps (Stress Test & Finalize Portfolio)

**Context Files to Add:**
- `frontend/src/components/wizard/StressTest.tsx`
- `frontend/src/components/wizard/FinalizePortfolio.tsx`
- `frontend/src/components/wizard/FinalAnalysisComponents.tsx`
- `frontend/src/components/wizard/PortfolioComparisonTable.tsx`
- `THEME_REDESIGN_TASKS.md` (Lines 352-381)

**Prompt:**
```
Update the final two wizard steps (StressTest and FinalizePortfolio) to complete the dark theme implementation.

For StressTest.tsx:
1. Update scenario selection cards styling
2. Update metric display cards (drawdown, volatility, recovery time)
3. Ensure progress indicators match theme
4. Update historical crisis cards to be elegant on dark background

For FinalizePortfolio.tsx and supporting components:
1. Update all four tab interfaces (Builder, Optimize, Analysis, Tax)
2. Update PortfolioComparisonTable styling for dark backgrounds
3. Update FinalAnalysisComponents (performance, quality, Monte Carlo cards)
4. Ensure charts and visualizations match dark theme
5. Update export/download button styling
6. Ensure all metrics and numbers are clearly readable

The final steps should feel polished and professional, representing the culmination of the wizard experience. All data should be clearly presented, and the interface should feel cohesive with previous steps.
```

---

### Prompt 2.6: Typography & Consistency Pass

**Context Files to Add:**
- `frontend/src/index.css`
- All wizard component files
- `THEME_REDESIGN_TASKS.md` (Lines 383-405)

**Prompt:**
```
Perform a comprehensive typography and consistency audit across all wizard components.

Typography checks:
1. Verify heading hierarchy (h1, h2, h3, h4) uses consistent sizes
2. Ensure font weights are consistent (prefer medium/500 as default)
3. Check letter-spacing for headings (should be -0.01em to 0)
4. Verify body text uses appropriate sizes (text-sm or text-base)
5. Ensure muted text uses text-muted-foreground

Visual consistency checks:
1. Search for any remaining "gradient" classes and remove them
2. Verify all hardcoded color classes (blue-600, green-500, etc.) are replaced with CSS variables
3. Check spacing consistency (gap-*, space-y-*, padding)
4. Verify border styles are consistent (border-border)
5. Check hover states are subtle and consistent
6. Verify loading and error states match theme

Contrast checks:
1. Use browser DevTools or contrast checker to verify WCAG AA compliance
2. Ensure all text has sufficient contrast against backgrounds
3. Check chart colors have adequate contrast
4. Verify focus indicators are visible

Document any remaining issues that need manual review.
```

---

### Prompt 2.7: Final QA & Documentation

**Context Files to Add:**
- `THEME_REDESIGN_TASKS.md`
- `IMPLEMENTATION_PLAN.md`
- All updated components

**Prompt:**
```
Perform final quality assurance and create documentation for the theme redesign.

QA Tasks:
1. Walk through the entire wizard from step 1 to step 7
2. Test with realistic data (various risk profiles, stock selections, portfolio sizes)
3. Verify all interactive elements function correctly:
   - Buttons and links
   - Form inputs
   - Tabs and navigation
   - Chart interactions (zoom, hover, selection)
   - Dropdowns and modals
4. Check loading states and error messages
5. Test responsive behavior (desktop, tablet, mobile)
6. Verify no console errors or warnings
7. Check browser performance (FPS, render times)

Documentation Tasks:
1. Create a list of completed changes
2. Document any known limitations or edge cases
3. Note any deviations from the original plan
4. List any remaining improvements for future work
5. Create screenshots showing before/after for key screens

Success Criteria Verification:
Use the checklist from THEME_REDESIGN_TASKS.md (Success Criteria section) and IMPLEMENTATION_PLAN.md (Success Metrics section) to verify completion.

Provide a final summary report with:
- Completed items
- Known issues
- Recommendations for next steps
```

---

## 🎯 SPECIALIZED PROMPTS

### Prompt: Emergency Gradient Removal

**Use this if gradients persist after other updates**

**Context Files to Add:**
- All wizard components
- `frontend/src/components/ui/*`

**Prompt:**
```
Search through all component files and remove any remaining gradient references.

Find and replace:
1. "bg-gradient-to-*" classes → "bg-secondary" or appropriate solid color
2. "bg-gradient-primary" → "bg-secondary"
3. "bg-gradient-accent" → "bg-accent/20"
4. Any inline style with gradients
5. Any CSS classes that reference gradients

After removal, verify:
- No visual regressions
- Replaced elements are still visible
- Hover states still work
- Components maintain hierarchy

List all files modified and what was changed.
```

---

### Prompt: Contrast Ratio Fixer

**Use this if accessibility issues are found**

**Context Files to Add:**
- Components with contrast issues
- `frontend/src/index.css`

**Prompt:**
```
Fix contrast ratio issues to meet WCAG AA standards (4.5:1 for normal text, 3:1 for large text).

For each flagged element:
1. Identify the text color and background color
2. Calculate current contrast ratio
3. Adjust foreground or background color to meet standards
4. Prefer adjusting lightness rather than changing hue
5. Test that changes don't break visual hierarchy

Priority areas:
- Body text on card backgrounds
- Muted text on various backgrounds
- Chart labels and axis text
- Button text on button backgrounds
- Form input text and placeholders

Document all changes made and final contrast ratios.
```

---

### Prompt: Quick Visual Debug

**Use this for general visual issues**

**Context Files to Add:**
- Specific component with issues
- `frontend/src/index.css`

**Prompt:**
```
Debug visual issues in [COMPONENT_NAME]:

Current problems:
[DESCRIBE ISSUES - e.g., "text not visible", "layout broken", "colors too bright"]

Expected result:
[DESCRIBE DESIRED OUTCOME]

Check for:
1. Missing CSS variable references
2. Hardcoded colors that need updating
3. Incorrect Tailwind classes
4. Z-index or positioning issues
5. Responsive breakpoint problems

Provide specific fixes with line numbers and code changes.
```

---

## 📝 TIPS FOR USING THESE PROMPTS

### General Guidelines:
1. **Add Context Files First:** Always add the specified files to Cursor's context before sending the prompt
2. **One Task at a Time:** Don't combine prompts - complete each task before moving to the next
3. **Test Immediately:** After each change, refresh browser and test the affected components
4. **Commit Often:** Commit after completing each major task
5. **Reference Documentation:** Keep THEME_REDESIGN_TASKS.md and IMPLEMENTATION_PLAN.md open for reference

### If Something Goes Wrong:
1. **Revert:** Use git to revert problematic changes
2. **Simplify:** Break the prompt into smaller, more specific tasks
3. **Add More Context:** Include additional files that might be relevant
4. **Manual Review:** Sometimes manual inspection and fixes are faster than AI iteration

### Prompt Customization:
- Add specific line numbers when you know exact locations
- Include error messages if you're debugging
- Add screenshots or descriptions of current state vs. desired state
- Reference specific colors or values from Linear.app if needed

---

## 🔗 REFERENCE LINKS

Include these in Cursor context when relevant:
- Linear.app: https://linear.app/
- Linear Features: https://linear.app/features
- Linear Method: https://linear.app/method
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/

---

**Document Version:** 1.0
**Last Updated:** 2026-02-04
**Total Prompts:** 15 main prompts + 3 specialized prompts
