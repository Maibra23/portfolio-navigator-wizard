import type { Meta, StoryObj } from '@storybook/react';
import { QuestionDisplay } from './QuestionDisplay';
import type { QuestionDisplayQuestion } from './QuestionDisplay';

const meta: Meta<typeof QuestionDisplay> = {
  component: QuestionDisplay,
  title: 'Wizard/QuestionDisplay',
  parameters: { layout: 'centered' },
};

export default meta;

type Story = StoryObj<typeof QuestionDisplay>;

const normalQuestion: QuestionDisplayQuestion = {
  id: 'M2',
  question: 'What is your investment time horizon?',
  options: [
    { value: 1, text: 'Less than 1 year' },
    { value: 2, text: '1–3 years' },
    { value: 3, text: '3–5 years' },
    { value: 4, text: '5–10 years' },
    { value: 5, text: 'More than 10 years' },
  ],
};

const reversedQuestion: QuestionDisplayQuestion = {
  id: 'M3-R',
  question: 'How important is stability in your investments?',
  options: [
    { value: 1, text: 'Not important at all' },
    { value: 2, text: 'Slightly important' },
    { value: 3, text: 'Moderately important' },
    { value: 4, text: 'Very important' },
    { value: 5, text: 'Extremely important' },
  ],
  reversed: true,
};

const pt13Question: QuestionDisplayQuestion = {
  id: 'PT-13',
  question:
    "Imagine two scenarios: In Scenario A, the market dropped 30% last month. In Scenario B, the market gained 30% last month. How would your answers to this questionnaire differ between these scenarios?",
  options: [
    { value: 1, text: "I would be much more conservative after a drop (Scenario A)" },
    { value: 2, text: "I would be somewhat more conservative after a drop" },
    { value: 3, text: "My answers wouldn't change much either way" },
    { value: 4, text: "I might actually be more aggressive after a drop (buying opportunity)" },
  ],
  ui_note: 'Display with special framing - this is a self-awareness question',
};

export const NormalQuestion: Story = {
  args: {
    question: normalQuestion,
    questionNumber: 3,
    totalQuestions: 12,
    onAnswer: () => {},
  },
};

export const ReverseCodedQuestion: Story = {
  args: {
    question: reversedQuestion,
    questionNumber: 5,
    totalQuestions: 12,
    onAnswer: () => {},
  },
};

export const PT13WithSpecialFraming: Story = {
  args: {
    question: pt13Question,
    questionNumber: 11,
    totalQuestions: 12,
    onAnswer: () => {},
  },
};

export const AdaptivePathApproximateTotal: Story = {
  args: {
    question: normalQuestion,
    questionNumber: 4,
    totalQuestions: '~12',
    onAnswer: () => {},
  },
};

export const FirstQuestion: Story = {
  args: {
    question: normalQuestion,
    questionNumber: 1,
    totalQuestions: 12,
    onAnswer: () => {},
  },
};

export const LastQuestion: Story = {
  args: {
    question: normalQuestion,
    questionNumber: 12,
    totalQuestions: 12,
    onAnswer: () => {},
  },
};

export const WithTimeTracking: Story = {
  args: {
    question: normalQuestion,
    questionNumber: 2,
    totalQuestions: 12,
    onAnswer: () => {},
    timeTracking: true,
    onTimeReport: () => {},
  },
};
