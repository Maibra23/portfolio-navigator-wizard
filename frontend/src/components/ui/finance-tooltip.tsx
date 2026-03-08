import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  getGlossaryEntry,
  type FinanceGlossaryKey,
} from "@/lib/finance-glossary";
import { cn } from "@/lib/utils";

interface FinanceTooltipProps {
  /** Key from finance-glossary (e.g. sharpe_ratio, efficient_frontier) */
  term: FinanceGlossaryKey | string;
  /** Optional override for tooltip content */
  customDescription?: string;
  /** Optional override for title */
  customTitle?: string;
  /** Additional class names for the trigger wrapper */
  className?: string;
  /** Side of the trigger to show tooltip */
  side?: "top" | "right" | "bottom" | "left";
  /** Max width of tooltip content */
  contentClassName?: string;
}

/**
 * Renders an Info icon that shows a plain-language definition for a finance term.
 * Uses the centralized finance glossary; supports overrides for custom copy.
 */
export function FinanceTooltip({
  term,
  customDescription,
  customTitle,
  className,
  side = "top",
  contentClassName = "max-w-[220px] p-2 text-xs",
}: FinanceTooltipProps) {
  const entry = getGlossaryEntry(term);
  const title = customTitle ?? entry?.title ?? term;
  const description =
    customDescription ?? entry?.description ?? "No definition available.";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex items-center cursor-help text-muted-foreground hover:text-foreground",
            className
          )}
          aria-label={`Learn more about ${title}`}
        >
          <Info className="h-3.5 w-3.5 shrink-0" />
        </span>
      </TooltipTrigger>
      <TooltipContent side={side} className={contentClassName}>
        <div className="font-semibold mb-1">{title}</div>
        <div>{description}</div>
      </TooltipContent>
    </Tooltip>
  );
}
