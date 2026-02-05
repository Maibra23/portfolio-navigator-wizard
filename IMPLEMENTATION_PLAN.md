# 2-Day Linear-Inspired Dark Theme Implementation Plan

**Project:** Portfolio Navigator Wizard Theme Redesign
**Duration:** 2 Days
**Objective:** Transform to minimalistic, professional dark theme inspired by Linear.app

---

## 📊 OVERVIEW

### Scope Summary
- **CSS Variables:** 1 file to update
- **Layout Components:** 1 main file
- **UI Components:** 45 shadcn/ui components (auto-inherit from CSS vars)
- **Wizard Components:** 27 components across 7 steps
- **Visualization Components:** 5-7 chart components
- **Typography:** System-wide updates

### Complexity Distribution
- **Automatic (60%):** CSS variable inheritance
- **Manual (30%):** Removing gradients, updating hardcoded classes
- **Complex (10%):** Data visualizations, risk profiler

---

## 🗓️ DAY 1: FOUNDATION & CORE COMPONENTS

### Morning Session (9:00 AM - 12:00 PM)

#### **9:00 - 10:00 AM: Environment Setup & CSS Variables**
**Task 1.1: Core Theme Infrastructure**

**What to do:**
1. Open `frontend/src/index.css`
2. Backup current CSS variables
3. Replace all `:root` variables with Linear-inspired dark theme
4. Remove gradient definitions
5. Update shadow definitions
6. Test in browser - verify color changes propagate

**Files:**
- `frontend/src/index.css` (Primary)
- `frontend/tailwind.config.ts` (Secondary)

**Deliverable:** Dark theme CSS foundation

**Verification:**
- Open app in browser
- Check if background turns dark
- Verify text is readable
- Check if most components inherit new colors

---

#### **10:00 - 11:00 AM: Main Layout & Navigation**
**Task 1.2: Main Wizard Layout**

**What to do:**
1. Open `frontend/src/components/PortfolioWizard.tsx`
2. Remove gradient background from main container (Line 207)
3. Update navigation header styling (Lines 209-225)
4. Update progress indicator (Lines 229-249)
5. Replace hardcoded color classes with CSS variable classes
6. Test navigation and progress bar

**Files:**
- `frontend/src/components/PortfolioWizard.tsx`

**Deliverable:** Dark-themed main layout

**Verification:**
- Main container has dark background
- Navigation is visible and functional
- Progress bar matches theme
- Step indicators are readable

---

#### **11:00 AM - 12:00 PM: Button & Card Components**
**Task 1.3 & 1.4: Core UI Components**

**What to do:**
1. Open `frontend/src/components/ui/button.tsx`
   - Remove gradient variant (Line 21)
   - Simplify hover states
   - Update risk profile variants
   - Test all button variants

2. Open `frontend/src/components/ui/card.tsx`
   - Update default card styling
   - Add subtle border styling
   - Increase border radius

