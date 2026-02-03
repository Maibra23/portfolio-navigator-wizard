/**
 * Question pool definitions for adaptive branching.
 * Phase 1: Anchor questions. Phase 2: Adaptive refinement. Phase 3: Consistency & coverage.
 */

import { CONSTRUCT_MAPPINGS } from './metadata';

// ============ Phase 1: Anchor (always asked first) ============
// M2: Time Horizon | M3: Volatility Tolerance | PT-2: Loss Aversion | PT-6: Drawdown Behavior
export const ANCHOR_QUESTIONS: readonly string[] = ['M2', 'M3', 'PT-2', 'PT-6'];

// ============ Phase 2: Adaptive refinement ============
// For users with phase1_score < 30 - conservative path
export const CONSERVATIVE_CONFIRMING: readonly string[] = ['M5', 'M8', 'PT-1', 'PT-4'];

// For users with phase1_score > 70 - aggressive path
export const AGGRESSIVE_CONFIRMING: readonly string[] = ['M4', 'M11', 'PT-8', 'PT-10'];

// For users with phase1_score 30–70 - moderate path
export const DISCRIMINATING: readonly string[] = ['M6', 'M10', 'PT-3', 'PT-7'];

// ============ Phase 3: Consistency pairs (original → reverse) ============
export const CONSISTENCY_PAIRS: Readonly<Record<string, string>> = {
  'M3': 'M3-R',
  'PT-2': 'PT-2-R'
};

// ============ Required constructs (must be covered for full assessment) ============
export const REQUIRED_CONSTRUCTS: readonly string[] = [
  'time_horizon',
  'volatility_tolerance',
  'loss_aversion',
  'market_reaction',
  'capital_allocation',
  'probability_weighting'
];

// ============ Combined QUESTION_POOLS object ============
export const QUESTION_POOLS = {
  ANCHOR: ANCHOR_QUESTIONS,
  CONSERVATIVE_CONFIRMING,
  AGGRESSIVE_CONFIRMING,
  DISCRIMINATING,
  CONSISTENCY_PAIRS
} as const;

// ============ Coverage validation (uses CONSTRUCT_MAPPINGS) ============

/**
 * Returns the set of required constructs covered by the given question IDs.
 */
export function getConstructsCoveredByQuestions(questionIds: string[]): Set<string> {
  const covered = new Set<string>();
  for (const id of questionIds) {
    const mapping = CONSTRUCT_MAPPINGS[id];
    if (mapping) covered.add(mapping.construct);
  }
  return covered;
}

/**
 * Returns required constructs not yet covered by the given question IDs.
 */
export function getMissingRequiredConstructs(questionIds: string[]): string[] {
  const covered = getConstructsCoveredByQuestions(questionIds);
  return REQUIRED_CONSTRUCTS.filter((c) => !covered.has(c));
}

/**
 * Returns true if the given question IDs cover all REQUIRED_CONSTRUCTS.
 */
export function hasRequiredConstructCoverage(questionIds: string[]): boolean {
  return getMissingRequiredConstructs(questionIds).length === 0;
}
