import * as React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/** Theme-safe step icon: use text-primary (never text-white) on bg-muted so icon is visible in light and dark themes. */
const sizeClasses = {
  sm: "w-9 h-9",
  md: "w-10 h-10",
  lg: "w-12 h-12",
} as const;

const iconSizeClasses = {
  sm: "h-4 w-4",
  md: "h-5 w-5",
  lg: "h-6 w-6",
} as const;

export interface StepHeaderIconProps {
  icon: LucideIcon;
  size?: keyof typeof sizeClasses;
  className?: string;
  "aria-hidden"?: boolean;
}

export function StepHeaderIcon({
  icon: Icon,
  size = "md",
  className,
  "aria-hidden": ariaHidden = true,
}: StepHeaderIconProps) {
  return (
    <div
      className={cn(
        "rounded-full bg-muted flex items-center justify-center border border-border",
        sizeClasses[size],
        className,
      )}
      aria-hidden={ariaHidden}
    >
      <Icon className={cn("text-primary", iconSizeClasses[size])} />
    </div>
  );
}