**Files:**
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/card.tsx`

**Deliverable:** Minimalist button and card components

**Verification:**
- Buttons have no gradients
- Cards have subtle borders
- Components feel cohesive
- All variants work properly

---

### Afternoon Session (1:00 PM - 5:00 PM)

#### **1:00 - 2:00 PM: Welcome Step**
**Task 1.5: First Wizard Step**

**What to do:**
1. Open `frontend/src/components/wizard/WelcomeStep.tsx`
2. Remove gradient icon background (Line 47)
3. Update feature cards (Lines 59-72)
4. Remove accent highlights (Line 74)
5. Update button styling (Line 100)
6. Test welcome screen appearance

**Files:**
- `frontend/src/components/wizard/WelcomeStep.tsx`

**Deliverable:** Clean welcome screen

**Verification:**
- No colorful gradients
- Feature cards are elegant
- Text hierarchy is clear
- Call-to-action button is prominent but subtle

---

#### **2:00 - 3:00 PM: Capital Input Step**
**Task 2.3 (Partial): Forms & Inputs**

**What to do:**
1. Open `frontend/src/components/wizard/CapitalInput.tsx`
2. Remove gradient icon (Line 48)
3. Update form input styling
4. Update validation messages
5. Test input interaction

**Files:**
- `frontend/src/components/wizard/CapitalInput.tsx`
- `frontend/src/components/ui/input.tsx`
- `frontend/src/components/ui/label.tsx`

**Deliverable:** Dark-themed form inputs

**Verification:**
- Input fields are visible and usable
- Placeholder text is readable
- Validation messages have appropriate colors
- Form feels professional

---

#### **3:00 - 4:30 PM: Risk Profiler (Part 1)**
**Task 2.2 (Partial): Risk Assessment UI**

**What to do:**
1. Open `frontend/src/components/wizard/CategoryCard.tsx`
   - Update card styling
   - Adjust risk category colors
   - Remove gradients

2. Open `frontend/src/components/wizard/RiskSpectrum.tsx`
   - Update spectrum visualization
   - Adjust color indicators

**Files:**
- `frontend/src/components/wizard/CategoryCard.tsx`
- `frontend/src/components/wizard/RiskSpectrum.tsx`

**Deliverable:** Updated risk profile cards and spectrum

**Verification:**
- Risk categories are distinguishable
- Colors are muted but clear
- Visual hierarchy is maintained

---

#### **4:30 - 5:00 PM: Day 1 Review & Testing**

**What to do:**
1. Run through steps 1-3 of wizard
2. Document any visual issues
3. Create list of quick fixes for tomorrow
4. Commit changes with clear message

**Deliverable:** Progress report and git commit

**Expected Status:**
- ✅ CSS variables updated
- ✅ Main layout dark-themed
- ✅ Buttons & cards updated
- ✅ Welcome & Capital steps complete
- ⏳ Risk profiler partially complete
- ⏳ Remaining steps untouched

---

## 🗓️ DAY 2: VISUALIZATIONS & POLISH

### Morning Session (9:00 AM - 12:00 PM)

#### **9:00 - 11:00 AM: Data Visualization Theme**
**Task 2.1: Chart Components**

**What to do:**
1. Create unified visualization theme object
2. Update `EfficientFrontierChart.tsx` (Lines 48-73)
   - Replace visualizationTheme with dark values
   - Test scatter plot visibility

3. Update `Portfolio3PartVisualization.tsx` (Lines 33-86)
   - Update vividPalette colors
   - Test pie charts and allocations

4. Update remaining chart components:
   - `FiveYearProjectionChart.tsx`
   - `RiskReturnChart.tsx`
   - `SectorDistributionChart.tsx`
   - `TwoAssetChart.tsx`

**Files:**
- `frontend/src/components/wizard/EfficientFrontierChart.tsx`
- `frontend/src/components/wizard/Portfolio3PartVisualization.tsx`
- `frontend/src/components/wizard/FiveYearProjectionChart.tsx`
- `frontend/src/components/wizard/RiskReturnChart.tsx`
- `frontend/src/components/wizard/SectorDistributionChart.tsx`
- `frontend/src/components/wizard/TwoAssetChart.tsx`

**Deliverable:** Dark-optimized data visualizations

**Verification:**
- All charts display clearly on dark background
- Data points are visible and distinguishable
- Grid lines are subtle but present
- Axis labels are readable
- Tooltips are styled appropriately
- Color contrast meets accessibility standards

---

#### **11:00 AM - 12:00 PM: Risk Profiler (Part 2)**
**Task 2.2 (Completion): Risk Assessment**

**What to do:**
1. Complete `ResultsPage.tsx` updates
   - Update flag alerts styling
   - Adjust quadrant visualizations
   - Update breakdown cards

2. Update `TwoDimensionalMap.tsx`
   - Adjust 2D risk mapping colors
   - Update quadrant backgrounds

3. Update `FlagAlerts.tsx`
   - Adjust alert styling for dark theme

**Files:**
- `frontend/src/components/wizard/ResultsPage.tsx`
- `frontend/src/components/wizard/TwoDimensionalMap.tsx`
- `frontend/src/components/wizard/FlagAlerts.tsx`
- `frontend/src/components/wizard/RiskProfiler.tsx`

**Deliverable:** Complete risk profiler in dark theme

**Verification:**
- All risk categories display correctly
- Flags and alerts are prominent
- 2D map is readable
- Results page is cohesive

---

### Afternoon Session (1:00 PM - 5:00 PM)

#### **1:00 - 2:00 PM: Stock Selection Step**
**Task 2.3 (Completion): Stock Selection Interface**

**What to do:**
1. Open `frontend/src/components/wizard/StockSelection.tsx`
2. Update tab interface styling
3. Update stock search results
4. Update correlation chart (TwoAssetChart)
5. Update allocation visualization
6. Test search functionality

**Files:**
- `frontend/src/components/wizard/StockSelection.tsx`
- `frontend/src/components/wizard/TwoAssetChart.tsx`

**Deliverable:** Dark-themed stock selection

**Verification:**
- Search interface is functional
- Results are readable
- Charts display correctly
- Selected stocks are highlighted appropriately

---

#### **2:00 - 3:00 PM: Portfolio Optimization**
**Task 2.4: Optimization Step**

**What to do:**
1. Open `frontend/src/components/wizard/PortfolioOptimization.tsx`
2. Update tab interface
3. Verify efficient frontier chart (already updated in 2.1)
4. Update strategy selection cards
5. Update legend styling
6. Test optimization controls

**Files:**
- `frontend/src/components/wizard/PortfolioOptimization.tsx`

**Deliverable:** Professional optimization interface

**Verification:**
- Efficient frontier is clearly visible
- Strategy cards are elegant
- Interactive controls work properly
- Zoom and selection features function

---

#### **3:00 - 4:00 PM: Final Steps (Stress Test & Finalize)**
**Task 2.5: Completing the Wizard**

**What to do:**
1. Open `frontend/src/components/wizard/StressTest.tsx`
   - Update scenario cards
   - Update metric displays
   - Test stress test flow

2. Open `frontend/src/components/wizard/FinalizePortfolio.tsx`
   - Update all four tabs
   - Update analysis components
   - Update comparison tables

3. Update supporting components:
   - `FinalAnalysisComponents.tsx`
   - `PortfolioComparisonTable.tsx`

**Files:**
- `frontend/src/components/wizard/StressTest.tsx`
- `frontend/src/components/wizard/FinalizePortfolio.tsx`
- `frontend/src/components/wizard/FinalAnalysisComponents.tsx`
- `frontend/src/components/wizard/PortfolioComparisonTable.tsx`

**Deliverable:** Complete wizard flow

**Verification:**
- All 7 steps are functional
- Stress test displays scenarios correctly
- Finalize tabs all work
- Portfolio export functions properly

---

#### **4:00 - 5:00 PM: Typography Pass & Final QA**
**Task 2.6 & 2.7: Consistency & Polish**

**What to do:**
1. **Typography Audit:**
   - Check heading hierarchy (h1, h2, h3)
   - Verify font weights are consistent
   - Check letter spacing
   - Verify color contrast ratios
   - Test responsive typography

2. **Visual Consistency Check:**
   - Spot check all 27 wizard components
   - Verify no gradients remain
   - Check spacing consistency
   - Verify border styles
   - Check hover states

3. **Full Wizard Walkthrough:**
   - Complete wizard from start to finish
   - Test with realistic data
   - Check all interactive elements
   - Verify loading states
   - Check error states
   - Document any issues

4. **Final Fixes:**
   - Address any remaining visual issues
   - Fix edge cases
   - Verify accessibility

5. **Documentation:**
   - Take screenshots of all steps
   - Document any known limitations
   - Create before/after comparison

**Deliverable:** Production-ready dark theme

**Verification Checklist:**
- [ ] All 7 wizard steps display correctly
- [ ] No gradients or bright colors remain
- [ ] Typography is consistent throughout
- [ ] All charts are readable
- [ ] Forms are functional
- [ ] Risk profiler works correctly
- [ ] Navigation is intuitive
- [ ] No console errors
- [ ] Accessibility standards met (WCAG AA)
- [ ] Performance is acceptable

---

## 🎯 END OF DAY 2 DELIVERABLES

### Expected Outcomes
✅ Complete dark theme across all 7 wizard steps
✅ Professional, minimalistic aesthetic matching Linear.app
✅ All data visualizations optimized for dark backgrounds
✅ Consistent typography throughout application
✅ No gradient backgrounds or bright color accents
✅ Accessible color contrast ratios
✅ Functional and tested wizard flow

### Final Commit Message
```
feat: Implement Linear-inspired dark theme redesign

