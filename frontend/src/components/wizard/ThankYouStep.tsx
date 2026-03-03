import { useEffect, useState, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { StepCardHeader } from "@/components/wizard/StepCardHeader";
import { StepHeaderIcon } from "@/components/wizard/StepHeaderIcon";
import { Button } from "@/components/ui/button";
import { CheckCircle, ArrowLeft, RotateCcw } from "lucide-react";
import confetti from "canvas-confetti";

const REDIRECT_SECONDS = 30;

const CONFETTI_COLORS = [
  "#2563eb",
  "#3b82f6",
  "#16a34a",
  "#22c55e",
  "#6366f1",
  "#8b5cf6",
];

interface ThankYouStepProps {
  onBackToSummary: () => void;
  onStartOver: () => void;
}

export const ThankYouStep = ({
  onBackToSummary,
  onStartOver,
}: ThankYouStepProps) => {
  const hasTriggeredConfetti = useRef(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [autoRedirectEnabled, setAutoRedirectEnabled] = useState(true);

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
    const t2 = setTimeout(
      () =>
        fire({ particleCount: 50, spread: 100, origin: { x: 0.25, y: 0.6 } }),
      150,
    );
    const t3 = setTimeout(
      () =>
        fire({ particleCount: 50, spread: 100, origin: { x: 0.75, y: 0.6 } }),
      300,
    );
    return () => {
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, []);

  useEffect(() => {
    if (!autoRedirectEnabled) return;
    setCountdown(REDIRECT_SECONDS);
  }, [autoRedirectEnabled]);

  useEffect(() => {
    if (countdown === null || countdown <= 0) return;
    const t = setTimeout(() => {
      setCountdown((c) => (c !== null && c <= 1 ? 0 : c - 1));
    }, 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  useEffect(() => {
    if (countdown === 0 && autoRedirectEnabled) {
      onStartOver();
    }
  }, [countdown, autoRedirectEnabled, onStartOver]);

  const handleStayHere = () => {
    setAutoRedirectEnabled(false);
    setCountdown(null);
  };

  return (
    <div>
      <Card className="shadow-sm border-t-2 border-t-primary/30">
        <StepCardHeader
          icon={<StepHeaderIcon icon={CheckCircle} size="lg" />}
          title="Thank you"
          subtitle="You have completed the Portfolio Navigator Wizard. Your portfolio is set up and you can export your report anytime from the Tax & Summary step."
        />
        <CardContent className="text-center space-y-3 pt-0">
          <p className="text-sm md:text-base font-medium text-foreground">
            Good luck with your investments.
          </p>
          {autoRedirectEnabled && countdown !== null && countdown > 0 && (
            <p className="text-xs md:text-sm text-muted-foreground">
              Starting over in {countdown} seconds.{" "}
              <button
                type="button"
                onClick={handleStayHere}
                className="underline hover:no-underline text-primary font-medium"
              >
                Stay here
              </button>
            </p>
          )}
          <div className="flex flex-col sm:flex-row gap-2 justify-center pt-4">
            <Button
              variant="outline"
              onClick={onBackToSummary}
              className="gap-2 min-h-[44px]"
              aria-label="Back to Tax & Summary"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to summary
            </Button>
            <Button onClick={onStartOver} className="gap-2 min-h-[44px]" aria-label="Start wizard over">
              <RotateCcw className="h-4 w-4" />
              Start over
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
