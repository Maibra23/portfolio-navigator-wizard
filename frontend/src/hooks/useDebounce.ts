import { useState, useEffect } from "react";

/**
 * Returns a debounced value that updates only after `delay` ms of no changes.
 * Use to throttle API calls triggered by rapid input (e.g. sliders, search).
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