- Update CSS variables to dark theme palette
- Remove gradient backgrounds and bright accents
- Redesign all 7 wizard steps with minimalist aesthetic
- Update 5+ data visualization components for dark backgrounds
- Implement consistent typography system
- Ensure WCAG AA accessibility standards
- Maintain full functionality across all features

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 📋 BACKUP PLAN

### If Running Behind Schedule

**Priority 1 (Must Complete):**
- ✅ CSS variables (Task 1.1)
- ✅ Main layout (Task 1.2)
- ✅ Buttons & cards (Task 1.3, 1.4)
- ✅ Welcome step (Task 1.5)
- ✅ Basic visualization updates (Task 2.1)

**Priority 2 (Should Complete):**
- Risk profiler components
- Stock selection
- Portfolio optimization

**Priority 3 (Nice to Have):**
- Typography refinements
- Edge case fixes
- Perfect pixel polish

### If Ahead of Schedule

**Enhancement Options:**
- Add subtle animations (fade-in, slide-in)
- Implement dark/light theme toggle
- Add Inter or custom font family
- Create style guide documentation
- Optimize bundle size

---

## 🛠️ TOOLS & RESOURCES

### Development Tools
- **Browser:** Chrome/Firefox with DevTools
- **Extensions:** React DevTools, Tailwind CSS IntelliSense
- **Editor:** Cursor AI with Claude integration

