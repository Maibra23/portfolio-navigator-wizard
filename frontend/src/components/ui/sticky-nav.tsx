/**
 * Sticky Navigation Component
 * Keeps navigation buttons visible when scrolling long wizard steps
 */

import { useEffect, useState, useRef } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ArrowLeft, ArrowRight } from "lucide-react";

interface StickyNavProps {
  onPrev?: () => void;
  onNext?: () => void;
  prevLabel?: string;
  nextLabel?: string;
  prevDisabled?: boolean;
  nextDisabled?: boolean;
  nextLoading?: boolean;
  showPrev?: boolean;
  showNext?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function StickyNav({
  onPrev,
  onNext,
  prevLabel = "Previous",
  nextLabel = "Continue",
  prevDisabled = false,
  nextDisabled = false,
  nextLoading = false,
  showPrev = true,
  showNext = true,
  className,
  children,
}: StickyNavProps) {
  const [isSticky, setIsSticky] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        // When sentinel is not visible, nav should be sticky
        setIsSticky(!entry.isIntersecting);
      },
      {
        threshold: 0,
        rootMargin: "0px 0px -100px 0px",
      }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      {/* Sentinel element - when this scrolls out of view, nav becomes sticky */}
      <div ref={sentinelRef} className="h-0" aria-hidden />

      {/* Navigation container */}
      <div
        className={cn(
          "mt-4 transition-all duration-200",
          isSticky && [
            "fixed bottom-0 left-0 right-0 z-40",
            "bg-background/95 backdrop-blur-sm",
            "border-t border-border",
            "py-3 px-4",
            "shadow-lg shadow-black/5 dark:shadow-black/20",
          ],
          className
        )}
      >
        <div
          className={cn(
            "flex flex-col sm:flex-row gap-2 sm:gap-3",
            isSticky && "max-w-5xl mx-auto",
            !showPrev && showNext && "sm:justify-end",
            showPrev && !showNext && "sm:justify-start",
            showPrev && showNext && "sm:justify-between"
          )}
        >
          {/* Custom children (e.g., additional buttons) */}
          {children}

          {/* Default navigation buttons */}
          {!children && (
            <>
              {showPrev && (
                <Button
                  variant="outline"
                  onClick={onPrev}
                  disabled={prevDisabled}
                  className="min-h-[44px] w-full sm:w-auto order-2 sm:order-1"
                  aria-label={`Go to ${prevLabel}`}
                >
                  <ArrowLeft className="mr-1.5 h-4 w-4" />
                  {prevLabel}
                </Button>
              )}

              {showNext && (
                <Button
                  onClick={onNext}
                  disabled={nextDisabled || nextLoading}
                  className="min-h-[44px] w-full sm:w-auto order-1 sm:order-2"
                  aria-label={`Go to ${nextLabel}`}
                >
                  {nextLoading ? (
                    <>
                      <span className="animate-spin mr-1.5">⏳</span>
                      Loading...
                    </>
                  ) : (
                    <>
                      {nextLabel}
                      <ArrowRight className="ml-1.5 h-4 w-4" />
                    </>
                  )}
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Spacer when sticky to prevent content jump */}
      {isSticky && <div className="h-20" aria-hidden />}
    </>
  );
}

/**
 * Hook to detect if user has scrolled past a threshold
 */
export function useScrollPosition(threshold: number = 100) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > threshold);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll(); // Check initial position

    return () => window.removeEventListener("scroll", handleScroll);
  }, [threshold]);

  return scrolled;
}
