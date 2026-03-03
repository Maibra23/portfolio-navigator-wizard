import * as React from "react";
import { CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface StepCardHeaderProps {
  /** Optional icon (e.g. StepHeaderIcon or custom styled element). */
  icon?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  /** Optional metadata row below subtitle (e.g. "Risk Profile: Moderate" with icon). */
  metadata?: React.ReactNode;
  /** Optional extra content below metadata (e.g. Progress bar). */
  children?: React.ReactNode;
  className?: string;
  /** If true, header content is centered (default). Set false for left-aligned sections. */
  centered?: boolean;
}

export function StepCardHeader({
  icon,
  title,
  subtitle,
  metadata,
  children,
  className,
  centered = true,
}: StepCardHeaderProps) {
  return (
    <CardHeader className={cn("pb-2", centered && "text-center", className)}>
      {icon && <div className={cn("mb-2", centered && "mx-auto")}>{icon}</div>}
      <CardTitle className="text-lg md:text-xl font-semibold leading-none tracking-tight">
        {title}
      </CardTitle>
      {subtitle != null && (
        <p className="text-sm md:text-base text-muted-foreground">{subtitle}</p>
      )}
      {metadata != null && (
        <div
          className={cn(
            "flex items-center gap-2 mt-1",
            centered && "justify-center",
          )}
        >
          {metadata}
        </div>
      )}
      {children}
    </CardHeader>
  );
}
