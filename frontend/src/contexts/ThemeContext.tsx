/**
 * Theme Context
 *
 * Provides theme state management and switching functionality
 * throughout the Portfolio Navigator Wizard application.
 */

import React, { createContext, useEffect, useState, ReactNode } from 'react';
import {
  ThemeType,
  DEFAULT_THEME,
  getSavedTheme,
  saveTheme,
  getThemeConfig,
  ThemeConfig,
} from '@/lib/themeConfig';

interface ThemeContextValue {
  /** Current active theme */
  theme: ThemeType;
  /** Current theme configuration */
  themeConfig: ThemeConfig;
  /** Function to switch theme */
  setTheme: (theme: ThemeType) => void;
  /** Toggle between original and dark theme */
  toggleTheme: () => void;
  /** Whether theme is currently being applied */
  isApplying: boolean;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
  /** Optional default theme (for testing) */
  defaultTheme?: ThemeType;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  defaultTheme,
}) => {
  // Initialize theme from localStorage or use default
  const [theme, setThemeState] = useState<ThemeType>(() => {
    return defaultTheme || getSavedTheme();
  });

  const [isApplying, setIsApplying] = useState(false);

  // Get current theme configuration
  const themeConfig = getThemeConfig(theme);

  /**
   * Apply theme to document root
   */
  const applyTheme = (themeId: ThemeType) => {
    setIsApplying(true);

    const root = document.documentElement;
    const config = getThemeConfig(themeId);

    // Remove all theme classes
    root.classList.remove('theme-dark', 'theme-original');

    // Add new theme class (if not default)
    if (config.className) {
      root.classList.add(config.className);
    }

    // Small delay to ensure smooth transition
    setTimeout(() => {
      setIsApplying(false);
    }, 50);
  };

  /**
   * Set theme and persist to localStorage
   */
  const setTheme = (newTheme: ThemeType) => {
    setThemeState(newTheme);
    saveTheme(newTheme);
    applyTheme(newTheme);
  };

  /**
   * Toggle between original and dark theme
   */
  const toggleTheme = () => {
    const newTheme = theme === 'original' ? 'dark' : 'original';
    setTheme(newTheme);
  };

  /**
   * Apply theme on mount and when theme changes
   */
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  /**
   * Listen for system theme preference changes (optional future enhancement)
   */
  useEffect(() => {
    // This is a placeholder for future system preference integration
    // Currently, we let users choose explicitly
  }, []);

  const value: ThemeContextValue = {
    theme,
    themeConfig,
    setTheme,
    toggleTheme,
    isApplying,
  };

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
};

/**
 * Hook to access theme context
 * Use this in components that need theme information or switching
 */
export const useThemeContext = () => {
  const context = React.useContext(ThemeContext);

  if (context === undefined) {
    throw new Error('useThemeContext must be used within a ThemeProvider');
  }

  return context;
};

export default ThemeContext;
