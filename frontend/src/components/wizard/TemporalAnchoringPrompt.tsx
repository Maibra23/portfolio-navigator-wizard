import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface TemporalAnchoringPromptProps {
  onContinue: () => void;
  className?: string;
}

const TEMPORAL_PROMPT_CONTENT = {
  title: 'Before You Begin',
  paragraphs: [
    <>Think about your financial goals and comfort level over the <strong>next 5-10 years</strong>, not just how you feel today.</>,
    <>Markets go through cycles of ups and downs. Consider how you'd feel during both good times and challenging periods.</>,
    <>Your answers should reflect your <strong>typical</strong> preferences, not reactions to recent news or events.</>
  ],
  cta: "I understand, let's begin"
} as const;

export const TemporalAnchoringPrompt: React.FC<TemporalAnchoringPromptProps> = ({
  onContinue,
  className
}) => {
  return (
    <Card className={cn('w-full max-w-lg border-muted/60 bg-card/95 shadow-sm', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Calendar className="h-5 w-5" aria-hidden />
          </div>
          <CardTitle className="text-xl font-semibold text-foreground">
            {TEMPORAL_PROMPT_CONTENT.title}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-2">
        <div className="space-y-3 text-sm leading-relaxed text-muted-foreground">
          {TEMPORAL_PROMPT_CONTENT.paragraphs.map((para, i) => (
            <p key={i} className="text-card-foreground/90">
              {para}
            </p>
          ))}
        </div>
        <Button
          type="button"
          onClick={onContinue}
          className="w-full sm:w-auto min-w-[200px]"
        >
          {TEMPORAL_PROMPT_CONTENT.cta}
        </Button>
      </CardContent>
    </Card>
  );
};
