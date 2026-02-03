import '@testing-library/jest-dom/vitest';

// Polyfill window.matchMedia for jsdom (required by sonner, radix, etc.)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false
  })
});

// Polyfill ResizeObserver for jsdom (required by recharts ResponsiveContainer)
class ResizeObserverMock {
  observe = () => {};
  unobserve = () => {};
  disconnect = () => {};
}
window.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver; 