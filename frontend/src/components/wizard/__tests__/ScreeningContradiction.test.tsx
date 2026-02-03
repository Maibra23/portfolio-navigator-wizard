import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScreeningContradiction, checkScreeningContradiction } from '../ScreeningContradiction';

describe('ScreeningContradiction', () => {
  it('renders message and two options', () => {
    render(
      <ScreeningContradiction
        onKeepBeginner={vi.fn()}
        onReviseKnowledge={vi.fn()}
      />
    );
    expect(screen.getByText(/Clarify your profile/i)).toBeInTheDocument();
    expect(
      screen.getByText(/You indicated significant investment experience but beginner-level knowledge/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /I have experience but still consider myself a beginner/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /I know more than a beginner—let me update my answer/i })
    ).toBeInTheDocument();
  });

  it('calls onKeepBeginner when keep button is clicked', async () => {
    const onKeepBeginner = vi.fn();
    const user = userEvent.setup();
    render(
      <ScreeningContradiction
        onKeepBeginner={onKeepBeginner}
        onReviseKnowledge={vi.fn()}
      />
    );
    await user.click(
      screen.getByRole('button', { name: /I have experience but still consider myself a beginner/i })
    );
    expect(onKeepBeginner).toHaveBeenCalledTimes(1);
  });

  it('calls onReviseKnowledge when revise button is clicked', async () => {
    const onReviseKnowledge = vi.fn();
    const user = userEvent.setup();
    render(
      <ScreeningContradiction
        onKeepBeginner={vi.fn()}
        onReviseKnowledge={onReviseKnowledge}
      />
    );
    await user.click(
      screen.getByRole('button', { name: /I know more than a beginner—let me update my answer/i })
    );
    expect(onReviseKnowledge).toHaveBeenCalledTimes(1);
  });
});

describe('checkScreeningContradiction', () => {
  it('returns true when experience is 6-10 and knowledge is beginner', () => {
    expect(checkScreeningContradiction('6-10', 'beginner')).toBe(true);
  });

  it('returns true when experience is 10+ and knowledge is beginner', () => {
    expect(checkScreeningContradiction('10+', 'beginner')).toBe(true);
  });

  it('returns false when experience is 6-10 and knowledge is intermediate', () => {
    expect(checkScreeningContradiction('6-10', 'intermediate')).toBe(false);
  });

  it('returns false when experience is 3-5 and knowledge is beginner', () => {
    expect(checkScreeningContradiction('3-5', 'beginner')).toBe(false);
  });

  it('returns false when experience or knowledge is null', () => {
    expect(checkScreeningContradiction(null, 'beginner')).toBe(false);
    expect(checkScreeningContradiction('10+', null)).toBe(false);
    expect(checkScreeningContradiction(null, null)).toBe(false);
  });
});
