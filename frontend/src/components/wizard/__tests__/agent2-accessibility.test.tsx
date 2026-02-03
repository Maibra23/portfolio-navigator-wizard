/**
 * Agent 2 Accessibility Audit
 * - Interactive elements have aria-labels or accessible names
 * - Focus states (handled by shadcn/Radix)
 * - Screen reader progress (QuestionDisplay)
 * - Modals use role="dialog" (Radix Dialog)
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QuestionDisplay } from '../QuestionDisplay';
import { ConfirmationModal } from '../ConfirmationModal';
import { FlagAlerts } from '../FlagAlerts';
import { ScreeningContradiction } from '../ScreeningContradiction';
import { TemporalAnchoringPrompt } from '../TemporalAnchoringPrompt';

describe('Agent 2 Accessibility', () => {
  describe('QuestionDisplay', () => {
    it('announces question progress for screen readers (role=status, aria-label)', () => {
      render(
        <QuestionDisplay
          question={{
            id: 'M2',
            question: 'Test?',
            options: [{ value: 1, text: 'Yes' }],
          }}
          questionNumber={3}
          totalQuestions={12}
          onAnswer={() => {}}
        />
      );
      const status = screen.getByRole('status', { name: /Question progress/i });
      expect(status).toBeInTheDocument();
      expect(status).toHaveAttribute('aria-live', 'polite');
    });

    it('radio group has aria-label for answer options', () => {
      render(
        <QuestionDisplay
          question={{
            id: 'M2',
            question: 'Test?',
            options: [{ value: 1, text: 'Yes' }],
          }}
          questionNumber={1}
          totalQuestions={12}
          onAnswer={() => {}}
        />
      );
      expect(screen.getByRole('radiogroup', { name: 'Answer options' })).toBeInTheDocument();
    });
  });

  describe('ConfirmationModal', () => {
    it('modal has role dialog when open', () => {
      render(
        <ConfirmationModal
          category="Conservative"
          isOpen={true}
          onConfirm={() => {}}
          onReview={() => {}}
          onShowDescription={() => {}}
        />
      );
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByRole('dialog')).toHaveAccessibleName('Please Confirm Your Profile');
    });
  });

  describe('FlagAlerts', () => {
    it('flag region has aria-label', () => {
      render(
        <FlagAlerts
          flags={{
            loss_sensitivity_warning: true,
            response_pattern_warning: false,
            high_uncertainty: false,
          }}
        />
      );
      expect(screen.getByRole('region', { name: /Profile flags/i })).toBeInTheDocument();
    });

    it('dismiss buttons have aria-label', () => {
      render(
        <FlagAlerts
          flags={{
            loss_sensitivity_warning: true,
            response_pattern_warning: false,
            high_uncertainty: false,
          }}
        />
      );
      expect(screen.getByRole('button', { name: 'Dismiss' })).toBeInTheDocument();
    });
  });

  describe('ScreeningContradiction', () => {
    it('dialog has accessible title', () => {
      render(
        <ScreeningContradiction onKeepBeginner={() => {}} onReviseKnowledge={() => {}} />
      );
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByRole('dialog')).toHaveAccessibleName('Clarify your profile');
    });
  });

  describe('TemporalAnchoringPrompt', () => {
    it('CTA button has accessible name', () => {
      render(<TemporalAnchoringPrompt onContinue={() => {}} />);
      expect(screen.getByRole('button', { name: /I understand, let's begin/i })).toBeInTheDocument();
    });
  });

  describe('Responsive / touch targets', () => {
    it('QuestionDisplay option labels have min-height for touch (44px+)', () => {
      const { container } = render(
        <QuestionDisplay
          question={{
            id: 'M2',
            question: 'Test?',
            options: [{ value: 1, text: 'Yes' }],
          }}
          questionNumber={1}
          totalQuestions={12}
          onAnswer={() => {}}
        />
      );
      const label = container.querySelector('label');
      expect(label).toBeInTheDocument();
      expect(label?.className).toMatch(/min-h-\[48px\]/);
    });
  });
});
