/**
 * ThemeSelector Component
 *
 * A floating button that allows users to toggle between themes.
 * Displays in the top-right corner with smooth animations.
 */

import React, { useState } from 'react';
import { Moon, Sun, Palette } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface ThemeSelectorProps {
  /** Position of the button (default: fixed top-right) */
  position?: 'fixed' | 'relative' | 'absolute';
  /** Custom className for styling */
  className?: string;
  /** Show theme name label */
  showLabel?: boolean;
}

export const ThemeSelector: React.FC<ThemeSelectorProps> = ({
  position = 'fixed',
  className = '',
  showLabel = false,
}) => {
  const { theme, toggleTheme, themeConfig } = useTheme();
  const [isAnimating, setIsAnimating] = useState(false);

  const handleToggle = () => {
    setIsAnimating(true);
    toggleTheme();

    // Reset animation state after transition
    setTimeout(() => {
      setIsAnimating(false);
    }, 300);
  };

  const isDark = theme === 'dark';
  const Icon = isDark ? Sun : Moon;
  const tooltipText = isDark
    ? 'Switch to Classic Theme'
    : 'Switch to Dark Theme';

  // Position classes
  const positionClass =
    position === 'fixed'
      ? 'fixed top-4 right-4 z-50'
      : position === 'absolute'
        ? 'absolute top-4 right-4'
        : '';

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="outline"
            size={showLabel ? 'default' : 'icon'}
            onClick={handleToggle}
            className={`
              ${positionClass}
              ${className}
              transition-all duration-300 ease-in-out
              hover:scale-105 active:scale-95
              shadow-lg hover:shadow-xl
              backdrop-blur-sm
              ${isDark ? 'bg-card/80 hover:bg-card' : 'bg-card/90 hover:bg-card'}
              border-border
              ${isAnimating ? 'rotate-180' : ''}
            `}
            aria-label={tooltipText}
          >
            <Icon
              className={`
                h-5 w-5
                transition-transform duration-300
                ${isAnimating ? 'scale-110' : ''}
                ${showLabel ? 'mr-2' : ''}
              `}
            />
            {showLabel && (
              <span className="font-medium text-sm">
                {themeConfig.name}
              </span>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="font-medium">
          <div className="flex items-center gap-2">
            <Palette className="h-4 w-4" />
            <span>{tooltipText}</span>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

/**
 * ThemeSelectorInline Component
 *
 * An inline version of the theme selector for embedding in layouts.
 * Shows both theme options as cards for selection.
 */
interface ThemeSelectorInlineProps {
  className?: string;
}

export const ThemeSelectorInline: React.FC<ThemeSelectorInlineProps> = ({
  className = '',
}) => {
  const { theme, setTheme } = useTheme();

  const themes = [
    {
      id: 'original' as const,
      name: 'Classic Theme',
      description: 'Bright theme with professional gradients',
      icon: Sun,
      gradient: 'from-blue-500 to-green-500',
      preview: (
        <div className="h-20 rounded-lg bg-gradient-to-br from-blue-100 to-green-100 border-2 border-blue-200" />
      ),
    },
    {
      id: 'dark' as const,
      name: 'Dark Theme',
      description: 'Minimalist dark theme',
      icon: Moon,
      gradient: 'from-gray-700 to-gray-900',
      preview: (
        <div className="h-20 rounded-lg bg-gradient-to-br from-gray-800 to-gray-950 border-2 border-gray-700" />
      ),
    },
  ];

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 ${className}`}>
      {themes.map((themeOption) => {
        const Icon = themeOption.icon;
        const isSelected = theme === themeOption.id;

        return (
          <button
            key={themeOption.id}
            onClick={() => setTheme(themeOption.id)}
            className={`
              relative p-6 rounded-xl border-2 text-left
              transition-all duration-300 ease-in-out
              hover:scale-[1.02] active:scale-[0.98]
              ${
                isSelected
                  ? 'border-primary bg-primary/5 shadow-lg'
                  : 'border-border bg-card hover:border-primary/50'
              }
            `}
            aria-label={`Select ${themeOption.name}`}
          >
            {isSelected && (
              <div className="absolute top-3 right-3">
                <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center">
                  <svg
                    className="h-4 w-4 text-primary-foreground"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
              </div>
            )}

            <div className="flex items-start gap-4">
              <div
                className={`
                p-3 rounded-lg bg-gradient-to-br ${themeOption.gradient}
                flex items-center justify-center
              `}
              >
                <Icon className="h-6 w-6 text-white" />
              </div>

              <div className="flex-1">
                <h3 className="font-semibold text-lg mb-1">
                  {themeOption.name}
                </h3>
                <p className="text-sm text-muted-foreground mb-3">
                  {themeOption.description}
                </p>
                {themeOption.preview}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
};

export default ThemeSelector;