### Testing Tools
- **Contrast Checker:** WebAIM Contrast Checker
- **Responsive Testing:** Browser DevTools responsive mode
- **Screen Reader:** Built-in screen reader (optional)

### Reference Materials
- Linear.app website (open in separate window)
- [THEME_REDESIGN_TASKS.md](./THEME_REDESIGN_TASKS.md) (detailed task breakdown)
- Current documentation and README

---

## 📞 DECISION POINTS

### If Unsure About:
1. **Color Choices:** Refer to Linear.app and use color picker
2. **Typography:** Default to medium weight (450-500)
3. **Spacing:** Use multiples of 4px (Tailwind default)
4. **Borders:** Use subtle, 1px with low opacity
5. **Hover States:** Subtle background color change, no dramatic effects

### When to Ask for Feedback:
- After Day 1 completion (review progress)
- If visualization colors don't feel right
- If typography feels off
- Before final commit

---

## ✅ SUCCESS METRICS

### Visual Quality (Subjective)
- Application feels professional and premium
- Matches Linear.app's aesthetic
- No jarring color transitions
- Elegant and minimal

### Technical Quality (Objective)
- All CSS variables updated
- No hardcoded colors remain
- Consistent spacing and typography
- No console errors or warnings

### Functional Quality (Critical)
- All 7 wizard steps work
- Forms are functional
- Charts display data correctly
- Navigation is smooth
- No regressions in functionality

---

**Plan Version:** 1.0
**Last Updated:** 2026-02-04
**Estimated Effort:** 16 hours (2 full workdays)
**Actual Effort:** _To be filled after completion_
