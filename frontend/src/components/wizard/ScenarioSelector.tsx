import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { CheckCircle, Activity, Landmark, Shield, Loader2 } from "lucide-react";

export type ScenarioId = "covid19" | "2008_crisis";

interface ScenarioOption {
  id: ScenarioId;
  title: string;
  description: string;
  details: string[];
  icon: typeof Activity;
}

const SCENARIOS: ScenarioOption[] = [
  {
    id: "covid19",
    title: "2020 COVID-19 Crash",
    description:
      "Fastest market crash in modern history (Feb-Apr 2020). Tests rapid volatility and recovery capability.",
    details: [
      "Crisis Duration: 3 months",
      "Recovery Pattern: V-shaped",
      "Volatility: High",
    ],
    icon: Activity,
  },
  {
    id: "2008_crisis",
    title: "2008 Financial Crisis",
    description:
      "Most severe crisis since Great Depression (Sep 2008 - Mar 2010). Tests prolonged drawdown and recovery behavior.",
    details: ["Crisis Duration: 18 months", "Recovery Pattern: Prolonged"],
    icon: Landmark,
  },
];

interface ScenarioSelectorProps {
  selectedScenario: ScenarioId | null;
  onSelectScenario: (id: ScenarioId) => void;
  onRunTest: () => void;
  isLoading: boolean;
  loadingProgress?: number;
  loadingStep?: string;
  runDisabled?: boolean;
}

export function ScenarioSelector({
  selectedScenario,
  onSelectScenario,
  onRunTest,
  isLoading,
  loadingProgress = 0,
  loadingStep = "",
  runDisabled = false,
}: ScenarioSelectorProps) {
  return (
    <div className="space-y-3">
      <div className="text-center">
        <h3 className="text-base font-semibold mb-1">
          Select Stress Test Scenario
        </h3>
        <p className="text-sm text-muted-foreground">
          Choose one scenario to test your portfolio&apos;s resilience
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SCENARIOS.map((scenario) => {
          const Icon = scenario.icon;
          const isSelected = selectedScenario === scenario.id;
          return (
            <Card
              key={scenario.id}
              className={`cursor-pointer transition-all ${
                isSelected
                  ? "border-2 border-blue-500 bg-blue-50 shadow-md dark:bg-blue-950/30 dark:border-blue-500"
                  : "border border-gray-200 hover:border-gray-300 hover:shadow-sm dark:border-border"
              }`}
              onClick={() => onSelectScenario(scenario.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      {isSelected && (
                        <CheckCircle className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                      )}
                      <Icon className="h-5 w-5 text-blue-600 dark:text-amber-500" />
                      <h3 className="font-semibold text-lg">
                        {scenario.title}
                      </h3>
                    </div>
                    <p className="text-xs text-gray-600 dark:text-muted-foreground mb-3">
                      {scenario.description}
                    </p>
                    <div className="space-y-1 text-xs text-gray-500 dark:text-muted-foreground">
                      {scenario.details.map((line, i) => (
                        <div key={i}>{line}</div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="flex flex-col gap-3 pt-4">
        {isLoading && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{loadingStep}</span>
              <span className="text-muted-foreground">{loadingProgress}%</span>
            </div>
            <Progress value={loadingProgress} className="h-2" />
          </div>
        )}

        <div className="flex justify-center pt-2">
          <Button
            onClick={onRunTest}
            disabled={!selectedScenario || isLoading || runDisabled}
            className="bg-primary hover:bg-primary/90 min-w-[200px]"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Running Stress Test...
              </>
            ) : (
              <>
                <Shield className="mr-2 h-5 w-5" />
                Run Selected Scenario
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
