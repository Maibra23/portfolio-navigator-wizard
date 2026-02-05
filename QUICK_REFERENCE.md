# Linear-Inspired Dark Theme - Quick Reference Guide

**Quick Links:**
- 📋 [Detailed Tasks](./THEME_REDESIGN_TASKS.md) - Complete task breakdown with design system
- 📅 [Implementation Plan](./IMPLEMENTATION_PLAN.md) - 2-day schedule with milestones
- 💬 [Cursor AI Prompts](./CURSOR_AI_PROMPTS.md) - Ready-to-use prompts for each task

---

## 🚀 QUICK START

### Day 1 Morning (Priority)
1. ✅ **CSS Variables** - Update `frontend/src/index.css` with dark theme
2. ✅ **Main Layout** - Update `frontend/src/components/PortfolioWizard.tsx`
3. ✅ **Buttons & Cards** - Update `frontend/src/components/ui/button.tsx` and `card.tsx`

### Day 1 Afternoon
4. ✅ **Welcome Step** - Update `frontend/src/components/wizard/WelcomeStep.tsx`
5. ✅ **Capital Input** - Update `frontend/src/components/wizard/CapitalInput.tsx`
6. ✅ **Risk Profiler** (Part 1) - Update `CategoryCard.tsx` and `RiskSpectrum.tsx`

### Day 2 Morning (Most Complex)
7. ✅ **Visualizations** - Update all chart components with dark theme
8. ✅ **Risk Profiler** (Part 2) - Complete risk assessment UI

### Day 2 Afternoon
9. ✅ **Stock Selection** - Update `StockSelection.tsx`
10. ✅ **Optimization** - Update `PortfolioOptimization.tsx`
11. ✅ **Final Steps** - Update `StressTest.tsx` and `FinalizePortfolio.tsx`
12. ✅ **QA & Polish** - Typography pass and full testing

---

## 🎨 DESIGN SYSTEM CHEAT SHEET

### Core Colors (Copy-Paste Ready)
```css
/* Dark Theme - Replace in index.css :root */
--background: 222 10% 5%;
--foreground: 0 0% 95%;
--card: 222 10% 8%;
--card-foreground: 0 0% 95%;
--primary: 0 0% 85%;
--primary-foreground: 222 10% 10%;
--secondary: 220 10% 15%;
--secondary-foreground: 0 0% 80%;
--muted: 220 10% 12%;
--muted-foreground: 0 0% 60%;
--accent: 220 10% 18%;
--accent-foreground: 0 0% 90%;
--border: 220 10% 18%;
--input: 220 10% 18%;
--ring: 0 0% 70%;
--destructive: 0 50% 45%;
--destructive-foreground: 0 0% 95%;

/* Risk Colors (Muted) */
--conservative: 214 50% 45%;
--moderate: 142 40% 40%;
--aggressive: 0 50% 50%;
```

### Chart Colors (Copy-Paste Ready)
```javascript
// Dark-optimized visualization palette
const darkPalette = [
  '#4ade80', '#f87171', '#60a5fa', '#fbbf24', '#a78bfa',
  '#fb923c', '#22d3ee', '#f472b6', '#84cc16', '#06b6d4'
];

// Chart theme object
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

### Typography Scale
```css
Font Weights: 450 (normal), 500 (medium), 600 (semibold)
Letter Spacing: -0.01em (tight), 0 (normal), 0.01em (wide)

Sizes:
- xs: 12px    | sm: 14px
- base: 16px  | lg: 18px
- xl: 20px    | 2xl: 24px
- 3xl: 30px   | 4xl: 36px
```

---

## 🔍 COMMON PATTERNS

### ❌ Remove These Patterns:
```tsx
// Gradients
className="bg-gradient-to-br from-blue-50 to-indigo-100"
className="bg-gradient-primary"
style={{ background: 'linear-gradient(...)' }}

// Hardcoded Colors
className="text-blue-600"
className="bg-green-500"
className="border-gray-200"

// Heavy Shadows
className="shadow-elegant"
className="shadow-card"

// Opacity Hovers
className="hover:opacity-90"
```

### ✅ Replace With:
```tsx
// Solid Backgrounds
className="bg-background"
className="bg-card"
className="bg-secondary"

// CSS Variable Colors
className="text-foreground"
className="text-muted-foreground"
className="border-border"

// Subtle Borders
className="border border-border/50"

