export interface ConfidenceBand {
  lower: number;
  upper: number;
  primary_category: string;
  secondary_category: string | null;
  band_width: number;
  adjustment_reasons: string[];
}

export interface VisualizationData {
  score: number;
  band: ConfidenceBand;
  gradient_intensity: 'narrow' | 'medium' | 'wide';
  boundary_proximity: 'far' | 'near' | 'crossing';
}

export const ADJUSTMENT_TOOLTIPS = {
  variance: "Your answers showed varied preferences across questions—this is natural and suggests flexibility.",
  speed: "You completed quickly. Consider if answers reflect your considered preferences.",
  divergence: "Your analytical and emotional risk responses differ, which is common.",
  zero_variance: "All answers were identical—consider if this reflects your genuine range of preferences."
};

const BASE_UNCERTAINTY = 5;

const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value));

const standardDeviation = (values: number[]): number => {
  if (values.length <= 1) return 0;
  const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
  const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
  return Math.sqrt(variance);
};

/** Exclusive upper bounds: [0,20) very-conservative, [20,40) conservative, [40,60) moderate, [60,80) aggressive, [80,100] very-aggressive */
export const getCategory = (score: number): string => {
  if (score < 20) return 'very-conservative';
  if (score < 40) return 'conservative';
  if (score < 60) return 'moderate';
  if (score < 80) return 'aggressive';
  return 'very-aggressive';
};

export const getSecondaryCategory = (score: number, adjustment: number): string | null => {
  const primary = getCategory(score);
  const lowerCategory = getCategory(score - adjustment);
  const upperCategory = getCategory(score + adjustment);

  if (lowerCategory === upperCategory && lowerCategory !== primary) return lowerCategory;
  if (upperCategory !== primary) return upperCategory;
  if (lowerCategory !== primary) return lowerCategory;
  return null;
};

export const determineGradientIntensity = (bandWidth: number): 'narrow' | 'medium' | 'wide' => {
  if (bandWidth < 10) return 'narrow';
  if (bandWidth <= 15) return 'medium';
  return 'wide';
};

export const determineBoundaryProximity = (
  score: number,
  lower: number,
  upper: number
): 'far' | 'near' | 'crossing' => {
  const lowerCategory = getCategory(lower);
  const upperCategory = getCategory(upper);
  if (lowerCategory !== upperCategory) return 'crossing';

  const boundaries = [20, 40, 60, 80];
  const nearestDistance = boundaries.reduce((min, boundary) => {
    return Math.min(min, Math.abs(score - boundary));
  }, Number.POSITIVE_INFINITY);

  return nearestDistance <= 5 ? 'near' : 'far';
};

export const calculateConfidenceBand = (
  normalizedScore: number,
  answers: Record<string, number>,
  mptScore: number,
  prospectScore: number,
  completionTimeSeconds: number,
  questionCount: number,
  maxScoresByQuestion: Record<string, number> = {}
): ConfidenceBand => {
  let adjustment = BASE_UNCERTAINTY;
  const reasons: string[] = [];

  const isShortAssessment = questionCount <= 6;
  const variancePenalty = isShortAssessment ? 1 : 2;
  const divergencePenalty = isShortAssessment ? 1.5 : 3;

  const normalizedAnswers = Object.entries(answers).map(([qId, value]) => {
    const maxScore = maxScoresByQuestion[qId] ?? 5;
    if (maxScore <= 1) return 0;
    return clamp((value - 1) / (maxScore - 1), 0, 1);
  });
  const variance = standardDeviation(normalizedAnswers);
  if (variance === 0 && normalizedAnswers.length > 1) {
    adjustment += 2;
    reasons.push('zero_variance');
  }
  if (variance > 0.3) {
    adjustment += variancePenalty;
    reasons.push('variance');
  }

  const avgTimePerQuestion = questionCount > 0 ? completionTimeSeconds / questionCount : completionTimeSeconds;
  if (avgTimePerQuestion < 3) {
    adjustment += 2;
    reasons.push('speed');
  }

  if (Math.abs(mptScore - prospectScore) > 25) {
    adjustment += divergencePenalty;
    reasons.push('divergence');
  }

  const lower = clamp(normalizedScore - adjustment, 0, 100);
  const upper = clamp(normalizedScore + adjustment, 0, 100);

  return {
    lower,
    upper,
    primary_category: getCategory(normalizedScore),
    secondary_category: getSecondaryCategory(normalizedScore, adjustment),
    band_width: adjustment * 2,
    adjustment_reasons: reasons
  };
};
