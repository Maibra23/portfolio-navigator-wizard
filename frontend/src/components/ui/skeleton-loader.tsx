/**
 * Skeleton Loader Components
 * Provides loading placeholders for better perceived performance
 */

import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "skeleton rounded-md bg-muted",
        className
      )}
      aria-hidden="true"
    />
  );
}

/**
 * Card skeleton with header and content
 */
export function CardSkeleton({ className }: SkeletonProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-6 space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
      {/* Content */}
      <div className="space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-4/5" />
        <Skeleton className="h-3 w-3/5" />
      </div>
    </div>
  );
}

/**
 * Chart skeleton
 */
export function ChartSkeleton({ className }: SkeletonProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-4", className)}>
      {/* Title */}
      <Skeleton className="h-5 w-1/4 mb-4" />
      {/* Chart area */}
      <div className="flex items-end justify-around gap-2 h-48">
        <Skeleton className="h-3/4 w-8 rounded-t" />
        <Skeleton className="h-1/2 w-8 rounded-t" />
        <Skeleton className="h-full w-8 rounded-t" />
        <Skeleton className="h-2/3 w-8 rounded-t" />
        <Skeleton className="h-1/3 w-8 rounded-t" />
        <Skeleton className="h-4/5 w-8 rounded-t" />
        <Skeleton className="h-1/2 w-8 rounded-t" />
      </div>
      {/* Legend */}
      <div className="flex justify-center gap-4 mt-4">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  );
}

/**
 * Table skeleton
 */
export function TableSkeleton({
  rows = 5,
  columns = 4,
  className,
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={cn("rounded-lg border bg-card overflow-hidden", className)}>
      {/* Header */}
      <div className="flex gap-4 p-4 border-b bg-muted/50">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`header-${i}`} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={`row-${rowIdx}`}
          className="flex gap-4 p-4 border-b last:border-b-0"
        >
          {Array.from({ length: columns }).map((_, colIdx) => (
            <Skeleton
              key={`cell-${rowIdx}-${colIdx}`}
              className="h-4 flex-1"
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * Metrics grid skeleton (for portfolio stats)
 */
export function MetricsGridSkeleton({ className }: SkeletonProps) {
  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-4 gap-4", className)}>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-lg border bg-card p-4 space-y-2">
          <Skeleton className="h-3 w-2/3" />
          <Skeleton className="h-6 w-1/2" />
        </div>
      ))}
    </div>
  );
}

/**
 * Stock card skeleton
 */
export function StockCardSkeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4 flex items-center gap-3",
        className
      )}
    >
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="text-right space-y-2">
        <Skeleton className="h-4 w-12 ml-auto" />
        <Skeleton className="h-3 w-8 ml-auto" />
      </div>
    </div>
  );
}

/**
 * Full page loading skeleton
 */
export function PageSkeleton() {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Skeleton className="h-12 w-12 rounded-full" />
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
      </div>

      {/* Metrics */}
      <MetricsGridSkeleton />

      {/* Main content */}
      <div className="grid md:grid-cols-2 gap-6">
        <ChartSkeleton />
        <CardSkeleton />
      </div>

      {/* Table */}
      <TableSkeleton />
    </div>
  );
}

/**
 * Inline text skeleton
 */
export function TextSkeleton({
  lines = 3,
  className,
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            "h-4",
            i === lines - 1 ? "w-3/4" : "w-full"
          )}
        />
      ))}
    </div>
  );
}

/**
 * Avatar skeleton
 */
export function AvatarSkeleton({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const sizes = {
    sm: "h-8 w-8",
    md: "h-10 w-10",
    lg: "h-12 w-12",
  };

  return <Skeleton className={cn("rounded-full", sizes[size])} />;
}

/**
 * Button skeleton
 */
export function ButtonSkeleton({
  size = "default",
}: {
  size?: "sm" | "default" | "lg";
}) {
  const sizes = {
    sm: "h-8 w-20",
    default: "h-10 w-24",
    lg: "h-12 w-32",
  };

  return <Skeleton className={cn("rounded-md", sizes[size])} />;
}
