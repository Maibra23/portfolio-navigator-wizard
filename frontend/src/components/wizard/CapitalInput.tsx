import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ArrowRight, ArrowLeft, DollarSign, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface CapitalInputProps {
  onNext: () => void;
  onPrev: () => void;
  onCapitalUpdate: (capital: number) => void;
  currentCapital: number;
}

export const CapitalInput = ({ onNext, onPrev, onCapitalUpdate, currentCapital }: CapitalInputProps) => {
  const [capital, setCapital] = useState(currentCapital > 0 ? currentCapital.toString() : '');
  const [error, setError] = useState('');

  const handleCapitalChange = (value: string) => {
    setCapital(value);
    setError('');
  };

  const handleNext = () => {
    const numCapital = parseFloat(capital);
    
    if (isNaN(numCapital) || numCapital < 1000) {
      setError('Please enter a minimum investment of 1,000 SEK');
      return;
    }

    onCapitalUpdate(numCapital);
    onNext();
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('sv-SE').format(num);
  };

  const capitalValue = parseFloat(capital) || 0;
  const isValid = capitalValue >= 1000;

  return (
    <div className="max-w-2xl mx-auto">
      <Card className="shadow-card">
        <CardHeader className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-primary flex items-center justify-center">
            <DollarSign className="h-8 w-8 text-white" />
          </div>
          <CardTitle className="text-2xl">Investment Capital</CardTitle>
          <p className="text-muted-foreground">
            How much would you like to invest in your portfolio?
          </p>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="capital" className="text-base font-medium">
              Investment Amount (SEK)
            </Label>
            <div className="relative">
              <Input
                id="capital"
                type="number"
                placeholder="10,000"
                value={capital}
                onChange={(e) => handleCapitalChange(e.target.value)}
                className="text-lg h-12 pl-8"
                min="1000"
                step="1000"
              />
              <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">
                kr
              </span>
            </div>
            {capitalValue > 0 && (
              <p className={`text-sm ${isValid ? 'text-green-600' : 'text-orange-600'}`}>
                Investment amount: {formatNumber(capitalValue)} SEK
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

          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="font-medium mb-2">Investment Guidelines</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Minimum investment: 1,000 SEK</li>
              <li>• Consider your financial situation and emergency fund</li>
              <li>• Only invest money you can afford to lose</li>
              <li>• Diversification helps manage risk</li>
            </ul>
          </div>

          <div className="flex gap-4 pt-4">
            <Button variant="outline" onClick={onPrev} className="flex-1">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <Button 
              onClick={handleNext} 
              className="flex-1"
              disabled={!isValid}
            >
              Continue
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
          
          {/* Debug info - remove in production */}
          <div className="text-xs text-muted-foreground bg-muted/30 p-2 rounded">
            Debug: Capital value = {capitalValue}, Valid = {isValid.toString()}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};