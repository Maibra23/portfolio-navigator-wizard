/**
 * Scoring Engine – Unified entry point for risk profiling computation.
 * Integrates confidence-calculator, safeguards, consistency-detector and monitoring modules.
 */

import {
  calculateConfidenceBand,
  determineGradientIntensity,
  determineBoundaryProximity,
  type ConfidenceBand,
  type VisualizationData
} from './confidence-calculator';
import { applySafeguards, type SafeguardResult } from './safeguards';
import { detectConsistencyIssues, type ConsistencyResult, type ReverseCodedPair } from './consistency-detector';
import {
  logAssessmentEvent,
  createAssessmentCompletedEvent,
  createOverrideTriggeredEvent,
  createFlagRaisedEvent
} from './monitoring';

// Re-export types consumed by RiskProfiler and Agent 2
export type { ConfidenceBand, VisualizationData } from './confidence-calculator';
export type { SafeguardResult } from './safeguards';
export type { ConsistencyResult, ReverseCodedPair } from './consistency-detector';

export type RUGroup = 'MPT' | 'PROSPECT' | 'SCREENING';

export interface RUQuestion {
  id: string;
  group: RUGroup;
  maxScore: number;
  excludeFromScoring?: boolean;
}

export interface ScoringResult {
  // Existing
  raw_score: number;
  normalized_score: number;
  normalized_mpt: number;
  normalized_prospect: number;
  risk_category: string;
  color_code: string;

  // New from Sprint 1
  confidence_band: ConfidenceBand;
  visualization_data: VisualizationData;
  safeguards: SafeguardResult;
  consistency: ConsistencyResult;

  // New from Sprint 2 - Branching metadata
  branching_metadata: {
    path: 'conservative' | 'aggressive' | 'moderate' | 'gamified';
    phase1_score: number | null;
    construct_coverage: {
      covered: string[];
      missing: string[];
      percent: number;
    };
  };
}

export interface ComputeScoringParams {
  selectedQuestions: RUQuestion[];
  answersMap: Record<string, number>;
  completionTimeSeconds: number;
  /** Optional session id for logging (defaults to generated id) */
  sessionId?: string;
  /** Optional answer for time-horizon question (e.g. M2) */
  timeHorizonAnswer?: number;
  /** Optional answer for loss-aversion question (e.g. PT-2) */
  lossAversionAnswer?: number;
  /** Optional reverse-coded answer pairs for consistency check */
  reverseCodedPairs?: ReverseCodedPair[];
  /** Branching metadata from Sprint 2 */
  branchingMetadata?: {
    path: 'conservative' | 'aggressive' | 'moderate' | 'gamified';
    phase1Score: number | null;
    constructCoverage: {
      covered: string[];
      missing: string[];
      percent: number;
    };
  };
}

