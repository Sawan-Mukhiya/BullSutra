import React from "react";
import { Info, AlertCircle, Scale } from "lucide-react";
import { Card } from "@/components/ui/card";
import { SignalBadge } from "@/components/common/SignalBadge";
import { ConfidenceGauge } from "@/components/common/ConfidenceGauge";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";
import { fmtScore } from "@/lib/format";
import { FLAG_LABELS } from "@/lib/constants";
import type { ResearchBrief } from "@/types";
import { cn } from "@/lib/utils";

export interface BriefSummaryCardProps {
  brief?: ResearchBrief | null;
  className?: string;
}

export function BriefSummaryCard({ brief, className }: BriefSummaryCardProps) {
  if (!brief) {
    return (
      <Card className={cn("p-6 space-y-4", className)}>
        <p className="text-sm text-text-subtle">No active brief summary.</p>
      </Card>
    );
  }

  const consensus = brief.signal;
  const { summary, meta } = brief;
  const isConflicted = brief.debate?.triggered && brief.debate.final_disagreement > 0.45;

  return (
    <TooltipProvider>
      <Card featured className={cn("p-6 space-y-6 lg:sticky lg:top-24", className)}>
        {/* Consensus Verdict Header */}
        <div className="flex flex-col items-center text-center space-y-3 pb-5 border-b border-border/80">
          <span className="text-xs uppercase font-semibold text-text-subtle tracking-wider">
            Consensus Research Verdict
          </span>
          <SignalBadge label={consensus.label} size="lg" />
          <ConfidenceGauge value={consensus.confidence} size="md" />

          {isConflicted && (
            <Badge variant="warning" className="gap-1.5 mt-2">
              <Scale className="size-3.5" />
              <span>Agents Conflicted</span>
            </Badge>
          )}
        </div>

        {/* Numeric Metrics Snapshot */}
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between py-1 border-b border-border/50">
            <span className="text-text-subtle">Aggregated Score:</span>
            <span className="font-mono font-bold text-foreground">
              {fmtScore(consensus.score)}
            </span>
          </div>

          <div className="flex items-center justify-between py-1 border-b border-border/50">
            <div className="flex items-center gap-1.5">
              <span className="text-text-subtle">Suggested Position Scale:</span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="size-3.5 text-text-subtle cursor-help" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs">
                    Suggested position scale reflecting risk and volatility levels. Research
                    output only, not trade advice.
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
            <span className="font-mono font-bold text-gold-500">
              ×{(consensus.position_multiplier || 1.0).toFixed(2)}
            </span>
          </div>
        </div>

        {/* Signal Flags */}
        {consensus.flags && consensus.flags.length > 0 && (
          <div className="space-y-1.5 pt-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-text-subtle block">
              Consensus Flags
            </span>
            <div className="flex flex-wrap gap-1.5">
              {consensus.flags.map((flag: string) => (
                <Badge key={flag} variant="secondary" className="text-[10px] gap-1 font-normal">
                  <AlertCircle className="size-3 text-warning" />
                  <span>{FLAG_LABELS[flag] || flag}</span>
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Narrative Executive Summary */}
        <div className="pt-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-text-subtle block mb-1.5">
            Executive Brief
          </span>
          <p className="text-xs text-muted-foreground leading-relaxed text-justify">
            {summary || "Quantitative synthesis ready. Review specialist agent cards for component drivers."}
          </p>
        </div>
      </Card>
    </TooltipProvider>
  );
}
