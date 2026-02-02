/**
 * Construct metadata for risk profiling questions.
 * Maps question IDs to constructs and categories; used for branching and coverage.
 */

export interface ConstructMapping {
  construct: string;
  category: 'mpt' | 'prospect';
  reversed?: true;
  original?: string;
}

export const CONSTRUCT_MAPPINGS: Record<string, ConstructMapping> = {
  // MPT (12 scored; M13, M14, M15 excluded from scoring)
  'M1': { construct: 'time_horizon', category: 'mpt' },
  'M2': { construct: 'time_horizon', category: 'mpt' },
  'M3': { construct: 'volatility_tolerance', category: 'mpt' },
  'M4': { construct: 'capital_allocation', category: 'mpt' },
  'M5': { construct: 'income_requirement', category: 'mpt' },
  'M6': { construct: 'capital_preservation', category: 'mpt' },
  'M7': { construct: 'return_utilization', category: 'mpt' },
  'M8': { construct: 'market_reaction', category: 'mpt' },
  'M9': { construct: 'diversification', category: 'mpt' },
  'M10': { construct: 'liquidity', category: 'mpt' },
  'M11': { construct: 'concentration_risk', category: 'mpt' },
  'M12': { construct: 'recovery_tolerance', category: 'mpt' },

  // Prospect
  'PT-1': { construct: 'certainty_effect', category: 'prospect' },
  'PT-2': { construct: 'loss_aversion', category: 'prospect' },
  'PT-3': { construct: 'regret_aversion', category: 'prospect' },
  'PT-4': { construct: 'probability_weighting', category: 'prospect' },
  'PT-5': { construct: 'sector_preference', category: 'prospect' },
  'PT-6': { construct: 'drawdown_behavior', category: 'prospect' },
  'PT-7': { construct: 'anchoring_bias', category: 'prospect' },
  'PT-8': { construct: 'disposition_effect', category: 'prospect' },
  'PT-9': { construct: 'overconfidence', category: 'prospect' },
  'PT-10': { construct: 'herd_behavior', category: 'prospect' },
  'PT-11': { construct: 'representativeness', category: 'prospect' },
  'PT-12': { construct: 'endowment_effect', category: 'prospect' },
  'PT-13': { construct: 'recency_awareness', category: 'prospect' },

  // Reverse-coded
  'M3-R': { construct: 'volatility_tolerance', category: 'mpt', reversed: true, original: 'M3' },
  'M8-R': { construct: 'market_reaction', category: 'mpt', reversed: true, original: 'M8' },
  'PT-2-R': { construct: 'loss_aversion', category: 'prospect', reversed: true, original: 'PT-2' },

  // Gamified
  'story-1': { construct: 'risk_allocation', category: 'prospect' },
  'story-2': { construct: 'drawdown_behavior', category: 'prospect' },
  'story-3': { construct: 'goal_risk_tradeoff', category: 'prospect' },
  'story-4': { construct: 'concentration_risk', category: 'prospect' },
  'story-5': { construct: 'risk_identity', category: 'prospect' }
};

export const RADAR_CONSTRUCTS: readonly string[] = [
  'time_horizon',
  'volatility_tolerance',
  'loss_aversion',
  'market_reaction',
  'capital_allocation',
  'probability_weighting'
];

export const SCORING_EXCLUSIONS: readonly string[] = ['M13', 'M14', 'M15'];

/**
 * Returns the construct for a question ID, or null if not found.
 */
export function getConstructForQuestion(questionId: string): string | null {
  const mapping = CONSTRUCT_MAPPINGS[questionId];
  return mapping ? mapping.construct : null;
}

/**
 * Returns all question IDs that measure the given construct.
 */
export function getQuestionsForConstruct(construct: string): string[] {
  return Object.entries(CONSTRUCT_MAPPINGS)
    .filter(([, m]) => m.construct === construct)
    .map(([id]) => id);
}