const generateSessionId = (): string => `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

/**
 * Main scoring function that orchestrates all Sprint 1 modules.
 */
export const computeScoring = (params: ComputeScoringParams): ScoringResult => {
  const {
    selectedQuestions,
    answersMap,
    completionTimeSeconds,
    sessionId = generateSessionId(),
    timeHorizonAnswer,
    lossAversionAnswer,
    reverseCodedPairs = [],
    branchingMetadata
  } = params;

  // --- Basic scoring (from legacy riskUtils logic) ---
  let rawSum = 0;
  let rawAdj = 0;
  let maxAdj = 0;
  let rawAdjMPT = 0;
  let maxAdjMPT = 0;
  let rawAdjProspect = 0;
  let maxAdjProspect = 0;

  const maxScoresByQuestion: Record<string, number> = {};

  // MPT vs Prospect weights are unequal (e.g. ~54.5% MPT / ~45.5% Prospect) due to question pool
  // sizes (more MPT questions for the analytical dimension). This is intentional; normalized_mpt
  // and normalized_prospect are computed separately and then combined for the composite score.
  selectedQuestions.forEach((question) => {
    if (!question || question.group === 'SCREENING' || question.maxScore === 0 || question.excludeFromScoring) return;
    maxScoresByQuestion[question.id] = question.maxScore;

    const answerValue = answersMap[question.id];
    rawSum += answerValue ?? 0;
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

  if (maxAdj === 0) {
    throw new Error('Insufficient data for risk assessment. Please answer at least one question.');
  }

  const normalizedScore = Math.min(100, Math.max(0, (rawAdj / maxAdj) * 100));
  const normalizedMPT = maxAdjMPT > 0 ? Math.min(100, Math.max(0, (rawAdjMPT / maxAdjMPT) * 100)) : 0;
  const normalizedProspect = maxAdjProspect > 0 ? Math.min(100, Math.max(0, (rawAdjProspect / maxAdjProspect) * 100)) : 0;

  /** Exclusive upper bounds: score in [0,20) -> very-conservative, [20,40) -> conservative, etc. */
  const categoryFromScore = (score: number): string => {
    if (score < 20) return 'very-conservative';
    if (score < 40) return 'conservative';
    if (score < 60) return 'moderate';
    if (score < 80) return 'aggressive';
    return 'very-aggressive';
  };

  const colorFromCategory = (cat: string): string => {
    switch (cat) {
      case 'very-conservative': return '#00008B';
      case 'conservative': return '#ADD8E6';
      case 'moderate': return '#008000';
      case 'aggressive': return '#FFA500';
      default: return '#FF0000';
    }
  };

  const originalCategory = categoryFromScore(normalizedScore);

  // --- Confidence Band ---
  const confidenceBand = calculateConfidenceBand(
    normalizedScore,
    answersMap,
    normalizedMPT,
    normalizedProspect,
    completionTimeSeconds,
    selectedQuestions.length,
    maxScoresByQuestion
  );

  const visualizationData: VisualizationData = {
    score: normalizedScore,
    band: confidenceBand,
    gradient_intensity: determineGradientIntensity(confidenceBand.band_width),
    boundary_proximity: determineBoundaryProximity(normalizedScore, confidenceBand.lower, confidenceBand.upper)
  };

  // --- Safeguards ---
  const safeguardsResult = applySafeguards({
    score: normalizedScore,
    original_category: originalCategory,
    answers: answersMap,
    maxScoresByQuestion,
    confidenceBand,
    timeHorizonAnswer,
    lossAversionAnswer
  });

  const finalCategory = safeguardsResult.final_category;
  const colorCode = colorFromCategory(finalCategory);

  // --- Adjust Scores if Overridden ---
  // When category is overridden (e.g. time_horizon or high_uncertainty caps at Moderate), we align
  // the displayed composite, MPT, and Prospect scores so the UI is consistent (e.g. not showing
  // "Moderate" with a score of 95). We reduce both MPT and Prospect proportionally by the same
  // factor (capScore / finalScore) so the analytical/emotional balance is preserved; only the
  // overall level is capped. Example: score 95 capped to 60 -> factor 60/95; both dimensions scaled.
  let finalScore = normalizedScore;
  let finalMPT = normalizedMPT;
  let finalProspect = normalizedProspect;

  if (safeguardsResult.category_was_overridden) {
    let capScore = 100;
    switch (finalCategory) {
      case 'very-conservative': capScore = 20; break;
      case 'conservative': capScore = 40; break;
      case 'moderate': capScore = 60; break;
      case 'aggressive': capScore = 80; break;
      default: capScore = 100;
    }

    if (finalScore > capScore) {
      const reductionFactor = capScore / finalScore;
      finalScore = capScore;
      finalMPT = Math.round(finalMPT * reductionFactor);
      finalProspect = Math.round(finalProspect * reductionFactor);
    }
  }

  // --- Consistency Detection ---
  const answersArray = selectedQuestions
    .filter((q) => q.group !== 'SCREENING' && q.maxScore > 0 && !q.excludeFromScoring)
    .map((q) => answersMap[q.id] ?? 1);
  const maxScoresArray = selectedQuestions
    .filter((q) => q.group !== 'SCREENING' && q.maxScore > 0 && !q.excludeFromScoring)
    .map((q) => q.maxScore);

  const consistencyResult = detectConsistencyIssues({
    answers: answersArray,
    maxScores: maxScoresArray,
    totalSeconds: completionTimeSeconds,
    questionCount: selectedQuestions.length,
    reverseCodedPairs
  });

  // --- Monitoring / Logging ---
  const eventDetails = {
    normalized_score: normalizedScore,
    confidence_band: confidenceBand,
    category: finalCategory,
    overrides_applied: safeguardsResult.category_was_overridden && safeguardsResult.override_reason
      ? [safeguardsResult.override_reason]
      : [],
    flags_raised: Object.keys(safeguardsResult.flag_messages),
    completion_time_seconds: completionTimeSeconds,
    mpt_score: normalizedMPT,
    prospect_score: normalizedProspect
  };

  logAssessmentEvent(createAssessmentCompletedEvent(sessionId, eventDetails, { completion_time_seconds: completionTimeSeconds }));

  if (safeguardsResult.category_was_overridden && safeguardsResult.override_reason) {
    logAssessmentEvent(createOverrideTriggeredEvent(sessionId, safeguardsResult.override_reason, eventDetails));
  }

  Object.keys(safeguardsResult.flag_messages).forEach((flagKey) => {
    logAssessmentEvent(createFlagRaisedEvent(sessionId, flagKey, eventDetails));
  });

  return {
    raw_score: rawSum,
    normalized_score: finalScore,
    normalized_mpt: finalMPT,
    normalized_prospect: finalProspect,
    risk_category: finalCategory,
    color_code: colorCode,
    confidence_band: confidenceBand,
    visualization_data: {
      ...visualizationData,
      score: finalScore // Update visualization score
    },
    safeguards: safeguardsResult,
    consistency: consistencyResult,
    branching_metadata: branchingMetadata ? {
      path: branchingMetadata.path,
      phase1_score: branchingMetadata.phase1Score,
      construct_coverage: {
        covered: branchingMetadata.constructCoverage.covered,
        missing: branchingMetadata.constructCoverage.missing,
        percent: branchingMetadata.constructCoverage.percent
      }
    } : {
      path: 'gamified',
      phase1_score: null,
      construct_coverage: {
        covered: [],
        missing: [],
        percent: 0
      }
    }
  };
};
