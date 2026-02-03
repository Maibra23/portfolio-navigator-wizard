import type { ConfidenceBand } from './confidence-calculator';
import { getCategory } from './confidence-calculator';

export interface SafeguardResult {
  original_category: string;
  final_category: string;
  category_was_overridden: boolean;
  override_reason: string | null;
  flags: {
    loss_sensitivity_warning: boolean;
    response_pattern_warning: boolean;
    extreme_profile_confirmation: boolean;
    high_uncertainty: boolean;
  };
  flag_messages: Record<string, string>;
}

export const FLAG_MESSAGES = {
  loss_sensitivity_warning: "Your responses indicate strong sensitivity to losses. Consider discussing with a financial advisor.",
  response_pattern_warning: "Your responses showed strong preferences at both extremes. Please confirm this reflects your genuine approach.",
  extreme_profile_confirmation: "Your profile is less common. Please confirm this feels accurate.",
  high_uncertainty: "Your responses suggest flexibility across approaches. We've positioned you at the middle of your range."
};

export interface ApplySafeguardsParams {
  score: number;
  original_category: string;
  answers: Record<string, number>;
  maxScoresByQuestion: Record<string, number>;
  confidenceBand: ConfidenceBand;
  /** Answer value for the time-horizon question (e.g. M2), 1–5 scale. Used when ≤2 with score>60 to cap at Moderate. */
  timeHorizonAnswer?: number;
  /** Answer value for the loss-aversion question (e.g. PT-2), 1–4 scale. Used when =1 with score>50 to set loss_sensitivity_warning. */
  lossAversionAnswer?: number;
}

function buildFlagMessages(flags: SafeguardResult['flags']): Record<string, string> {
  const out: Record<string, string> = {};
  if (flags.loss_sensitivity_warning) out.loss_sensitivity_warning = FLAG_MESSAGES.loss_sensitivity_warning;
  if (flags.response_pattern_warning) out.response_pattern_warning = FLAG_MESSAGES.response_pattern_warning;
  if (flags.extreme_profile_confirmation) out.extreme_profile_confirmation = FLAG_MESSAGES.extreme_profile_confirmation;
  if (flags.high_uncertainty) out.high_uncertainty = FLAG_MESSAGES.high_uncertainty;
  return out;
}

/**
 * True if time-horizon dimension is ≤2 and score > 60 (should cap at Moderate).
 */
export function checkTimeHorizonOverride(timeHorizonAnswer: number | undefined, score: number): boolean {
  if (timeHorizonAnswer === undefined) return false;
  return timeHorizonAnswer <= 2 && score > 60;
}

/**
 * True if loss-aversion answer is 1 (most sensitive) and score > 50 (add warning).
 */
export function checkLossAversion(lossAversionAnswer: number | undefined, score: number): boolean {
  if (lossAversionAnswer === undefined) return false;
  return lossAversionAnswer === 1 && score > 50;
}

/**
 * True if every answer is at an extreme (1 or maxScore for that question).
 */
export function checkExtremeAnswerPattern(
  answers: Record<string, number>,
  maxScoresByQuestion: Record<string, number>
): boolean {
  const entries = Object.entries(answers);
  if (entries.length === 0) return false;
  return entries.every(([qId, value]) => {
    const maxScore = maxScoresByQuestion[qId] ?? 5;
    return value === 1 || value === maxScore;
  });
}

/**
 * True if score < 15 or score > 85 (require confirmation).
 */
export function checkExtremeProfile(score: number): boolean {
  return score < 15 || score > 85;
}

const CATEGORY_BOUNDARIES = [0, 20, 40, 60, 80, 100];

/**
 * Count how many risk categories the band [lower, upper] intersects.
 */
function countCategoriesSpanned(lower: number, upper: number): number {
  const categories = new Set<string>();
  for (let i = 0; i < CATEGORY_BOUNDARIES.length - 1; i++) {
    const low = CATEGORY_BOUNDARIES[i];
    const high = CATEGORY_BOUNDARIES[i + 1];
    if (upper > low && lower < high) categories.add(getCategory((low + high) / 2));
  }
  return categories.size;
}

/**
 * True if confidence band spans 3 or more categories (default to middle, add high_uncertainty).
 */
export function checkHighUncertainty(confidenceBand: ConfidenceBand): boolean {
  return countCategoriesSpanned(confidenceBand.lower, confidenceBand.upper) >= 3;
}

/**
 * Apply all override rules and set flags. Overrides: time_horizon cap at Moderate, high_uncertainty default to middle.
 */
export function applySafeguards(params: ApplySafeguardsParams): SafeguardResult {
  const {
    score,
    original_category,
    answers,
    maxScoresByQuestion,
    confidenceBand,
    timeHorizonAnswer,
    lossAversionAnswer
  } = params;

  let final_category = original_category;
  let category_was_overridden = false;
  let override_reason: string | null = null;

  if (checkTimeHorizonOverride(timeHorizonAnswer, score)) {
    final_category = 'moderate';
    category_was_overridden = true;
    override_reason = 'time_horizon_override';
  }

  if (checkHighUncertainty(confidenceBand)) {
    final_category = 'moderate';
    category_was_overridden = true;
    override_reason = override_reason ?? 'high_uncertainty';
  }

  // If category is overridden to moderate, we shouldn't flag it as extreme profile
  const isExtreme = checkExtremeProfile(score);
  const shouldFlagExtreme = isExtreme && final_category !== 'moderate';

  const flags = {
    loss_sensitivity_warning: checkLossAversion(lossAversionAnswer, score),
    response_pattern_warning: checkExtremeAnswerPattern(answers, maxScoresByQuestion),
    extreme_profile_confirmation: shouldFlagExtreme,
    high_uncertainty: checkHighUncertainty(confidenceBand)
  };

  const flag_messages = buildFlagMessages(flags);

  return {
    original_category,
    final_category,
    category_was_overridden,
    override_reason,
    flags,
    flag_messages
  };
}
