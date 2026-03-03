/**
 * Hook to detect user's motion preference
 * Respects prefers-reduced-motion media query for accessibility
 */

import { useState, useEffect } from "react";

export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    // Check if window is available (SSR safety)
    if (typeof window === "undefined") return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    const handleChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
    // Legacy browsers (Safari < 14)
    else {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, []);

  return prefersReducedMotion;
}

/**
 * Get animation duration based on motion preference
 * Returns 0 for reduced motion, otherwise the provided duration
 */
export function getAnimationDuration(
  duration: number,
  prefersReducedMotion: boolean
): number {
  return prefersReducedMotion ? 0 : duration;
}

/**
 * Get Framer Motion transition config that respects reduced motion
 */
export function getMotionTransition(
  prefersReducedMotion: boolean,
  duration: number = 0.3
) {
  if (prefersReducedMotion) {
    return { duration: 0 } as const;
  }
  return { duration, ease: "easeOut" as const };
}
