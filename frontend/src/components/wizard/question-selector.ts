/**
 * Question selection state machine.
 * Under-19: gamified path (5 scenarios). Above-19: adaptive branching (12 questions).
 */

import { CONSTRUCT_MAPPINGS, getQuestionsForConstruct } from './metadata';
import {
  ANCHOR_QUESTIONS,
  QUESTION_POOLS,
  REQUIRED_CONSTRUCTS,
  CONSISTENCY_PAIRS
} from './question-pools';
import {
  type BranchingState,
  createInitialState,
  submitAnswer as submitAnswerToBranching,
  isBranchingComplete,
  TOTAL_ADAPTIVE_QUESTIONS
} from './adaptive-branching';

// ============ Types ============

export interface Question {
  id: string;
  group: 'MPT' | 'PROSPECT';
  maxScore: number;
  construct: string;
  question?: string;
  options?: Array<{ value: number; text: string }>;
}

export interface QuestionSelector {
  initialize(userProfile: { ageGroup: string; experiencePoints: number }): void;
  getNextQuestion(): Question | null;
  submitAnswer(questionId: string, answer: number, timeSeconds: number): void;
  isComplete(): boolean;
  getSelectedQuestions(): Question[];
  getBranchingPath(): string;
  getState(): BranchingState | null;
}

// Gamified path: 5 scenarios, fixed order
const GAMIFIED_QUESTION_IDS: readonly string[] = ['story-1', 'story-2', 'story-3', 'story-4', 'story-5'];
const GAMIFIED_QUESTION_COUNT = 5;

// Max score per question ID (for building minimal Question from id)
const DEFAULT_MAX_SCORES: Record<string, number> = {
  'M1': 5, 'M2': 5, 'M3': 5, 'M4': 5, 'M5': 5, 'M6': 5, 'M7': 5, 'M8': 5, 'M9': 5,
  'M10': 5, 'M11': 5, 'M12': 5,
  'M3-R': 5, 'M8-R': 5,
  'PT-1': 4, 'PT-2': 4, 'PT-3': 4, 'PT-4': 4, 'PT-5': 4, 'PT-6': 4, 'PT-7': 4, 'PT-8': 5,
  'PT-9': 4, 'PT-10': 4, 'PT-11': 4, 'PT-12': 4, 'PT-13': 4,
  'PT-2-R': 4,
  'story-1': 4, 'story-2': 4, 'story-3': 4, 'story-4': 4, 'story-5': 4
};

function buildQuestion(id: string): Question {
  const mapping = CONSTRUCT_MAPPINGS[id];
  const group = mapping?.category === 'mpt' ? 'MPT' : 'PROSPECT';
  const construct = mapping?.construct ?? 'unknown';
  const maxScore = DEFAULT_MAX_SCORES[id] ?? 5;
  return { id, group, maxScore, construct };
}

function findQuestionForConstruct(construct: string, questionsAsked: string[]): string | null {
  const candidates = getQuestionsForConstruct(construct);
  const askedSet = new Set(questionsAsked);
  for (const id of candidates) {
    if (!askedSet.has(id)) return id;
  }
  return null;
}

function selectConsistencyQuestion(questionsAsked: string[]): string | null {
  const asked = new Set(questionsAsked);
  for (const [original, reverse] of Object.entries(CONSISTENCY_PAIRS)) {
    if (asked.has(original) && !asked.has(reverse)) return reverse;
  }
  return null;
}

// ============ QuestionSelector class ============

export class QuestionSelectorImpl implements QuestionSelector {
  private ageGroup: string = 'above-19';
  private experiencePoints: number = 0;
  private branchingState: BranchingState | null = null;
  private gamifiedAsked: string[] = [];

  initialize(userProfile: { ageGroup: string; experiencePoints: number }): void {
    this.ageGroup = userProfile.ageGroup;
    this.experiencePoints = userProfile.experiencePoints;
    if (userProfile.ageGroup === 'under-19') {
      this.branchingState = null;
      this.gamifiedAsked = [];
    } else {
      this.branchingState = createInitialState();
      this.gamifiedAsked = [];
    }
  }

  getNextQuestion(): Question | null {
    if (this.isComplete()) return null;

    if (this.ageGroup === 'under-19') {
      const remaining = GAMIFIED_QUESTION_IDS.filter((id) => !this.gamifiedAsked.includes(id));
      const nextId = remaining[0] ?? null;
      return nextId ? buildQuestion(nextId) : null;
    }

    const state = this.branchingState;
    if (!state) return null;

    // Phase 1: anchor
    if (state.current_phase === 1) {
      const remaining = ANCHOR_QUESTIONS.filter((q) => !state.questions_asked.includes(q));
      const nextId = remaining[0] ?? null;
      return nextId ? buildQuestion(nextId) : null;
    }

    // Phase 2: path pool
    if (state.current_phase === 2) {
      const pool =
        state.selected_path === 'conservative'
          ? QUESTION_POOLS.CONSERVATIVE_CONFIRMING
          : state.selected_path === 'aggressive'
            ? QUESTION_POOLS.AGGRESSIVE_CONFIRMING
            : QUESTION_POOLS.DISCRIMINATING;
      const remaining = pool.filter((q) => !state.questions_asked.includes(q));
      const nextId = remaining[0] ?? null;
      return nextId ? buildQuestion(nextId) : null;
    }

    // Phase 3: gaps, then PT-13, then consistency
    if (state.current_phase === 3) {
      const missing = REQUIRED_CONSTRUCTS.filter((c) => !state.constructs_covered.has(c));
      if (missing.length > 0) {
        const nextId = findQuestionForConstruct(missing[0], state.questions_asked);
        if (nextId) return buildQuestion(nextId);
      }
      if (!state.questions_asked.includes('PT-13')) return buildQuestion('PT-13');
      const consistencyId = selectConsistencyQuestion(state.questions_asked);
      if (consistencyId) return buildQuestion(consistencyId);
      return null;
    }

    return null;
  }

  submitAnswer(questionId: string, answer: number, timeSeconds: number): void {
    if (this.ageGroup === 'under-19') {
      this.gamifiedAsked.push(questionId);
      return;
    }

    const state = this.branchingState;
    if (!state) return;

    this.branchingState = submitAnswerToBranching(state, questionId, answer, timeSeconds);
  }

  isComplete(): boolean {
    if (this.ageGroup === 'under-19') {
      return this.gamifiedAsked.length >= GAMIFIED_QUESTION_COUNT;
    }
    const state = this.branchingState;
    if (!state) return false;
    return isBranchingComplete(state);
  }

  getSelectedQuestions(): Question[] {
    if (this.ageGroup === 'under-19') return this.gamifiedAsked.map(buildQuestion);
    const state = this.branchingState;
    return state ? state.questions_asked.map(buildQuestion) : [];
  }

  getBranchingPath(): string {
    if (this.ageGroup === 'under-19') return 'gamified';
    const state = this.branchingState;
    if (!state || state.selected_path === null) return 'none';
    return state.selected_path;
  }

  getState(): BranchingState | null {
    return this.branchingState;
  }
}

export function createQuestionSelector(): QuestionSelector {
  return new QuestionSelectorImpl();
}
