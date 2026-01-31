import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { computeScoring, type RUQuestion, type ScoringResult } from '../scoring-engine';

describe('scoring-engine integration', () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => undefined);
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  const questions: RUQuestion[] = [
    { id: 'M1', group: 'MPT', maxScore: 5 },
    { id: 'M2', group: 'MPT', maxScore: 5 },
    { id: 'PT1', group: 'PROSPECT', maxScore: 4 },
    { id: 'PT2', group: 'PROSPECT', maxScore: 4 }
  ];

  it('returns complete ScoringResult structure', () => {
    const result: ScoringResult = computeScoring({
      selectedQuestions: questions,
      answersMap: { M1: 3, M2: 4, PT1: 2, PT2: 3 },
      completionTimeSeconds: 60
    });

    expect(result).toHaveProperty('raw_score');
    expect(result).toHaveProperty('normalized_score');
    expect(result).toHaveProperty('normalized_mpt');
    expect(result).toHaveProperty('normalized_prospect');
    expect(result).toHaveProperty('risk_category');
    expect(result).toHaveProperty('color_code');
    expect(result).toHaveProperty('confidence_band');
    expect(result).toHaveProperty('visualization_data');
    expect(result).toHaveProperty('safeguards');
    expect(result).toHaveProperty('consistency');
  });

  it('calculates normalized scores correctly', () => {
    const result = computeScoring({
      selectedQuestions: questions,
      answersMap: { M1: 5, M2: 5, PT1: 4, PT2: 4 },
      completionTimeSeconds: 60
    });

    expect(result.normalized_score).toBeCloseTo(100);
    expect(result.normalized_mpt).toBeCloseTo(100);
    expect(result.normalized_prospect).toBeCloseTo(100);
  });

  it('applies time_horizon override when conditions met', () => {
    const result = computeScoring({
      selectedQuestions: questions,
      answersMap: { M1: 5, M2: 5, PT1: 4, PT2: 4 },
      completionTimeSeconds: 60,
      timeHorizonAnswer: 2
    });

    expect(result.safeguards.category_was_overridden).toBe(true);
    expect(result.safeguards.override_reason).toBe('time_horizon_override');
    expect(result.risk_category).toBe('moderate');
  });

  it('logs assessment events', () => {
    computeScoring({
      selectedQuestions: questions,
      answersMap: { M1: 3, M2: 3, PT1: 2, PT2: 2 },
      completionTimeSeconds: 60
    });

    expect(consoleSpy).toHaveBeenCalled();
  });

  it('detects consistency issues when fast completion', () => {
    const result = computeScoring({
      selectedQuestions: questions,
      answersMap: { M1: 3, M2: 3, PT1: 2, PT2: 2 },
      completionTimeSeconds: 8
    });

    expect(result.consistency.fast_completion).toBe(true);
  });
});
