import React from "react";
import { Database } from "lucide-react";

/**
 * Small attribution line for Yahoo Finance data. Use at the bottom of
 * portfolio recommendations, optimization, stress test, and projection views.
 */
export const DataSourceAttribution: React.FC<{ className?: string }> = ({
  className = "",
}) => (
  <div
    className={
      "flex items-start gap-2 pt-2 border-t border-border/30 mt-2 text-xs text-muted-foreground " +
      className
    }
  >
    <Database className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
    <span>
      <strong className="text-foreground">Data source:</strong> Yahoo Finance
      (monthly returns, annualized). Historical data for educational purposes
      only.
    </span>
  </div>
);
