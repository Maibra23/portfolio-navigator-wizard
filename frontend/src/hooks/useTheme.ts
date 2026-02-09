/**
 * useTheme Hook
 *
 * Simplified hook for accessing theme functionality in components.
 * Re-exports the useThemeContext hook with a cleaner name.
 */

import { useThemeContext } from '@/contexts/ThemeContext';

/**
 * Hook to access theme state and controls
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { theme, toggleTheme, themeConfig } = useTheme();
 *
 *   return (
 *     <div>
 *       <p>Current theme: {theme}</p>
 *       <button onClick={toggleTheme}>Toggle Theme</button>
 *     </div>
 *   );
 * }
 * ```
 *
 * @returns Theme context value with current theme and control functions
 * @throws Error if used outside of ThemeProvider
 */
export const useTheme = useThemeContext;

export default useTheme;
