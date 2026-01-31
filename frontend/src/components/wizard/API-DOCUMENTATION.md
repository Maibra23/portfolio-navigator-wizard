# Risk Profiling Scoring Engine API Documentation

Agent 1 Sprint 1 delivers the following interfaces for Agent 2 (Experience Agent) to consume when building visualizations and UX flows.

---

## 1. ScoringResult (main output)

```typescript
interface ScoringResult {
  // Basic scoring outputs
  raw_score: number;
  normalized_score: number;       // 0-100 scale
  normalized_mpt: number;         // 0-100 MPT subset
  normalized_prospect: number;    // 0-100 Prospect subset
  risk_category: string;          // 'very-conservative' | 'conservative' | 'moderate' | 'aggressive' | 'very-aggressive'
  color_code: string;             // Hex color for UI

  // Sprint 1 additions
  confidence_band: ConfidenceBand;
  visualization_data: VisualizationData;
  safeguards: SafeguardResult;
  consistency: ConsistencyResult;
}
```

---

## 2. ConfidenceBand

```typescript
interface ConfidenceBand {
  lower: number;                   // Lower bound (0-100)
  upper: number;                   // Upper bound (0-100)
  primary_category: string;        // Category at score center
  secondary_category: string|null; // Adjacent category if band crosses boundary
  band_width: number;              // upper - lower (twice the adjustment)
  adjustment_reasons: string[];    // 'variance' | 'speed' | 'divergence'
}
```

### Adjustment Reasons
| Key | Meaning |
|-----|---------|
| variance | Answer std deviation > 0.3 |
| speed | Avg time per question < 3s |
| divergence | |MPT - Prospect| > 25 |

### Tooltip Copy (ADJUSTMENT_TOOLTIPS)
```typescript
const ADJUSTMENT_TOOLTIPS = {
  variance: "Your answers showed varied preferences across questions—this is natural and suggests flexibility.",
  speed: "You completed quickly. Consider if answers reflect your considered preferences.",
  divergence: "Your analytical and emotional risk responses differ, which is common."
};
```

---

## 3. VisualizationData

```typescript
interface VisualizationData {
  score: number;                                   // Same as normalized_score
  band: ConfidenceBand;
  gradient_intensity: 'narrow' | 'medium' | 'wide'; // < 10 | 10-15 | > 15
  boundary_proximity: 'far' | 'near' | 'crossing';  // Distance to category boundary
}
```

### gradient_intensity
| Value | Condition |
|-------|-----------|
| narrow | band_width < 10 |
| medium | 10 ≤ band_width ≤ 15 |
| wide | band_width > 15 |

### boundary_proximity
| Value | Condition |
|-------|-----------|
| crossing | Band spans multiple categories |
| near | Score within 5 points of a boundary |
| far | Otherwise |

---

## 4. SafeguardResult

```typescript
interface SafeguardResult {
  original_category: string;
  final_category: string;
  category_was_overridden: boolean;
  override_reason: string | null;   // 'time_horizon_override' | 'high_uncertainty'
  flags: {
    loss_sensitivity_warning: boolean;
    response_pattern_warning: boolean;
    extreme_profile_confirmation: boolean;
    high_uncertainty: boolean;
  };
  flag_messages: Record<string, string>; // Only keys for raised flags
}
```

### Override Rules
| Condition | Action |
|-----------|--------|
| time_horizon ≤ 2 AND score > 60 | Cap at 'moderate' |
| Band spans 3+ categories | Default to 'moderate' |

### Flag Triggers
| Flag | Condition |
|------|-----------|
| loss_sensitivity_warning | loss_aversion = 1 AND score > 50 |
| response_pattern_warning | All answers at extremes (1 or max) |
| extreme_profile_confirmation | score < 15 OR score > 85 |
| high_uncertainty | Band spans 3+ categories |

### Flag Messages (FLAG_MESSAGES)
```typescript
const FLAG_MESSAGES = {
  loss_sensitivity_warning: "Your responses indicate strong sensitivity to losses. Consider discussing with a financial advisor.",
  response_pattern_warning: "Your responses showed strong preferences at both extremes. Please confirm this reflects your genuine approach.",
  extreme_profile_confirmation: "Your profile is less common. Please confirm this feels accurate.",
  high_uncertainty: "Your responses suggest flexibility across approaches. We've positioned you at the middle of your range."
};
```

---

## 5. ConsistencyResult

```typescript
interface ConsistencyResult {
  high_variance: boolean;          // Normalized answer std dev > 0.35
  fast_completion: boolean;        // Avg time per question < 3s
  potential_acquiescence: boolean; // Reverse-coded pair contradiction > 0.5
  flags: string[];                 // Array of raised flag keys
}
```

---

## 6. Example Response

```json
{
  "raw_score": 36,
  "normalized_score": 58.3,
  "normalized_mpt": 62.5,
  "normalized_prospect": 53.3,
  "risk_category": "moderate",
  "color_code": "#008000",
  "confidence_band": {
    "lower": 51.3,
    "upper": 65.3,
    "primary_category": "moderate",
    "secondary_category": "aggressive",
    "band_width": 14,
    "adjustment_reasons": ["divergence"]
  },
  "visualization_data": {
    "score": 58.3,
    "band": { /* same as above */ },
    "gradient_intensity": "medium",
    "boundary_proximity": "near"
  },
  "safeguards": {
    "original_category": "moderate",
    "final_category": "moderate",
    "category_was_overridden": false,
    "override_reason": null,
    "flags": {
      "loss_sensitivity_warning": false,
      "response_pattern_warning": false,
      "extreme_profile_confirmation": false,
      "high_uncertainty": false
    },
    "flag_messages": {}
  },
  "consistency": {
    "high_variance": false,
    "fast_completion": false,
    "potential_acquiescence": false,
    "flags": []
  }
}
```

---

## 7. How to Use

1. Import `computeScoring` from `scoring-engine.ts`.
2. Pass `selectedQuestions`, `answersMap`, `completionTimeSeconds` and optional dimension answers.
3. Receive `ScoringResult` with all Sprint 1 data.

```typescript
import { computeScoring } from './scoring-engine';

const result = computeScoring({
  selectedQuestions,
  answersMap,
  completionTimeSeconds: 55,
  timeHorizonAnswer: answers['M2'],
  lossAversionAnswer: answers['PT-2']
});

// result.confidence_band → for RiskSpectrum component
// result.visualization_data → gradient_intensity, boundary_proximity
// result.safeguards → confirmation flows, inline warnings
// result.consistency → additional quality flags
```

---

## 8. Files Summary

| File | Purpose |
|------|---------|
| scoring-engine.ts | Unified scoring entry point |
| confidence-calculator.ts | ConfidenceBand, VisualizationData, helpers |
| safeguards.ts | SafeguardResult, FLAG_MESSAGES, applySafeguards |
| consistency-detector.ts | ConsistencyResult, detectConsistencyIssues |
| monitoring.ts | AssessmentEvent logging |

---

**Sprint 1 Complete – Agent 1**
