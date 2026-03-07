# Theme Switching System - Technical Guide

**Last Updated:** February 9, 2026
**Version:** 1.0

## Overview

Portfolio Navigator Wizard features a dual-theme system that allows users to choose between a **Classic Theme** (default) and a **Dark Theme** (alternative). This document provides technical details about the theme system architecture and how to work with it.

---

## 🎨 Available Themes

### 1. Classic Theme (Default)
- **ID:** `original`
- **Description:** Bright, professional light theme with gradients
- **Visual Style:**
  - Light backgrounds (hsl(210 20% 98%))
  - Blue primary colors (hsl(214 84% 56%))
  - Green accent colors (hsl(142 76% 36%))
  - Professional gradients for depth
  - Elegant shadows
- **Use Cases:**
  - Daytime work
  - Presentations
  - High-contrast environments
  - Professional settings

### 2. Dark Theme (Alternative)
- **ID:** `dark`
- **Description:** Linear-inspired minimalist dark theme
- **Visual Style:**
  - Near-black backgrounds (hsl(222 10% 5%))
  - Subtle gray tones
  - Minimal color accents
  - Flat design (no gradients)
  - Subtle borders
- **Use Cases:**
  - Low-light environments
  - Extended work sessions
  - Reduced eye strain
  - Modern aesthetic preference

---

## 🏗️ Architecture

### File Structure

```
frontend/src/
├── lib/
│   └── themeConfig.ts              # Theme definitions and constants
├── contexts/
│   └── ThemeContext.tsx            # Theme state management
├── hooks/
│   └── useTheme.ts                 # Hook for accessing theme
├── components/
│   └── ThemeSelector.tsx           # UI components for theme switching
└── index.css                       # CSS variables for both themes
```

### Component Hierarchy

```
App (ThemeProvider wraps entire app)
├── ThemeContext (manages global theme state)
├── WelcomeStep
│   └── ThemeSelector (floating button)
└── Other Components (automatically inherit theme)
```

---

## 📁 Key Files

### 1. `frontend/src/lib/themeConfig.ts`

**Purpose:** Central configuration for all theme definitions

**Key Exports:**
- `ThemeType`: TypeScript type for theme IDs (`'original' | 'dark'`)
- `ThemeConfig`: Interface for theme metadata
- `ORIGINAL_THEME`: Classic theme configuration
- `DARK_THEME`: Dark theme configuration
- `THEMES`: Array of all available themes
- `DEFAULT_THEME`: Default theme ID
- `getSavedTheme()`: Load theme from localStorage
- `saveTheme()`: Save theme to localStorage

**Example Usage:**
```typescript
import { ORIGINAL_THEME, getThemeConfig } from '@/lib/themeConfig';

const theme = getThemeConfig('dark');
console.log(theme.name); // "Dark Theme"
```

### 2. `frontend/src/contexts/ThemeContext.tsx`

**Purpose:** React Context for theme state management

**Exports:**
- `ThemeProvider`: Wrap app to enable theming
- `useThemeContext`: Hook to access theme state

**Context Value:**
```typescript
{
  theme: ThemeType;              // Current theme ID
  themeConfig: ThemeConfig;      // Current theme configuration
  setTheme: (theme: ThemeType) => void;    // Set specific theme
  toggleTheme: () => void;       // Toggle between themes
  isApplying: boolean;           // Theme change in progress
}
```

**How It Works:**
1. Loads saved theme from localStorage on mount
2. Applies theme by adding/removing CSS class on `<html>`
3. Persists theme choice to localStorage
4. Provides smooth transitions between themes

### 3. `frontend/src/hooks/useTheme.ts`

**Purpose:** Simplified hook for components

**Example Usage:**
```typescript
import { useTheme } from '@/hooks/useTheme';

function MyComponent() {
  const { theme, toggleTheme, themeConfig } = useTheme();

  return (
    <div>
      <p>Current: {themeConfig.name}</p>
      <button onClick={toggleTheme}>Switch Theme</button>
    </div>
  );
}
```

### 4. `frontend/src/components/ThemeSelector.tsx`

**Purpose:** UI components for theme switching

**Components:**
- `ThemeSelector`: Floating button (used in WelcomeStep)
- `ThemeSelectorInline`: Card-based selector (for future use)

**Props:**
```typescript
interface ThemeSelectorProps {
  position?: 'fixed' | 'relative' | 'absolute';
  className?: string;
  showLabel?: boolean;
}
```

