import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Shield } from "lucide-react";

function getResilienceColor(score: number): string {
  if (score >= 70) return "text-green-500 dark:text-green-400";
  if (score >= 50) return "text-yellow-500 dark:text-yellow-400";
  return "text-red-500 dark:text-red-400";
}

function getResilienceBadgeColor(score: number): string {
  if (score >= 70) return "bg-green-500 dark:bg-green-400";
  if (score >= 50) return "bg-yellow-500 dark:bg-yellow-400";
  return "bg-red-500 dark:bg-red-400";
}

function getResilienceLabel(score: number): string {
  if (score >= 70) return "Strong";
  if (score >= 50) return "Moderate";
  return "Weak";
}

interface ResilienceScoreProps {
  score: number;
  assessment: string;
}

export function ResilienceScore({ score, assessment }: ResilienceScoreProps) {
  const clamped = Math.min(100, Math.max(0, score));
  const strokeColor =
    clamped >= 70 ? "#22c55e" : clamped >= 50 ? "#f59e0b" : "#ef4444";
  const circumference = 2 * Math.PI * 56;
  const strokeDash = (clamped / 100) * circumference;

  return (
    <Card className="border-2 border-green-500/30">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Shield className="h-5 w-5 text-green-500 dark:text-green-400" />
          Portfolio Resilience Score
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <div className="relative w-32 h-32">
            <svg
              className="w-32 h-32 transform -rotate-90"
              viewBox="0 0 128 128"
            >
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="currentColor"
                strokeWidth="12"
                fill="none"
                className="text-muted"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke={strokeColor}
                strokeWidth="12"
                fill="none"
                strokeDasharray={`${strokeDash} ${circumference}`}
                strokeLinecap="round"
                className="transition-all duration-700 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div
                  className={`text-2xl font-bold ${getResilienceColor(clamped)}`}
                >
                  {clamped.toFixed(0)}
                </div>
                <div className="text-xs text-muted-foreground">out of 100</div>
              </div>
            </div>
          </div>
          <div className="flex-1">
            <p className="text-sm text-muted-foreground mb-3">{assessment}</p>
            <Badge className={`${getResilienceBadgeColor(score)} text-white`}>
              {getResilienceLabel(score)} Resilience
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
