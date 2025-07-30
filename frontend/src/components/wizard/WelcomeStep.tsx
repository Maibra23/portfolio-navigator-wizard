import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowRight, TrendingUp, Shield, BarChart3, Target, Calculator, AlertTriangle } from 'lucide-react';

interface WelcomeStepProps {
  onNext: () => void;
}

export const WelcomeStep = ({ onNext }: WelcomeStepProps) => {
  const features = [
    {
      icon: Shield,
      title: 'Risk Assessment',
      description: 'Discover your investment personality through our comprehensive risk profiler'
    },
    {
      icon: Calculator,
      title: 'Capital Planning',
      description: 'Set your investment amount and build a portfolio that fits your budget'
    },
    {
      icon: TrendingUp,
      title: 'Stock Selection',
      description: 'Choose from curated picks or search the entire market for your ideal investments'
    },
    {
      icon: BarChart3,
      title: 'Portfolio Optimization',
      description: 'See the efficient frontier and optimize your risk-return balance'
    },
    {
      icon: Target,
      title: 'Performance Analysis',
      description: 'Understand your expected returns and portfolio composition'
    },
    {
      icon: AlertTriangle,
      title: 'Stress Testing',
      description: 'Test your portfolio against historical crises and market scenarios'
    }
  ];

  return (
    <div className="max-w-4xl mx-auto">
      <Card className="shadow-elegant">
        <CardHeader className="text-center pb-6">
          <div className="w-16 h-16 bg-gradient-primary rounded-full flex items-center justify-center mx-auto mb-4">
            <TrendingUp className="h-8 w-8 text-primary-foreground" />
          </div>
          <CardTitle className="text-3xl mb-4">Welcome to Portfolio Wizard</CardTitle>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Your complete guide to building, optimizing, and testing a custom investment portfolio. 
            We'll walk you through every step, from understanding your risk tolerance to stress-testing 
            your investments against real market scenarios.
          </p>
        </CardHeader>
        
        <CardContent>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div key={index} className="flex flex-col items-center text-center p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
                  <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
                    <Icon className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-2">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </div>
              );
            })}
          </div>

          <div className="bg-accent/10 rounded-lg p-6 mb-8">
            <h3 className="font-semibold text-accent mb-2">What You'll Learn</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-accent rounded-full" />
                Your personal risk tolerance and investment style
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-accent rounded-full" />
                How to optimize your portfolio for the best risk-return ratio
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-accent rounded-full" />
                How your investments might perform during market stress
              </li>
              <li className="flex items-center gap-2">
                <div className="w-2 h-2 bg-accent rounded-full" />
                Professional portfolio management techniques
              </li>
            </ul>
          </div>

          <div className="text-center">
            <Button 
              onClick={onNext} 
              size="lg" 
              className="bg-gradient-primary hover:opacity-90 transition-opacity"
            >
              Start Building Your Portfolio
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <p className="text-xs text-muted-foreground mt-3">
              This process takes about 10-15 minutes to complete
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};