import { Card, CardContent } from "@/components/ui/card";
import { StepCardHeader } from "@/components/wizard/StepCardHeader";
import { StepHeaderIcon } from "@/components/wizard/StepHeaderIcon";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  ArrowRight,
  Search,
  Shield,
  BarChart3,
  Target,
  Calculator,
  Flame,
  TrendingUp,
  RotateCcw,
  PlayCircle,
  CheckCircle2,
} from "lucide-react";

interface WelcomeStepProps {
  onNext: () => void;
  /** Whether user has saved progress from a previous session */
  hasProgress?: boolean;
  /** The step name where user left off */
  savedStepName?: string;
  /** Callback to clear progress and start fresh */
  onStartFresh?: () => void;
  /** Callback to continue from saved progress */
  onContinue?: () => void;
}

export const WelcomeStep = ({
  onNext,
  hasProgress = false,
  savedStepName,
  onStartFresh,
  onContinue,
}: WelcomeStepProps) => {
  const features = [
    {
      icon: Shield,
      title: "Risk Assessment",
      description:
        "Discover your investment personality through our comprehensive risk profiler",
    },
    {
      icon: Calculator,
      title: "Capital Planning",
      description:
        "Set your investment amount and build a portfolio that fits your budget",
    },
    {
      icon: Search,
      title: "Stock Selection",
      description:
        "Choose from curated picks or search the entire market for your ideal investments",
    },
    {
      icon: BarChart3,
      title: "Portfolio Optimization",
      description:
        "See the efficient frontier and optimize your risk-return balance",
    },
    {
      icon: Target,
      title: "Performance Analysis",
      description: "Understand your expected returns and portfolio composition",
    },
    {
      icon: Flame,
      title: "Stress Testing",
      description:
        "Test your portfolio against historical crises and market scenarios",
    },
  ];

  return (
    <div className="relative" data-tour="welcome-card">
      <Card className="shadow-sm border-t-2 border-t-primary/30">
        <StepCardHeader
          icon={<StepHeaderIcon icon={TrendingUp} size="lg" />}
          title="Welcome to Portfolio Wizard"
          subtitle="A smart, end to end platform for building, optimizing, and validating your investment portfolio. Move step by step from defining your risk profile to rigorously testing your strategy against real world market conditions."
        />

        <CardContent>
          {/* Welcome Back prompt for returning users */}
          {hasProgress && onContinue && onStartFresh && (
            <Alert className="mb-4 bg-primary/5 dark:bg-primary/10 border-primary/20">
              <PlayCircle className="h-4 w-4 text-primary" />
              <AlertDescription className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <span className="text-sm text-foreground">
                  <strong>Welcome back!</strong> You have saved progress
                  {savedStepName && (
                    <span className="text-muted-foreground">
                      {" "}(left off at: {savedStepName})
                    </span>
                  )}
                </span>
                <div className="flex gap-2 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onStartFresh}
                    className="min-h-[36px]"
                  >
                    <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                    Start Fresh
                  </Button>
                  <Button
                    size="sm"
                    onClick={onContinue}
                    className="min-h-[36px]"
                  >
                    <PlayCircle className="h-3.5 w-3.5 mr-1.5" />
                    Continue
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div
                  key={index}
                  className="flex flex-col items-center text-center p-3 rounded-lg bg-muted hover:bg-muted/80 hover:border-primary/30 border border-transparent transition-all duration-200"
                >
                  <div className="w-9 h-9 bg-muted rounded-full flex items-center justify-center mb-2 border border-border">
                    <Icon className="h-4 w-4 text-primary" />
                  </div>
                  <h3 className="font-semibold text-sm md:text-base mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-xs md:text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="bg-muted rounded-lg p-4 mb-4 border border-border">
            <h3 className="font-semibold text-foreground text-base md:text-lg mb-1.5">
              What You'll Learn
            </h3>
            <ul className="space-y-1 text-sm md:text-base">
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full" />
                Your personal risk tolerance and investment style
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full" />
                How to optimize your portfolio for the best risk-return ratio
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full" />
                How your investments might perform during market stress
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary rounded-full" />
                Professional portfolio management techniques
              </li>
            </ul>
          </div>

          <div className="bg-muted/60 rounded-lg p-4 mb-4 border border-border">
            <h3 className="font-semibold text-foreground text-base md:text-lg mb-1.5">
              What You&apos;ll Need
            </h3>
            <ul className="space-y-1.5 text-sm md:text-base text-muted-foreground">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0" aria-hidden />
                How much you want to invest (minimum 1,000 SEK)
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0" aria-hidden />
                Your comfort level with market ups and downs
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0" aria-hidden />
                How long you plan to invest
              </li>
            </ul>
          </div>

          <div className="text-center">
            <Button
              onClick={onNext}
              size="lg"
              className="bg-primary hover:bg-primary/90 transition-colors min-h-[44px] px-6"
              aria-label="Start building your portfolio"
              data-tour="start-button"
            >
              Start Building Your Portfolio
              <ArrowRight className="ml-1.5 h-4 w-4" />
            </Button>
            <p className="text-xs md:text-sm text-muted-foreground mt-2">
              This process takes about 10-15 minutes to complete
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
