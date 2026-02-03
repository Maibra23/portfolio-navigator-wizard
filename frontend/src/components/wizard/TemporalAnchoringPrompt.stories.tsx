import type { Meta, StoryObj } from '@storybook/react';
import { TemporalAnchoringPrompt } from './TemporalAnchoringPrompt';

const meta: Meta<typeof TemporalAnchoringPrompt> = {
  component: TemporalAnchoringPrompt,
  title: 'Wizard/TemporalAnchoringPrompt',
  parameters: { layout: 'centered' },
};

export default meta;

type Story = StoryObj<typeof TemporalAnchoringPrompt>;

export const Default: Story = {
  args: {
    onContinue: () => {},
  },
};

export const WithAlertOnContinue: Story = {
  args: {
    onContinue: () => window.alert('Continued'),
  },
};
