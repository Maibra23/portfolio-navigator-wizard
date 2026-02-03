import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FlagAlerts } from '../FlagAlerts';
import { FLAG_MESSAGES } from '../safeguards';

const noFlags = {
  loss_sensitivity_warning: false,
  response_pattern_warning: false,
  high_uncertainty: false,
};

describe('FlagAlerts', () => {
  it('renders nothing when no flags are set', () => {
    const { container } = render(<FlagAlerts flags={noFlags} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders loss_sensitivity_warning alert with default message', () => {
    render(
      <FlagAlerts
        flags={{ ...noFlags, loss_sensitivity_warning: true }}
      />
    );
    expect(screen.getByRole('region', { name: /Profile flags/i })).toBeInTheDocument();
    expect(screen.getByText('Loss Sensitivity Warning')).toBeInTheDocument();
    expect(screen.getByText(FLAG_MESSAGES.loss_sensitivity_warning)).toBeInTheDocument();
  });

  it('renders response_pattern_warning alert with review button when onReviewAnswers provided', () => {
    const onReview = vi.fn();
    render(
      <FlagAlerts
        flags={{ ...noFlags, response_pattern_warning: true }}
        onReviewAnswers={onReview}
      />
    );
    expect(screen.getByText('Response Pattern Warning')).toBeInTheDocument();
    expect(screen.getByText(FLAG_MESSAGES.response_pattern_warning)).toBeInTheDocument();
    const reviewBtn = screen.getByRole('button', { name: /Review answers/i });
    expect(reviewBtn).toBeInTheDocument();
  });

  it('calls onReviewAnswers when Review answers is clicked', async () => {
    const onReview = vi.fn();
    const user = userEvent.setup();
    render(
      <FlagAlerts
        flags={{ ...noFlags, response_pattern_warning: true }}
        onReviewAnswers={onReview}
      />
    );
    await user.click(screen.getByRole('button', { name: /Review answers/i }));
    expect(onReview).toHaveBeenCalledTimes(1);
  });

  it('renders high_uncertainty alert with info message', () => {
    render(
      <FlagAlerts
        flags={{ ...noFlags, high_uncertainty: true }}
      />
    );
    expect(screen.getByText('High Uncertainty')).toBeInTheDocument();
    expect(screen.getByText(FLAG_MESSAGES.high_uncertainty)).toBeInTheDocument();
  });

  it('uses custom flagMessages when provided', () => {
    const custom = {
      loss_sensitivity_warning: 'Custom loss message',
      response_pattern_warning: 'Custom pattern message',
      high_uncertainty: 'Custom uncertainty message',
    };
    render(
      <FlagAlerts
        flags={{
          loss_sensitivity_warning: true,
          response_pattern_warning: true,
          high_uncertainty: true,
        }}
        flagMessages={custom}
      />
    );
    expect(screen.getByText('Custom loss message')).toBeInTheDocument();
    expect(screen.getByText('Custom pattern message')).toBeInTheDocument();
    expect(screen.getByText('Custom uncertainty message')).toBeInTheDocument();
  });

  it('dismisses alert when dismiss button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <FlagAlerts
        flags={{ ...noFlags, loss_sensitivity_warning: true }}
      />
    );
    const dismissButtons = screen.getAllByRole('button', { name: 'Dismiss' });
    expect(dismissButtons).toHaveLength(1);
    await user.click(dismissButtons[0]);
    expect(screen.queryByText('Loss Sensitivity Warning')).not.toBeInTheDocument();
  });

  it('renders all three alerts when all flags are true', () => {
    render(
      <FlagAlerts
        flags={{
          loss_sensitivity_warning: true,
          response_pattern_warning: true,
          high_uncertainty: true,
        }}
      />
    );
    expect(screen.getByText('Loss Sensitivity Warning')).toBeInTheDocument();
    expect(screen.getByText('Response Pattern Warning')).toBeInTheDocument();
    expect(screen.getByText('High Uncertainty')).toBeInTheDocument();
  });
});
