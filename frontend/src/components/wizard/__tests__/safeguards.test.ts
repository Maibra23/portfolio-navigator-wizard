import { describe, it, expect } from 'vitest';
import {
  FLAG_MESSAGES,
  applySafeguards,
  checkTimeHorizonOverride,
  checkLossAversion,
  checkExtremeAnswerPattern,
  checkExtremeProfile,
  checkHighUncertainty
} from '../safeguards';
import type { ConfidenceBand } from '../confidence-calculator';

function band(lower: number, upper: number): ConfidenceBand {
  return {
    lower,
    upper,
    primary_category: 'moderate',
    secondary_category: null,
    band_width: upper - lower,
    adjustment_reasons: []
  };
}

describe('safeguards', () => {
  describe('FLAG_MESSAGES', () => {
    it('has all four messages', () => {
      expect(FLAG_MESSAGES.loss_sensitivity_warning).toContain('financial advisor');
      expect(FLAG_MESSAGES.response_pattern_warning).toContain('extremes');
      expect(FLAG_MESSAGES.extreme_profile_confirmation).toContain('less common');
      expect(FLAG_MESSAGES.high_uncertainty).toContain('middle of your range');
    });
  });

  describe('checkTimeHorizonOverride', () => {
    it('returns true when time_horizon ≤ 2 and score > 60', () => {
      expect(checkTimeHorizonOverride(1, 61)).toBe(true);
      expect(checkTimeHorizonOverride(2, 61)).toBe(true);
      expect(checkTimeHorizonOverride(2, 60)).toBe(false);
      expect(checkTimeHorizonOverride(3, 61)).toBe(false);
    });
    it('returns false when timeHorizonAnswer is undefined', () => {
      expect(checkTimeHorizonOverride(undefined, 70)).toBe(false);
    });
  });

  describe('checkLossAversion', () => {
    it('returns true when loss_aversion = 1 and score > 50', () => {
      expect(checkLossAversion(1, 51)).toBe(true);
      expect(checkLossAversion(1, 50)).toBe(false);
      expect(checkLossAversion(2, 51)).toBe(false);
    });
    it('returns false when lossAversionAnswer is undefined', () => {
      expect(checkLossAversion(undefined, 60)).toBe(false);
    });
  });

  describe('checkExtremeAnswerPattern', () => {
    it('returns true when all answers are 1 or maxScore', () => {
      expect(checkExtremeAnswerPattern({ q1: 1, q2: 5 }, { q1: 5, q2: 5 })).toBe(true);
      expect(checkExtremeAnswerPattern({ q1: 1, q2: 4 }, { q1: 5, q2: 4 })).toBe(true);
    });
    it('returns false when any answer is not extreme', () => {
      expect(checkExtremeAnswerPattern({ q1: 1, q2: 3 }, { q1: 5, q2: 5 })).toBe(false);
    });
    it('returns false for empty answers', () => {
      expect(checkExtremeAnswerPattern({}, {})).toBe(false);
    });
  });

  describe('checkExtremeProfile', () => {
    it('returns true when score < 15 or score > 85', () => {
      expect(checkExtremeProfile(14)).toBe(true);
      expect(checkExtremeProfile(86)).toBe(true);
      expect(checkExtremeProfile(15)).toBe(false);
      expect(checkExtremeProfile(85)).toBe(false);
      expect(checkExtremeProfile(50)).toBe(false);
    });
  });

  describe('checkHighUncertainty', () => {
    it('returns true when band spans 3+ categories', () => {
      expect(checkHighUncertainty(band(10, 65))).toBe(true);
      expect(checkHighUncertainty(band(5, 70))).toBe(true);
    });
    it('returns false when band spans fewer than 3 categories', () => {
      expect(checkHighUncertainty(band(25, 35))).toBe(false);
      expect(checkHighUncertainty(band(45, 55))).toBe(false);
      expect(checkHighUncertainty(band(30, 55))).toBe(false);
    });
  });

  describe('applySafeguards', () => {
    const defaultParams = {
      score: 55,
      original_category: 'moderate',
      answers: { q1: 3, q2: 3 },
      maxScoresByQuestion: { q1: 5, q2: 5 },
      confidenceBand: band(45, 65),
      timeHorizonAnswer: undefined,
      lossAversionAnswer: undefined
    };

    it('leaves category and flags unchanged when no conditions match', () => {
      const result = applySafeguards(defaultParams);
      expect(result.original_category).toBe('moderate');
      expect(result.final_category).toBe('moderate');
      expect(result.category_was_overridden).toBe(false);
      expect(result.override_reason).toBeNull();
      expect(result.flags.loss_sensitivity_warning).toBe(false);
      expect(result.flags.response_pattern_warning).toBe(false);
      expect(result.flags.extreme_profile_confirmation).toBe(false);
      expect(result.flags.high_uncertainty).toBe(false);
      expect(Object.keys(result.flag_messages)).toHaveLength(0);
    });

    it('caps at Moderate when time_horizon ≤ 2 and score > 60', () => {
      const result = applySafeguards({
        ...defaultParams,
        score: 70,
        original_category: 'aggressive',
        timeHorizonAnswer: 2
      });
      expect(result.final_category).toBe('moderate');
      expect(result.category_was_overridden).toBe(true);
      expect(result.override_reason).toBe('time_horizon_override');
    });

    it('sets loss_sensitivity_warning when loss_aversion = 1 and score > 50', () => {
      const result = applySafeguards({
        ...defaultParams,
        score: 55,
        lossAversionAnswer: 1
      });
      expect(result.flags.loss_sensitivity_warning).toBe(true);
      expect(result.flag_messages.loss_sensitivity_warning).toBe(FLAG_MESSAGES.loss_sensitivity_warning);
    });

    it('sets response_pattern_warning when all answers at extremes', () => {
      const result = applySafeguards({
        ...defaultParams,
        answers: { q1: 1, q2: 5 },
        maxScoresByQuestion: { q1: 5, q2: 5 }
      });
      expect(result.flags.response_pattern_warning).toBe(true);
      expect(result.flag_messages.response_pattern_warning).toBe(FLAG_MESSAGES.response_pattern_warning);
    });

    it('sets extreme_profile_confirmation when score < 15 or score > 85', () => {
      const low = applySafeguards({ ...defaultParams, score: 10, original_category: 'very-conservative' });
      expect(low.flags.extreme_profile_confirmation).toBe(true);
      const high = applySafeguards({ ...defaultParams, score: 90, original_category: 'very-aggressive' });
      expect(high.flags.extreme_profile_confirmation).toBe(true);
      expect(high.flag_messages.extreme_profile_confirmation).toBe(FLAG_MESSAGES.extreme_profile_confirmation);
    });

    it('defaults to middle and sets high_uncertainty when band spans 3+ categories', () => {
      const result = applySafeguards({
        ...defaultParams,
        score: 50,
        original_category: 'moderate',
        confidenceBand: band(15, 75)
      });
      expect(result.final_category).toBe('moderate');
      expect(result.category_was_overridden).toBe(true);
      expect(result.override_reason).toBe('high_uncertainty');
      expect(result.flags.high_uncertainty).toBe(true);
      expect(result.flag_messages.high_uncertainty).toBe(FLAG_MESSAGES.high_uncertainty);
    });

    it('time_horizon override takes precedence for override_reason when both time_horizon and high_uncertainty apply', () => {
      const result = applySafeguards({
        ...defaultParams,
        score: 70,
        original_category: 'aggressive',
        confidenceBand: band(15, 75),
        timeHorizonAnswer: 1
      });
      expect(result.final_category).toBe('moderate');
      expect(result.override_reason).toBe('time_horizon_override');
    });
  });
});
