import { describe, it, expect } from 'vitest';
import { computeRiskResult } from '../riskUtils';

type Q = {
  id: string;
  group: 'MPT' | 'PROSPECT' | 'SCREENING';
  maxScore: number;
};

describe('computeRiskResult', () => {
  it('all minimum answers -> normalized_score = 0', () => {
    const qs: any[] = [
      { id: 'q1', group: 'MPT', maxScore: 5 },
      { id: 'q2', group: 'PROSPECT', maxScore: 4 }
    ];
    const answers = { q1: 1, q2: 1 };
    const res = computeRiskResult(qs as any, answers);
    expect(res.normalized_score).toBeCloseTo(0);
  });

  it('all maximum answers -> normalized_score = 100', () => {
    const qs: any[] = [
      { id: 'q1', group: 'MPT', maxScore: 5 },
      { id: 'q2', group: 'PROSPECT', maxScore: 4 }
    ];
    const answers = { q1: 5, q2: 4 };
    const res = computeRiskResult(qs as any, answers);
    expect(res.normalized_score).toBeCloseTo(100);
  });

  it('mixed answers compute expected normalized score', () => {
    // Two MPT questions (max 5) answered 3 and 5
    const qs: any[] = [
      { id: 'm1', group: 'MPT', maxScore: 5 },
      { id: 'm2', group: 'MPT', maxScore: 5 }
    ];
    const answers = { m1: 3, m2: 5 };
    // adj numerator = (3-1) + (5-1) = 2 + 4 = 6
    // adj denom = (5-1) + (5-1) = 4 + 4 = 8
    // normalized = 6/8 * 100 = 75
    const res = computeRiskResult(qs as any, answers);
    expect(res.normalized_score).toBeCloseTo(75);
    expect(res.normalized_mpt).toBeCloseTo(75);
  });

  it('pt-2 monotonicity: higher PT answer increases score', () => {
    const qs: any[] = [
      { id: 'pt2', group: 'PROSPECT', maxScore: 4 },
      { id: 'm1', group: 'MPT', maxScore: 5 }
    ];
    const baseAnswers = { pt2: 1, m1: 3 };
    const higherAnswers = { pt2: 4, m1: 3 };
    const base = computeRiskResult(qs as any, baseAnswers);
    const higher = computeRiskResult(qs as any, higherAnswers);
    expect(higher.normalized_score).toBeGreaterThan(base.normalized_score);
  });

  it('removing a question decreases denominator correctly', () => {
    const qsAll: any[] = [
      { id: 'a', group: 'MPT', maxScore: 5 },
      { id: 'b', group: 'MPT', maxScore: 5 }
    ];
    const qsOne: any[] = [{ id: 'a', group: 'MPT', maxScore: 5 }];
    const answers = { a: 5, b: 5 };
    const resAll = computeRiskResult(qsAll as any, answers);
    const resOne = computeRiskResult(qsOne as any, { a: 5 });
    // resAll should equal resOne when both answered max relative to denominators (both 100)
    expect(resAll.normalized_score).toBeCloseTo(100);
    expect(resOne.normalized_score).toBeCloseTo(100);
  });

  it('screening-only users produce 0 normalized score (insufficient data)', () => {
    const qs: any[] = [{ id: 's1', group: 'SCREENING', maxScore: 0 }];
    const res = computeRiskResult(qs as any, {});
    expect(res.normalized_score).toBeCloseTo(0);
  });
});

