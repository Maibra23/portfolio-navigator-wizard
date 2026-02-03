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

  describe('all risk profiles as reference', () => {
    const fullQuestions: RUQuestion[] = [
      { id: 'M1', group: 'MPT', maxScore: 5 },
      { id: 'M2', group: 'MPT', maxScore: 5 },
      { id: 'M3', group: 'MPT', maxScore: 5 },
      { id: 'PT1', group: 'PROSPECT', maxScore: 4 },
      { id: 'PT2', group: 'PROSPECT', maxScore: 4 }
    ];

    it('very-conservative: low scores yield category and score in 0–20', () => {
      const result = computeScoring({
        selectedQuestions: fullQuestions,
        answersMap: { M1: 1, M2: 1, M3: 1, PT1: 1, PT2: 1 },
        completionTimeSeconds: 60
      });
      expect(result.risk_category).toBe('very-conservative');
      expect(result.normalized_score).toBeGreaterThanOrEqual(0);
      expect(result.normalized_score).toBeLessThanOrEqual(20);
      expect(result.safeguards.flags.extreme_profile_confirmation).toBe(true);
      expect(result.visualization_data.score).toBe(result.normalized_score);
      expect(result.visualization_data.score).toBeGreaterThanOrEqual(0);
      expect(result.visualization_data.score).toBeLessThanOrEqual(20);
    });

    it('conservative: scores in 21–40', () => {
      const result = computeScoring({
        selectedQuestions: fullQuestions,
        answersMap: { M1: 2, M2: 2, M3: 2, PT1: 1, PT2: 2 },
        completionTimeSeconds: 60
      });
      expect(result.risk_category).toBe('conservative');
      expect(result.normalized_score).toBeGreaterThanOrEqual(20);
      expect(result.normalized_score).toBeLessThanOrEqual(40);
      expect(result.safeguards.flags.extreme_profile_confirmation).toBe(false);
      expect(result.visualization_data.score).toBe(result.normalized_score);
      expect(result.normalized_mpt).toBeGreaterThanOrEqual(0);
      expect(result.normalized_mpt).toBeLessThanOrEqual(100);
      expect(result.normalized_prospect).toBeGreaterThanOrEqual(0);
      expect(result.normalized_prospect).toBeLessThanOrEqual(100);
    });

    it('moderate: scores in 41–60', () => {
      const result = computeScoring({
        selectedQuestions: fullQuestions,
        answersMap: { M1: 3, M2: 3, M3: 3, PT1: 2, PT2: 2 },
        completionTimeSeconds: 60
      });
      expect(result.risk_category).toBe('moderate');
      expect(result.normalized_score).toBeGreaterThanOrEqual(40);
      expect(result.normalized_score).toBeLessThanOrEqual(60);
      expect(result.safeguards.flags.extreme_profile_confirmation).toBe(false);
      expect(result.visualization_data.score).toBe(result.normalized_score);
    });

    it('aggressive: scores in 61–80', () => {
      const result = computeScoring({
        selectedQuestions: fullQuestions,
        answersMap: { M1: 4, M2: 4, M3: 4, PT1: 3, PT2: 3 },
        completionTimeSeconds: 60
      });
      expect(result.risk_category).toBe('aggressive');
      expect(result.normalized_score).toBeGreaterThanOrEqual(60);
      expect(result.normalized_score).toBeLessThanOrEqual(80);
      expect(result.safeguards.flags.extreme_profile_confirmation).toBe(false);
      expect(result.visualization_data.score).toBe(result.normalized_score);
    });

    it('very-aggressive: high scores yield category and score in 81–100', () => {
      const result = computeScoring({
        selectedQuestions: fullQuestions,
        answersMap: { M1: 5, M2: 5, M3: 5, PT1: 4, PT2: 4 },
        completionTimeSeconds: 60
      });
      expect(result.risk_category).toBe('very-aggressive');
      expect(result.normalized_score).toBeGreaterThanOrEqual(80);
      expect(result.normalized_score).toBeLessThanOrEqual(100);
      expect(result.safeguards.flags.extreme_profile_confirmation).toBe(true);
      expect(result.visualization_data.score).toBe(result.normalized_score);
    });

    it('when overridden to moderate, caps normalized_score at 60 and scales mpt/prospect', () => {
      const result = computeScoring({
        selectedQuestions: fullQuestions,
        answersMap: { M1: 5, M2: 2, M3: 5, PT1: 4, PT2: 4 },
        completionTimeSeconds: 60,
        timeHorizonAnswer: 2
      });
      expect(result.risk_category).toBe('moderate');
      expect(result.safeguards.category_was_overridden).toBe(true);
      expect(result.safeguards.override_reason).toBe('time_horizon_override');
      expect(result.normalized_score).toBe(60);
      expect(result.visualization_data.score).toBe(60);
      expect(result.normalized_mpt).toBeLessThanOrEqual(100);
      expect(result.normalized_prospect).toBeLessThanOrEqual(100);
      expect(result.safeguards.flags.extreme_profile_confirmation).toBe(false);
    });
  });
});
