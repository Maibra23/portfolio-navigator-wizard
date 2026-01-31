export interface ConsistencyResult {
  high_variance: boolean;
  fast_completion: boolean;
  potential_acquiescence: boolean;
  flags: string[];
}

export interface ReverseCodedPair {
  originalAnswer: number;
  originalMax: number;
  reverseAnswer: number;
  reverseMax: number;
}

export const standardDeviation = (values: number[]): number => {
  if (values.length <= 1) return 0;
  const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
  const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
  return Math.sqrt(variance);
};

export const checkAnswerVariance = (answers: number[], maxScores: number[]): boolean => {
  const normalized: number[] = [];
  for (let i = 0; i < answers.length && i < maxScores.length; i++) {
    const maxScore = maxScores[i];
    if (maxScore <= 1) continue;
    normalized.push((answers[i] - 1) / (maxScore - 1));
  }
  if (normalized.length === 0) return false;
  return standardDeviation(normalized) > 0.35;
};

export const checkCompletionSpeed = (totalSeconds: number, questionCount: number): boolean => {
  if (questionCount <= 0) return false;
  return (totalSeconds / questionCount) < 3;
};

export const checkReverseCodedConsistency = (
  originalAnswer: number,
  originalMax: number,
  reverseAnswer: number,
  reverseMax: number
): boolean => {
  if (originalMax <= 1 || reverseMax <= 1) return false;
  const origNorm = (originalAnswer - 1) / (originalMax - 1);
  const revNorm = 1 - ((reverseAnswer - 1) / (reverseMax - 1));
  return Math.abs(origNorm - revNorm) > 0.5;
};

export interface DetectConsistencyParams {
  answers: number[];
  maxScores: number[];
  totalSeconds: number;
  questionCount: number;
  reverseCodedPairs?: ReverseCodedPair[];
}

export const detectConsistencyIssues = ({
  answers,
  maxScores,
  totalSeconds,
  questionCount,
  reverseCodedPairs = []
}: DetectConsistencyParams): ConsistencyResult => {
  const high_variance = checkAnswerVariance(answers, maxScores);
  const fast_completion = checkCompletionSpeed(totalSeconds, questionCount);
  const potential_acquiescence = reverseCodedPairs.some((pair) =>
    checkReverseCodedConsistency(
      pair.originalAnswer,
      pair.originalMax,
      pair.reverseAnswer,
      pair.reverseMax
    )
  );

  const flags: string[] = [];
  if (high_variance) flags.push('high_variance');
  if (fast_completion) flags.push('fast_completion');
  if (potential_acquiescence) flags.push('potential_acquiescence');

  return {
    high_variance,
    fast_completion,
    potential_acquiescence,
    flags
  };
};
