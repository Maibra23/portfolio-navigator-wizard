# Mobile Landscape Hint Implementation Plan

This document outlines the implementation plan for displaying orientation hints to mobile users viewing charts and visualizations in the Portfolio Navigator Wizard application.

---

## Feature Overview

### Goal

When users view graphs, charts, or visualizations on a mobile phone in portrait orientation, display a non-intrusive notification encouraging them to rotate their device for a better viewing experience.

### Example Message

> **Rotate for better view**
>
> Turn your phone sideways to see the full chart

### Key Requirements

1. Only show on mobile devices in portrait orientation
2. Allow users to dismiss temporarily or permanently
3. Non-blocking — users can still interact with the chart
4. Consistent design across all chart components
5. Respect user preferences (remember dismissal)

---

## Current Implementation Status

### Existing Components

The feature is **already partially implemented**. The following files exist:

| File | Purpose | Status |
|------|---------|--------|
| `frontend/src/components/ui/landscape-hint.tsx` | Reusable hint wrapper component | Complete |
| `frontend/src/hooks/use-orientation.tsx` | Orientation detection hook | Complete |
| `frontend/src/hooks/use-mobile.tsx` | Mobile device detection | Complete |

### Current Usage

Currently applied to **1 component**:

| Component | Storage Key | Status |
|-----------|-------------|--------|
| `EfficientFrontierChart.tsx` | `efficient-frontier-landscape-hint` | Implemented |

---

## Technical Approach

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LandscapeHint                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Props:                                                      │    │
│  │  - storageKey: string (localStorage key for dismissal)       │    │
│  │  - children: ReactNode (the chart/visualization)             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Hooks Used:                                                 │    │
│  │  - useIsMobile() → boolean (screen width < 768px)            │    │
│  │  - useOrientation() → { isPortrait, isLandscape, angle }     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Display Logic:                                              │    │
│  │  showHint = isMobile && isPortrait && !isDismissed           │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Detection Methods

#### Mobile Detection (`useIsMobile`)

```typescript
// Uses media query for responsive detection
const isMobile = window.matchMedia("(max-width: 768px)").matches;
```

| Screen Width | Classification |
|--------------|----------------|
| < 768px | Mobile |
| >= 768px | Desktop/Tablet |

#### Orientation Detection (`useOrientation`)

```typescript
// Combines multiple detection methods for reliability
const isLandscape =
  window.matchMedia("(orientation: landscape)").matches ||
  window.innerWidth > window.innerHeight;
```

| Detection Method | Reliability | Notes |
|------------------|-------------|-------|
| `matchMedia("orientation")` | High | Standard CSS media query |
| `innerWidth > innerHeight` | High | Fallback for older browsers |
| `screen.orientation.angle` | Medium | Not supported in all browsers |

---

## UI Behavior

### State Machine

```
┌─────────────┐     User visits      ┌─────────────────┐
│   Hidden    │ ──────────────────── │ Check Conditions│
└─────────────┘                      └────────┬────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
              Not Mobile OR            Mobile + Portrait         Mobile + Landscape
              Already Dismissed         + Not Dismissed
                    │                         │                         │
                    ▼                         ▼                         ▼
              ┌─────────┐             ┌───────────────┐           ┌─────────┐
              │ Hidden  │             │ Show (500ms)  │           │ Hidden  │
              └─────────┘             └───────┬───────┘           └─────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
              "Continue anyway"      "Don't show again"          Rotate Phone
                    │                         │                         │
                    ▼                         ▼                         ▼
              ┌─────────┐             ┌───────────────┐           ┌─────────┐
              │ Hidden  │             │ Hidden        │           │ Hidden  │
              │(session)│             │ (permanent)   │           │(natural)│
              └─────────┘             └───────────────┘           └─────────┘
```

### Display Timing

| Event | Behavior |
|-------|----------|
| Component mounts | Wait 500ms before showing hint |
| User rotates to landscape | Immediately hide hint |
| User rotates back to portrait | Show hint again (unless dismissed) |
| User clicks "Continue anyway" | Hide for current session only |
| User clicks "Don't show again" | Hide permanently (localStorage) |

