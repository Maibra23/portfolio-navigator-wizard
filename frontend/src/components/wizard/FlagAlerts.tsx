import React, { useState, useCallback } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { FLAG_MESSAGES } from './safeguards';

interface FlagAlertsProps {
  flags: {
    loss_sensitivity_warning: boolean;
    response_pattern_warning: boolean;
    extreme_profile_confirmation: boolean;
    high_uncertainty: boolean;
  };
  flagMessages?: Record<string, string>;
  onReviewAnswers?: () => void;
  className?: string;
}

type FlagKey = 'loss_sensitivity_warning' | 'response_pattern_warning' | 'extreme_profile_confirmation' | 'high_uncertainty';

function getMessage(key: FlagKey, flagMessages?: Record<string, string>): string {
  return flagMessages?.[key] ?? FLAG_MESSAGES[key];
}

export const FlagAlerts: React.FC<FlagAlertsProps> = ({
  flags,
  flagMessages,
  onReviewAnswers,
  className
}) => {
  const [dismissed, setDismissed] = useState<Set<FlagKey>>(() => new Set());
  const dismiss = useCallback((key: FlagKey) => {
    setDismissed((prev) => new Set(prev).add(key));
  }, []);

  const alerts: React.ReactNode[] = [];

  if (flags.loss_sensitivity_warning && !dismissed.has('loss_sensitivity_warning')) {
    alerts.push(
      <Alert key="loss_sensitivity" className="relative bg-yellow-50/70 text-yellow-800 border-yellow-200 pr-10">
        <AlertTriangle className="h-4 w-4 text-yellow-600" aria-hidden />
        <AlertTitle className="text-yellow-800">Loss Sensitivity Warning</AlertTitle>
        <AlertDescription className="text-yellow-700">
          {getMessage('loss_sensitivity_warning', flagMessages)}
        </AlertDescription>
        <button
          type="button"
          onClick={() => dismiss('loss_sensitivity_warning')}
          className="absolute right-2 top-2 rounded p-1 text-yellow-600 hover:bg-yellow-200/50 focus:outline-none focus:ring-2 focus:ring-yellow-400"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </Alert>
    );
  }

  if (flags.extreme_profile_confirmation && !dismissed.has('extreme_profile_confirmation')) {
    alerts.push(
      <Alert key="extreme_profile" className="relative bg-blue-50/70 text-blue-800 border-blue-200 pr-10">
        <Info className="h-4 w-4 text-blue-600" aria-hidden />
        <AlertTitle className="text-blue-800">Profile confirmation</AlertTitle>
        <AlertDescription className="text-blue-700">
          {getMessage('extreme_profile_confirmation', flagMessages)}
        </AlertDescription>
        <button
          type="button"
          onClick={() => dismiss('extreme_profile_confirmation')}
          className="absolute right-2 top-2 rounded p-1 text-blue-600 hover:bg-blue-200/50 focus:outline-none focus:ring-2 focus:ring-blue-400"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </Alert>
    );
  }

  if (flags.response_pattern_warning && !dismissed.has('response_pattern_warning')) {
    alerts.push(
      <Alert key="response_pattern" className="relative bg-yellow-50/70 text-yellow-800 border-yellow-200 pr-10">
        <AlertTriangle className="h-4 w-4 text-yellow-600" aria-hidden />
        <AlertTitle className="text-yellow-800">Response Pattern Warning</AlertTitle>
        <AlertDescription className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-yellow-700">
          <p>{getMessage('response_pattern_warning', flagMessages)}</p>
          {onReviewAnswers && (
            <Button onClick={onReviewAnswers} variant="outline" size="sm" className="text-yellow-800 border-yellow-300 hover:bg-yellow-100/50 hover:text-yellow-900 shrink-0">
              Review answers
            </Button>
          )}
        </AlertDescription>
        <button
          type="button"
          onClick={() => dismiss('response_pattern_warning')}
          className="absolute right-2 top-2 rounded p-1 text-yellow-600 hover:bg-yellow-200/50 focus:outline-none focus:ring-2 focus:ring-yellow-400"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </Alert>
    );
  }

  if (flags.high_uncertainty && !dismissed.has('high_uncertainty')) {
    alerts.push(
      <Alert key="high_uncertainty" className="relative bg-blue-50/70 text-blue-800 border-blue-200 pr-10">
        <Info className="h-4 w-4 text-blue-600" aria-hidden />
        <AlertTitle className="text-blue-800">High Uncertainty</AlertTitle>
        <AlertDescription className="text-blue-700">
          {getMessage('high_uncertainty', flagMessages)}
        </AlertDescription>
        <button
          type="button"
          onClick={() => dismiss('high_uncertainty')}
          className="absolute right-2 top-2 rounded p-1 text-blue-600 hover:bg-blue-200/50 focus:outline-none focus:ring-2 focus:ring-blue-400"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </Alert>
    );
  }

  if (alerts.length === 0) return null;

  return <div className={cn('space-y-4', className)} role="region" aria-label="Profile flags">{alerts}</div>;
};