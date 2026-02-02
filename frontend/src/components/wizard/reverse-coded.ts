/**
 * Reverse-coded questions for consistency detection.
 * Scoring: use 1 - normalized(answer) when aggregating so that high score on reverse = low on original construct.
 */

export interface ReversedQuestion {
  id: string;
  original_id: string;
  reversed: true;
  group: 'MPT' | 'PROSPECT';
  type: 'mpt' | 'prospect';
  question: string;
  text: string;
  maxScore: number;
  construct: string;
  difficulty?: 'low' | 'medium' | 'high';
  options: Array<{
    label: string;
    value: number;
    text: string;
    score: number;
  }>;
  sliderConfig: {
    min: number;
    max: number;
    step: number;
    labels: { min: string; max: string };
  };
}

/** M3-R: Reverse of M3 (Volatility Tolerance). High = prefers stability = low risk tolerance. */
export const M3_R: ReversedQuestion = {
  id: 'M3-R',
  original_id: 'M3',
  reversed: true,
  group: 'MPT',
  type: 'mpt',
  question: "How important is stability and predictability in your investments?",
  text: "How important is stability and predictability in your investments?",
  maxScore: 5,
  construct: 'volatility_tolerance',
  difficulty: 'low',
  options: [
    { label: 'Not important at all', value: 1, text: 'Not important at all', score: 1 },
    { label: 'Slightly important', value: 2, text: 'Slightly important', score: 2 },
    { label: 'Moderately important', value: 3, text: 'Moderately important', score: 3 },
    { label: 'Very important', value: 4, text: 'Very important', score: 4 },
    { label: 'Extremely important', value: 5, text: 'Extremely important', score: 5 }
  ],
  sliderConfig: {
    min: 1,
    max: 5,
    step: 1,
    labels: { min: 'Not important at all', max: 'Extremely important' }
  }
};

/** M8-R: Reverse of M8 (Market Reaction). High = very concerned = low risk tolerance. */
export const M8_R: ReversedQuestion = {
  id: 'M8-R',
  original_id: 'M8',
  reversed: true,
  group: 'MPT',
  type: 'mpt',
  question: "When markets drop significantly, how concerned do you become about your investments?",
  text: "When markets drop significantly, how concerned do you become about your investments?",
  maxScore: 5,
  construct: 'market_reaction',
  difficulty: 'medium',
  options: [
    { label: 'Not concerned at all', value: 1, text: 'Not concerned at all', score: 1 },
    { label: 'Slightly concerned', value: 2, text: 'Slightly concerned', score: 2 },
    { label: 'Moderately concerned', value: 3, text: 'Moderately concerned', score: 3 },
    { label: 'Quite concerned', value: 4, text: 'Quite concerned', score: 4 },
    { label: 'Very concerned', value: 5, text: 'Very concerned', score: 5 }
  ],
  sliderConfig: {
    min: 1,
    max: 5,
    step: 1,
    labels: { min: 'Not concerned at all', max: 'Very concerned' }
  }
};

/** PT-2-R: Reverse of PT-2 (Loss Aversion). High = avoid larger losses = strong loss aversion. */
export const PT_2_R: ReversedQuestion = {
  id: 'PT-2-R',
  original_id: 'PT-2',
  reversed: true,
  group: 'PROSPECT',
  type: 'prospect',
  question: "How important is it to you to avoid the possibility of larger losses, even if it means accepting a certain smaller loss?",
  text: "How important is it to you to avoid the possibility of larger losses, even if it means accepting a certain smaller loss?",
  maxScore: 4,
  construct: 'loss_aversion',
  difficulty: 'medium',
  options: [
    { label: 'Not important', value: 1, text: 'Not important', score: 1 },
    { label: 'Slightly important', value: 2, text: 'Slightly important', score: 2 },
    { label: 'Quite important', value: 3, text: 'Quite important', score: 3 },
    { label: 'Very important', value: 4, text: 'Very important', score: 4 }
  ],
  sliderConfig: {
    min: 1,
    max: 4,
    step: 1,
    labels: { min: 'Not important', max: 'Very important' }
  }
};

/** All reverse-coded questions in one array for pooling or iteration. */
export const REVERSE_CODED_QUESTIONS: ReversedQuestion[] = [M3_R, M8_R, PT_2_R];
