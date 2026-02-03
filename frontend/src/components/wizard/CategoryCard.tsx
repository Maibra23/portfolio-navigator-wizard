import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Shield,
  Lock,
  Scale as BalanceScale,
  TrendingUp,
  Rocket,
  LucideIcon
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface CategoryCardProps {
  category: string;
  secondaryCategory?: string | null;
  score: number;
  className?: string;
}

// Category content as specified in task document
const CATEGORY_CONTENT = {
  'very-conservative': {
    title: 'Very Conservative',
    icon: 'shield',
    summary: "You prioritize protecting your money over growing it.",
    characteristics: [
      "Prefer guaranteed returns",
      "Uncomfortable with market swings",
      "Focus on capital preservation"
    ],
    typical_allocation: "80-100% bonds, 0-20% stocks"
  },
  'conservative': {
    title: 'Conservative',
    icon: 'lock',
    summary: "You accept modest risk for steady growth.",
    characteristics: [
      "Some tolerance for fluctuation",
      "Value consistent income",
      "Prefer slower, steadier growth"
    ],
    typical_allocation: "60-80% bonds, 20-40% stocks"
  },
  'moderate': {
    title: 'Moderate',
    icon: 'balance-scale',
    summary: "You balance growth and stability.",
    characteristics: [
      "Accept ups and downs",
      "Long-term focused",
      "Diversification-minded"
    ],
    typical_allocation: "40-60% bonds, 40-60% stocks"
  },
  'aggressive': {
    title: 'Aggressive',
    icon: 'trending-up',
    summary: "You pursue growth and tolerate volatility.",
    characteristics: [
      "Comfortable with large swings",
      "Very long time horizon",
      "Growth over income"
    ],
    typical_allocation: "20-40% bonds, 60-80% stocks"
  },
  'very-aggressive': {
    title: 'Very Aggressive',
    icon: 'rocket',
    summary: "You seek maximum growth with high risk tolerance.",
    characteristics: [
      "Embrace volatility",
      "Longest time horizon",
      "Concentrated positions acceptable"
    ],
    typical_allocation: "0-20% bonds, 80-100% stocks"
  }
} as const;

// Category colors matching RiskSpectrum
const CATEGORY_COLORS = {
  'very-conservative': '#00008B',
  'conservative': '#ADD8E6',
  'moderate': '#008000',
  'aggressive': '#FFA500',
  'very-aggressive': '#FF0000'
} as const;

// Icon mapping
const ICON_COMPONENTS: Record<string, LucideIcon> = {
  shield: Shield,
  lock: Lock,
  'balance-scale': BalanceScale,
  'trending-up': TrendingUp,
  rocket: Rocket
};

export const CategoryCard: React.FC<CategoryCardProps> = ({
  category,
  secondaryCategory,
  score,
  className
}) => {
  const content = CATEGORY_CONTENT[category as keyof typeof CATEGORY_CONTENT];
  const color = CATEGORY_COLORS[category as keyof typeof CATEGORY_COLORS];

  if (!content) {
    return (
      <Card className={cn("w-full max-w-md", className)}>
        <CardContent className="p-6">
          <p className="text-muted-foreground">Category content not found</p>
        </CardContent>
      </Card>
    );
  }

  const IconComponent = ICON_COMPONENTS[content.icon];

  return (
    <Card className={cn("w-full max-w-md", className)} style={{ borderColor: color }}>
      <CardHeader className="pb-4">
        <div className="flex items-center gap-3">
          {IconComponent && (
            <IconComponent
              className="w-8 h-8 flex-shrink-0"
              style={{ color }}
            />
          )}
          <div>
            <CardTitle className="text-xl font-bold" style={{ color }}>
              {content.title}
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Risk Score: {score}
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <p className="text-sm leading-relaxed">
          {content.summary}
        </p>

        <div>
          <h4 className="text-sm font-semibold mb-2">Your Characteristics:</h4>
          <ul className="space-y-1">
            {content.characteristics.map((characteristic, index) => (
              <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                <span className="w-1 h-1 bg-muted-foreground rounded-full mt-2 flex-shrink-0" />
                {characteristic}
              </li>
            ))}
          </ul>
        </div>

        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium">Typical Allocation:</span> {content.typical_allocation}
          </p>
        </div>

        {secondaryCategory && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground italic">
              You also share some characteristics with{' '}
              <span className="font-medium">
                {CATEGORY_CONTENT[secondaryCategory as keyof typeof CATEGORY_CONTENT]?.title || secondaryCategory}
              </span>{' '}
              investors.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};