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
    typical_allocation: "Stable dividend stocks, broad diversification, low concentration"
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
    typical_allocation: "Mix of stable and growth stocks, diversified, moderate concentration"
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
    typical_allocation: "Balanced mix of value and growth stocks, diversified"
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
    typical_allocation: "Growth-oriented stocks, comfortable with volatility, fewer holdings"
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
    typical_allocation: "High-conviction growth stocks, concentrated positions, long horizon"
  }
} as const;

// Category colors matching RiskSpectrum (more vibrant)
const CATEGORY_COLORS = {
  'very-conservative': '#1e40af',
  'conservative': '#60a5fa',
  'moderate': '#10b981',
  'aggressive': '#f59e0b',
  'very-aggressive': '#ef4444'
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
    <Card 
      className={cn("w-full shadow-md", className)} 
      style={{ 
        borderLeftWidth: '4px',
        borderLeftColor: color,
      }}
    >
      <CardHeader className="pb-3 text-center">
        <div className="flex flex-col items-center justify-center gap-3">
          {IconComponent && (
            <div 
              className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: `${color}15` }}
            >
              <IconComponent
                className="w-6 h-6"
                style={{ color }}
              />
            </div>
          )}
          <div className="min-w-0">
            <CardTitle className="text-lg font-bold" style={{ color }}>
              {content.title}
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">
              {content.summary}
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Characteristics - Compact Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {content.characteristics.map((characteristic, index) => (
            <div 
              key={index} 
              className="text-xs px-2 py-1.5 rounded-md bg-muted/50 text-muted-foreground"
            >
              {characteristic}
            </div>
          ))}
        </div>

        {/* Equity style guidance (stock-only, no bonds) */}
        <div className="flex items-center gap-2 text-xs bg-muted rounded-md p-2 border border-border">
          <span className="font-semibold text-blue-900">Style:</span>
          <span className="text-blue-800">{content.typical_allocation}</span>
        </div>

        {secondaryCategory && (
          <div className="text-xs text-amber-700 bg-amber-50 rounded-md p-2 border border-amber-200">
            Also shares traits with{' '}
            <span className="font-semibold">
              {CATEGORY_CONTENT[secondaryCategory as keyof typeof CATEGORY_CONTENT]?.title || secondaryCategory}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};