/**
 * Keyboard Navigation Hook
 * Provides keyboard shortcuts for wizard navigation and common actions
 */

import { useEffect, useCallback } from "react";

interface KeyboardNavigationOptions {
  onNext?: () => void;
  onPrev?: () => void;
  onConfirm?: () => void;
  onCancel?: () => void;
  onUndo?: () => void;
  enabled?: boolean;
}

export function useKeyboardNavigation({
  onNext,
  onPrev,
  onConfirm,
  onCancel,
  onUndo,
  enabled = true,
}: KeyboardNavigationOptions) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Don't trigger if user is typing in an input
      const target = event.target as HTMLElement;
      const isInputElement =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;

      // Allow Escape to work even in inputs
      if (event.key === "Escape" && onCancel) {
        event.preventDefault();
        onCancel();
        return;
      }

      // Don't trigger navigation shortcuts when typing
      if (isInputElement) return;

      // Arrow key navigation
      if (event.key === "ArrowRight" && onNext) {
        event.preventDefault();
        onNext();
      } else if (event.key === "ArrowLeft" && onPrev) {
        event.preventDefault();
        onPrev();
      }

      // Enter to confirm (when not in input)
      if (event.key === "Enter" && onConfirm) {
        event.preventDefault();
        onConfirm();
      }

      // Cmd/Ctrl + Z for undo
      if ((event.metaKey || event.ctrlKey) && event.key === "z" && onUndo) {
        event.preventDefault();
        onUndo();
      }
    },
    [enabled, onNext, onPrev, onConfirm, onCancel, onUndo]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [enabled, handleKeyDown]);
}

/**
 * Hook to trap focus within a container (for modals, dialogs)
 */
export function useFocusTrap(containerRef: React.RefObject<HTMLElement>) {
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTabKey = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;

      if (event.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement?.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement?.focus();
        }
      }
    };

    container.addEventListener("keydown", handleTabKey);
    firstElement?.focus();

    return () => container.removeEventListener("keydown", handleTabKey);
  }, [containerRef]);
}