// Simple Hovers
className="hover:bg-secondary/80"
```

---

## 📂 KEY FILES TO MODIFY

### Core (Day 1 Priority)
- ✅ `frontend/src/index.css` - CSS variables
- ✅ `frontend/tailwind.config.ts` - Remove gradient utilities
- ✅ `frontend/src/components/PortfolioWizard.tsx` - Main layout
- ✅ `frontend/src/components/ui/button.tsx` - Buttons
- ✅ `frontend/src/components/ui/card.tsx` - Cards

### Wizard Steps (Day 1-2)
- ✅ `frontend/src/components/wizard/WelcomeStep.tsx`
- ✅ `frontend/src/components/wizard/CapitalInput.tsx`
- ✅ `frontend/src/components/wizard/RiskProfiler.tsx`
- ✅ `frontend/src/components/wizard/StockSelection.tsx`
- ✅ `frontend/src/components/wizard/PortfolioOptimization.tsx`
- ✅ `frontend/src/components/wizard/StressTest.tsx`
- ✅ `frontend/src/components/wizard/FinalizePortfolio.tsx`

### Visualizations (Day 2 Priority)
- ✅ `frontend/src/components/wizard/EfficientFrontierChart.tsx`
- ✅ `frontend/src/components/wizard/Portfolio3PartVisualization.tsx`
- ✅ `frontend/src/components/wizard/FiveYearProjectionChart.tsx`
- ✅ `frontend/src/components/wizard/RiskReturnChart.tsx`
- ✅ `frontend/src/components/wizard/SectorDistributionChart.tsx`
- ✅ `frontend/src/components/wizard/TwoAssetChart.tsx`

### Risk Profiler Components
- ✅ `frontend/src/components/wizard/CategoryCard.tsx`
- ✅ `frontend/src/components/wizard/RiskSpectrum.tsx`
- ✅ `frontend/src/components/wizard/ResultsPage.tsx`
- ✅ `frontend/src/components/wizard/TwoDimensionalMap.tsx`
- ✅ `frontend/src/components/wizard/FlagAlerts.tsx`

---

## 🎯 TESTING CHECKLIST

### After Each Change:
- [ ] Refresh browser
- [ ] Check component renders
- [ ] Verify no console errors
- [ ] Check text is readable
- [ ] Test interactive elements

### End of Day 1:
- [ ] Steps 1-3 display correctly
- [ ] Navigation works
- [ ] Forms are functional
- [ ] No gradients in completed sections

### End of Day 2:
- [ ] All 7 steps functional
- [ ] All charts readable
- [ ] Risk profiler works correctly
- [ ] Full wizard completion works
- [ ] No console errors
- [ ] Contrast ratios meet WCAG AA

---

## ⚡ QUICK COMMANDS

### Start Development Server
```bash
cd frontend
npm run dev
```

### Build for Production
```bash
cd frontend
npm run build
```

### Run Tests
```bash
cd frontend
npm test
```

### Commit Changes
```bash
git add .
git commit -m "feat: implement Linear-inspired dark theme - [COMPONENT_NAME]"
```

---

## 🐛 COMMON ISSUES & FIXES

### Issue: Text Not Visible
**Fix:** Check if using `text-foreground` instead of hardcoded colors

### Issue: Charts Too Dark
**Fix:** Increase grid opacity and use lighter axis colors

### Issue: Buttons Not Visible
**Fix:** Ensure button variant uses appropriate background contrast

### Issue: Forms Hard to Use
**Fix:** Add border to inputs, adjust placeholder color

### Issue: Risk Categories Not Distinguishable
**Fix:** Use muted but distinct colors (blue/green/red with reduced saturation)

---

## 📊 PROGRESS TRACKING

### Day 1 End Status:
- [ ] CSS variables updated ✅
- [ ] Main layout dark-themed ✅
- [ ] Core UI components updated ✅
- [ ] Steps 1-3 complete ✅
- [ ] Risk profiler partially done 🔄
- [ ] Ready for Day 2 visualizations 🎯

### Day 2 End Status:
- [ ] All visualizations updated ✅
- [ ] Risk profiler complete ✅
- [ ] All 7 steps functional ✅
- [ ] Typography consistent ✅
- [ ] QA completed ✅
- [ ] Production ready 🚀

---

## 🎨 LINEAR.APP REFERENCE

### What Makes Linear Special:
1. **Near-black backgrounds** (#08090a) not pure black
2. **Subtle grayscale gradients** for depth, not color
3. **Typography-driven hierarchy** not color-driven
4. **Medium font weight** (450-500) as default
5. **Minimal accent color** use
6. **Precise spacing** with modular scale
7. **Subtle borders** instead of heavy shadows
8. **Professional, premium feel** through restraint

### Pages to Reference:
- Homepage: https://linear.app/
- Features: https://linear.app/features
- Method: https://linear.app/method

---

## 💡 PRO TIPS

1. **Work Top-Down:** Start with CSS variables, then layout, then components
2. **Test Frequently:** Refresh browser after every file save
3. **Use DevTools:** Inspect elements to verify CSS variable application
4. **Commit Often:** Small commits are easier to revert if needed
5. **Check Contrast:** Use browser DevTools contrast checker
6. **Reference Linear:** Keep Linear.app open for visual reference
7. **Stay Minimal:** When in doubt, use less color and simpler styling
8. **Typography Matters:** Proper font weights and spacing create premium feel
9. **Subtle Borders:** Use `border-border/50` for gentle separation
10. **Test All States:** Don't forget hover, focus, active, loading, error states

---

## 📞 DECISION FLOWCHART

```
Need to update styling?
├─ Is it a color? → Use CSS variable (e.g., text-foreground)
├─ Is it a gradient? → Remove and use solid color
├─ Is it a shadow? → Replace with subtle border
├─ Is it a chart? → Use darkPalette colors
├─ Is it typography? → Use consistent weights (450-600)
└─ Not sure? → Check Linear.app for reference
```

---

## 📚 RESOURCES

### Documentation
- [THEME_REDESIGN_TASKS.md](./THEME_REDESIGN_TASKS.md) - Full task breakdown
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Day-by-day schedule
- [CURSOR_AI_PROMPTS.md](./CURSOR_AI_PROMPTS.md) - AI prompts for each task

### Design References
- Linear.app: https://linear.app/
- Tailwind CSS: https://tailwindcss.com/docs
- Recharts: https://recharts.org/

### Tools
- Contrast Checker: https://webaim.org/resources/contrastchecker/
- Color Picker: Browser DevTools
- React DevTools: Browser extension

---

**Last Updated:** 2026-02-04
**Document Version:** 1.0
**Estimated Completion:** 2 days (16 hours)

**Ready to start? Begin with [CURSOR_AI_PROMPTS.md](./CURSOR_AI_PROMPTS.md) Prompt 1.1!**
