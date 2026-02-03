/**
 * Adaptive branching state machine.
 * Phase 1: 4 anchor questions → phase1_score → path. Phase 2: 4 adaptive. Phase 3: 4 (gaps + PT-13 + consistency).
 */

import { CONSTRUCT_MAPPINGS, getQuestionsForConstruct } from './metadata';
import {
  ANCHOR_QUESTIONS,
  QUESTION_POOLS,
  REQUIRED_CONSTRUCTS,
  CONSISTENCY_PAIRS
} from './question-pools';

// ============ Types ============

export interface BranchingState {
  current_phase: 1 | 2 | 3;
  questions_asked: string[];
  answers: Map<string, { value: number; timeSeconds: number }>;
  phase1_score: number | null;
  selected_path: 'conservative' | 'aggressive' | 'moderate' | null;
  constructs_covered: Set<string>;
}

export type PathKind = 'conservative' | 'aggressive' | 'moderate';

// Anchor max scores: M2, M3 = 5; PT-2, PT-6 = 4
const ANCHOR_MAX_SCORES: Record<string, number> = {
  'M2': 5,
  'M3': 5,
  'PT-2': 4,
  'PT-6': 4
};

// ============ Helpers ============

/**
 * Normalized contribution for one answer: (value - 1) / (maxScore - 1), then * 100 for 0-100 scale.
 */
function normalizedContribution(value: number, maxScore: number): number {
  if (maxScore <= 1) return 0;
  return ((value - 1) / (maxScore - 1)) * 100;
}

/**
 * Phase 1 score = average of normalized contributions (0-100) for anchor questions.
 */
export function calculatePhase1Score(
  answers: Map<string, { value: number }>,
  anchorQuestionIds: readonly string[],
  maxScoresByQuestion?: Record<string, number>
): number {
  const maxScores = maxScoresByQuestion ?? ANCHOR_MAX_SCORES;
  let sum = 0;
  let count = 0;
  for (const id of anchorQuestionIds) {
    const entry = answers.get(id);
    const maxScore = maxScores[id] ?? 5;
    if (entry != null) {
      sum += normalizedContribution(entry.value, maxScore);
      count += 1;
    }
  }
  return count === 0 ? 0 : sum / count;
}

/**
 * Returns the Phase 2 pool for the given phase1 score.
 */
export function selectPathPool(phase1Score: number): string[] {
  if (phase1Score < 30) return [...QUESTION_POOLS.CONSERVATIVE_CONFIRMING];
  if (phase1Score > 70) return [...QUESTION_POOLS.AGGRESSIVE_CONFIRMING];
  return [...QUESTION_POOLS.DISCRIMINATING];
}

/**
 * Returns the path label for the given phase1 score.
 */
export function selectPath(phase1Score: number): PathKind {
  if (phase1Score < 30) return 'conservative';
  if (phase1Score > 70) return 'aggressive';
  return 'moderate';
}

/**
 * Returns the set of constructs covered by the given question IDs.
 */
export function getConstructsFromQuestions(questionIds: string[]): Set<string> {
  const set = new Set<string>();
  for (const id of questionIds) {
    const m = CONSTRUCT_MAPPINGS[id];
    if (m) set.add(m.construct);
  }
  return set;
}

/**
 * Returns required constructs not yet in the covered set.
 */
export function findMissingConstructs(
  covered: Set<string>,
  required: readonly string[]
): string[] {
  return required.filter((c) => !covered.has(c));
}

/**
 * Returns construct coverage analysis for given questions.
 */
export function checkConstructCoverage(
  questionsAsked: string[],
  constructMappings: Record<string, { construct: string }>
): {
  covered: Set<string>;
  missing: string[];
  coveragePercent: number;
} {
  const covered = new Set<string>();
  questionsAsked.forEach(qId => {
    const mapping = constructMappings[qId];
    if (mapping) covered.add(mapping.construct);
  });

  const missing = REQUIRED_CONSTRUCTS.filter(c => !covered.has(c));
  const coveragePercent = ((REQUIRED_CONSTRUCTS.length - missing.length) / REQUIRED_CONSTRUCTS.length) * 100;

  return { covered, missing, coveragePercent };
}

/**
 * Returns the best question ID that measures the given construct and is not yet asked, or null.
 * Prefers non-reverse-coded questions over reverse-coded ones.
 */
