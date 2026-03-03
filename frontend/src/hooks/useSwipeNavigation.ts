/**
 * Swipe Navigation Hook
 * Enables touch gesture navigation for mobile devices
 */

import { useRef, useEffect, useCallback } from "react";

interface SwipeNavigationOptions {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  threshold?: number; // Minimum distance for a swipe (default: 50px)
  enabled?: boolean;
}

interface TouchState {
  startX: number;
  startY: number;
  startTime: number;
}

export function useSwipeNavigation({
  onSwipeLeft,
  onSwipeRight,
  onSwipeUp,
  onSwipeDown,
  threshold = 50,
  enabled = true,
}: SwipeNavigationOptions) {
  const touchState = useRef<TouchState | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleTouchStart = useCallback(
    (event: TouchEvent) => {
      if (!enabled) return;

      const touch = event.touches[0];
      touchState.current = {
        startX: touch.clientX,
        startY: touch.clientY,
        startTime: Date.now(),
      };
    },
    [enabled]
  );

  const handleTouchEnd = useCallback(
    (event: TouchEvent) => {
      if (!enabled || !touchState.current) return;

      const touch = event.changedTouches[0];
      const deltaX = touch.clientX - touchState.current.startX;
      const deltaY = touch.clientY - touchState.current.startY;
      const deltaTime = Date.now() - touchState.current.startTime;

      // Must complete swipe within 500ms
      if (deltaTime > 500) {
        touchState.current = null;
        return;
      }

      const absX = Math.abs(deltaX);
      const absY = Math.abs(deltaY);

      // Determine if horizontal or vertical swipe
      if (absX > absY && absX > threshold) {
        // Horizontal swipe
        if (deltaX > 0 && onSwipeRight) {
          onSwipeRight();
        } else if (deltaX < 0 && onSwipeLeft) {
          onSwipeLeft();
        }
      } else if (absY > absX && absY > threshold) {
        // Vertical swipe
        if (deltaY > 0 && onSwipeDown) {
          onSwipeDown();
        } else if (deltaY < 0 && onSwipeUp) {
          onSwipeUp();
        }
      }

      touchState.current = null;
    },
    [enabled, threshold, onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !enabled) return;

    container.addEventListener("touchstart", handleTouchStart, {
      passive: true,
    });
    container.addEventListener("touchend", handleTouchEnd, { passive: true });

    return () => {
      container.removeEventListener("touchstart", handleTouchStart);
      container.removeEventListener("touchend", handleTouchEnd);
    };
  }, [enabled, handleTouchStart, handleTouchEnd]);

  return containerRef;
}

/**
 * Simple hook to detect if the device supports touch
 */
export function useTouchDevice(): boolean {
  if (typeof window === "undefined") return false;
  return "ontouchstart" in window || navigator.maxTouchPoints > 0;
}
