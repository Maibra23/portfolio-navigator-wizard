import { useState } from "react";
import { Link } from "react-router-dom";
import { HelpCircle, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

const STEP_HELP: Record<
  string,
  { title: string; points: string[] }
> = {
  welcome: {
    title: "Welcome",
    points: [
      "This wizard guides you from risk assessment to a ready-to-use portfolio.",
      "Your progress is saved automatically so you can leave and come back.",
      "You'll need: investment amount (min 1,000 SEK), your risk comfort, and investment horizon.",
    ],
  },
  risk: {
    title: "Risk Profile",
    points: [
      "We ask a few questions to understand how much market ups and downs you can tolerate.",
      "Your answers determine recommended portfolio style (conservative to aggressive).",
      "There are no wrong answers; be honest so the recommendations fit you.",
    ],
  },
  capital: {
    title: "Capital Input",
    points: [
      "Enter how much you plan to invest (in SEK). Minimum is 1,000 SEK.",
      "This amount is used to size your portfolio and for tax estimates later.",
    ],
  },
  stocks: {
    title: "Stock Selection",
    points: [
      "Start with the mini-lesson to see how risk and return work, then pick a recommended portfolio or build your own.",
      "Recommendations are based on your risk profile. You can customize weights and see expected return and diversification.",
    ],
  },
  optimization: {
    title: "Optimization",
    points: [
      "The chart shows your portfolio vs. the 'efficient frontier' (best risk-return tradeoff).",
      "Use Optimize to get a suggested portfolio that better matches your risk for the same or higher return.",
    ],
  },
  "stress-test": {
    title: "Stress Test",
    points: [
      "See how your portfolio would have behaved in past crises (e.g. COVID-19, 2008).",
      "Overview shows key numbers; use 'Show detailed analysis' for timeline and simulations.",
    ],
  },
  finalize: {
    title: "Finalize Portfolio",
    points: [
      "Review tax impact (Swedish ISK/KF/AF) and get a summary you can export.",
      "Use the tabs to compare account types and see recommendations.",
    ],
  },
  "thank-you": {
    title: "Complete",
    points: [
      "You're done. You can go back to the summary or start over.",
    ],
  },
};

interface StepHelpButtonProps {
  stepId: string;
  className?: string;
}

export function StepHelpButton({ stepId, className }: StepHelpButtonProps) {
  const [open, setOpen] = useState(false);
  const content = STEP_HELP[stepId];

  if (!content) return null;

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={className}
          aria-label="Step help"
        >
          <HelpCircle className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full sm:max-w-sm">
        <SheetHeader>
          <SheetTitle>{content.title} – Help</SheetTitle>
        </SheetHeader>
        <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
          {content.points.map((point, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-primary font-medium">•</span>
              <span>{point}</span>
            </li>
          ))}
        </ul>
        <div className="mt-6 pt-4 border-t border-border">
          <Button variant="outline" size="sm" asChild className="w-full">
            <Link to="/glossary" target="_blank" rel="noopener noreferrer">
              <BookOpen className="mr-2 h-4 w-4" />
              View full glossary
            </Link>
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
