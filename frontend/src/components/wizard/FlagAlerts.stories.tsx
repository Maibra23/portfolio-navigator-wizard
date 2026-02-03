import type { Meta, StoryObj } from '@storybook/react';
import { FlagAlerts } from './FlagAlerts';

const meta: Meta<typeof FlagAlerts> = {
  component: FlagAlerts,
  title: 'Wizard/FlagAlerts',
  parameters: { layout: 'padded' },
};

export default meta;

type Story = StoryObj<typeof FlagAlerts>;

const noFlags = {
  loss_sensitivity_warning: false,
  response_pattern_warning: false,
  high_uncertainty: false,
};

export const NoFlags: Story = {
  args: { flags: noFlags },
};

export const LossSensitivityOnly: Story = {
  args: {
    flags: {
      ...noFlags,
      loss_sensitivity_warning: true,
    },
  },
};

export const ResponsePatternOnly: Story = {
  args: {
    flags: {
      ...noFlags,
      response_pattern_warning: true,
    },
    onReviewAnswers: () => {},
  },
};

export const HighUncertaintyOnly: Story = {
  args: {
    flags: {
      ...noFlags,
      high_uncertainty: true,
    },
  },
};

export const AllFlags: Story = {
  args: {
    flags: {
      loss_sensitivity_warning: true,
      response_pattern_warning: true,
      high_uncertainty: true,
    },
    onReviewAnswers: () => {},
  },
};

export const CustomFlagMessages: Story = {
  args: {
    flags: {
      loss_sensitivity_warning: true,
      response_pattern_warning: true,
      high_uncertainty: true,
    },
    flagMessages: {
      loss_sensitivity_warning: 'Custom: You may be very sensitive to losses.',
      response_pattern_warning: 'Custom: Your answers showed extreme preferences.',
      high_uncertainty: 'Custom: Your range spans several approaches.',
    },
    onReviewAnswers: () => {},
  },
};
