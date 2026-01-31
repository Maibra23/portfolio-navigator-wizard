// Utility functions for risk scoring - kept free of UI imports so tests can run in isolation
export type RUGroup = 'MPT' | 'PROSPECT' | 'SCREENING';
export type RUQuestion = { id: string; group: RUGroup; maxScore: number };

export type RURiskResult = {
  raw_score: number;
  normalized_score: number;
  normalized_mpt?: number;
  normalized_prospect?: number;
  risk_category: string;
  color_code: string;
};

export const computeRiskResult = (selectedQs: RUQuestion[], answersMap: Record<string, number>): RURiskResult => {
  let rawSum = 0;
  let maxPossible = 0;

  let rawAdj = 0;
  let maxAdj = 0;

  let rawAdjMPT = 0;
  let maxAdjMPT = 0;
  let rawAdjProspect = 0;
  let maxAdjProspect = 0;

  selectedQs.forEach((question) => {
    if (!question) return;
    if (question.group === 'SCREENING' || question.maxScore === 0) return;

    const answerValue = answersMap[question.id];
    rawSum += (answerValue !== undefined ? answerValue : 0);
    maxPossible += question.maxScore;

    const denom = Math.max(0, question.maxScore - 1);
    maxAdj += denom;
    if (question.group === 'MPT') maxAdjMPT += denom;
    if (question.group === 'PROSPECT') maxAdjProspect += denom;

    if (answerValue !== undefined) {
      const adj = Math.max(0, answerValue - 1);
      rawAdj += adj;
      if (question.group === 'MPT') rawAdjMPT += adj;
      if (question.group === 'PROSPECT') rawAdjProspect += adj;
    }
  });

  const normalizedScore = maxAdj > 0 ? Math.min(100, Math.max(0, (rawAdj / maxAdj) * 100)) : 0;
  const normalizedMPT = maxAdjMPT > 0 ? (rawAdjMPT / maxAdjMPT) * 100 : 0;
  const normalizedProspect = maxAdjProspect > 0 ? (rawAdjProspect / maxAdjProspect) * 100 : 0;

  // Determine category using normalizedScore
  let riskCategory: string;
  let colorCode: string;
  if (normalizedScore <= 20) {
    riskCategory = 'very-conservative';
    colorCode = '#00008B';
  } else if (normalizedScore <= 40) {
    riskCategory = 'conservative';
    colorCode = '#ADD8E6';
  } else if (normalizedScore <= 60) {
    riskCategory = 'moderate';
    colorCode = '#008000';
  } else if (normalizedScore <= 80) {
    riskCategory = 'aggressive';
    colorCode = '#FFA500';
  } else {
    riskCategory = 'very-aggressive';
    colorCode = '#FF0000';
  }

  return {
    raw_score: rawSum,
    normalized_score: normalizedScore,
    normalized_mpt: normalizedMPT,
    normalized_prospect: normalizedProspect,
    risk_category: riskCategory,
    color_code: colorCode
  };
};

