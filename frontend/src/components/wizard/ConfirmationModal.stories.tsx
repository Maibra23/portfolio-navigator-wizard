import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { ConfirmationModal } from './ConfirmationModal';
import { Button } from '@/components/ui/button';

const meta: Meta<typeof ConfirmationModal> = {
  component: ConfirmationModal,
  title: 'Wizard/ConfirmationModal',
  parameters: { layout: 'centered' },
};

export default meta;

type Story = StoryObj<typeof ConfirmationModal>;

export const Closed: Story = {
  args: {
    category: 'Conservative',
    isOpen: false,
    onConfirm: () => {},
    onReview: () => {},
    onShowDescription: () => {},
  },
};

export const OpenVeryConservative: Story = {
  args: {
    category: 'Conservative',
    isOpen: true,
    onConfirm: () => {},
    onReview: () => {},
    onShowDescription: () => {},
  },
};

export const OpenVeryAggressive: Story = {
  args: {
    category: 'Aggressive',
    isOpen: true,
    onConfirm: () => {},
    onReview: () => {},
    onShowDescription: () => {},
  },
};

export const OpenModerate: Story = {
  args: {
    category: 'Moderate',
    isOpen: true,
    onConfirm: () => {},
    onReview: () => {},
    onShowDescription: () => {},
  },
};

export const WithTrigger: Story = {
  render: function WithTrigger() {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button onClick={() => setOpen(true)}>Show confirmation</Button>
        <ConfirmationModal
          category="Aggressive"
          isOpen={open}
          onConfirm={() => setOpen(false)}
          onReview={() => setOpen(false)}
          onShowDescription={() => setOpen(false)}
        />
      </>
    );
  },
};
