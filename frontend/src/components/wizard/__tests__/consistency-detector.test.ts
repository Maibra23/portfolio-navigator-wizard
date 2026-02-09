import { describe, it, expect } from 'vitest';
import {
  standardDeviation,
  checkAnswerVariance,
  checkCompletionSpeed,
  checkReverseCodedConsistency,
  detectConsistencyIssues
} from '../consistency-detector';

describe('consistency-detector', () => {
  it('standardDeviation returns 0 for empty or single value', () => {
    expect(standardDeviation([])).toBe(0);
    expect(standardDeviation([1])).toBe(0);
  });

  it('checkAnswerVariance returns true for high variance', () => {
    const answers = [1, 5, 1, 5];
    const maxScores = [5, 5, 5, 5];
    expect(checkAnswerVariance(answers, maxScores)).toBe(true);
  });

  it('checkAnswerVariance returns false for low variance', () => {
    const answers = [3, 3, 3, 3];
    const maxScores = [5, 5, 5, 5];
    expect(checkAnswerVariance(answers, maxScores)).toBe(false);
  });

  it('checkAnswerVariance ignores invalid maxScores', () => {
    const answers = [1, 5, 3];
    const maxScores = [1, 0, 5];
    expect(checkAnswerVariance(answers, maxScores)).toBe(false);
  });

  it('checkCompletionSpeed uses 5 sec threshold for short (<=6) and 3 sec for standard', () => {
    expect(checkCompletionSpeed(10, 4)).toBe(true);
    expect(checkCompletionSpeed(24, 4)).toBe(false);
    expect(checkCompletionSpeed(20, 8)).toBe(true);
    expect(checkCompletionSpeed(24, 8)).toBe(false);
  });

  it('checkCompletionSpeed returns false when questionCount <= 0', () => {
    expect(checkCompletionSpeed(10, 0)).toBe(false);
  });

  it('checkReverseCodedConsistency returns true for contradictions', () => {
    expect(checkReverseCodedConsistency(5, 5, 5, 5)).toBe(true);
    expect(checkReverseCodedConsistency(1, 5, 1, 5)).toBe(true);
  });

  it('checkReverseCodedConsistency returns false for consistent pairs', () => {
    expect(checkReverseCodedConsistency(5, 5, 1, 5)).toBe(false);
    expect(checkReverseCodedConsistency(3, 5, 3, 5)).toBe(false);
  });

  it('checkReverseCodedConsistency returns false when max scores invalid', () => {
    expect(checkReverseCodedConsistency(2, 1, 2, 5)).toBe(false);
  });

  it('detectConsistencyIssues aggregates flags', () => {
    const result = detectConsistencyIssues({
      answers: [1, 5, 1, 5],
      maxScores: [5, 5, 5, 5],
      totalSeconds: 8,
      questionCount: 4,
      reverseCodedPairs: [{ originalAnswer: 5, originalMax: 5, reverseAnswer: 5, reverseMax: 5 }]
    });
    expect(result.high_variance).toBe(true);
    expect(result.fast_completion).toBe(true);
    expect(result.potential_acquiescence).toBe(true);
    expect(result.flags).toEqual(['high_variance', 'fast_completion', 'potential_acquiescence']);
  });

  it('detectConsistencyIssues handles empty inputs', () => {
    const result = detectConsistencyIssues({
      answers: [],
      maxScores: [],
      totalSeconds: 0,
      questionCount: 0
    });
    expect(result.high_variance).toBe(false);
    expect(result.fast_completion).toBe(false);
    expect(result.potential_acquiescence).toBe(false);
    expect(result.flags).toEqual([]);
  });
});
