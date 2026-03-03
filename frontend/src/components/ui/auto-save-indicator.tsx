/**
 * Auto-Save Indicator Component
 * Shows users that their progress is automatically saved
 */

import { useState, useEffect } from "react";
import { Cloud, CloudOff, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type SaveStatus = "saved" | "saving" | "error" | "offline";

interface AutoSaveIndicatorProps {
  status?: SaveStatus;
  lastSaved?: Date;
  className?: string;
  showTimestamp?: boolean;
}

export function AutoSaveIndicator({
  status = "saved",
  lastSaved,
  className,
  showTimestamp = true,
}: AutoSaveIndicatorProps) {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const effectiveStatus = !isOnline ? "offline" : status;

  const formatTime = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return "just now";
    if (diffMins === 1) return "1 min ago";
    if (diffMins < 60) return `${diffMins} mins ago`;
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const statusConfig = {
    saved: {
      icon: Check,
      text: "Saved",
      color: "text-green-600 dark:text-green-400",
      bgColor: "bg-green-50 dark:bg-green-950/30",
    },
    saving: {
      icon: Loader2,
      text: "Saving...",
      color: "text-blue-600 dark:text-blue-400",
      bgColor: "bg-blue-50 dark:bg-blue-950/30",
    },
    error: {
      icon: CloudOff,
      text: "Save failed",
      color: "text-red-600 dark:text-red-400",
      bgColor: "bg-red-50 dark:bg-red-950/30",
    },
    offline: {
      icon: CloudOff,
      text: "Offline",
      color: "text-amber-600 dark:text-amber-400",
      bgColor: "bg-amber-50 dark:bg-amber-950/30",
    },
  };

  const config = statusConfig[effectiveStatus];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors",
        config.bgColor,
        config.color,
        className
      )}
      role="status"
      aria-live="polite"
    >
      <Icon
        className={cn(
          "h-3.5 w-3.5",
          effectiveStatus === "saving" && "animate-spin"
        )}
        aria-hidden
      />
      <span>{config.text}</span>
      {showTimestamp && lastSaved && effectiveStatus === "saved" && (
        <span className="text-muted-foreground ml-1">
          · {formatTime(lastSaved)}
        </span>
      )}
    </div>
  );
}

/**
 * Hook to manage auto-save state
 */
interface UseAutoSaveOptions {
  onSave?: () => Promise<void>;
  debounceMs?: number;
}

export function useAutoSave({ onSave, debounceMs = 2000 }: UseAutoSaveOptions) {
  const [status, setStatus] = useState<SaveStatus>("saved");
  const [lastSaved, setLastSaved] = useState<Date>(new Date());

  const triggerSave = async () => {
    if (!onSave) return;

    setStatus("saving");
    try {
      await onSave();
      setStatus("saved");
      setLastSaved(new Date());
    } catch {
      setStatus("error");
    }
  };

  // Debounced save effect would go here in actual implementation

  return {
    status,
    lastSaved,
    triggerSave,
  };
}
