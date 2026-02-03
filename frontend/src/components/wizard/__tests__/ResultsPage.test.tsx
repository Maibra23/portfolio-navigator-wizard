import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResultsPage } from '../ResultsPage';
import type { ConfidenceBand } from '../confidence-calculator';
import type { SafeguardResult } from '../safeguards';

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

describe('ResultsPage', () => {
  it('renders all main components', () => {
    render(
      <ResultsPage
        scoringResult={baseScoringResult}
        isGamifiedPath={false}
        onReviewAnswers={vi.fn()}
        onContinue={vi.fn()}
      />
    );
    expect(screen.getAllByText('Moderate').length).toBeGreaterThan(0); // CategoryCard
    expect(screen.getByText('Your Risk Profile')).toBeInTheDocument(); // RiskSpectrum
    expect(screen.getByText('Two-Dimensional Risk Map')).toBeInTheDocument(); // TwoDimensionalMap
    expect(screen.getByRole('button', { name: /Continue to Portfolio/i })).toBeInTheDocument();
  });

  it('shows FlagAlerts when flags are present', () => {
    const resultWithFlags = {
      ...baseScoringResult,
      safeguards: {
        ...mockSafeguards,
        flags: { ...mockSafeguards.flags, loss_sensitivity_warning: true },
        flag_messages: { loss_sensitivity_warning: 'Warning message' },
      },
    };
    render(
      <ResultsPage
        scoringResult={resultWithFlags}
        isGamifiedPath={false}
        onReviewAnswers={vi.fn()}
        onContinue={vi.fn()}
      />
    );
    expect(screen.getByText('Warning message')).toBeInTheDocument();
  });

  it('shows ConfirmationModal when extreme profile flag is set', () => {
    const resultWithConfirmation = {
      ...baseScoringResult,
      safeguards: {
        ...mockSafeguards,
        flags: { ...mockSafeguards.flags, extreme_profile_confirmation: true },
      },
    };
    render(
      <ResultsPage
        scoringResult={resultWithConfirmation}
        isGamifiedPath={false}
        onReviewAnswers={vi.fn()}
        onContinue={vi.fn()}
      />
    );
    expect(screen.getByText('Please Confirm Your Profile')).toBeInTheDocument();
  });

  it('handles gamified path correctly (hides 2D map chart)', () => {
    render(
      <ResultsPage
        scoringResult={baseScoringResult}
        isGamifiedPath={true}
        onReviewAnswers={vi.fn()}
        onContinue={vi.fn()}
      />
    );
    expect(screen.getByText('Analytical vs Emotional Risk')).toBeInTheDocument();
    expect(screen.queryByText('Two-Dimensional Risk Map')).not.toBeInTheDocument();
  });

  it('calls actions when buttons clicked', async () => {
    const onReview = vi.fn();
    const onContinue = vi.fn();
    const user = userEvent.setup();
    render(
      <ResultsPage
        scoringResult={baseScoringResult}
        isGamifiedPath={false}
        onReviewAnswers={onReview}
        onContinue={onContinue}
      />
    );
    await user.click(screen.getByRole('button', { name: /Review My Answers/i }));
    expect(onReview).toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: /Continue to Portfolio/i }));
    expect(onContinue).toHaveBeenCalled();
  });
});
