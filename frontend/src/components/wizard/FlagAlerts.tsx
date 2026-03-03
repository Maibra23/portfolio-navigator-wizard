import React, { useState, useCallback } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { FLAG_MESSAGES } from './safeguards';
import { alertStyles, iconColors, hoverStyles, focusRingStyles } from "@/utils/semanticColors";

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
      <Alert key="loss_sensitivity" className={cn("relative pr-10", alertStyles.warning)}>
        <AlertTriangle className={cn("h-4 w-4", iconColors.warning)} aria-hidden />
        <AlertTitle className="text-amber-800 dark:text-amber-200">Loss Sensitivity Warning</AlertTitle>
        <AlertDescription className="text-amber-700 dark:text-amber-300">
          {getMessage('loss_sensitivity_warning', flagMessages)}
        </AlertDescription>
        <button
          type="button"
          onClick={() => dismiss('loss_sensitivity_warning')}
          className={cn("absolute right-2 top-2 rounded p-1 focus:outline-none", iconColors.warning, hoverStyles.warning, focusRingStyles.warning)}
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </Alert>
    );
  }

  if (flags.extreme_profile_confirmation && !dismissed.has('extreme_profile_confirmation')) {
    alerts.push(
      <Alert key="extreme_profile" className={cn("relative pr-10", alertStyles.info)}>
        <Info className={cn("h-4 w-4", iconColors.info)} aria-hidden />
        <AlertTitle className="text-blue-800 dark:text-blue-200">Profile confirmation</AlertTitle>
        <AlertDescription className="text-blue-700 dark:text-blue-300">
          {getMessage('extreme_profile_confirmation', flagMessages)}
        </AlertDescription>
        <button
          type="button"
          onClick={() => dismiss('extreme_profile_confirmation')}
          className={cn("absolute right-2 top-2 rounded p-1 focus:outline-none", iconColors.info, hoverStyles.info, focusRingStyles.info)}
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </Alert>
    );
  }

  if (flags.response_pattern_warning && !dismissed.has('response_pattern_warning')) {
    alerts.push(
      <Alert key="response_pattern" className={cn("relative pr-10", alertStyles.warning)}>
        <AlertTriangle className={cn("h-4 w-4", iconColors.warning)} aria-hidden />
        <AlertTitle className="text-amber-800 dark:text-amber-200">Response Pattern Warning</AlertTitle>
        <AlertDescription className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-amber-700 dark:text-amber-300">
          <p>{getMessage('response_pattern_warning', flagMessages)}</p>
          {onReviewAnswers && (
            <Button onClick={onReviewAnswers} variant="outline" size="sm" className="text-amber-800 dark:text-amber-200 border-amber-300 dark:border-amber-700 hover:bg-amber-100/50 dark:hover:bg-amber-900/30 hover:text-amber-900 dark:hover:text-amber-100 shrink-0">
              Review answers
            </Button>
          )}
        </AlertDescription>
        <button
          type="button"
          onClick={() => dismiss('response_pattern_warning')}
          className={cn("absolute right-2 top-2 rounded p-1 focus:outline-none", iconColors.warning, hoverStyles.warning, focusRingStyles.warning)}
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </Alert>
    );
  }

  if (flags.high_uncertainty && !dismissed.has('high_uncertainty')) {
    alerts.push(
      <Alert key="high_uncertainty" className={cn("relative pr-10", alertStyles.info)}>
        <Info className={cn("h-4 w-4", iconColors.info)} aria-hidden />
        <AlertTitle className="text-blue-800 dark:text-blue-200">High Uncertainty</AlertTitle>
        <AlertDescription className="text-blue-700 dark:text-blue-300">
          {getMessage('high_uncertainty', flagMessages)}
        </AlertDescription>
        <button
          type="button"
          onClick={() => dismiss('high_uncertainty')}
          className={cn("absolute right-2 top-2 rounded p-1 focus:outline-none", iconColors.info, hoverStyles.info, focusRingStyles.info)}
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