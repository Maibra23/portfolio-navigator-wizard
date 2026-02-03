import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip
} from 'recharts';
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface TwoDimensionalMapProps {
  mptScore: number;
  prospectScore: number;
  isGamifiedPath?: boolean;
  className?: string;
}

// Quadrant explanations (show on click/hover)
const QUADRANT_EXPLANATIONS = {
  'high-high': {
    title: 'Fully Risk-Seeking',
    explanation: "You're comfortable with risk analytically and emotionally.",
    implication: 'Your portfolio can align with your analytical preferences.'
  },
  'low-high': {
    title: 'Emotionally Bold, Analytically Cautious',
    explanation: 'You may feel confident about taking risks, but your analytical responses suggest caution.',
    implication: 'Building investment knowledge may help align your feelings with fundamentals.'
  },
  'high-low': {
    title: 'Analytically Bold, Emotionally Cautious',
    explanation: 'You understand risk-return connection, but may feel uncomfortable during downturns.',
    implication: 'Consider whether your analytical view or emotional response should guide your portfolio.'
  },
  'low-low': {
    title: 'Fully Risk-Averse',
    explanation: 'You prefer safety on all dimensions.',
    implication: 'A conservative portfolio aligns with your complete risk profile.'
  }
} as const;

// Quadrant colors (subtle tints)
const QUADRANT_COLORS = {
  'high-high': 'rgba(34, 197, 94, 0.15)',   // green tint
  'low-high': 'rgba(234, 179, 8, 0.15)',    // yellow tint
  'high-low': 'rgba(59, 130, 246, 0.15)',   // blue tint
  'low-low': 'rgba(107, 114, 128, 0.15)'   // gray tint
} as const;

type QuadrantKey = keyof typeof QUADRANT_EXPLANATIONS;

const getQuadrant = (mpt: number, prospect: number): QuadrantKey => {
  const highMpt = mpt >= 50;
  const highProspect = prospect >= 50;
  if (highMpt && highProspect) return 'high-high';
  if (!highMpt && highProspect) return 'low-high';
  if (highMpt && !highProspect) return 'high-low';
  return 'low-low';
};

const GAMIFIED_MESSAGE =
  'Complete the full assessment at 19+ to see your analytical vs emotional risk breakdown.';

export const TwoDimensionalMap: React.FC<TwoDimensionalMapProps> = ({
  mptScore,
  prospectScore,
  isGamifiedPath = false,
  className
}) => {
  const userPoint = useMemo(
    () => [{ x: Math.max(0, Math.min(100, mptScore)), y: Math.max(0, Math.min(100, prospectScore)) }],
    [mptScore, prospectScore]
  );

  const quadrant = getQuadrant(mptScore, prospectScore);
  const explanation = QUADRANT_EXPLANATIONS[quadrant];

  if (isGamifiedPath) {
    return (
      <Card className={cn('w-full max-w-lg', className)}>
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-center">
            Analytical vs Emotional Risk
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center">
            {GAMIFIED_MESSAGE}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <TooltipProvider>
      <Card className={cn('w-full max-w-lg', className)}>
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-center">
            Two-Dimensional Risk Map
          </CardTitle>
          <p className="text-xs text-muted-foreground text-center">
            X: Analytical Risk Tolerance (MPT) · Y: Emotional Risk Tolerance (Prospect)
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 16, right: 16, bottom: 24, left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="MPT"
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}`}
                  label={{ value: 'Analytical Risk Tolerance', position: 'bottom', offset: 0, style: { fontSize: 11 } }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="Prospect"
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}`}
                  label={{ value: 'Emotional Risk Tolerance', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }}
                />
                {/* Quadrant background areas */}
                <ReferenceArea x1={50} x2={100} y1={50} y2={100} fill={QUADRANT_COLORS['high-high']} />
                <ReferenceArea x1={0} x2={50} y1={50} y2={100} fill={QUADRANT_COLORS['low-high']} />
                <ReferenceArea x1={50} x2={100} y1={0} y2={50} fill={QUADRANT_COLORS['high-low']} />
                <ReferenceArea x1={0} x2={50} y1={0} y2={50} fill={QUADRANT_COLORS['low-low']} />
                {/* Quadrant dividers at 50/50 */}
                <ReferenceLine x={50} stroke="rgba(0,0,0,0.2)" strokeWidth={1} />
                <ReferenceLine y={50} stroke="rgba(0,0,0,0.2)" strokeWidth={1} />
                <Scatter
                  data={userPoint}
                  fill="#0f172a"
                  shape={(props) => {
                    const { cx, cy } = props;
                    return (
                      <g>
                        <circle cx={cx} cy={cy} r={10} fill="rgba(15, 23, 42, 0.2)" />
                        <circle cx={cx} cy={cy} r={6} fill="#0f172a" className="animate-pulse" />
                      </g>
                    );
                  }}
                />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const point = payload[0].payload;
                    return (
                      <div className="rounded-md border bg-background p-3 shadow-md text-xs">
                        <div className="font-medium">Your position</div>
                        <div>Analytical: {Math.round(point.x)}</div>
                        <div>Emotional: {Math.round(point.y)}</div>
                      </div>
                    );
                  }}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>

          {/* Quadrant labels - clickable/hoverable for explanation */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            {(Object.entries(QUADRANT_EXPLANATIONS) as [QuadrantKey, typeof explanation][]).map(([key, data]) => (
              <UITooltip key={key}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className={cn(
                      'rounded border p-2 text-left transition-colors hover:bg-muted/50',
                      quadrant === key && 'ring-2 ring-primary ring-offset-2'
                    )}
                  >
                    <span className="font-medium">{data.title}</span>
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="font-medium">{data.title}</p>
                  <p className="mt-1 text-muted-foreground">{data.explanation}</p>
                  <p className="mt-1 text-muted-foreground italic">{data.implication}</p>
                </TooltipContent>
              </UITooltip>
            ))}
          </div>

          {/* Current quadrant explanation */}
          <div className="rounded-lg border bg-muted/30 p-3 text-sm">
            <div className="font-medium">{explanation.title}</div>
            <p className="mt-1 text-muted-foreground">{explanation.explanation}</p>
            <p className="mt-1 text-muted-foreground italic">{explanation.implication}</p>
          </div>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
};
