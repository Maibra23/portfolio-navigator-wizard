import React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

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
    <Dialog open={true} onOpenChange={() => {}}>
      <DialogContent className={cn('sm:max-w-[425px]', className)}>
        <DialogHeader>
          <DialogTitle className="text-center text-lg font-medium text-foreground">
            Clarify your profile
          </DialogTitle>
          <DialogDescription className="text-center text-sm leading-relaxed mt-2 text-muted-foreground">
            {CONTENT.message}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="flex flex-col gap-3 sm:gap-2 pt-4">
          <Button
            type="button"
            onClick={onKeepBeginner}
            variant="default"
            className="w-full"
          >
            {CONTENT.keep}
          </Button>
          <Button
            type="button"
            onClick={onReviseKnowledge}
            variant="outline"
            className="w-full"
          >
            {CONTENT.revise}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

/** Trigger: show contradiction prompt when experience is 6-10 or 10+ and knowledge is beginner. */
export function checkScreeningContradiction(experience: string | null, knowledge: string | null): boolean {
  const highExperience = experience === '6-10' || experience === '10+';
  const isBeginner = knowledge === 'beginner';
  return Boolean(highExperience && isBeginner);
}
