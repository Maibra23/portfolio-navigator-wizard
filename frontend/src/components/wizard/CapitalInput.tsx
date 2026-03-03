import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { StepCardHeader } from "@/components/wizard/StepCardHeader";
import { StepHeaderIcon } from "@/components/wizard/StepHeaderIcon";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowRight, ArrowLeft, DollarSign, AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface CapitalInputProps {
  onNext: () => void;
  onPrev: () => void;
  onCapitalUpdate: (capital: number) => void;
  currentCapital: number;
}

export const CapitalInput = ({
  onNext,
  onPrev,
  onCapitalUpdate,
  currentCapital,
}: CapitalInputProps) => {
  const [capital, setCapital] = useState(
    currentCapital > 0 ? currentCapital.toString() : "",
  );
  const [error, setError] = useState("");

  const handleCapitalChange = (value: string) => {
    setCapital(value);
    setError("");
  };

  const handleNext = () => {
    const numCapital = parseFloat(capital);

    if (isNaN(numCapital) || numCapital < 1000) {
      setError("Please enter a minimum investment of 1,000 SEK");
      return;
    }

    onCapitalUpdate(numCapital);
    onNext();
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("sv-SE").format(num);
  };

  const capitalValue = parseFloat(capital) || 0;
  const isValid = capitalValue >= 1000;

  return (
    <div>
      <Card className="shadow-sm border-t-2 border-t-primary/30">
        <StepCardHeader
          icon={<StepHeaderIcon icon={DollarSign} size="md" />}
          title="Investment Capital"
          subtitle="How much would you like to invest in your portfolio?"
        />

        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="capital" className="text-xs md:text-sm font-medium">
              Investment Amount (SEK)
            </Label>
            <div className="relative">
              <Input
                id="capital"
                type="number"
                placeholder="10,000"
                value={capital}
                onChange={(e) => handleCapitalChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleNext();
                  }
                }}
                className="text-sm md:text-base min-h-[44px] pl-8"
                style={{ fontFamily: "inherit", fontWeight: "normal" }}
                min="1000"
                step="1000"
              />
              <span
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground text-sm"
                style={{ fontWeight: "normal" }}
              >
                kr
              </span>
            </div>
            {capitalValue > 0 && (
              <p
                className={`text-sm ${isValid ? "text-moderate" : "text-destructive"}`}
                style={{ fontFamily: "inherit", fontWeight: "normal" }}
              >
                Investment amount:{" "}
                <span style={{ fontWeight: "normal" }}>
                  {formatNumber(capitalValue)}
                </span>{" "}
                SEK
                {!isValid && capitalValue > 0 && (
                  <span className="ml-2">(Minimum 1,000 SEK required)</span>
                )}
              </p>
            )}
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="bg-muted/50 rounded-lg p-3">
            <h4 className="font-medium text-xs md:text-sm mb-1.5">
              Investment Guidelines
            </h4>
            <ul className="text-xs text-muted-foreground space-y-0.5">
              <li>• Minimum investment: 1,000 SEK</li>
              <li>• Consider your financial situation and emergency fund</li>
              <li>• Only invest money you can afford to lose</li>
              <li>• Diversification helps manage risk</li>
            </ul>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 pt-4">
            <Button variant="outline" onClick={onPrev} className="flex-1 min-h-[44px]" aria-label="Go to previous step">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <Button onClick={handleNext} className="flex-1 min-h-[44px]" disabled={!isValid} aria-label="Continue to next step">
              Continue
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
