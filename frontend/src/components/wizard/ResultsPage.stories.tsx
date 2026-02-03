import type { Meta, StoryObj } from '@storybook/react';
import { ResultsPage } from './ResultsPage';
import type { ConfidenceBand } from './confidence-calculator';
import type { SafeguardResult } from './safeguards';

const meta: Meta<typeof ResultsPage> = {
  component: ResultsPage,
  title: 'Wizard/ResultsPage',
  parameters: { layout: 'padded' },
};

export default meta;

type Story = StoryObj<typeof ResultsPage>;

// Mock data
const mockConfidenceBand: ConfidenceBand = {
  lower: 45,
  upper: 55,
  primary_category: 'moderate',
  secondary_category: null,
  band_width: 10,
  adjustment_reasons: [],
};

const mockVisualizationData = {
  gradient_intensity: 'medium' as const,
  boundary_proximity: 'far' as const,
};

const mockSafeguards: SafeguardResult = {
  original_category: 'moderate',
  final_category: 'moderate',
  category_was_overridden: false,
  override_reason: null,
  flags: {
    loss_sensitivity_warning: false,
    response_pattern_warning: false,
    extreme_profile_confirmation: false,
    high_uncertainty: false,
  },
  flag_messages: {},
};

const baseScoringResult = {
  normalized_score: 50,
  normalized_mpt: 48,
  normalized_prospect: 52,
  risk_category: 'moderate',
  confidence_band: mockConfidenceBand,
  visualization_data: mockVisualizationData,
  safeguards: mockSafeguards,
};

export const DefaultModerate: Story = {
  args: {
    scoringResult: baseScoringResult,
    isGamifiedPath: false,
    onReviewAnswers: () => {},
    onContinue: () => {},
  },
};

export const WithFlags: Story = {
  args: {
    scoringResult: {
      ...baseScoringResult,
      safeguards: {
        ...mockSafeguards,
        flags: {
          ...mockSafeguards.flags,
          loss_sensitivity_warning: true,
          response_pattern_warning: true,
        },
        flag_messages: {
          loss_sensitivity_warning: 'Warning: High loss sensitivity.',
          response_pattern_warning: 'Warning: Extreme response pattern.',
        },
      },
    },
    isGamifiedPath: false,
    onReviewAnswers: () => {},
    onContinue: () => {},
  },
};

export const ExtremeProfileConfirmation: Story = {
  args: {
    scoringResult: {
      ...baseScoringResult,
      normalized_score: 95,
      risk_category: 'very-aggressive',
      safeguards: {
        ...mockSafeguards,
        flags: {
          ...mockSafeguards.flags,
          extreme_profile_confirmation: true,
        },
      },
    },
    isGamifiedPath: false,
    onReviewAnswers: () => {},
    onContinue: () => {},
  },
};

export const GamifiedPath: Story = {
  args: {
    scoringResult: baseScoringResult,
    isGamifiedPath: true,
    onReviewAnswers: () => {},
    onContinue: () => {},
  },
};

export const HighUncertainty: Story = {
  args: {
    scoringResult: {
      ...baseScoringResult,
      confidence_band: {
        ...mockConfidenceBand,
        secondary_category: 'conservative',
      },
      safeguards: {
        ...mockSafeguards,
        flags: {
          ...mockSafeguards.flags,
          high_uncertainty: true,
        },
        flag_messages: {
          high_uncertainty: 'Your answers suggest a wide range.',
        },
      },
    },
    isGamifiedPath: false,
    onReviewAnswers: () => {},
    onContinue: () => {},
  },
};