export function findQuestionForConstruct(
  construct: string,
  questionsAsked: string[],
  constructMappings: Record<string, { construct: string; reversed?: boolean }>
): string | null {
  const candidates = getQuestionsForConstruct(construct);
  const askedSet = new Set(questionsAsked);

  // First, try to find a non-reverse-coded question
  for (const id of candidates) {
    if (!askedSet.has(id) && !constructMappings[id]?.reversed) return id;
  }

  // If no non-reverse-coded available, try reverse-coded
  for (const id of candidates) {
    if (!askedSet.has(id)) return id;
  }

  return null;
}

/**
 * Returns a consistency-check question (reverse-coded) not yet asked, or null.
 */
function selectConsistencyQuestion(state: BranchingState): string | null {
  const asked = new Set(state.questions_asked);
  for (const [original, reverse] of Object.entries(CONSISTENCY_PAIRS)) {
    if (asked.has(original) && !asked.has(reverse)) return reverse;
  }
  return null;
}

// ============ State machine ============

export const PHASE1_SIZE = 4;
export const PHASE2_SIZE = 4;
export const PHASE3_SIZE = 4;
export const TOTAL_ADAPTIVE_QUESTIONS = 12;

/**
 * Creates initial branching state.
 */
export function createInitialState(): BranchingState {
  return {
    current_phase: 1,
    questions_asked: [],
    answers: new Map(),
    phase1_score: null,
    selected_path: null,
    constructs_covered: new Set()
  };
}

/**
 * Returns the next question ID to ask, or null if phase complete / assessment complete.
 */
export function getNextQuestion(
  state: BranchingState,
  maxScoresByQuestion?: Record<string, number>
): string | null {
  if (state.current_phase === 1) {
    const remaining = ANCHOR_QUESTIONS.filter((q) => !state.questions_asked.includes(q));
    return remaining[0] ?? null;
  }

  if (state.current_phase === 2) {
    const pool =
      state.selected_path === 'conservative'
        ? QUESTION_POOLS.CONSERVATIVE_CONFIRMING
        : state.selected_path === 'aggressive'
          ? QUESTION_POOLS.AGGRESSIVE_CONFIRMING
          : QUESTION_POOLS.DISCRIMINATING;
    const remaining = pool.filter((q) => !state.questions_asked.includes(q));
    return remaining[0] ?? null;
  }

  if (state.current_phase === 3) {
    const missing = findMissingConstructs(state.constructs_covered, REQUIRED_CONSTRUCTS);
    if (missing.length > 0) {
      const q = findQuestionForConstruct(missing[0], state.questions_asked, CONSTRUCT_MAPPINGS);
      if (q) return q;
      // Log warning if coverage cannot be achieved (should not happen in well-designed pools)
      console.warn(`Cannot find question for required construct: ${missing[0]}`);
    }
    if (!state.questions_asked.includes('PT-13')) return 'PT-13';
    const consistencyQ = selectConsistencyQuestion(state);
    if (consistencyQ) return consistencyQ;
    return null;
  }

  return null;
}

/**
 * Submits an answer and advances state. Returns updated state (caller should replace state).
 */
export function submitAnswer(
  state: BranchingState,
  questionId: string,
  value: number,
  timeSeconds: number,
  maxScoresByQuestion?: Record<string, number>
): BranchingState {
  const answers = new Map(state.answers);
  answers.set(questionId, { value, timeSeconds });

  const questions_asked = [...state.questions_asked, questionId];
  const constructs_covered = new Set(state.constructs_covered);
  const mapping = CONSTRUCT_MAPPINGS[questionId];
  if (mapping) constructs_covered.add(mapping.construct);

  let current_phase = state.current_phase;
  let phase1_score = state.phase1_score;
  let selected_path = state.selected_path;

  if (state.current_phase === 1 && questions_asked.length === PHASE1_SIZE) {
    const maxScores = maxScoresByQuestion ?? ANCHOR_MAX_SCORES;
    phase1_score = calculatePhase1Score(answers, ANCHOR_QUESTIONS, maxScores);
    selected_path = selectPath(phase1_score);
    current_phase = 2;
  } else if (state.current_phase === 2 && questions_asked.length === PHASE1_SIZE + PHASE2_SIZE) {
    current_phase = 3;
  }

  return {
    current_phase,
    questions_asked,
    answers,
    phase1_score,
    selected_path,
    constructs_covered
  };
}

/**
 * Returns true when all 12 adaptive questions have been asked (including PT-13 and one consistency question).
 */
export function isBranchingComplete(state: BranchingState): boolean {
  return state.questions_asked.length >= TOTAL_ADAPTIVE_QUESTIONS;
}
