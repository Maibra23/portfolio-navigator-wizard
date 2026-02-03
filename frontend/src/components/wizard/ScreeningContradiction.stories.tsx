import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { ScreeningContradiction } from './ScreeningContradiction';
import { Button } from '@/components/ui/button';

const meta: Meta<typeof ScreeningContradiction> = {
  component: ScreeningContradiction,
  title: 'Wizard/ScreeningContradiction',
  parameters: { layout: 'centered' },
};

export default meta;

type Story = StoryObj<typeof ScreeningContradiction>;

export const Default: Story = {
  args: {
    onKeepBeginner: () => {},
    onReviseKnowledge: () => {},
  },
  render: (args) => (
    <ScreeningContradiction
      {...args}
      onKeepBeginner={() => window.alert('Keep beginner')}
      onReviseKnowledge={() => window.alert('Revise knowledge')}
    />
  ),
};

export const WithTrigger: Story = {
  render: function WithTrigger() {
    const [show, setShow] = useState(false);
    return (
      <>
        <Button onClick={() => setShow(true)}>Simulate contradiction (open prompt)</Button>
        {show && (
          <ScreeningContradiction
            onKeepBeginner={() => setShow(false)}
            onReviseKnowledge={() => setShow(false)}
          />
        )}
      </>
    );
  },
};
