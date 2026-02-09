/**
 * Theme Configuration
 *
 * Defines the two available themes for the Portfolio Navigator Wizard:
 * 1. Original Theme (default) - Classic light theme with gradients
 * 2. Dark Theme (alternative) - Linear-inspired minimalist dark theme
 */

export type ThemeType = 'original' | 'dark';

export interface ThemeConfig {
  id: ThemeType;
  name: string;
  description: string;
  className: string;
  preview: {
    background: string;
    text: string;
    accent: string;
  };
}

/**
 * Original Theme (Default)
 * - Bright, professional light theme
 * - Blue and green gradients
 * - Perfect for daytime use
 * - High contrast for readability
 */
export const ORIGINAL_THEME: ThemeConfig = {
  id: 'original',
  name: 'Classic Theme',
  description: 'Bright theme with professional gradients',
  className: '', // No class needed - it's the default :root
  preview: {
    background: 'hsl(210 20% 98%)',
    text: 'hsl(213 31% 9%)',
    accent: 'hsl(214 84% 56%)',
  },
};

/**
 * Dark Theme (Alternative)
 * - Minimalist Linear-inspired design
 * - Near-black backgrounds
 * - Subtle gray tones
 * - Reduced eye strain for extended sessions
 */
export const DARK_THEME: ThemeConfig = {
  id: 'dark',
  name: 'Dark Theme',
  description: 'Minimalist dark theme inspired by Linear',
  className: 'theme-dark',
  preview: {
    background: 'hsl(222 10% 5%)',
    text: 'hsl(0 0% 95%)',
    accent: 'hsl(0 0% 85%)',
  },
};

/**
 * All available themes
 */
export const THEMES: ThemeConfig[] = [ORIGINAL_THEME, DARK_THEME];

/**
 * Default theme
 */
export const DEFAULT_THEME: ThemeType = 'original';

/**
 * LocalStorage key for theme preference
 */
export const THEME_STORAGE_KEY = 'portfolio-wizard-theme';

/**
 * Get theme config by ID
 */
export const getThemeConfig = (themeId: ThemeType): ThemeConfig => {
  return THEMES.find(theme => theme.id === themeId) || ORIGINAL_THEME;
};

/**
 * Get saved theme from localStorage or return default
 */
export const getSavedTheme = (): ThemeType => {
  if (typeof window === 'undefined') return DEFAULT_THEME;

  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved && (saved === 'original' || saved === 'dark')) {
      return saved as ThemeType;
    }
  } catch (error) {
    console.warn('Failed to load theme from localStorage:', error);
  }

  return DEFAULT_THEME;
};

/**
 * Save theme to localStorage
 */
export const saveTheme = (themeId: ThemeType): void => {
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(THEME_STORAGE_KEY, themeId);
  } catch (error) {
    console.warn('Failed to save theme to localStorage:', error);
  }
};