### Dismissal Persistence

```typescript
// Per-component storage keys prevent one dismissal affecting others
localStorage.setItem("efficient-frontier-landscape-hint", "true");
localStorage.setItem("stress-test-landscape-hint", "true");
// etc.
```

---

## Implementation Steps

### Step 1: Identify Target Components

Components containing charts/visualizations that benefit from landscape orientation:

| Component | File | Chart Type | Priority |
|-----------|------|------------|----------|
| EfficientFrontierChart | `EfficientFrontierChart.tsx` | Scatter plot | Done |
| PortfolioOptimization | `PortfolioOptimization.tsx` | Line/Area charts | High |
| StressTest | `StressTest.tsx` | Line charts | High |
| PortfolioBuilder | `PortfolioBuilder.tsx` | Pie/Bar charts | Medium |
| StockSelection | `StockSelection.tsx` | Data tables | Low |
| SectorDistribution | Various | Pie charts | Medium |

### Step 2: Add Import

For each component that needs the hint:

```typescript
import { LandscapeHint } from "@/components/ui/landscape-hint";
```

### Step 3: Wrap Chart Content

Example for `PortfolioOptimization.tsx`:

```tsx
// Before
<Card className="chart-container">
  <ResponsiveContainer width="100%" height={400}>
    <LineChart data={data}>
      {/* chart content */}
    </LineChart>
  </ResponsiveContainer>
</Card>

// After
<LandscapeHint storageKey="portfolio-optimization-landscape-hint">
  <Card className="chart-container">
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={data}>
        {/* chart content */}
      </LineChart>
    </ResponsiveContainer>
  </Card>
</LandscapeHint>
```

### Step 4: Choose Unique Storage Keys

| Component | Storage Key |
|-----------|-------------|
| EfficientFrontierChart | `efficient-frontier-landscape-hint` |
| PortfolioOptimization | `portfolio-optimization-landscape-hint` |
| StressTest | `stress-test-landscape-hint` |
| PortfolioBuilder | `portfolio-builder-landscape-hint` |
| SectorDistribution | `sector-distribution-landscape-hint` |

---

## Edge Cases

### Tablets

| Scenario | Behavior |
|----------|----------|
| iPad in portrait (768px+) | Hint NOT shown (exceeds mobile breakpoint) |
| Small tablet (< 768px) | Hint shown (treated as mobile) |
| iPad Mini | Depends on viewport width |

**Recommendation**: The 768px breakpoint is appropriate. Tablets have enough screen real estate that charts are usually readable in portrait.

### Already in Landscape

```typescript
// useOrientation detects current state on mount
if (isLandscape) {
  // Hint never shows — user already rotated
}
```

### Very Small Screens

The hint overlay is responsive:

```tsx
<div className="mx-4 max-w-sm rounded-lg border bg-card p-4 shadow-lg">
  {/* Content scales with screen */}
</div>
```

| Screen Width | Overlay Width |
|--------------|---------------|
| 320px | ~288px (320 - 32 margin) |
| 375px | ~343px |
| 414px | ~384px (max-sm = 384px) |

### Screen Rotation Lock

If the user has rotation lock enabled:

- Hint will show every time (portrait is permanent)
- User can dismiss permanently with "Don't show again"
- This is acceptable behavior

---

## Integration Points

### Existing Frontend Architecture

```
frontend/src/
├── components/
│   ├── ui/
│   │   ├── landscape-hint.tsx     ← Existing component
│   │   └── button.tsx             ← Used by hint
│   └── wizard/
│       ├── EfficientFrontierChart.tsx  ← Already integrated
│       ├── PortfolioOptimization.tsx   ← Needs integration
│       ├── StressTest.tsx              ← Needs integration
│       └── PortfolioBuilder.tsx        ← Needs integration
├── hooks/
│   ├── use-mobile.tsx             ← Existing hook
│   └── use-orientation.tsx        ← Existing hook
└── lib/
    └── utils.ts                   ← cn() utility for styling
```

### Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| `lucide-react` | RotateCcw, X icons | Already installed |
| `@/components/ui/button` | Button component | Already installed |
| `tailwindcss` | Styling | Already installed |

No new dependencies required.

---

## Testing Considerations

### Unit Tests (Existing)

```typescript
// frontend/src/components/ui/__tests__/landscape-hint.test.tsx
describe("LandscapeHint", () => {
  it("renders children");
  it("uses custom storageKey when provided");
});
```

### Manual Testing Checklist

| Test Case | Expected Result |
|-----------|-----------------|
| Desktop browser | Hint never shows |
| Mobile (portrait) + first visit | Hint shows after 500ms |
| Mobile (landscape) | Hint never shows |
| Tap "Continue anyway" | Hint hides, shows again on next visit |
| Tap "Don't show again" | Hint never shows again for that component |
| Rotate phone while hint visible | Hint immediately hides |
| Different charts | Each has independent dismissal state |

### Browser DevTools Mobile Simulation

1. Open Chrome DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Select mobile device (e.g., iPhone 12)
4. Set to portrait orientation
5. Verify hint appears

---

## Accessibility

### Current Implementation

| Feature | Status |
|---------|--------|
| Keyboard navigation | Buttons are focusable |
| Screen reader | Buttons have text labels |
| Color contrast | Uses theme colors (verified) |
| Touch targets | 44x44px minimum (verified) |

### ARIA Considerations

```tsx
// The overlay uses role="dialog" semantics implicitly via structure
<div
  className="absolute inset-0 z-50"
  aria-label="Rotate phone for better chart viewing"
>
```

---

## Performance

### Impact

| Metric | Impact |
|--------|--------|
| Bundle size | +2KB (component + hooks already bundled) |
| Runtime | Negligible (event listeners on orientation) |
| Re-renders | Only on orientation change |

### Optimization

The hooks use `useCallback` and proper cleanup:

```typescript
useEffect(() => {
  const handleChange = () => setOrientation(getOrientation());

  window.addEventListener("orientationchange", handleChange);
  window.addEventListener("resize", handleChange);

  return () => {
    window.removeEventListener("orientationchange", handleChange);
    window.removeEventListener("resize", handleChange);
  };
}, []);
```

---

## Rollout Plan

### Phase 1: High-Priority Charts (Week 1)

1. `PortfolioOptimization.tsx` — Main optimization view
2. `StressTest.tsx` — Stress test visualizations

### Phase 2: Medium-Priority Charts (Week 2)

1. `PortfolioBuilder.tsx` — Portfolio composition
2. Sector distribution charts

### Phase 3: Monitoring

1. Track dismissal rates via analytics (optional)
2. Gather user feedback
3. Adjust message copy if needed

---

## Code Example: Full Integration

```tsx
// frontend/src/components/wizard/StressTest.tsx

import { LandscapeHint } from "@/components/ui/landscape-hint";

export function StressTest({ portfolio }: StressTestProps) {
  // ... existing logic ...

  return (
    <div className="space-y-6">
      <h2>Stress Test Analysis</h2>

      {/* Wrap chart section with LandscapeHint */}
      <LandscapeHint storageKey="stress-test-landscape-hint">
        <Card>
          <CardHeader>
            <CardTitle>Historical Scenarios</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={scenarioData}>
                <XAxis dataKey="date" />
                <YAxis />
                <Line type="monotone" dataKey="value" stroke="#8884d8" />
                {/* ... */}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </LandscapeHint>

      {/* Other non-chart content doesn't need wrapper */}
      <Card>
        <CardContent>
          <p>Summary statistics...</p>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Summary

| Aspect | Details |
|--------|---------|
| **Feature** | Landscape orientation hint for mobile users |
| **Status** | Partially implemented (1 of 5+ charts) |
| **Effort** | Low — wrapper component exists, just needs application |
| **Risk** | Very low — non-breaking, progressively enhanced |
| **User Impact** | Improved mobile UX for chart viewing |

---

*Implementation plan created: 2026-03-06*
