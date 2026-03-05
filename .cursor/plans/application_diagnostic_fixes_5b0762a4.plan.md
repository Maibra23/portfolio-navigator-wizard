---
name: Application Diagnostic Fixes
overview: "Full diagnostic and fix plan for five application issues: risk assessment question/answer ordering, Lovable favicon remnants, Efficient Frontier color inconsistency, stock search error handling, and mobile graph usability."
todos:
  - id: favicon-fix
    content: Remove Lovable references from index.html, add custom favicon
    status: completed
  - id: efficient-frontier-colors
    content: Replace hardcoded colors with theme-aware getPortfolioColors() in EfficientFrontierChart.tsx and PortfolioOptimization.tsx
    status: completed
  - id: mobile-orientation
    content: Create useOrientation hook and LandscapeHint component for chart views
    status: completed
  - id: stock-search-ux
    content: Standardize empty-result messaging and add informative text about search scope
    status: completed
  - id: risk-docs-update
    content: Update RISK_PROFILING_QUESTIONNAIRE_AND_LOGIC.md to reflect actual adaptive branching behavior
    status: completed
isProject: false
---

# Application Diagnostic and Fix Plan

## Issue 1: Risk Assessment Phase Behavior

### Current Implementation

**Question Order:**

- **Under-19 (gamified path)**: Fixed order - `story-1` through `story-5` (see [question-selector.ts](frontend/src/components/wizard/question-selector.ts) lines 42-44)
- **Above-19 (adaptive path)**: Fixed adaptive sequence using phases:
  - Phase 1 anchors: `M2, M3, PT-2, PT-6`
  - Phase 2: pool based on early scores (conservative/aggressive/moderate)
  - Phase 3: gap filling, PT-13, consistency pairs

**Answer Choice Order:**

- **Under-19**: Fixed order (storyline options rendered in source order)
- **Above-19**: Randomized via `sort(() => Math.random() - 0.5)` in [RiskProfiler.tsx](frontend/src/components/wizard/RiskProfiler.tsx) lines 1737-1743

**Scoring:**

- Order-independent; uses `answersMap[question.id]` for lookup
- Scoring engine in [scoring-engine.ts](frontend/src/components/wizard/scoring-engine.ts) iterates by question ID, not display order

### Assessment

- Current behavior is **intentional** - adaptive branching requires fixed question phases
- Answer randomization (above-19) prevents pattern memorization
- Scoring is unaffected by display order
- Documentation in `RISK_PROFILING_QUESTIONNAIRE_AND_LOGIC.md` is outdated (mentions unused shuffle logic)

### Recommendation

No code changes needed. Update documentation to reflect actual adaptive branching behavior.

---

## Issue 2: Lovable Icon in Browser Tab

### Root Cause

[frontend/index.html](frontend/index.html) contains no favicon link, but has Lovable remnants:

```html
<meta name="description" content="Lovable Generated Project" />
<meta name="author" content="Lovable" />
<meta property="og:image" content="https://lovable.dev/opengraph-image-p98pqg.png" />
<meta name="twitter:site" content="@lovable_dev" />
<meta name="twitter:image" content="https://lovable.dev/opengraph-image-p98pqg.png" />
```

The Lovable favicon appears due to **browser caching** from previous builds when the scaffold included a favicon.

### Files to Modify

- [frontend/index.html](frontend/index.html)
- Add: `frontend/public/favicon.ico` (new file)
- Add: `frontend/public/favicon.svg` (optional, for modern browsers)

### Fix Steps

1. Create a custom favicon and place in `frontend/public/`
2. Add favicon link to `index.html`:

```html
   <link rel="icon" type="image/x-icon" href="/favicon.ico" />
   

```

1. Update meta tags to remove Lovable references
2. Clear browser cache or hard-refresh after deployment

---

## Issue 3: Efficient Frontier Color Inconsistency

### Root Cause

Both chart files import `getPortfolioColors()` but **ignore it**, using hardcoded hex values instead:


| Portfolio         | Hardcoded (Chart) | Theme System       |
| ----------------- | ----------------- | ------------------ |
| Current           | `#ef4444` (red)   | `#3b82f6` (blue)   |
| Weights-Optimized | `#3b82f6` (blue)  | `#10b981` (green)  |
| Market-Optimized  | `#22c55e` (green) | `#8b5cf6` (purple) |


Within each file, marker and legend colors **match each other** (both use hardcoded values). The inconsistency is:

- Between charts and the theme system (`getPortfolioColors`)
- Potential future inconsistency if other components use theme colors

### Files to Modify

