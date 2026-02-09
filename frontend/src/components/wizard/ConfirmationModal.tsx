import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { AlertCircle } from 'lucide-react';

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
  if (!isOpen) return null;

  const bodyText = ExtremeProfileModalContent.body.replace('{category}', category);

  return (
    <Card className={cn("w-full border border-border", className)}>
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center mb-4">
          <AlertCircle className="h-6 w-6 text-blue-600" />
        </div>
        <CardTitle className="text-xl font-bold text-foreground">
          {ExtremeProfileModalContent.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-center space-y-4">
        <p className="text-muted-foreground text-sm leading-relaxed">
          {bodyText}
        </p>
      </CardContent>
      <CardFooter className="flex flex-col gap-3 pt-2">
        <Button
          type="button"
          onClick={onConfirm}
          className="w-full bg-primary text-primary-foreground hover:opacity-90 transition-colors"
        >
          {ExtremeProfileModalContent.options.confirm.label}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={onReview}
          className="w-full border-border text-foreground hover:bg-accent transition-colors"
        >
          {ExtremeProfileModalContent.options.review.label}
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={onShowDescription}
          className="w-full text-muted-foreground hover:text-foreground transition-colors text-xs"
        >
          {ExtremeProfileModalContent.options.showDescription.label}
        </Button>
      </CardFooter>
    </Card>
  );
};
