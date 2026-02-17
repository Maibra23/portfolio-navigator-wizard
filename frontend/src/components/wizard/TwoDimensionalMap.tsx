import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useTheme } from "@/hooks/useTheme";
import { getChartTheme } from "@/utils/chartThemes";

interface TwoDimensionalMapProps {
  mptScore: number;
  prospectScore: number;
  isGamifiedPath?: boolean;
  className?: string;
}

// Quadrant explanations (show on click/hover) - exported for use in ResultsPage
export const QUADRANT_EXPLANATIONS = {
  "high-high": {
    title: "Fully Risk-Seeking",
    explanation: "You're comfortable with risk analytically and emotionally.",
    implication: "Your portfolio can align with your analytical preferences.",
  },
  "low-high": {
    title: "Emotionally Bold, Analytically Cautious",
    explanation:
      "You may feel confident about taking risks, but your analytical responses suggest caution.",
    implication:
      "Building investment knowledge may help align your feelings with fundamentals.",
  },
  "high-low": {
    title: "Analytically Bold, Emotionally Cautious",
    explanation:
      "You understand risk-return connection, but may feel uncomfortable during downturns.",
    implication:
      "Consider whether your analytical view or emotional response should guide your portfolio.",
  },
  "low-low": {
    title: "Fully Risk-Averse",
    explanation: "You prefer safety on all dimensions.",
    implication:
      "A conservative portfolio aligns with your complete risk profile.",
  },
} as const;

// Quadrant colors (subtle tints)
const QUADRANT_COLORS = {
  "high-high": "rgba(34, 197, 94, 0.15)", // green tint
  "low-high": "rgba(234, 179, 8, 0.15)", // yellow tint
  "high-low": "rgba(59, 130, 246, 0.15)", // blue tint
  "low-low": "rgba(107, 114, 128, 0.15)", // gray tint
} as const;

type QuadrantKey = keyof typeof QUADRANT_EXPLANATIONS;

export const getQuadrant = (mpt: number, prospect: number): QuadrantKey => {
  const highMpt = mpt >= 50;
  const highProspect = prospect >= 50;
  if (highMpt && highProspect) return "high-high";
  if (!highMpt && highProspect) return "low-high";
  if (highMpt && !highProspect) return "high-low";
  return "low-low";
};

/** Shown as optional disclaimer when under-19; breakdown is always visible. */
export const GAMIFIED_DISCLAIMER =
  "Based on a shorter assessment. Complete the full assessment at 19+ for the most precise breakdown.";

export const TwoDimensionalMap: React.FC<TwoDimensionalMapProps> = ({
  mptScore,
  prospectScore,
  isGamifiedPath = false,
  chartOnly = false,
  className,
}) => {
  const userPoint = useMemo(
    () => [
      {
        x: Math.max(0, Math.min(100, mptScore)),
        y: Math.max(0, Math.min(100, prospectScore)),
      },
    ],
    [mptScore, prospectScore],
  );

  const { theme } = useTheme();
  const chartTheme = getChartTheme(theme);
  const quadrant = getQuadrant(mptScore, prospectScore);
  const explanation = QUADRANT_EXPLANATIONS[quadrant];

  const chartBlock = (
    <div className="relative w-full">
      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 text-[10px] font-medium text-muted-foreground">
        Analytical (MPT) →
      </div>
      <div className="absolute top-1/2 -left-1 -translate-y-1/2 -rotate-90 text-[10px] font-medium text-muted-foreground">
        Emotional (Prospect) →
      </div>
      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 5, right: 5, bottom: 20, left: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis
              type="number"
              dataKey="x"
              domain={[0, 100]}
              ticks={[0, 50, 100]}
              tick={{ fontSize: 10, fill: chartTheme.axes.label }}
            />
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, 100]}
              ticks={[0, 50, 100]}
              tick={{ fontSize: 10, fill: chartTheme.axes.label }}
            />
            <ReferenceArea
              x1={50}
              x2={100}
              y1={50}
              y2={100}
              fill="rgba(16, 185, 129, 0.35)"
            />
            <ReferenceArea
              x1={0}
              x2={50}
              y1={50}
              y2={100}
              fill="rgba(245, 158, 11, 0.35)"
            />
            <ReferenceArea
              x1={50}
              x2={100}
              y1={0}
              y2={50}
              fill="rgba(59, 130, 246, 0.35)"
            />
            <ReferenceArea
              x1={0}
              x2={50}
              y1={0}
              y2={50}
              fill="rgba(156, 163, 175, 0.35)"
            />
            <ReferenceLine
              x={50}
              stroke="#6b7280"
              strokeWidth={1.5}
              strokeDasharray="4 4"
            />
            <ReferenceLine
              y={50}
              stroke="#6b7280"
              strokeWidth={1.5}
              strokeDasharray="4 4"
            />
            <Scatter
              data={userPoint}
              fill="#1e40af"
              shape={(props) => {
                const { cx, cy } = props;
                return (
                  <g>
                    <circle
                      cx={cx}
                      cy={cy}
                      r={14}
                      fill="rgba(30, 64, 175, 0.15)"
                    />
                    <circle
                      cx={cx}
                      cy={cy}
                      r={8}
                      fill="#1e40af"
                      stroke="#fff"
                      strokeWidth={2.5}
                    />
                  </g>
                );
              }}
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3", stroke: "#60a5fa" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const point = payload[0].payload;
                return (
                  <div className="rounded-lg border-2 border-border bg-popover text-popover-foreground p-2.5 shadow-lg text-xs">
                    <div className="font-bold mb-1">Your Position</div>
                    <div>Analytical: {Math.round(point.x)}</div>
                    <div>Emotional: {Math.round(point.y)}</div>
                  </div>
                );
              }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  if (chartOnly) {
    return (
      <TooltipProvider>
        <div className={cn("w-full", className)}>{chartBlock}</div>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <Card className={cn("w-full", className)}>
        <CardHeader className="pb-3 text-center">
          <CardTitle className="text-base font-semibold">
            Risk Breakdown
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Analytical vs Emotional Risk Tolerance
          </p>
        </CardHeader>
        <CardContent className="p-4">
          {chartBlock}
          <div
            className="rounded-lg p-2.5 text-xs border-2 mt-4"
            style={{
              backgroundColor: QUADRANT_COLORS[quadrant],
              borderColor:
                quadrant === "high-high"
                  ? "#10b981"
                  : quadrant === "low-high"
                    ? "#eab308"
                    : quadrant === "high-low"
                      ? "#3b82f6"
                      : "#9ca3af",
            }}
          >
            <div className="font-bold text-foreground">{explanation.title}</div>
            <p className="mt-1 text-muted-foreground leading-snug">
              {explanation.explanation}
            </p>
          </div>
          {isGamifiedPath && (
            <p className="text-xs text-muted-foreground mt-3 text-center">
              {GAMIFIED_DISCLAIMER}
            </p>
          )}
        </CardContent>
      </Card>
    </TooltipProvider>
  );
};