**Example:**
```tsx
// Floating button (default)
<ThemeSelector />

// With label
<ThemeSelector showLabel={true} />

// Relative position
<ThemeSelector position="relative" />
```

### 5. `frontend/src/index.css`

**Purpose:** CSS variables for both themes

**Structure:**
```css
:root {
  /* Original Theme Variables (DEFAULT) */
  --background: 210 20% 98%;
  --primary: 214 84% 56%;
  /* ... */
}

.theme-dark {
  /* Dark Theme Variables (ALTERNATIVE) */
  --background: 222 10% 5%;
  --primary: 0 0% 85%;
  /* ... */
}
```

**Theme Application:**
- Original theme: No class (uses `:root`)
- Dark theme: `.theme-dark` class on `<html>`

---

## 🔧 How Theme Switching Works

### Flow Diagram

```
User clicks theme button
        ↓
toggleTheme() called
        ↓
Update state (theme = 'dark')
        ↓
Save to localStorage
        ↓
Apply CSS class to <html>
        ↓
All components re-render with new theme
        ↓
Smooth transition (300ms)
```

### CSS Class Application

```typescript
// In ThemeContext.tsx
const applyTheme = (themeId: ThemeType) => {
  const root = document.documentElement;
  const config = getThemeConfig(themeId);

  // Remove all theme classes
  root.classList.remove('theme-dark', 'theme-original');

  // Add new theme class (if not default)
  if (config.className) {
    root.classList.add(config.className);
  }
};
```

### Persistence

**Storage:**
- Key: `'portfolio-wizard-theme'`
- Value: `'original'` or `'dark'`
- Location: `localStorage`

**Load on mount:**
```typescript
const [theme, setTheme] = useState(() => {
  return getSavedTheme(); // Loads from localStorage
});
```

---

## 🎯 Usage Examples

### Basic Theme Access

```tsx
import { useTheme } from '@/hooks/useTheme';

function MyComponent() {
  const { theme } = useTheme();

  return (
    <div>
      {theme === 'dark' ? (
        <p>Welcome to dark mode!</p>
      ) : (
        <p>Enjoying the classic theme!</p>
      )}
    </div>
  );
}
```

### Toggle Theme Button

```tsx
import { useTheme } from '@/hooks/useTheme';
import { Button } from '@/components/ui/button';
import { Moon, Sun } from 'lucide-react';

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <Button onClick={toggleTheme}>
      {theme === 'dark' ? <Sun /> : <Moon />}
      Switch Theme
    </Button>
  );
}
```

### Conditional Styling

```tsx
import { useTheme } from '@/hooks/useTheme';

function Chart() {
  const { theme } = useTheme();

  const chartColors = theme === 'dark'
    ? ['#4ade80', '#f87171', '#60a5fa'] // Dark theme colors
    : ['#3b82f6', '#10b981', '#f59e0b']; // Light theme colors

  return <VisualizationChart colors={chartColors} />;
}
```

---

## 🛠️ Customization Guide

### Adding a New Theme

**1. Define theme in `themeConfig.ts`:**

```typescript
export const NEW_THEME: ThemeConfig = {
  id: 'new',
  name: 'New Theme',
  description: 'Description of new theme',
  className: 'theme-new',
  preview: {
    background: 'hsl(0 0% 50%)',
    text: 'hsl(0 0% 100%)',
    accent: 'hsl(200 100% 50%)',
  },
};

// Add to THEMES array
export const THEMES: ThemeConfig[] = [
  ORIGINAL_THEME,
  DARK_THEME,
  NEW_THEME,
];
```

**2. Add CSS variables in `index.css`:**

```css
.theme-new {
  --background: 0 0% 50%;
  --foreground: 0 0% 100%;
  --primary: 200 100% 50%;
  /* ... all other variables ... */
}
```

**3. Update TypeScript type:**

```typescript
export type ThemeType = 'original' | 'dark' | 'new';
```

### Modifying Existing Theme

**1. Update CSS variables:**

Edit `frontend/src/index.css`:

```css
:root {
  /* Change a color */
  --primary: 214 84% 56%; /* OLD */
  --primary: 220 90% 60%; /* NEW */
}
```

**2. Update theme config (optional):**

Edit `frontend/src/lib/themeConfig.ts`:

```typescript
export const ORIGINAL_THEME: ThemeConfig = {
  // ...
  description: 'Updated description',
  // ...
};
```

