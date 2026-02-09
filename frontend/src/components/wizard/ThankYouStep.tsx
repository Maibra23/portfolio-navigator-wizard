import { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle, ArrowLeft, RotateCcw } from 'lucide-react';
import confetti from 'canvas-confetti';

const REDIRECT_SECONDS = 30;

// Theme-aligned colors for confetti (primary blue, accent green, indigo)
const CONFETTI_COLORS = ['#2563eb', '#3b82f6', '#16a34a', '#22c55e', '#6366f1', '#8b5cf6'];

interface ThankYouStepProps {
  onBackToSummary: () => void;
  onStartOver: () => void;
}

export const ThankYouStep = ({ onBackToSummary, onStartOver }: ThankYouStepProps) => {
  const hasTriggeredConfetti = useRef(false);

  useEffect(() => {
    if (hasTriggeredConfetti.current) return;
    hasTriggeredConfetti.current = true;

    const fire = (options: confetti.Options) => {
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: CONFETTI_COLORS,
        ...options,
      });
    };
    fire({});
    const t2 = setTimeout(() => fire({ particleCount: 50, spread: 100, origin: { x: 0.25, y: 0.6 } }), 150);
    const t3 = setTimeout(() => fire({ particleCount: 50, spread: 100, origin: { x: 0.75, y: 0.6 } }), 300);
    return () => {
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, []);

  useEffect(() => {
    const timeoutId = setTimeout(() => onStartOver(), REDIRECT_SECONDS * 1000);
    return () => clearTimeout(timeoutId);
  }, [onStartOver]);

  return (
    <div className="max-w-4xl mx-auto">
      <Card>
        <CardHeader className="text-center pb-4">
          <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center mx-auto mb-4 border border-border">
            <CheckCircle className="h-10 w-10 text-foreground" aria-hidden />
          </div>
          <h2 className="text-2xl font-semibold text-foreground mb-2">Thank you</h2>
          <p className="text-muted-foreground text-lg max-w-xl mx-auto">
            You have completed the Portfolio Navigator Wizard. Your portfolio is set up and you can export your report anytime from the Tax & Summary step.
          </p>
        </CardHeader>
        <CardContent className="text-center space-y-6 pt-2">
          <p className="text-base font-medium text-foreground">
            Good luck with your investments.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
            <Button variant="outline" onClick={onBackToSummary} className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to summary
            </Button>
            <Button onClick={onStartOver} className="gap-2">
              <RotateCcw className="h-4 w-4" />
              Start over
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
