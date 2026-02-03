import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmationModal } from '../ConfirmationModal';

describe('ConfirmationModal', () => {
  it('renders nothing when isOpen is false', () => {
    render(
      <ConfirmationModal
        category="Conservative"
        isOpen={false}
        onConfirm={vi.fn()}
        onReview={vi.fn()}
        onShowDescription={vi.fn()}
      />
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders modal with title and body when open', () => {
    render(
      <ConfirmationModal
        category="Conservative"
        isOpen={true}
        onConfirm={vi.fn()}
        onReview={vi.fn()}
        onShowDescription={vi.fn()}
      />
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Please Confirm Your Profile')).toBeInTheDocument();
    expect(
      screen.getByText(/Your responses indicate a Very Conservative approach/)
    ).toBeInTheDocument();
    expect(screen.getByText(/about 10% of investors/)).toBeInTheDocument();
  });

  it('interpolates category in body text', () => {
    render(
      <ConfirmationModal
        category="Aggressive"
        isOpen={true}
        onConfirm={vi.fn()}
        onReview={vi.fn()}
        onShowDescription={vi.fn()}
      />
    );
    expect(
      screen.getByText(/Your responses indicate a Very Aggressive approach/)
    ).toBeInTheDocument();
  });

  it('shows three action buttons', () => {
    render(
      <ConfirmationModal
        category="Moderate"
        isOpen={true}
        onConfirm={vi.fn()}
        onReview={vi.fn()}
        onShowDescription={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /Yes, this reflects my preferences/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /I'd like to review my answers/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /I'm not sure/i })).toBeInTheDocument();
  });

  it('calls onConfirm when Yes button is clicked', async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    render(
      <ConfirmationModal
        category="Conservative"
        isOpen={true}
        onConfirm={onConfirm}
        onReview={vi.fn()}
        onShowDescription={vi.fn()}
      />
    );
    await user.click(screen.getByRole('button', { name: /Yes, this reflects my preferences/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onReview when review button is clicked', async () => {
    const onReview = vi.fn();
    const user = userEvent.setup();
    render(
      <ConfirmationModal
        category="Conservative"
        isOpen={true}
        onConfirm={vi.fn()}
        onReview={onReview}
        onShowDescription={vi.fn()}
      />
    );
    await user.click(screen.getByRole('button', { name: /I'd like to review my answers/i }));
    expect(onReview).toHaveBeenCalledTimes(1);
  });

  it('calls onShowDescription when I\'m not sure is clicked', async () => {
    const onShowDescription = vi.fn();
    const user = userEvent.setup();
    render(
      <ConfirmationModal
        category="Conservative"
        isOpen={true}
        onConfirm={vi.fn()}
        onReview={vi.fn()}
        onShowDescription={onShowDescription}
      />
    );
    await user.click(screen.getByRole('button', { name: /I'm not sure/i }));
    expect(onShowDescription).toHaveBeenCalledTimes(1);
  });
});
