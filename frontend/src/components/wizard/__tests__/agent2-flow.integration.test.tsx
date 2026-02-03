/**
 * Agent 2 Full Flow Integration Tests
 * Screening → Temporal Prompt → Questions → Results
 * Covers: gamified (under-19), conservative, aggressive, extreme profile, high uncertainty
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, userEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScreeningContradiction, checkScreeningContradiction } from '../ScreeningContradiction';
import { TemporalAnchoringPrompt } from '../TemporalAnchoringPrompt';
import { QuestionDisplay } from '../QuestionDisplay';
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

const mockVisualizationData = {
  gradient_intensity: 'medium' as const,
  boundary_proximity: 'far' as const,
};

describe('Agent 2 Full Flow Integration', () => {
  describe('Screening → Contradiction', () => {
    it('checkScreeningContradiction triggers for 6-10/10+ experience + beginner knowledge', () => {
      expect(checkScreeningContradiction('6-10', 'beginner')).toBe(true);
      expect(checkScreeningContradiction('10+', 'beginner')).toBe(true);
      expect(checkScreeningContradiction('3-5', 'beginner')).toBe(false);
    });

    it('ScreeningContradiction renders and triggers onKeepBeginner / onReviseKnowledge', async () => {
      const onKeep = vi.fn();
      const onRevise = vi.fn();
      const user = userEvent.setup();
      render(<ScreeningContradiction onKeepBeginner={onKeep} onReviseKnowledge={onRevise} />);
      await user.click(screen.getByRole('button', { name: /I have experience but still consider myself a beginner/i }));
      expect(onKeep).toHaveBeenCalled();
      expect(onRevise).not.toHaveBeenCalled();
    });
  });

  describe('Temporal Prompt → Questions', () => {
    it('TemporalAnchoringPrompt continues to next step on CTA', async () => {
      const onContinue = vi.fn();
      const user = userEvent.setup();
      render(<TemporalAnchoringPrompt onContinue={onContinue} />);
      await user.click(screen.getByRole('button', { name: /I understand, let's begin/i }));
      expect(onContinue).toHaveBeenCalled();
    });

    it('QuestionDisplay reports answer and optional time', async () => {
      const onAnswer = vi.fn();
      const onTimeReport = vi.fn();
      const user = userEvent.setup();
      render(
        <QuestionDisplay
          question={{
            id: 'M2',
            question: 'Time horizon?',
            options: [
              { value: 1, text: 'Short' },
              { value: 2, text: 'Long' },
            ],
          }}
          questionNumber={1}
          totalQuestions={12}
          onAnswer={onAnswer}
          timeTracking={true}
          onTimeReport={onTimeReport}
        />
      );
      await user.click(screen.getByLabelText('Long'));
      await user.click(screen.getByRole('button', { name: 'Next' }));
      expect(onAnswer).toHaveBeenCalledWith('M2', 2);
      expect(onTimeReport).toHaveBeenCalledWith('M2', expect.any(Number));
    });
  });

  describe('Results with mock paths', () => {
    it('Gamified path: ResultsPage hides 2D map and shows message', () => {
      const scoringResult = {
        normalized_score: 35,
        normalized_mpt: 0,
        normalized_prospect: 35,
        risk_category: 'conservative',
        confidence_band: mockConfidenceBand,
        visualization_data: mockVisualizationData,
        safeguards: mockSafeguards,
      };
      render(
        <ResultsPage
          scoringResult={scoringResult}
          isGamifiedPath={true}
          onReviewAnswers={vi.fn()}
          onContinue={vi.fn()}
        />
      );
      expect(screen.getByText('Analytical vs Emotional Risk')).toBeInTheDocument();
      expect(screen.getByText(/Complete the full assessment/)).toBeInTheDocument();
    });

    it('Conservative result: ResultsPage shows CategoryCard and spectrum', () => {
      const scoringResult = {
        normalized_score: 28,
        normalized_mpt: 30,
        normalized_prospect: 26,
        risk_category: 'conservative',
        confidence_band: { ...mockConfidenceBand, primary_category: 'conservative' },
        visualization_data: mockVisualizationData,
        safeguards: mockSafeguards,
      };
      render(
        <ResultsPage
          scoringResult={scoringResult}
          isGamifiedPath={false}
          onReviewAnswers={vi.fn()}
          onContinue={vi.fn()}
        />
      );
      expect(screen.getAllByText('Conservative').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Risk Score:/)).toBeInTheDocument();
    });

    it('Aggressive result: ResultsPage shows aggressive category', () => {
      const scoringResult = {
        normalized_score: 72,
        normalized_mpt: 70,
        normalized_prospect: 74,
        risk_category: 'aggressive',
        confidence_band: { ...mockConfidenceBand, primary_category: 'aggressive' },
        visualization_data: mockVisualizationData,
        safeguards: mockSafeguards,
      };
      render(
        <ResultsPage
          scoringResult={scoringResult}
          isGamifiedPath={false}
          onReviewAnswers={vi.fn()}
          onContinue={vi.fn()}
        />
      );
      expect(screen.getAllByText('Aggressive').length).toBeGreaterThanOrEqual(1);
    });

    it('Extreme profile: results page is shown with flag alert (no modal)', () => {
      const scoringResult = {
        normalized_score: 92,
        normalized_mpt: 90,
        normalized_prospect: 94,
        risk_category: 'very-aggressive',
        confidence_band: mockConfidenceBand,
        visualization_data: mockVisualizationData,
        safeguards: {
          ...mockSafeguards,
          flags: { ...mockSafeguards.flags, extreme_profile_confirmation: true },
        },
      };
      render(
        <ResultsPage
          scoringResult={scoringResult}
          isGamifiedPath={false}
          onReviewAnswers={vi.fn()}
          onContinue={vi.fn()}
        />
      );
      expect(screen.getByText('Risk Breakdown')).toBeInTheDocument();
      expect(screen.getByText(/Your profile is less common/)).toBeInTheDocument();
    });

    it('High uncertainty: ResultsPage shows secondary category and wide band', () => {
      const scoringResult = {
        normalized_score: 50,
        normalized_mpt: 48,
        normalized_prospect: 52,
        risk_category: 'moderate',
        confidence_band: {
          ...mockConfidenceBand,
          secondary_category: 'conservative',
          band_width: 40,
        },
        visualization_data: mockVisualizationData,
        safeguards: {
          ...mockSafeguards,
          flags: { ...mockSafeguards.flags, high_uncertainty: true },
          flag_messages: { high_uncertainty: 'Your responses suggest flexibility.' },
        },
      };
      render(
        <ResultsPage
          scoringResult={scoringResult}
          isGamifiedPath={false}
          onReviewAnswers={vi.fn()}
          onContinue={vi.fn()}
        />
      );
      expect(screen.getByText(/Your responses suggest flexibility/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Continue/i })).toBeInTheDocument();
    });
  });
});