- [frontend/src/components/wizard/EfficientFrontierChart.tsx](frontend/src/components/wizard/EfficientFrontierChart.tsx)
- [frontend/src/components/wizard/PortfolioOptimization.tsx](frontend/src/components/wizard/PortfolioOptimization.tsx)

### Fix Strategy

Replace all hardcoded portfolio colors with `portfolioColors.current`, `portfolioColors.weightsOptimized`, `portfolioColors.marketOptimized` from the already-imported `getPortfolioColors(theme)`.

Locations to update in EfficientFrontierChart.tsx:

- Legend circles (lines ~527-548)
- Scatter markers (lines ~919-1046)

Locations to update in PortfolioOptimization.tsx:

- Legend circles (lines ~4114-4173)
- Scatter markers (lines ~5006-5100)

---

## Issue 4: Stock Search Function Behavior

### Current Implementation

**Data Source:**

- Redis cache only (no live Yahoo Finance lookup at search time)
- Master list: ~1,432 validated tickers from `fetchable_master_list_validated_latest.csv`
- Implementation: [redis_first_data_service.py](backend/utils/redis_first_data_service.py) lines 599-707

**API Endpoint:**

- `GET /api/v1/portfolio/search-tickers?q={query}&limit=20`
- Returns `{ success: true, results: [...] }` (empty array if not found)

**Current Error Handling:**


| Component        | Empty Results                                         | API Error                     |
| ---------------- | ----------------------------------------------------- | ----------------------------- |
| PortfolioBuilder | Shows "No stocks found" message (not via error state) | Sets error state with message |
| StockSelection   | Sets error state with detailed message                | Sets error state              |
| StockSearchBar   | No error display                                      | Parent handles                |


### Issues Identified

1. Inconsistent empty-result handling between components
2. Users may not understand why valid tickers are missing (not in Redis cache)
3. No explanation that search is limited to cached/validated tickers

### Recommended Improvements

1. Standardize empty-result messaging across components
2. Add informative message: "Search includes pre-validated US stocks. Some tickers may not be available."
3. Consider adding a "Request ticker" feature for missing stocks

### Files to Review/Modify

- [frontend/src/components/wizard/PortfolioBuilder.tsx](frontend/src/components/wizard/PortfolioBuilder.tsx) (lines 494-564)
- [frontend/src/components/wizard/StockSelection.tsx](frontend/src/components/wizard/StockSelection.tsx) (search logic ~1360-1432)

---

## Issue 5: Mobile Graph Usability

### Current State

**Responsive Handling:**

- All charts use Recharts `ResponsiveContainer` with `width="100%"` (horizontal scaling works)
- Heights are often fixed (500px, 320px) regardless of viewport

**Mobile Detection:**

- `useIsMobile` hook exists ([use-mobile.tsx](frontend/src/hooks/use-mobile.tsx)) - breakpoint at 768px
- Only used for Dialog/Drawer and sidebar; **not used by any chart component**

**Missing Features:**

- No orientation detection
- No landscape mode suggestions
- No responsive height adjustments for charts
- Box zoom only supports mouse events (no touch support)

### Recommended Improvements

**1. Orientation Detection Hook** (new file: `frontend/src/hooks/use-orientation.tsx`)

```typescript
export function useOrientation() {
  const [isLandscape, setIsLandscape] = useState(
    window.matchMedia("(orientation: landscape)").matches
  );
  // Listen for orientation changes
  return { isLandscape, isPortrait: !isLandscape };
}
```

**2. Landscape Suggestion Component** (new file: `frontend/src/components/ui/landscape-hint.tsx`)

A non-intrusive overlay that:

- Only appears on mobile portrait mode when viewing charts
- Shows message: "Rotate your phone for a better view of this chart"
- Dismissible (remembers preference)
- Uses existing design system styling

**3. Chart Wrapper Updates**

Create a responsive chart wrapper that:

- Detects mobile + portrait orientation
- Shows landscape hint for complex charts
- Adjusts chart heights on mobile breakpoints

### Files to Create/Modify

- Create: `frontend/src/hooks/use-orientation.tsx`
- Create: `frontend/src/components/ui/landscape-hint.tsx`
- Modify: Chart components to wrap with responsive container
- Optionally: Add touch event handlers for box zoom

---

## Implementation Priority

1. **Favicon fix** - Quick win, improves branding
2. **Efficient Frontier colors** - Visual consistency fix
3. **Mobile orientation hint** - UX improvement
4. **Stock search messaging** - User clarity
5. **Documentation update** - Maintenance task

