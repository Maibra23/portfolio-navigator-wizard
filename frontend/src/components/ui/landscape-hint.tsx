import { useState, useEffect } from "react";
import { X, RotateCcw } from "lucide-react";
import { useIsMobile } from "@/hooks/use-mobile";
import { useOrientation } from "@/hooks/use-orientation";
import { Button } from "@/components/ui/button";

const GLOBAL_DISMISS_KEY = "landscape-hint-dismissed-global";
const SESSION_DISMISS_KEY = "landscape-hint-dismissed-session";

interface LandscapeHintProps {
  /** Kept for API compatibility; hybrid uses global + session keys. */
  storageKey?: string;
  children: React.ReactNode;
}

function getGlobalDismissed(): boolean {
  if (typeof window === "undefined") return true;
  return localStorage.getItem(GLOBAL_DISMISS_KEY) === "true";
}

function getSessionDismissed(): boolean {
  if (typeof window === "undefined") return true;
  return sessionStorage.getItem(SESSION_DISMISS_KEY) === "true";
}

export function LandscapeHint({
  storageKey = "landscape-hint-dismissed",
  children,
}: LandscapeHintProps) {
  const isMobile = useIsMobile();
  const { isPortrait } = useOrientation();
  const [globalDismissed, setGlobalDismissed] = useState(true);
  const [sessionDismissed, setSessionDismissed] = useState(true);
  const [showHint, setShowHint] = useState(false);

  useEffect(() => {
    setGlobalDismissed(getGlobalDismissed());
    setSessionDismissed(getSessionDismissed());
  }, []);

  const isDismissed = globalDismissed || sessionDismissed;

  useEffect(() => {
    if (isMobile && isPortrait && !isDismissed) {
      const timer = setTimeout(() => setShowHint(true), 500);
      return () => clearTimeout(timer);
    } else {
      setShowHint(false);
    }
  }, [isMobile, isPortrait, isDismissed]);

  const handleDismiss = () => {
    setShowHint(false);
    setGlobalDismissed(true);
    if (typeof window !== "undefined") {
      localStorage.setItem(GLOBAL_DISMISS_KEY, "true");
    }
  };

  const handleDismissOnce = () => {
    setShowHint(false);
    setSessionDismissed(true);
    if (typeof window !== "undefined") {
      sessionStorage.setItem(SESSION_DISMISS_KEY, "true");
    }
  };

  return (
    <div className="relative">
      {children}

      {showHint && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="mx-4 max-w-sm rounded-lg border bg-card p-4 shadow-lg">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                  <RotateCcw className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">
                    Rotate for better view
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Turn your phone sideways to see the full chart
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0"
                onClick={handleDismissOnce}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="mt-3 flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1 text-xs"
                onClick={handleDismissOnce}
              >
                Continue anyway
              </Button>
              <Button
                variant="secondary"
                size="sm"
                className="flex-1 text-xs"
                onClick={handleDismiss}
              >
                Don't show again
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
