import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TemporalAnchoringPrompt } from '../TemporalAnchoringPrompt';

describe('TemporalAnchoringPrompt', () => {
  it('renders title and paragraphs', () => {
    render(<TemporalAnchoringPrompt onContinue={vi.fn()} />);
    expect(screen.getByText('Before You Begin')).toBeInTheDocument();
    expect(screen.getByText(/Think about your financial goals and comfort level over the/)).toBeInTheDocument();
    expect(screen.getByText('next 5-10 years')).toBeInTheDocument();
    expect(screen.getByText(/Markets go through cycles/)).toBeInTheDocument();
    expect(screen.getByText(/Your answers should reflect your/)).toBeInTheDocument();
    expect(screen.getByText('typical')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /I understand, let's begin/i })).toBeInTheDocument();
  });

  it('calls onContinue when CTA is clicked', async () => {
    const onContinue = vi.fn();
    const user = userEvent.setup();
    render(<TemporalAnchoringPrompt onContinue={onContinue} />);
    await user.click(screen.getByRole('button', { name: /I understand, let's begin/i }));
    expect(onContinue).toHaveBeenCalledTimes(1);
  });
});
