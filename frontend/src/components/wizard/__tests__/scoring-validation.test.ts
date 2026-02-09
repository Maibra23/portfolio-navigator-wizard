import { describe, it, expect } from 'vitest';
import { computeScoring } from '../scoring-engine';
import type { RUQuestion } from '../scoring-engine';
import { checkCompletionSpeed } from '../consistency-detector';

function makeQuestions(count: number, maxScore = 5): RUQuestion[] {
  const qs: RUQuestion[] = [];
  for (let i = 0; i < count; i++) {
    qs.push({
      id: `q${i + 1}`,
      group: i % 2 === 0 ? 'MPT' : 'PROSPECT',
      maxScore
    });
  }
  return qs;
}

describe('Scoring validation (plan 13 cases)', () => {
  const fiveQuestions = makeQuestions(5);

  describe('Deterministic risk profiles (5)', () => {
    it('Very Conservative: score in [0, 20)', () => {
      const answers = { q1: 1, q2: 1, q3: 1, q4: 2, q5: 1 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBeGreaterThanOrEqual(0);
      expect(r.normalized_score).toBeLessThan(20);
      expect(r.risk_category).toBe('very-conservative');
    });

    it('Conservative: score in [20, 40)', () => {
      const answers = { q1: 2, q2: 2, q3: 2, q4: 3, q5: 2 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBeGreaterThanOrEqual(20);
      expect(r.normalized_score).toBeLessThan(40);
      expect(r.risk_category).toBe('conservative');
    });

    it('Moderate: score in [40, 60)', () => {
      const answers = { q1: 3, q2: 3, q3: 3, q4: 3, q5: 3 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBeGreaterThanOrEqual(40);
      expect(r.normalized_score).toBeLessThan(60);
      expect(r.risk_category).toBe('moderate');
    });

    it('Aggressive: score in [60, 80)', () => {
      const answers = { q1: 4, q2: 4, q3: 4, q4: 3, q5: 4 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBeGreaterThanOrEqual(60);
      expect(r.normalized_score).toBeLessThan(80);
      expect(r.risk_category).toBe('aggressive');
    });

    it('Very Aggressive: score in [80, 100]', () => {
      const answers = { q1: 5, q2: 5, q3: 5, q4: 4, q5: 5 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBeGreaterThanOrEqual(80);
      expect(r.normalized_score).toBeLessThanOrEqual(100);
      expect(r.risk_category).toBe('very-aggressive');
    });
  });

  describe('Boundary scores (4) – exclusive upper bounds', () => {
    it('Score 20 -> conservative (not very-conservative)', () => {
      const answers = { q1: 2, q2: 2, q3: 2, q4: 2, q5: 1 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBe(20);
      expect(r.risk_category).toBe('conservative');
    });

    it('Score 40 -> moderate', () => {
      const answers = { q1: 3, q2: 3, q3: 3, q4: 2, q5: 2 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBe(40);
      expect(r.risk_category).toBe('moderate');
    });

    it('Score 60 -> aggressive', () => {
      const answers = { q1: 4, q2: 4, q3: 4, q4: 3, q5: 2 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBe(60);
      expect(r.risk_category).toBe('aggressive');
    });

    it('Score 80 -> very-aggressive', () => {
      const answers = { q1: 5, q2: 5, q3: 5, q4: 4, q5: 2 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBe(80);
      expect(r.risk_category).toBe('very-aggressive');
    });
  });

  describe('Edge cases (4)', () => {
    it('Empty answers -> throws', () => {
      const allExcluded = fiveQuestions.map((q) => ({ ...q, excludeFromScoring: true }));
      expect(() =>
        computeScoring({
          selectedQuestions: allExcluded,
          answersMap: {},
          completionTimeSeconds: 60
        })
      ).toThrow('Insufficient data for risk assessment');
    });

    it('Zero variance -> flagged in confidence band', () => {
      const answers = { q1: 3, q2: 3, q3: 3, q4: 3, q5: 3 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.confidence_band.adjustment_reasons).toContain('zero_variance');
    });

    it('High variance -> flagged', () => {
      const answers = { q1: 1, q2: 5, q3: 1, q4: 5, q5: 3 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 10
      });
      expect(r.confidence_band.adjustment_reasons).toContain('variance');
    });

    it('Fast completion -> adaptive threshold (gamified 5 q: 5 sec)', () => {
      expect(checkCompletionSpeed(20, 5)).toBe(true);
      expect(checkCompletionSpeed(25, 5)).toBe(false);
      expect(checkCompletionSpeed(20, 8)).toBe(true);
      expect(checkCompletionSpeed(24, 8)).toBe(false);
    });
  });

  describe('Score bounds', () => {
    it('All scores in [0, 100]', () => {
      const answers = { q1: 1, q2: 2, q3: 3, q4: 4, q5: 5 };
      const r = computeScoring({
        selectedQuestions: fiveQuestions,
        answersMap: answers,
        completionTimeSeconds: 60
      });
      expect(r.normalized_score).toBeGreaterThanOrEqual(0);
      expect(r.normalized_score).toBeLessThanOrEqual(100);
      expect(r.normalized_mpt).toBeGreaterThanOrEqual(0);
      expect(r.normalized_mpt).toBeLessThanOrEqual(100);
      expect(r.normalized_prospect).toBeGreaterThanOrEqual(0);
      expect(r.normalized_prospect).toBeLessThanOrEqual(100);
    });
  });
});
