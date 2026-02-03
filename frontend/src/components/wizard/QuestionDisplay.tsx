import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

export interface QuestionDisplayQuestion {
  id: string;
  question: string;
  options: Array<{ value: number; text: string }>;
  reversed?: boolean;
  ui_note?: string;
}

export interface QuestionDisplayProps {
  question: QuestionDisplayQuestion;
  questionNumber: number;
  totalQuestions: number | '~12';
  onAnswer: (questionId: string, value: number) => void;
  timeTracking?: boolean;
  onTimeReport?: (questionId: string, seconds: number) => void;
  className?: string;
}

const PT13_INTRO =
  "This question helps us understand how market conditions might affect your preferences.";
const PT13_FOOTER =
  "There's no right answer—we're interested in your honest self-assessment.";

function progressPercent(questionNumber: number, totalQuestions: number | '~12'): number {
  const total = typeof totalQuestions === 'number' ? totalQuestions : 12;
  return Math.min(100, Math.round((questionNumber / total) * 100));
}

function progressLabel(questionNumber: number, totalQuestions: number | '~12'): string {
  const total = typeof totalQuestions === 'number' ? String(totalQuestions) : '~12';
  return `Question ${questionNumber} of ${total}`;
}

export const QuestionDisplay: React.FC<QuestionDisplayProps> = ({
  question,
  questionNumber,
  totalQuestions,
  onAnswer,
  timeTracking = false,
  onTimeReport,
  className
}) => {
  const [selected, setSelected] = useState<string>('');
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    if (timeTracking) startTimeRef.current = Date.now();
    setSelected('');
  }, [question.id, timeTracking]);

  const handleNext = () => {
    const value = Number(selected);
    if (Number.isNaN(value) || !question.options.some((o) => o.value === value)) return;
    if (timeTracking && startTimeRef.current != null && onTimeReport) {
      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      onTimeReport(question.id, elapsed);
    }
    onAnswer(question.id, value);
  };

  const hasSelection = selected !== '' && question.options.some((o) => String(o.value) === selected);
  const showPt13Framing = Boolean(question.ui_note);
  const percent = progressPercent(questionNumber, totalQuestions);
  const label = progressLabel(questionNumber, totalQuestions);

  return (
    <Card className={cn('w-full max-w-xl overflow-hidden transition-opacity duration-200', className)}>
      {/* Progress bar at top - announced for screen readers */}
      <div className="px-4 pt-4" role="status" aria-live="polite" aria-label={`Question progress: ${label}`}>
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
          <span>{label}</span>
        </div>
        <Progress value={percent} className="h-1.5" aria-label={`Progress: ${percent}%`} />
      </div>

      <CardHeader className="pb-2">
        {showPt13Framing && (
          <p className="text-sm text-muted-foreground mb-3 rounded-md bg-muted/50 p-3">
            {PT13_INTRO}
          </p>
        )}
        <p className="text-base font-medium text-foreground leading-relaxed">
          {question.question}
        </p>
      </CardHeader>

      <CardContent className="space-y-4 pt-2">
        <RadioGroup
          value={selected}
          onValueChange={setSelected}
          className="grid gap-2"
          aria-label="Answer options"
        >
          {question.options.map((opt) => (
            <Label
              key={opt.value}
              htmlFor={`${question.id}-${opt.value}`}
              className={cn(
                'flex items-center gap-3 rounded-lg border p-4 transition-colors min-h-[48px] cursor-pointer',
                'hover:bg-muted/50 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
                selected === String(opt.value) && 'border-primary bg-primary/5 ring-1 ring-primary/30'
              )}
            >
              <RadioGroupItem
                value={String(opt.value)}
                id={`${question.id}-${opt.value}`}
                className="shrink-0"
              />
              <span className="flex-1 text-sm font-normal leading-snug">
                {opt.text}
              </span>
            </Label>
          ))}
        </RadioGroup>

        {showPt13Framing && (
          <p className="text-xs text-muted-foreground italic pt-1">
            {PT13_FOOTER}
          </p>
        )}

        <div className="pt-2">
          <Button
            type="button"
            onClick={handleNext}
            disabled={!hasSelection}
            className="w-full sm:w-auto min-w-[140px]"
          >
            Next
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