### Theme-Specific Component Behavior

```tsx
import { useTheme } from '@/hooks/useTheme';

function AdaptiveComponent() {
  const { theme } = useTheme();

  // Different behavior per theme
  const showGradients = theme === 'original';
  const shadowSize = theme === 'dark' ? 'sm' : 'lg';

  return (
    <div className={`shadow-${shadowSize}`}>
      {showGradients && <GradientBackground />}
      <Content />
    </div>
  );
}
```

---

## 🧪 Testing

### Manual Testing Checklist

- [ ] Theme toggles correctly on button click
- [ ] Theme persists after page refresh
- [ ] All wizard steps display correctly in both themes
- [ ] Charts are readable in both themes
- [ ] Text contrast meets WCAG AA standards
- [ ] Buttons and interactive elements work in both themes
- [ ] No console errors when switching
- [ ] Smooth transition animation (300ms)
- [ ] Theme selector tooltip shows correct text

### Automated Testing

**Test theme context:**

```typescript
import { renderHook, act } from '@testing-library/react';
import { ThemeProvider, useThemeContext } from '@/contexts/ThemeContext';

test('toggleTheme switches between themes', () => {
  const wrapper = ({ children }) => (
    <ThemeProvider>{children}</ThemeProvider>
  );

  const { result } = renderHook(() => useThemeContext(), { wrapper });

  expect(result.current.theme).toBe('original');

  act(() => {
    result.current.toggleTheme();
  });

  expect(result.current.theme).toBe('dark');
});
```

---

## 🔍 Debugging

### Common Issues

**1. Theme not persisting:**
- Check localStorage is enabled in browser
- Verify `THEME_STORAGE_KEY` is correct
- Check browser console for storage errors

**2. Theme not applying:**
- Verify CSS class is added to `<html>` element
- Check CSS variables are defined in `index.css`
- Ensure component is inside `ThemeProvider`

**3. Components not updating:**
- Verify component uses CSS variables (not hardcoded colors)
- Check component is accessing `useTheme` if needed
- Ensure proper re-rendering on theme change

### Debug Tools

**Check current theme:**
```javascript
// In browser console
localStorage.getItem('portfolio-wizard-theme')
```

**Inspect applied classes:**
```javascript
// In browser console
document.documentElement.className
```

**Force theme:**
```javascript
// In browser console
document.documentElement.classList.add('theme-dark')
```

---

## 📊 Performance

### Metrics

- **Theme switch time:** ~50-100ms
- **CSS transition duration:** 300ms
- **localStorage write:** < 1ms
- **Re-render impact:** Minimal (CSS-driven)

### Optimization Notes

- Theme switching is CSS-driven (no component prop drilling)
- Uses `transition` for smooth color changes
- LocalStorage operations are debounced
- No full app re-render required

---

## 🚀 Future Enhancements

### Potential Features

1. **System Theme Detection**
   ```typescript
   const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
     ? 'dark'
     : 'original';
   ```

2. **Auto Theme Switching**
   - Switch to dark at night
   - Light during day
   - Based on user's timezone

3. **Custom Themes**
   - Allow users to create custom color schemes
   - Theme marketplace/gallery
   - Import/export themes

4. **Theme Preview**
   - Live preview before applying
   - Side-by-side comparison
   - Theme customization UI

5. **Per-Component Themes**
   - Different themes for different sections
   - Mixed theme layouts
   - Theme inheritance

---

## 📚 References

### Related Files
- `frontend/src/lib/themeConfig.ts`
- `frontend/src/contexts/ThemeContext.tsx`
- `frontend/src/hooks/useTheme.ts`
- `frontend/src/components/ThemeSelector.tsx`
- `frontend/src/index.css`
- `THEME_REDESIGN_TASKS.md`

### External Resources
- [Linear.app Design System](https://linear.app/)
- [CSS Custom Properties (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
- [React Context API](https://react.dev/reference/react/createContext)
- [localStorage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)

---

## 🤝 Contributing

When adding features to the theme system:

1. **Update this guide** with new features
2. **Add tests** for theme-related functionality
3. **Update type definitions** if adding new theme properties
4. **Test all wizard steps** with new theme
5. **Check accessibility** (WCAG contrast ratios)
6. **Document breaking changes** in README

---

**Document Version:** 1.0
**Last Updated:** February 9, 2026
**Maintained By:** Portfolio Navigator Wizard Team
