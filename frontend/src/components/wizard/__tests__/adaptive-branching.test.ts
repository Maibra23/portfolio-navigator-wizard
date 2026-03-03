import { describe, it, expect } from 'vitest';
import {
  createInitialState,
  getNextQuestion,
  submitAnswer,
  isBranchingComplete,
  calculatePhase1Score,
  selectPathPool,
  selectPath,
  getConstructsFromQuestions,
  findMissingConstructs,
  checkConstructCoverage,
  findQuestionForConstruct,
  PHASE1_SIZE,
  TOTAL_ADAPTIVE_QUESTIONS
} from '../adaptive-branching';
import { CONSTRUCT_MAPPINGS } from '../metadata';

describe('adaptive-branching', () => {
  describe('calculatePhase1Score', () => {
    it('returns 0 when no answers', () => {
      expect(calculatePhase1Score(new Map(), ['M2', 'M3', 'PT-2', 'PT-6'])).toBe(0);
    });
    it('returns 100 when all anchor answers at max', () => {
      const answers = new Map([
        ['M2', { value: 5 }],
        ['M3', { value: 5 }],
        ['PT-2', { value: 4 }],
        ['PT-6', { value: 4 }]
      ]);
      expect(calculatePhase1Score(answers, ['M2', 'M3', 'PT-2', 'PT-6'])).toBe(100);
    });
    it('returns 0 when all anchor answers at min', () => {
      const answers = new Map([
        ['M2', { value: 1 }],
        ['M3', { value: 1 }],
        ['PT-2', { value: 1 }],
        ['PT-6', { value: 1 }]
      ]);
      expect(calculatePhase1Score(answers, ['M2', 'M3', 'PT-2', 'PT-6'])).toBe(0);
    });
    it('returns mid-range for mid-scale answers', () => {
      const answers = new Map([
        ['M2', { value: 3 }],
        ['M3', { value: 3 }],
        ['PT-2', { value: 2 }],
        ['PT-6', { value: 2 }]
      ]);
      const score = calculatePhase1Score(answers, ['M2', 'M3', 'PT-2', 'PT-6']);
      expect(score).toBeGreaterThan(35);
      expect(score).toBeLessThan(55);
    });
  });

  describe('selectPathPool / selectPath', () => {
    it('selects conservative for phase1_score < 30', () => {
      expect(selectPath(20)).toBe('conservative');
      expect(selectPathPool(20)).toEqual(['M5', 'M8', 'PT-1', 'PT-4']);
    });
    it('selects aggressive for phase1_score > 70', () => {
      expect(selectPath(80)).toBe('aggressive');
      expect(selectPathPool(80)).toEqual(['M4', 'M11', 'PT-8', 'PT-10']);
    });
    it('selects moderate for 30 <= score <= 70', () => {
      expect(selectPath(30)).toBe('moderate');
      expect(selectPath(70)).toBe('moderate');
      expect(selectPath(50)).toBe('moderate');
      expect(selectPathPool(50)).toEqual(['M6', 'M10', 'PT-3', 'PT-7']);
    });
  });

  describe('getConstructsFromQuestions / findMissingConstructs', () => {
    it('returns constructs for given question IDs', () => {
      const set = getConstructsFromQuestions(['M2', 'M3', 'PT-2']);
      expect(set.has('time_horizon')).toBe(true);
      expect(set.has('volatility_tolerance')).toBe(true);
      expect(set.has('loss_aversion')).toBe(true);
    });
    it('findMissingConstructs returns required not in covered', () => {
      const covered = new Set(['time_horizon', 'volatility_tolerance']);
      const missing = findMissingConstructs(covered, [
        'time_horizon',
        'volatility_tolerance',
        'loss_aversion',
        'market_reaction'
      ]);
      expect(missing).toEqual(['loss_aversion', 'market_reaction']);
    });
  });

  describe('phase transitions', () => {
    it('initial state has phase 1 and first question is M2', () => {
      const state = createInitialState();
      expect(state.current_phase).toBe(1);
      expect(state.phase1_score).toBeNull();
      expect(state.selected_path).toBeNull();
      expect(getNextQuestion(state)).toBe('M2');
    });
    it('after 4 anchor answers, transitions to phase 2 and sets path', () => {
      let state = createInitialState();
      state = submitAnswer(state, 'M2', 1, 10);
      state = submitAnswer(state, 'M3', 1, 8);
      state = submitAnswer(state, 'PT-2', 1, 12);
      state = submitAnswer(state, 'PT-6', 1, 9);
      expect(state.current_phase).toBe(2);
      expect(state.phase1_score).toBe(0);
      expect(state.selected_path).toBe('conservative');
      expect(state.questions_asked).toEqual(['M2', 'M3', 'PT-2', 'PT-6']);
    });
    it('phase1_score > 70 selects aggressive path', () => {
      let state = createInitialState();
      state = submitAnswer(state, 'M2', 5, 10);
      state = submitAnswer(state, 'M3', 5, 8);
      state = submitAnswer(state, 'PT-2', 4, 12);
      state = submitAnswer(state, 'PT-6', 4, 9);
      expect(state.current_phase).toBe(2);
      expect(state.selected_path).toBe('aggressive');
    });
    it('phase 2 next question comes from selected pool', () => {
      let state = createInitialState();
      for (const [q, v] of [['M2', 1], ['M3', 1], ['PT-2', 1], ['PT-6', 1]] as const) {
        state = submitAnswer(state, q, v, 10);
      }
      expect(getNextQuestion(state)).toBe('M5');
    });
    it('after 8 total questions, transitions to phase 3', () => {
      let state = createInitialState();
      const anchors = [['M2', 3], ['M3', 3], ['PT-2', 2], ['PT-6', 2]] as const;
      for (const [q, v] of anchors) state = submitAnswer(state, q, v, 10);
      const phase2 = ['M8', 'M10', 'PT-3', 'PT-8'];
      for (const q of phase2) state = submitAnswer(state, q, 3, 10);
      expect(state.current_phase).toBe(3);
      expect(state.questions_asked.length).toBe(8);
    });
    it('phase 3 can suggest PT-13 or construct-fill or consistency', () => {
      let state = createInitialState();
      const anchors = [['M2', 3], ['M3', 3], ['PT-2', 2], ['PT-6', 2]] as const;
      for (const [q, v] of anchors) state = submitAnswer(state, q, v, 10);
      for (const q of ['M8', 'M10', 'PT-3', 'PT-8']) state = submitAnswer(state, q, 3, 10);
      const next = getNextQuestion(state);
      expect(next).toBeTruthy();
      expect(state.current_phase).toBe(3);
    });
    it('isBranchingComplete is false until 12 questions', () => {
      let state = createInitialState();
      expect(isBranchingComplete(state)).toBe(false);
      for (const [q, v] of [['M2', 3], ['M3', 3], ['PT-2', 2], ['PT-6', 2]] as const) {
        state = submitAnswer(state, q, v, 10);
      }
      for (const q of ['M8', 'M10', 'PT-3', 'PT-8']) state = submitAnswer(state, q, 3, 10);
      expect(state.questions_asked.length).toBe(8);
      expect(isBranchingComplete(state)).toBe(false);
    });
  });

  describe('checkConstructCoverage', () => {
    it('returns coverage for given questions', () => {
      const { covered, missing, coveragePercent } = checkConstructCoverage(
        ['M2', 'M3', 'PT-2'],
        CONSTRUCT_MAPPINGS
      );
      expect(covered.has('time_horizon')).toBe(true);
      expect(covered.has('volatility_tolerance')).toBe(true);
      expect(covered.has('loss_aversion')).toBe(true);
      expect(missing.length).toBe(3); // market_reaction, capital_allocation, probability_weighting
      expect(coveragePercent).toBe(50); // 3 out of 6 constructs
    });

    it('returns 100% coverage when all required constructs are covered', () => {
      const questions = ['M2', 'M3', 'PT-2', 'M8', 'M4', 'PT-4'];
      const { covered, missing, coveragePercent } = checkConstructCoverage(
        questions,
        CONSTRUCT_MAPPINGS
      );
      expect(missing.length).toBe(0);
      expect(coveragePercent).toBe(100);
    });

    it('returns 0% coverage when no questions asked', () => {
      const { covered, missing, coveragePercent } = checkConstructCoverage(
        [],
        CONSTRUCT_MAPPINGS
      );
      expect(covered.size).toBe(0);
      expect(missing.length).toBe(6);
      expect(coveragePercent).toBe(0);
    });
  });

  describe('findQuestionForConstruct', () => {
    it('prefers non-reverse-coded questions over reverse-coded ones', () => {
      const q = findQuestionForConstruct('volatility_tolerance', [], CONSTRUCT_MAPPINGS);
      expect(q).toBe('M3'); // Should prefer M3 over M3-R
    });

    it('returns next non-reverse question when primary is already asked', () => {
      const q = findQuestionForConstruct('volatility_tolerance', ['M3'], CONSTRUCT_MAPPINGS);
      expect(q).toBe('story-5'); // M3 asked; story-5 is next non-reverse for volatility_tolerance
    });

    it('returns null when no questions available for construct', () => {
      const q = findQuestionForConstruct('nonexistent_construct', [], CONSTRUCT_MAPPINGS);
      expect(q).toBeNull();
    });

    it('skips already asked questions', () => {
      const q = findQuestionForConstruct('time_horizon', ['M2'], CONSTRUCT_MAPPINGS);
      expect(q).toBe('M1'); // M2 asked, so return M1
    });
  });

  describe('construct coverage across all branching paths', () => {
    function simulateFullBranchingPath(anchorAnswers: [number, number, number, number]): {
      finalState: any;
      coverage: ReturnType<typeof checkConstructCoverage>;
    } {
      let state = createInitialState();
      const anchors = ['M2', 'M3', 'PT-2', 'PT-6'];
      for (let i = 0; i < 4; i++) {
        state = submitAnswer(state, anchors[i], anchorAnswers[i], 10);
      }

      // Phase 2: 4 questions from selected pool
      for (let i = 0; i < 4; i++) {
        const q = getNextQuestion(state);
        if (!q) break;
        state = submitAnswer(state, q, 3, 10);
      }

      // Phase 3: fill until complete (may need more than 4 questions to reach 12 total)
      while (!isBranchingComplete(state)) {
        const q = getNextQuestion(state);
        if (!q) break;
        state = submitAnswer(state, q, 3, 10);
      }

      const coverage = checkConstructCoverage(state.questions_asked, CONSTRUCT_MAPPINGS);
      return { finalState: state, coverage };
    }

    it('conservative path achieves 100% construct coverage', () => {
      const { finalState, coverage } = simulateFullBranchingPath([1, 1, 1, 1]); // Low scores
      expect(finalState.questions_asked.length).toBe(12);
      expect(coverage.coveragePercent).toBe(100);
      expect(coverage.missing.length).toBe(0);
      expect(finalState.selected_path).toBe('conservative');
    });

    it('moderate path achieves 100% construct coverage', () => {
      const { finalState, coverage } = simulateFullBranchingPath([3, 3, 2, 2]); // Medium scores
      expect(finalState.questions_asked.length).toBe(12);
      expect(coverage.coveragePercent).toBe(100);
      expect(coverage.missing.length).toBe(0);
      expect(finalState.selected_path).toBe('moderate');
    });

    it('aggressive path achieves 100% construct coverage', () => {
      const { finalState, coverage } = simulateFullBranchingPath([5, 5, 4, 4]); // High scores
      expect(finalState.questions_asked.length).toBe(12);
      expect(coverage.coveragePercent).toBe(100);
      expect(coverage.missing.length).toBe(0);
      expect(finalState.selected_path).toBe('aggressive');
    });

    it('edge case: very low scores still achieve coverage', () => {
      const { finalState, coverage } = simulateFullBranchingPath([1, 1, 1, 1]);
      expect(coverage.coveragePercent).toBe(100);
      expect(coverage.missing.length).toBe(0);
    });

    it('edge case: very high scores still achieve coverage', () => {
      const { finalState, coverage } = simulateFullBranchingPath([5, 5, 4, 4]);
      expect(coverage.coveragePercent).toBe(100);
      expect(coverage.missing.length).toBe(0);
    });
  });
});
