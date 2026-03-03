/**
 * Undo Toast Component
 * Provides undo capability for reversible actions
 */

import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";
import { Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface UndoAction<T = unknown> {
  id: string;
  description: string;
  data: T;
  undoFn: (data: T) => void | Promise<void>;
  timeoutMs?: number;
}

/**
 * Hook to manage undo operations with toast notifications
 */
export function useUndoToast() {
  const pendingActions = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const showUndoToast = useCallback(<T,>(action: UndoAction<T>) => {
    const { id, description, data, undoFn, timeoutMs = 5000 } = action;

    // Clear any existing timeout for this action
    const existingTimeout = pendingActions.current.get(id);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
    }

    // Set timeout for when undo window expires
    const timeout = setTimeout(() => {
      pendingActions.current.delete(id);
    }, timeoutMs);

    pendingActions.current.set(id, timeout);

    toast(description, {
      duration: timeoutMs,
      action: {
        label: "Undo",
        onClick: async () => {
          // Clear the timeout
          clearTimeout(timeout);
          pendingActions.current.delete(id);

          // Execute undo
          try {
            await undoFn(data);
            toast.success("Action undone");
          } catch {
            toast.error("Failed to undo action");
          }
        },
      },
      icon: <Undo2 className="h-4 w-4" />,
    });
  }, []);

  const clearPendingUndo = useCallback((id: string) => {
    const timeout = pendingActions.current.get(id);
    if (timeout) {
      clearTimeout(timeout);
      pendingActions.current.delete(id);
    }
  }, []);

  const clearAllPendingUndos = useCallback(() => {
    pendingActions.current.forEach((timeout) => clearTimeout(timeout));
    pendingActions.current.clear();
  }, []);

  return {
    showUndoToast,
    clearPendingUndo,
    clearAllPendingUndos,
  };
}

/**
 * Simple undo toast for stock removal
 */
interface StockUndoData {
  ticker: string;
  name: string;
  weight?: number;
}

export function useStockUndoToast(
  onRestore: (stock: StockUndoData) => void
) {
  const { showUndoToast } = useUndoToast();

  const showRemoveUndo = useCallback(
    (stock: StockUndoData) => {
      showUndoToast({
        id: `stock-${stock.ticker}`,
        description: `Removed ${stock.ticker}`,
        data: stock,
        undoFn: onRestore,
        timeoutMs: 5000,
      });
    },
    [showUndoToast, onRestore]
  );

  return { showRemoveUndo };
}

/**
 * Standalone undo button component
 */
interface UndoButtonProps {
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}

export function UndoButton({
  onClick,
  disabled = false,
  className,
}: UndoButtonProps) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      disabled={disabled}
      className={className}
      aria-label="Undo last action"
    >
      <Undo2 className="h-4 w-4 mr-1.5" />
      Undo
    </Button>
  );
}

/**
 * History stack for multi-level undo
 */
interface HistoryItem<T> {
  action: string;
  data: T;
  timestamp: Date;
}

export function useUndoHistory<T>(maxItems: number = 10) {
  const [history, setHistory] = useState<HistoryItem<T>[]>([]);

  const push = useCallback(
    (action: string, data: T) => {
      setHistory((prev) => {
        const newHistory = [
          { action, data, timestamp: new Date() },
          ...prev,
        ].slice(0, maxItems);
        return newHistory;
      });
    },
    [maxItems]
  );

  const pop = useCallback(() => {
    let item: HistoryItem<T> | undefined;
    setHistory((prev) => {
      if (prev.length === 0) return prev;
      [item] = prev;
      return prev.slice(1);
    });
    return item;
  }, []);

  const clear = useCallback(() => {
    setHistory([]);
  }, []);

  const canUndo = history.length > 0;
  const lastAction = history[0];

  return {
    history,
    push,
    pop,
    clear,
    canUndo,
    lastAction,
  };
}
