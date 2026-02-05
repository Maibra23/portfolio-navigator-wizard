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
    expect(screen.getByText(/Risk Score:/)).toBeInTheDocument(); // RiskSpectrum
    expect(screen.getByText('Risk Breakdown')).toBeInTheDocument(); // Risk breakdown section
    expect(screen.getByRole('button', { name: /Continue/i })).toBeInTheDocument();
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

  it('shows results page with flag alert when extreme profile flag is set (no modal)', () => {
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
    expect(screen.getByText('Risk Breakdown')).toBeInTheDocument();
    expect(screen.getByText(/Your profile is less common/)).toBeInTheDocument();
  });

  it('handles gamified path correctly (shows risk breakdown with disclaimer)', () => {
    render(
      <ResultsPage
        scoringResult={baseScoringResult}
        isGamifiedPath={true}
        onReviewAnswers={vi.fn()}
        onContinue={vi.fn()}
      />
    );
    expect(screen.getByText('Risk Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Analytical vs Emotional Risk Tolerance')).toBeInTheDocument();
    expect(screen.getByText(/Complete the full assessment at 19\+/)).toBeInTheDocument();
    expect(screen.getByText(/Based on a shorter assessment/)).toBeInTheDocument();
    expect(screen.getByText('Analytical')).toBeInTheDocument();
    expect(screen.getByText('Emotional')).toBeInTheDocument();
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
    await user.click(screen.getByRole('button', { name: /Review/i }));
    expect(onReview).toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: /Continue/i }));
    expect(onContinue).toHaveBeenCalled();
  });

  describe('all risk profiles as reference', () => {
    const makeScoringResult = (risk_category: string, normalized_score: number, extreme_flag = false) => ({
      normalized_score,
      normalized_mpt: normalized_score,
      normalized_prospect: normalized_score,
      risk_category,
      confidence_band: mockConfidenceBand,
      visualization_data: mockVisualizationData,
      safeguards: {
        ...mockSafeguards,
        final_category: risk_category,
        flags: { ...mockSafeguards.flags, extreme_profile_confirmation: extreme_flag },
        flag_messages: extreme_flag ? { extreme_profile_confirmation: 'Your profile is less common. Please confirm this feels accurate.' } : {},
      },
    });

    it('renders Very Conservative and shows profile confirmation when flagged', () => {
      const result = makeScoringResult('very-conservative', 15, true);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getAllByText('Very Conservative').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Your profile is less common/)).toBeInTheDocument();
    });

    it('renders Conservative', () => {
      const result = makeScoringResult('conservative', 30, false);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getAllByText('Conservative').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryByText(/Your profile is less common/)).not.toBeInTheDocument();
    });

    it('renders Moderate and does not show profile confirmation', () => {
      const result = makeScoringResult('moderate', 50, false);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getAllByText('Moderate').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryByText(/Your profile is less common/)).not.toBeInTheDocument();
    });

    it('renders Aggressive', () => {
      const result = makeScoringResult('aggressive', 70, false);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getAllByText('Aggressive').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryByText(/Your profile is less common/)).not.toBeInTheDocument();
    });

    it('renders Very Aggressive and shows profile confirmation when flagged', () => {
      const result = makeScoringResult('very-aggressive', 92, true);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getAllByText('Very Aggressive').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Your profile is less common/)).toBeInTheDocument();
    });

    it('Moderate with override: no profile confirmation even if raw score was high', () => {
      const result = {
        ...makeScoringResult('moderate', 60, false),
        safeguards: {
          ...mockSafeguards,
          final_category: 'moderate',
          category_was_overridden: true,
          override_reason: 'time_horizon_override',
          flags: { ...mockSafeguards.flags, extreme_profile_confirmation: false },
          flag_messages: {},
        },
      };
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getAllByText('Moderate').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryByText(/Your profile is less common/)).not.toBeInTheDocument();
    });
  });

  describe('visualizations aligned with assigned risk profile', () => {
    const band = (lower: number, upper: number) => ({
      lower,
      upper,
      primary_category: 'moderate',
      secondary_category: null,
      band_width: upper - lower,
      adjustment_reasons: [] as string[],
    });
    const makeResult = (
      risk_category: string,
      normalized_score: number,
      normalized_mpt: number,
      normalized_prospect: number
    ) => ({
      normalized_score,
      normalized_mpt,
      normalized_prospect,
      risk_category,
      confidence_band: band(
        Math.max(0, normalized_score - 5),
        Math.min(100, normalized_score + 5)
      ),
      visualization_data: { gradient_intensity: 'medium' as const, boundary_proximity: 'far' as const },
      safeguards: {
        ...mockSafeguards,
        final_category: risk_category,
        flags: { ...mockSafeguards.flags, extreme_profile_confirmation: false },
        flag_messages: {},
      },
    });

    it('very-conservative: Risk Score and category match (score in 0–20)', () => {
      const score = 10;
      const result = makeResult('very-conservative', score, 12, 8);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getByText(new RegExp(`Risk Score:\\s*${score}`))).toBeInTheDocument();
      expect(screen.getAllByText('Very Conservative').length).toBeGreaterThanOrEqual(1);
    });

    it('conservative: Risk Score and category match (score in 21–40)', () => {
      const score = 30;
      const result = makeResult('conservative', score, 28, 32);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getByText(new RegExp(`Risk Score:\\s*${score}`))).toBeInTheDocument();
      expect(screen.getAllByText('Conservative').length).toBeGreaterThanOrEqual(1);
    });

    it('moderate: Risk Score and category match (score in 41–60)', () => {
      const score = 50;
      const result = makeResult('moderate', score, 48, 52);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getByText(new RegExp(`Risk Score:\\s*${score}`))).toBeInTheDocument();
      expect(screen.getAllByText('Moderate').length).toBeGreaterThanOrEqual(1);
    });

    it('aggressive: Risk Score and category match (score in 61–80)', () => {
      const score = 70;
      const result = makeResult('aggressive', score, 68, 72);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getByText(new RegExp(`Risk Score:\\s*${score}`))).toBeInTheDocument();
      expect(screen.getAllByText('Aggressive').length).toBeGreaterThanOrEqual(1);
    });

    it('very-aggressive: Risk Score and category match (score in 81–100)', () => {
      const score = 92;
      const result = makeResult('very-aggressive', score, 90, 94);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getByText(new RegExp(`Risk Score:\\s*${score}`))).toBeInTheDocument();
      expect(screen.getAllByText('Very Aggressive').length).toBeGreaterThanOrEqual(1);
    });

    it('override to moderate: displayed score 60 aligns with assigned Moderate profile', () => {
      const result = makeResult('moderate', 60, 58, 62);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getByText(/Risk Score:\s*60/)).toBeInTheDocument();
      expect(screen.getAllByText('Moderate').length).toBeGreaterThanOrEqual(1);
    });

    it('Risk Breakdown shows Analytical and Emotional scores matching passed mpt/prospect', () => {
      const result = makeResult('moderate', 50, 45, 55);
      render(<ResultsPage scoringResult={result} isGamifiedPath={false} onReviewAnswers={vi.fn()} onContinue={vi.fn()} />);
      expect(screen.getByText('45')).toBeInTheDocument();
      expect(screen.getByText('55')).toBeInTheDocument();
    });
  });
});
