import React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ConfirmationModalProps {
  category: string;
  isOpen: boolean;
  onConfirm: () => void;
  onReview: () => void;
  onShowDescription: () => void;
  className?: string;
}

const ExtremeProfileModalContent = {
  title: "Please Confirm Your Profile",
  body: "Your responses indicate a Very {category} approach. This is less common—about 10% of investors fall into this category.",
  options: {
    confirm: { label: "Yes, this reflects my preferences", action: 'confirm' },
    review: { label: "I'd like to review my answers", action: 'review' },
    showDescription: { label: "I'm not sure", action: 'showDescription' }
  }
} as const;

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  category,
  isOpen,
  onConfirm,
  onReview,
  onShowDescription,
  className
}) => {
  const bodyText = ExtremeProfileModalContent.body.replace('{category}', category);

  return (
    <Dialog open={isOpen} onOpenChange={() => { /* Prevent closing on overlay click */ }}>
      <DialogContent className={cn("sm:max-w-[425px]", className)}>
        <DialogHeader>
          <DialogTitle className="text-center text-lg">
            {ExtremeProfileModalContent.title}
          </DialogTitle>
          <DialogDescription className="text-center text-sm leading-relaxed mt-2">
            {bodyText}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="flex flex-col gap-3 sm:gap-2 pt-4">
          <Button
            type="button"
            onClick={onConfirm}
            className="w-full"
          >
            {ExtremeProfileModalContent.options.confirm.label}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={onReview}
            className="w-full"
          >
            {ExtremeProfileModalContent.options.review.label}
          </Button>
          <Button
            type="button"
            variant="link"
            onClick={onShowDescription}
            className="w-full text-muted-foreground"
          >
            {ExtremeProfileModalContent.options.showDescription.label}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
