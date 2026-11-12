import React from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export interface RiskFlagItem {
  code: string;
  message: string;
  severity: "low" | "medium" | "high";
}

export function RiskFlags({
  flags = [],
  className,
}: {
  flags?: RiskFlagItem[];
  className?: string;
}) {
  if (!flags || flags.length === 0) {
    return (
      <Badge variant="gain" className={cn("gap-1.5 py-1 px-3", className)}>
        <CheckCircle2 className="size-3.5" />
        No major risk flags identified
      </Badge>
    );
  }

  return (
    <TooltipProvider>
      <div className={cn("flex flex-wrap gap-2 items-center", className)}>
        {flags.map((flag, idx) => {
          const badgeVariant =
            flag.severity === "high"
              ? "destructive"
              : flag.severity === "medium"
              ? "warning"
              : "outline";

          return (
            <Tooltip key={idx}>
              <TooltipTrigger asChild>
                <Badge variant={badgeVariant} className="cursor-help gap-1.5 py-1 px-2.5">
                  <AlertTriangle className="size-3" />
                  <span>{flag.message}</span>
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p className="font-mono text-xs">{flag.code}</p>
                <p className="text-[11px] text-muted-foreground capitalize">
                  Severity: {flag.severity}
                </p>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
}
