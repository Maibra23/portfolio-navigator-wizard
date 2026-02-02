# Risk Profiling System Strengthening: Agent Task Coordination Document

**Project Duration:** 2 Days  
**Start Date:** Today  
**Objective:** Strengthen the risk profiling system by minimizing structural weaknesses, reducing bias, improving classification reliability, and enhancing interpretability.

---

## Table of Contents

1. [Project Context](#project-context)
2. [Execution Timeline](#execution-timeline)
3. [Dependency Map](#dependency-map)
4. [Agent 1: Core Logic Agent](#agent-1-core-logic-agent)
5. [Agent 2: Experience Agent](#agent-2-experience-agent)
6. [Agent 3: Question Content Agent](#agent-3-question-content-agent)
7. [Coordination Checklist](#coordination-checklist)
8. [Cursor Operating Guidelines](#cursor-operating-guidelines)

---

## Project Context

### System Overview

The risk profiling system is a questionnaire-based tool assessing investment risk tolerance. It combines Modern Portfolio Theory (MPT) with Prospect Theory to produce a normalized 0-100 risk score mapped to five categories:

| Score Range | Category |
|-------------|----------|
| 0-20 | Very Conservative |
| 21-40 | Conservative |
| 41-60 | Moderate |
| 61-80 | Aggressive |
| 81-100 | Very Aggressive |

### Key System Facts

- **27 total questions:** 3 screening (unscored), 15 MPT pool (1-5 scale), 12 Prospect pool (mostly 1-4 scale)
- **Under-19 users:** See 5 gamified scenarios (all Prospect, 1-4 scale)
- **19+ users:** See 12 questions selected from pools based on experience/knowledge
- **Scoring formula:** `normalized_contribution = (answer - 1) / (maxScore - 1)`
- **Sub-scores:** Separate MPT and Prospect scores tracked

### Problems Being Solved

1. No uncertainty quantification (false precision)
2. Static question set (no adaptation)
3. Acquiescence and recency bias vulnerabilities
4. Potential misclassification at boundaries
5. Limited visualization for user understanding

---

## Execution Timeline

```
DAY 1
═══════════════════════════════════════════════════════════════
│ MORNING (4-5 hours)                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ AGENT 1 - Sprint 1                                      │ │
│ │ • Confidence band calculation                           │ │
│ │ • Override logic and safeguards                         │ │
│ │ • Consistency detection                                 │ │
│ │ • Monitoring instrumentation                            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ AFTERNOON (4-5 hours)                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ AGENT 3 - Full Sprint (runs parallel after lunch)       │ │
│ │ • Question revisions                                    │ │
│ │ • Reverse-coded questions                               │ │
│ │ • Counterfactual question                               │ │
│ │ • Gamified scenario improvements                        │ │
│ │ • Construct metadata                                    │ │
│ └─────────────────────────────────────────────────────────┘ │
═══════════════════════════════════════════════════════════════

DAY 2
═══════════════════════════════════════════════════════════════
│ MORNING (4-5 hours)                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ AGENT 1 - Sprint 2                                      │ │
│ │ • Rule-based adaptive branching                         │ │
│ │ • Question selection state machine                      │ │
│ │ • Integration with Agent 3 metadata                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ AFTERNOON (4-5 hours)                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ AGENT 2 - Full Sprint                                   │ │
│ │ • Risk spectrum visualization                           │ │
│ │ • Category description card                             │ │
│ │ • 2D risk map                                           │ │
│ │ • Confirmation flows                                    │ │
│ │ • Question display updates                              │ │
│ └─────────────────────────────────────────────────────────┘ │
═══════════════════════════════════════════════════════════════
```

---

## Dependency Map

```
AGENT 1 (Core Logic)              AGENT 3 (Questions)           AGENT 2 (Experience)
────────────────────              ───────────────────           ────────────────────

[Day 1 AM]                        [Day 1 PM]                    [Day 2 PM]

confidence_band_calc ─────────────────────────────────────────► spectrum_visualization
        │                                                              │
override_logic ───────────────────────────────────────────────► confirmation_prompts
        │                                                              │
consistency_detection ────────────────────────────────────────► band_width_display
        │                                │                             │
        │                         question_revisions ─────────► question_ui_updates
        │                                │                             │
        │                         reverse_coded_flags ────────► scoring_inversion
        │                                │                             │
        │                         counterfactual_q ───────────► counterfactual_ui
        │                                │
[Day 2 AM]                               │
        │                                │
adaptive_branching ◄──────────── question_metadata
        │                                │
question_selector ◄─────────────  construct_mappings
        │
        └─────────────────────────────────────────────────────► dynamic_question_ui
```

### Critical Handoffs

| From | To | What | When |
|------|-----|------|------|
| Agent 1 Sprint 1 | Agent 2 | Confidence band API interface | End of Day 1 AM |
| Agent 3 | Agent 1 Sprint 2 | Question metadata + construct mappings | End of Day 1 PM |
| Agent 3 | Agent 2 | Revised question text + reverse-coded flags | End of Day 1 PM |
| Agent 1 Sprint 2 | Agent 2 | Branching state machine interface | End of Day 2 AM |

---

## Agent 1: Core Logic Agent

### Identity and Role

You are the **Core Logic Agent** responsible for the mathematical and algorithmic backbone of the risk profiling system. Your work ensures scoring accuracy, classification reliability, and system robustness.

### Responsibilities

1. Confidence interval computation and integration
2. Misclassification safeguards and override logic
3. Consistency detection algorithms
4. Rule-based adaptive branching logic
5. Monitoring instrumentation

### Primary Files/Modules

```
scoring-engine.ts       - Core scoring calculations
risk-classifier.ts      - Category assignment logic
question-selector.ts    - Question selection and branching
confidence-calculator.ts - NEW: Uncertainty quantification
safeguards.ts           - NEW: Override and flag logic
consistency-detector.ts - NEW: Response pattern analysis
monitoring.ts           - NEW: Event logging
```

---

### Day 1 Tasks (Morning: Sprint 1)

#### Task 1.1: Confidence Band Calculation

**Objective:** Compute uncertainty bands reflecting response noise, scale ambiguity, and internal inconsistency.

**Implementation:**

```typescript
// Base uncertainty (empirical retest variance)
const BASE_UNCERTAINTY = 5;

// Adjustment rules
function calculateConfidenceBand(
  normalizedScore: number,
  answers: Record<string, number>,
  mptScore: number,
  prospectScore: number,
  completionTimeSeconds: number,
  questionCount: number
): ConfidenceBand {
  
  let adjustment = BASE_UNCERTAINTY;
  const reasons: string[] = [];
  
  // 1. Answer variance check
  const normalizedAnswers = Object.values(answers).map(/* normalize each */);
  const variance = standardDeviation(normalizedAnswers);
  if (variance > 0.3) {
    adjustment += 2;
    reasons.push('variance');
  }
  
  // 2. Speed check
  const avgTimePerQuestion = completionTimeSeconds / questionCount;
  if (avgTimePerQuestion < 3) {
    adjustment += 2;
    reasons.push('speed');
  }
  
  // 3. MPT/Prospect divergence check
  if (Math.abs(mptScore - prospectScore) > 25) {
    adjustment += 3;
    reasons.push('divergence');
  }
  
  return {
    lower: Math.max(0, normalizedScore - adjustment),
    upper: Math.min(100, normalizedScore + adjustment),
    primary_category: getCategory(normalizedScore),
    secondary_category: getSecondaryCategory(normalizedScore, adjustment),
    band_width: adjustment * 2,
    adjustment_reasons: reasons
  };
}
```

**Output Interface:**

```typescript
interface ConfidenceBand {
  lower: number;
  upper: number;
  primary_category: string;
  secondary_category: string | null;
  band_width: number;
  adjustment_reasons: string[];
}

interface VisualizationData {
  score: number;
  band: ConfidenceBand;
  gradient_intensity: 'narrow' | 'medium' | 'wide';
  boundary_proximity: 'far' | 'near' | 'crossing';
}
```

**Tooltip Content to Provide:**

```typescript
const ADJUSTMENT_TOOLTIPS = {
  variance: "Your answers showed varied preferences across questions—this is natural and suggests flexibility.",
  speed: "You completed quickly. Consider if answers reflect your considered preferences.",
  divergence: "Your analytical and emotional risk responses differ, which is common."
};
```

#### Task 1.2: Critical Dimension Override Logic

**Objective:** Prevent harmful misclassification with hard safeguards.

**Override Rules:**

| Condition | Action | Flag |
|-----------|--------|------|
| `time_horizon ≤ 2 AND score > 60` | Cap at Moderate | `time_horizon_override` |
| `loss_aversion = 1 AND score > 50` | Add warning | `loss_sensitivity_warning` |
| `all answers at extremes only` | Add warning | `response_pattern_warning` |
| `score < 15 OR score > 85` | Require confirmation | `extreme_profile_confirmation` |
| `band spans 3+ categories` | Default to middle | `high_uncertainty` |

**Output Interface:**

```typescript
interface SafeguardResult {
  original_category: string;
  final_category: string;
  category_was_overridden: boolean;
  override_reason: string | null;
  flags: {
    loss_sensitivity_warning: boolean;
    response_pattern_warning: boolean;
    extreme_profile_confirmation: boolean;
    high_uncertainty: boolean;
  };
  flag_messages: Record<string, string>;
}

const FLAG_MESSAGES = {
  loss_sensitivity_warning: "Your responses indicate strong sensitivity to losses. Consider discussing with a financial advisor.",
  response_pattern_warning: "Your responses showed strong preferences at both extremes. Please confirm this reflects your genuine approach.",
  extreme_profile_confirmation: "Your profile is less common. Please confirm this feels accurate.",
  high_uncertainty: "Your responses suggest flexibility across approaches. We've positioned you at the middle of your range."
};
```

#### Task 1.3: Consistency Detection

**Objective:** Detect unreliable response patterns.

**Algorithms:**

```typescript
// 1. Answer variance
function checkAnswerVariance(answers: number[], maxScores: number[]): boolean {
  const normalized = answers.map((a, i) => (a - 1) / (maxScores[i] - 1));
  return standardDeviation(normalized) > 0.35;
}

// 2. Speed check
function checkCompletionSpeed(totalSeconds: number, questionCount: number): boolean {
  return (totalSeconds / questionCount) < 3;
}

// 3. Reverse-coded contradiction (for Day 2 integration)
function checkReverseCodedConsistency(
  originalAnswer: number,
  originalMax: number,
  reverseAnswer: number,
  reverseMax: number
): boolean {
  const origNorm = (originalAnswer - 1) / (originalMax - 1);
  const revNorm = 1 - ((reverseAnswer - 1) / (reverseMax - 1));
  return Math.abs(origNorm - revNorm) > 0.5;
}
```

#### Task 1.4: Monitoring Instrumentation

**Objective:** Log events for post-deployment analysis.

```typescript
interface AssessmentEvent {
  event_type: 'assessment_completed' | 'override_triggered' | 'flag_raised';
  timestamp: Date;
  session_id: string;
  data: {
    normalized_score: number;
    confidence_band: ConfidenceBand;
    category: string;
    overrides_applied: string[];
    flags_raised: string[];
    completion_time_seconds: number;
    mpt_score: number;
    prospect_score: number;
  };
}

function logAssessmentEvent(event: AssessmentEvent): void {
  // Implementation: send to logging service
}
```

---

### Day 2 Tasks (Morning: Sprint 2)

**Prerequisite:** Agent 3's question metadata must be complete.

#### Task 2.1: Rule-Based Adaptive Branching

**Objective:** Implement deterministic branching that improves accuracy without behavioral calibration data.

**Architecture:**

```
PHASE 1: Anchor Questions (4 questions) - Always asked first
├── M2: Time Horizon
├── M3: Volatility Tolerance
├── PT-2: Loss Aversion
└── PT-6: Drawdown Behavior

→ Calculate phase1_score = average of normalized contributions

PHASE 2: Adaptive Refinement (4 questions)
├── IF phase1_score < 30: CONSERVATIVE_POOL [M5, M6, PT-1, PT-7]
├── IF phase1_score > 70: AGGRESSIVE_POOL [M4, M11, PT-4, PT-10]
└── ELSE: DISCRIMINATING_POOL [M8, M10, PT-3, PT-8]

PHASE 3: Consistency & Coverage (4 questions)
├── Q9-10: Fill construct gaps
├── Q11: Counterfactual question (PT-13)
└── Q12: Consistency check question
```

**Question Pools:**

```typescript
const QUESTION_POOLS = {
  ANCHOR: ['M2', 'M3', 'PT-2', 'PT-6'],
  CONSERVATIVE_CONFIRMING: ['M5', 'M6', 'PT-1', 'PT-7'],
  AGGRESSIVE_CONFIRMING: ['M4', 'M11', 'PT-4', 'PT-10'],
  DISCRIMINATING: ['M8', 'M10', 'PT-3', 'PT-8'],
  CONSISTENCY_PAIRS: {
    'M3': 'M3-R',
    'PT-2': 'PT-2-R'
  }
};

const REQUIRED_CONSTRUCTS = [
  'time_horizon',
  'volatility_tolerance',
  'loss_aversion',
  'market_reaction',
  'capital_allocation',
  'probability_weighting'
];
```

#### Task 2.2: Question Selection State Machine

**Interface:**

```typescript
interface BranchingState {
  current_phase: 1 | 2 | 3;
  questions_asked: string[];
  phase1_score: number | null;
  selected_path: 'conservative' | 'aggressive' | 'moderate' | null;
  constructs_covered: Set<string>;
}

interface QuestionSelector {
  initialize(userProfile: { ageGroup: string; experiencePoints: number }): void;
  getNextQuestion(): Question | null;
  submitAnswer(questionId: string, answer: number, timeSeconds: number): void;
  isComplete(): boolean;
  getSelectedQuestions(): Question[];
  getBranchingPath(): string;
  getState(): BranchingState;
}
```

**Implementation Logic:**

```typescript
function getNextQuestion(state: BranchingState, answers: Map<string, number>): string | null {
  if (state.current_phase === 1) {
    const remaining = QUESTION_POOLS.ANCHOR.filter(q => !state.questions_asked.includes(q));
    return remaining[0] || null;
  }
  
  if (state.current_phase === 2) {
    const pool = state.selected_path === 'conservative' ? QUESTION_POOLS.CONSERVATIVE_CONFIRMING
               : state.selected_path === 'aggressive' ? QUESTION_POOLS.AGGRESSIVE_CONFIRMING
               : QUESTION_POOLS.DISCRIMINATING;
    const remaining = pool.filter(q => !state.questions_asked.includes(q));
    return remaining[0] || null;
  }
  
  if (state.current_phase === 3) {
    // Fill construct gaps first
    const missingConstructs = REQUIRED_CONSTRUCTS.filter(c => !state.constructs_covered.has(c));
    if (missingConstructs.length > 0) {
      return findQuestionForConstruct(missingConstructs[0], state.questions_asked);
    }
    // Then counterfactual
    if (!state.questions_asked.includes('PT-13')) return 'PT-13';
    // Then consistency check
    return selectConsistencyQuestion(state);
  }
  
  return null;
}
```

---

### Expected Outputs After Each Day

**End of Day 1:**
- `confidence-calculator.ts` - Complete with tests
- `safeguards.ts` - Complete with all override rules
- `consistency-detector.ts` - Complete with all detection algorithms
- `monitoring.ts` - Complete with event logging
- API interface documentation for Agent 2

**End of Day 2:**
- `adaptive-branching.ts` - Complete state machine
- `question-selector.ts` - Updated with branching integration
- Integration tests for full scoring pipeline
- Updated `scoring-engine.ts` with all new modules

### Success Metrics

| Metric | Target |
|--------|--------|
| Confidence band contains retest score | >80% |
| Override false positive rate | <5% |
| Scoring latency | <100ms |
| All existing tests pass | 100% |
| Branching produces valid question sets | 100% |
| Construct coverage achieved | 100% |

---

## Agent 2: Experience Agent

### Identity and Role

You are the **Experience Agent** responsible for all user-facing elements of the risk profiling system. Your work ensures users understand their profile intuitively and trust the results.

### Responsibilities

1. All visualization implementations
2. User-facing uncertainty communication
3. UI components for questions and results
4. Tooltip and explanation copy
5. Confirmation flows for edge cases
6. Dynamic question loading support

### Primary Files/Modules

```
components/RiskSpectrum.tsx      - Main score visualization
components/CategoryCard.tsx      - Category description
components/TwoDimensionalMap.tsx - MPT vs Prospect plot
components/ConfidenceBand.tsx    - Uncertainty display
components/ConfirmationModal.tsx - Extreme profile handling
components/FlagAlerts.tsx        - Inline warnings
components/QuestionDisplay.tsx   - Question rendering
components/TemporalPrompt.tsx    - Pre-assessment prompt
utils/tooltips.ts                - All tooltip content
```

### Dependencies

**You must wait for:**
- Agent 1 Sprint 1 completion (confidence band API)
- Agent 3 completion (question content)

**Start: Day 2 Afternoon**

---

### Day 2 Tasks (Afternoon)

#### Task 1: Risk Spectrum with Confidence Band

**Objective:** Primary visualization showing user position with uncertainty.

**Requirements:**

1. Horizontal spectrum 0-100 with five color zones:
   - Very Conservative (0-20): `#00008B`
   - Conservative (21-40): `#ADD8E6`
   - Moderate (41-60): `#008000`
   - Aggressive (61-80): `#FFA500`
   - Very Aggressive (81-100): `#FF0000`

2. User marker with soft gradient based on `gradient_intensity`:
   - `narrow` (<10): Sharp marker, minimal glow
   - `medium` (10-15): Moderate glow
   - `wide` (>15): Large glow, prominent band

3. Confidence band as semi-transparent overlay

4. Boundary handling based on `boundary_proximity`:
   - `far`: No special treatment
   - `near`: Show nearby boundary indicator
   - `crossing`: Display "Your range spans..."

**Props Interface:**

```typescript
interface RiskSpectrumProps {
  score: number;
  confidenceBand: {
    lower: number;
    upper: number;
    primary_category: string;
    secondary_category: string | null;
    band_width: number;
    adjustment_reasons: string[];
  };
  visualizationData: {
    gradient_intensity: 'narrow' | 'medium' | 'wide';
    boundary_proximity: 'far' | 'near' | 'crossing';
  };
}
```

**Tooltips:**

```typescript
const SPECTRUM_TOOLTIPS = {
  score_marker: "Your risk score based on your responses.",
  confidence_band: "The shaded area shows your natural range—most people's preferences vary slightly.",
  category_boundary: "You're near the boundary between {cat1} and {cat2}.",
  crossing_band: "Your responses suggest flexibility between {cat1} and {cat2}."
};
```

#### Task 2: Category Description Card

**Content:**

```typescript
const CATEGORY_CONTENT = {
  'very-conservative': {
    title: 'Very Conservative',
    icon: 'shield',
    summary: "You prioritize protecting your money over growing it.",
    characteristics: [
      "Prefer guaranteed returns",
      "Uncomfortable with market swings",
      "Focus on capital preservation"
    ],
    typical_allocation: "80-100% bonds, 0-20% stocks"
  },
  'conservative': {
    title: 'Conservative',
    icon: 'lock',
    summary: "You accept modest risk for steady growth.",
    characteristics: [
      "Some tolerance for fluctuation",
      "Value consistent income",
      "Prefer slower, steadier growth"
    ],
    typical_allocation: "60-80% bonds, 20-40% stocks"
  },
  'moderate': {
    title: 'Moderate',
    icon: 'balance-scale',
    summary: "You balance growth and stability.",
    characteristics: [
      "Accept ups and downs",
      "Long-term focused",
      "Diversification-minded"
    ],
    typical_allocation: "40-60% bonds, 40-60% stocks"
  },
  'aggressive': {
    title: 'Aggressive',
    icon: 'trending-up',
    summary: "You pursue growth and tolerate volatility.",
    characteristics: [
      "Comfortable with large swings",
      "Very long time horizon",
      "Growth over income"
    ],
    typical_allocation: "20-40% bonds, 60-80% stocks"
  },
  'very-aggressive': {
    title: 'Very Aggressive',
    icon: 'rocket',
    summary: "You seek maximum growth with high risk tolerance.",
    characteristics: [
      "Embrace volatility",
      "Longest time horizon",
      "Concentrated positions acceptable"
    ],
    typical_allocation: "0-20% bonds, 80-100% stocks"
  }
};
```

#### Task 3: Two-Dimensional Risk Map

**Objective:** Show MPT vs Prospect score relationship.

**Quadrant Definitions:**

| Position | Label | Explanation |
|----------|-------|-------------|
| High MPT, High Prospect | "Fully Risk-Seeking" | Comfortable with risk analytically and emotionally |
| Low MPT, High Prospect | "Emotionally Bold" | May take risks impulsively |
| High MPT, Low Prospect | "Analytically Bold" | Understands risk but feels uncomfortable |
| Low MPT, Low Prospect | "Fully Risk-Averse" | Prefers safety on all dimensions |

**Special Case:** Under-19 users have no MPT score. Show message: "Complete full assessment at 19+ for this breakdown."

#### Task 4: Confirmation Flows

**For `extreme_profile_confirmation`:**

```typescript
const ExtremeProfileModal = {
  title: "Please Confirm Your Profile",
  body: "Your responses indicate a Very {category} approach. This is less common.",
  options: [
    { label: "Yes, this reflects my preferences", action: 'confirm' },
    { label: "I'd like to review my answers", action: 'review' }
  ]
};
```

**For `loss_sensitivity_warning`:** Inline alert, not modal.

**For `response_pattern_warning`:** Inline prompt with review option.

**For `high_uncertainty`:** Explanatory text with both adjacent categories mentioned.

#### Task 5: Temporal Anchoring Prompt

**Display before first scored question:**

```typescript
const TemporalPrompt = {
  title: "Before You Begin",
  body: `Think about your goals over the next 5-10 years, not just today.
         Markets have ups and downs. Consider how you'd feel in both scenarios.
         Answer based on your typical preferences, not recent news.`,
  cta: "I understand, let's begin"
};
```

#### Task 6: Question Display Updates

- Support `reversed: boolean` flag (display identical, scoring handled by Agent 1)
- Support dynamic question loading for adaptive branching
- Show progress as "Question X of ~12" (approximate for adaptive)
- Special framing for counterfactual question (PT-13)

---

### Expected Outputs

**End of Day 2:**
- All visualization components complete
- All tooltip content implemented
- Confirmation flows working
- Question display supporting reverse-coded and dynamic loading
- Component tests passing
- Mobile responsive

### Success Metrics

| Metric | Target |
|--------|--------|
| Visualizations render correctly | All browsers + mobile |
| User comprehension | >85% interpret correctly |
| Completion rate | No decrease |
| Accessibility | WCAG 2.1 AA |
| Confidence band understood | >80% |

---

## Agent 3: Question Content Agent

### Identity and Role

You are the **Question Content Agent** responsible for all questionnaire content including question text, answer options, scoring metadata, and gamified scenarios.

### Responsibilities

1. Question text revisions for economic validity
2. Reverse-coded question creation
3. Counterfactual question creation
4. Gamified scenario improvements
5. Question metadata (construct mappings)
6. Screening consistency logic

### Primary Files/Modules

```
questions/mpt-questions.ts       - MPT question pool
questions/prospect-questions.ts  - Prospect question pool
questions/gamified-scenarios.ts  - Under-19 storyline
questions/screening-questions.ts - Routing questions
questions/metadata.ts            - Construct mappings
questions/reverse-coded.ts       - NEW: Reverse versions
```

### Dependencies

**No blocking dependencies. Start: Day 1 Afternoon.**

---

### Day 1 Tasks (Afternoon)

#### Task 1: Question Revisions

**Questions to Revise:**

| ID | Issue | Revision |
|----|-------|----------|
| M9 | "As many as possible" meaningless | "How would you prefer to spread investments?" 1="Concentrated in 1-2" → 5="Spread across 10+" |
| M13 | Conflates trading with risk | **Remove from scoring** (keep as preference) |
| M14 | Tax unrelated to risk | **Remove from scoring** |
| M15 | ESG unrelated to risk | **Remove from scoring** |
| PT-5 | No risk context | Add: "(Note: these have different risk levels)" with descriptions |
| PT-9 | Self-report unreliable | Rephrase as behavioral: "After researching, how would you act?" |

**Scoring Exclusions:**

```typescript
const SCORING_EXCLUSIONS = ['M13', 'M14', 'M15'];
// Updated MPT max = 12 × 5 = 60 (was 75)
```

#### Task 2: Reverse-Coded Questions

**Create these reverse versions:**

| Original | Reverse-Coded |
|----------|---------------|
| **M3:** "How much volatility can you tolerate?" (1=low, 5=high) | **M3-R:** "How important is stability in your investments?" (1=not, 5=very) |
| **M8:** "Reaction to market downturns?" (1=sell, 5=opportunity) | **M8-R:** "How concerned do you become when markets drop?" (1=not, 5=very) |
| **PT-2:** "Guaranteed loss vs gamble?" (1=guaranteed, 4=gamble) | **PT-2-R:** "How important to avoid larger losses even if accepting smaller certain loss?" (1=not, 4=very) |

**Metadata Format:**

```typescript
interface ReversedQuestion {
  id: string;          // 'M3-R'
  original_id: string; // 'M3'
  reversed: true;
  group: 'MPT' | 'PROSPECT';
  maxScore: number;
  construct: string;
}
```

#### Task 3: Counterfactual Question

**New PT-13:**

```typescript
const PT_13 = {
  id: 'PT-13',
  group: 'PROSPECT',
  construct: 'recency_awareness',
  maxScore: 4,
  question: "Imagine: Scenario A—market dropped 30% last month. Scenario B—market gained 30%. How would your answers differ?",
  options: [
    { value: 1, text: "Much more conservative after a drop" },
    { value: 2, text: "Somewhat more conservative after a drop" },
    { value: 3, text: "Wouldn't change much either way" },
    { value: 4, text: "More aggressive after a drop (buying opportunity)" }
  ]
};
```

#### Task 4: Gamified Scenario Improvements

**Story-1 Revision:**

```typescript
{
  id: 'story-1',
  scenario: "You received $1,000—maybe a gift or from work. You won't need it for 3 years. What do you do?",
  options: [
    { value: 1, text: "Savings account", consequence: "Safe, grows slowly" },
    { value: 2, text: "Save most, invest a little", consequence: "Mostly safe with learning" },
    { value: 3, text: "Invest most in diversified fund", consequence: "Could grow, will fluctuate" },
    { value: 4, text: "High growth potential investment", consequence: "Could grow a lot or lose" }
  ]
}
```

**Story-3 Revision (Major):**

```typescript
{
  id: 'story-3',
  scenario: "You saved $2,000 for something in 2 years. Keep safe for exactly $2,000, or invest for chance of more (or less)?",
  options: [
    { value: 1, text: "Keep completely safe—need every dollar" },
    { value: 2, text: "Keep most safe, invest small portion" },
    { value: 3, text: "Invest about half" },
    { value: 4, text: "Invest most—can adjust timeline if needed" }
  ]
}
```

**Story-5 Revision:**

```typescript
{
  id: 'story-5',
  scenario: "A friend asks what YOU would do with $500 based on your experience.",
  options: [
    { value: 1, text: "Keep it safe—protecting money is most important" },
    { value: 2, text: "Save most, maybe invest tiny bit to learn" },
    { value: 3, text: "Invest good portion, accept some ups and downs" },
    { value: 4, text: "Look for growth—have to take some risk" }
  ]
}
```

#### Task 5: Construct Metadata

```typescript
const CONSTRUCT_MAPPINGS = {
  // MPT
  'M1': { construct: 'time_horizon', category: 'mpt' },
  'M2': { construct: 'time_horizon', category: 'mpt' },
  'M3': { construct: 'volatility_tolerance', category: 'mpt' },
  'M4': { construct: 'capital_allocation', category: 'mpt' },
  'M5': { construct: 'income_requirement', category: 'mpt' },
  'M6': { construct: 'capital_preservation', category: 'mpt' },
  'M7': { construct: 'return_utilization', category: 'mpt' },
  'M8': { construct: 'market_reaction', category: 'mpt' },
  'M9': { construct: 'diversification', category: 'mpt' },
  'M10': { construct: 'liquidity', category: 'mpt' },
  'M11': { construct: 'concentration_risk', category: 'mpt' },
  'M12': { construct: 'recovery_tolerance', category: 'mpt' },
  
  // Prospect
  'PT-1': { construct: 'certainty_effect', category: 'prospect' },
  'PT-2': { construct: 'loss_aversion', category: 'prospect' },
  'PT-3': { construct: 'regret_aversion', category: 'prospect' },
  'PT-4': { construct: 'probability_weighting', category: 'prospect' },
  'PT-5': { construct: 'sector_preference', category: 'prospect' },
  'PT-6': { construct: 'drawdown_behavior', category: 'prospect' },
  'PT-7': { construct: 'anchoring_bias', category: 'prospect' },
  'PT-8': { construct: 'disposition_effect', category: 'prospect' },
  'PT-9': { construct: 'overconfidence', category: 'prospect' },
  'PT-10': { construct: 'herd_behavior', category: 'prospect' },
  'PT-11': { construct: 'representativeness', category: 'prospect' },
  'PT-12': { construct: 'endowment_effect', category: 'prospect' },
  'PT-13': { construct: 'recency_awareness', category: 'prospect' },
  
  // Reverse-coded
  'M3-R': { construct: 'volatility_tolerance', category: 'mpt', reversed: true, original: 'M3' },
  'M8-R': { construct: 'market_reaction', category: 'mpt', reversed: true, original: 'M8' },
  'PT-2-R': { construct: 'loss_aversion', category: 'prospect', reversed: true, original: 'PT-2' },
  
  // Gamified
  'story-1': { construct: 'risk_allocation', category: 'prospect' },
  'story-2': { construct: 'drawdown_behavior', category: 'prospect' },
  'story-3': { construct: 'goal_risk_tradeoff', category: 'prospect' },
  'story-4': { construct: 'concentration_risk', category: 'prospect' },
  'story-5': { construct: 'risk_identity', category: 'prospect' }
};

const RADAR_CONSTRUCTS = [
  'time_horizon',
  'volatility_tolerance',
  'loss_aversion',
  'market_reaction',
  'capital_allocation',
  'probability_weighting'
];
```

#### Task 6: Screening Consistency

**Contradiction Detection:**

```typescript
const SCREENING_CONTRADICTION = {
  trigger: {
    experience: ['6-10', '10+'],
    knowledge: 'beginner'
  },
  prompt: {
    message: "You indicated significant experience but beginner knowledge. Which better describes you?",
    options: [
      { label: "I have experience but consider myself a beginner", action: 'keep' },
      { label: "I know more than a beginner", action: 'revise' }
    ]
  }
};
```

---

### Expected Outputs

**End of Day 1:**
- Updated `mpt-questions.ts` with revisions and exclusion flags
- Updated `prospect-questions.ts` with PT-13
- New `reverse-coded.ts` with M3-R, M8-R, PT-2-R
- Updated `gamified-scenarios.ts`
- Complete `metadata.ts` with construct mappings
- Screening contradiction config
- Documentation of changes

### Success Metrics

| Metric | Target |
|--------|--------|
| All revisions reviewed | 100% |
| Construct coverage complete | All 6 radar constructs have 2+ questions |
| Question metadata accurate | 100% |
| Gamified completion rate | No decrease |

---

## Coordination Checklist

### End of Day 1

**Agent 1 Sprint 1:**
- [x] `confidence-calculator.ts` complete with tests
- [x] `safeguards.ts` complete with override rules
- [x] `consistency-detector.ts` complete
- [x] `monitoring.ts` complete
- [x] API interface documented for Agent 2

**Agent 3:**
- [x] All question revisions complete
- [x] Reverse-coded questions created (M3-R, M8-R, PT-2-R)
- [x] Counterfactual question (PT-13) created
- [x] Gamified scenarios updated
- [x] Complete construct metadata
- [x] Screening contradiction logic defined

**Handoffs Complete:**
- [x] Agent 3 → Agent 1: Question metadata delivered
- [x] Agent 1 → Agent 2: Confidence band API spec delivered

### End of Day 2

**Agent 1 Sprint 2:**
- [ ] Adaptive branching state machine complete
- [ ] Question selector with branching integration
- [ ] Consistency check using reverse-coded questions
- [ ] Integration tests passing

**Agent 2:**
- [ ] Risk Spectrum visualization complete
- [ ] Category Card complete
- [ ] 2D Risk Map complete
- [ ] Confirmation flows complete
- [ ] Question display with dynamic loading
- [ ] Temporal anchoring prompt
- [ ] All tooltips implemented
- [ ] Mobile responsive

**Final Integration:**
- [ ] Full flow test: screening → questions → scoring → visualization
- [ ] Safeguard flags trigger correctly
- [ ] Extreme profiles show confirmation
- [ ] All success metrics verified

---

## Cursor Operating Guidelines

### How to Use This Document

Each Cursor agent (chat session) should:

1. **Identify which agent you are** at the start of your session
2. **Check the timeline** to confirm it's your turn to work
3. **Review dependencies** before starting
4. **Follow your specific task list** in order
5. **Produce the expected outputs** listed for your day
6. **Update the coordination checklist** as you complete items

### Agent Startup Protocol

When starting a new Cursor chat for an agent:

```
1. State: "I am Agent [1/2/3] - [Core Logic/Experience/Question Content] Agent"
2. State: "Today is Day [1/2], [Morning/Afternoon]"
3. List: "My tasks for this session are: [list from document]"
4. Check: "My dependencies are: [list] - Status: [ready/waiting]"
5. Begin work on first task
```

### Execution Rules

1. **Agent 3 starts first** (Day 1 Afternoon) - no dependencies
2. **Agent 1 Sprint 1 can run parallel** with Agent 3 (Day 1)
3. **Agent 1 Sprint 2 waits** for Agent 3 metadata (Day 2 Morning)
4. **Agent 2 waits** for both Agent 1 Sprint 1 AND Agent 3 (Day 2 Afternoon)

### Communication Protocol

Agents communicate through **file outputs**, not direct messaging:

- Agent 1 outputs API interfaces in documentation files
- Agent 3 outputs question files and metadata
- Agent 2 consumes both when building UI

### Quality Gates

Before marking a task complete:

1. Code compiles without errors
2. Unit tests pass (where applicable)
3. Output matches the interface specified in this document
4. No blocking issues for downstream agents

### Handling Blockers

If blocked:

1. Document the blocker clearly
2. Note which dependency is missing
3. Work on non-blocked tasks if possible
4. Flag for human intervention if critical

### File Naming Convention

```
[module-name].ts          - Implementation
[module-name].test.ts     - Tests
[module-name].types.ts    - Type definitions (if separate)
```

### Progress Tracking

Each agent should maintain awareness of:

- Tasks completed (checked in this document)
- Current task in progress
- Remaining tasks
- Any blockers or issues

### End of Session Protocol

Before ending a Cursor session:

```
1. List completed tasks
2. List remaining tasks
3. Note any blockers or issues
4. Confirm outputs are in correct locations
5. Update checklist status
```

---

## Quick Reference Cards

### Agent 1 Quick Reference

```
ROLE: Core Logic Agent
FILES: scoring-engine, risk-classifier, question-selector, 
       confidence-calculator, safeguards, consistency-detector, monitoring
DAY 1 AM: Confidence bands, Safeguards, Consistency, Monitoring
DAY 2 AM: Adaptive branching, Question selector
OUTPUTS TO: Agent 2 (API interfaces)
INPUTS FROM: Agent 3 (question metadata)
```

### Agent 2 Quick Reference

```
ROLE: Experience Agent
FILES: RiskSpectrum, CategoryCard, TwoDimensionalMap, ConfidenceBand,
       ConfirmationModal, FlagAlerts, QuestionDisplay, tooltips
DAY 2 PM: All visualizations and UI components
OUTPUTS TO: End users
INPUTS FROM: Agent 1 (confidence API), Agent 3 (questions)
```

### Agent 3 Quick Reference

```
ROLE: Question Content Agent
FILES: mpt-questions, prospect-questions, gamified-scenarios,
       screening-questions, metadata, reverse-coded
DAY 1 PM: All question content and metadata
OUTPUTS TO: Agent 1 (metadata), Agent 2 (content)
INPUTS FROM: None (first to start)
```

---

*Document Version: 1.0*  
*Last Updated: Today*  
*Project: Risk Profiling System Strengthening*
