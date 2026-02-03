import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { HelpCircle } from 'lucide-react';

export interface ScreeningContradictionProps {
  onKeepBeginner: () => void;
  onReviseKnowledge: () => void;
  className?: string;
}

const CONTENT = {
  message:
    "You indicated significant investment experience but beginner-level knowledge. Which better describes your situation?",
  keep: "I have experience but still consider myself a beginner",
  revise: "I know more than a beginner—let me update my answer",
} as const;

export const ScreeningContradiction: React.FC<ScreeningContradictionProps> = ({
  onKeepBeginner,
  onReviseKnowledge,
  className,
}) => {
  return (
    <Card className={cn("w-full shadow-elegant border-2 border-amber-100", className)}>
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-12 h-12 bg-amber-50 rounded-full flex items-center justify-center mb-4">
          <HelpCircle className="h-6 w-6 text-amber-600" />
        </div>
        <CardTitle className="text-xl font-bold text-foreground">
          Clarify your profile
        </CardTitle>
      </CardHeader>
      <CardContent className="text-center">
        <p className="text-muted-foreground text-sm leading-relaxed">
          {CONTENT.message}
        </p>
      </CardContent>
      <CardFooter className="flex flex-col gap-3 pt-2">
        <Button
          type="button"
          onClick={onKeepBeginner}
          variant="default"
          className="w-full bg-amber-600 hover:bg-amber-700 transition-colors"
        >
          {CONTENT.keep}
        </Button>
        <Button
          type="button"
          onClick={onReviseKnowledge}
          variant="outline"
          className="w-full border-amber-200 text-amber-700 hover:bg-amber-50 transition-colors"
        >
          {CONTENT.revise}
        </Button>
      </CardFooter>
    </Card>
  );
};

/** Trigger: show contradiction prompt when experience is 6-10 or 10+ and knowledge is beginner. */
export function checkScreeningContradiction(experience: string | null, knowledge: string | null): boolean {
  const highExperience = experience === '6-10' || experience === '10+';
  const isBeginner = knowledge === 'beginner';
  return Boolean(highExperience && isBeginner);
}
