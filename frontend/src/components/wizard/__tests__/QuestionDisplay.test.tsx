import { describe, it, expect, vi } from 'vitest';
import { render, screen, userEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuestionDisplay } from '../QuestionDisplay';

const normalQuestion = {
  id: 'M2',
  question: 'What is your investment time horizon?',
  options: [
    { value: 1, text: 'Less than 1 year' },
    { value: 2, text: '1–3 years' },
    { value: 3, text: '5–10 years' },
  ],
};

describe('QuestionDisplay', () => {
  it('renders progress and question text', () => {
    render(
      <QuestionDisplay
        question={normalQuestion}
        questionNumber={3}
        totalQuestions={12}
        onAnswer={vi.fn()}
      />
    );
    expect(screen.getByText('Question 3 of 12')).toBeInTheDocument();
    expect(screen.getByText(normalQuestion.question)).toBeInTheDocument();
    normalQuestion.options.forEach((o) => {
      expect(screen.getByText(o.text)).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'Next' })).toBeInTheDocument();
  });

  it('displays approximate total when totalQuestions is ~12', () => {
    render(
      <QuestionDisplay
        question={normalQuestion}
        questionNumber={4}
        totalQuestions="~12"
        onAnswer={vi.fn()}
      />
    );
    expect(screen.getByText('Question 4 of ~12')).toBeInTheDocument();
  });

  it('disables Next until an option is selected', () => {
    render(
      <QuestionDisplay
        question={normalQuestion}
        questionNumber={1}
        totalQuestions={12}
        onAnswer={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  it('enables Next after selection and calls onAnswer with questionId and value', async () => {
    const onAnswer = vi.fn();
    const user = userEvent.setup();
    render(
      <QuestionDisplay
        question={normalQuestion}
        questionNumber={1}
        totalQuestions={12}
        onAnswer={onAnswer}
      />
    );
    await user.click(screen.getByLabelText('5–10 years'));
    expect(screen.getByRole('button', { name: 'Next' })).not.toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer).toHaveBeenCalledWith('M2', 3);
  });

  it('shows PT-13 intro and footer when question has ui_note', () => {
    const pt13 = {
      ...normalQuestion,
      id: 'PT-13',
      ui_note: 'special framing',
    };
    render(
      <QuestionDisplay
        question={pt13}
        questionNumber={11}
        totalQuestions={12}
        onAnswer={vi.fn()}
      />
    );
    expect(
      screen.getByText(/This question helps us understand how market conditions/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/There's no right answer—we're interested in your honest self-assessment/)
    ).toBeInTheDocument();
  });

  it('reverse-coded question displays identically (no reversed badge)', () => {
    const reversed = { ...normalQuestion, id: 'M3-R', reversed: true };
    render(
      <QuestionDisplay
        question={reversed}
        questionNumber={2}
        totalQuestions={12}
        onAnswer={vi.fn()}
      />
    );
    expect(screen.getByText(reversed.question)).toBeInTheDocument();
    expect(screen.queryByText(/reversed/i)).not.toBeInTheDocument();
  });

  it('reports time via onTimeReport when timeTracking is true and user answers', async () => {
    const onAnswer = vi.fn();
    const onTimeReport = vi.fn();
    const user = userEvent.setup();
    render(
      <QuestionDisplay
        question={normalQuestion}
        questionNumber={1}
        totalQuestions={12}
        onAnswer={onAnswer}
        timeTracking={true}
        onTimeReport={onTimeReport}
      />
    );
    await user.click(screen.getByLabelText('5–10 years'));
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(onAnswer).toHaveBeenCalledWith('M2', 3);
    expect(onTimeReport).toHaveBeenCalledTimes(1);
    expect(onTimeReport).toHaveBeenCalledWith('M2', expect.any(Number));
    expect(typeof (onTimeReport.mock.calls[0][1] as number)).toBe('number');
  });
});
