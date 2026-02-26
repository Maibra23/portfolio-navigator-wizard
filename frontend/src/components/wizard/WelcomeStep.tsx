import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  Search,
  Shield,
  BarChart3,
  Target,
  Calculator,
  Flame,
} from "lucide-react";

interface WelcomeStepProps {
  onNext: () => void;
}

export const WelcomeStep = ({ onNext }: WelcomeStepProps) => {
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
    <div className="max-w-4xl mx-auto relative">
      <Card>
        <CardHeader className="text-center pb-3">
          <CardTitle className="text-2xl mb-2">
            Welcome to Portfolio Wizard
          </CardTitle>
          <p className="text-muted-foreground text-base max-w-2xl mx-auto">
            A smart, end to end platform for building, optimizing, and
            validating your investment portfolio. Move step by step from
            defining your risk profile to rigorously testing your strategy
            against real world market conditions.
          </p>
        </CardHeader>

        <CardContent>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div
                  key={index}
                  className="flex flex-col items-center text-center p-3 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
                >
                  <div className="w-9 h-9 bg-muted rounded-full flex items-center justify-center mb-2 border border-border">
                    <Icon className="h-4 w-4 text-primary" />
                  </div>
                  <h3 className="font-semibold text-sm mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="bg-muted rounded-lg p-4 mb-4 border border-border">
            <h3 className="font-semibold text-foreground text-sm mb-1.5">
              What You'll Learn
            </h3>
            <ul className="space-y-1 text-sm">
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

          <div className="text-center">
            <Button
              onClick={onNext}
              size="sm"
              className="bg-primary hover:bg-primary/90 transition-colors"
            >
              Start Building Your Portfolio
              <ArrowRight className="ml-1.5 h-4 w-4" />
            </Button>
            <p className="text-xs text-muted-foreground mt-2">
              This process takes about 10-15 minutes to complete
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
