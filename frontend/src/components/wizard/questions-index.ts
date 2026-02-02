/**
 * Unified entry point for Agent 3 question content and metadata.
 * Agent 1 Sprint 2 and Agent 2 can import from this file.
 * 
 * === AGENT 3 DAY 1 OUTPUTS ===
 * 
 * Task 1 - Question Revisions:
 *   - M9: Revised to "How would you prefer to spread your investments?"
 *   - PT-5: Added risk context note and descriptions for each sector
 *   - PT-9: Rephrased as behavioral "After researching an investment..."
 *   - M13, M14, M15: Marked with excludeFromScoring: true (preferences only)
 * 
 * Task 2 - Reverse-Coded Questions:
 *   - M3-R (reverse of M3 - volatility_tolerance)
 *   - M8-R (reverse of M8 - market_reaction)
 *   - PT-2-R (reverse of PT-2 - loss_aversion)
 * 
 * Task 3 - Counterfactual Question:
 *   - PT-13 (construct: recency_awareness)
 * 
 * Task 4 - Gamified Scenario Improvements:
 *   - Story-1, Story-3, Story-5 revised per spec
 * 
 * Task 5 - Construct Metadata:
 *   - CONSTRUCT_MAPPINGS: All 33 question IDs mapped to constructs
 *   - RADAR_CONSTRUCTS: 6 key constructs for visualization
 *   - SCORING_EXCLUSIONS: ['M13', 'M14', 'M15']
 *   - getConstructForQuestion(), getQuestionsForConstruct()
 * 
 * Task 6 - Screening Consistency:
 *   - SCREENING_CONTRADICTION trigger + prompt
 *   - checkScreeningContradiction() helper
 */

// ============ Reverse-Coded Questions ============
export {
  M3_R,
  M8_R,
  PT_2_R,
  REVERSE_CODED_QUESTIONS,
  type ReversedQuestion
} from './reverse-coded';

// ============ Construct Metadata ============
export {
  CONSTRUCT_MAPPINGS,
  RADAR_CONSTRUCTS,
  SCORING_EXCLUSIONS,
  getConstructForQuestion,
  getQuestionsForConstruct,
  type ConstructMapping
} from './metadata';

// ============ Screening Consistency ============
export {
  SCREENING_CONTRADICTION,
  checkScreeningContradiction,
  type ContradictionResult
} from './screening-consistency';

// ============ Scoring Engine (Agent 1 Sprint 1) ============
// Re-export for convenience - Agent 2 may need these
export { computeScoring, type ScoringResult, type RUQuestion } from './scoring-engine';
export type { ConfidenceBand, VisualizationData } from './confidence-calculator';
export type { SafeguardResult } from './safeguards';
export type { ConsistencyResult } from './consistency-detector';
