import React from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { SignalBadge } from "@/components/common/SignalBadge";
import { SymbolAvatar } from "@/components/common/SymbolAvatar";
import { fmtDate, fmtPct } from "@/lib/format";
import type { BriefSummary } from "@/types";
import { cn } from "@/lib/utils";

export interface BriefCardProps {
  brief: BriefSummary;
  className?: string;
}

export function BriefCard({ brief, className }: BriefCardProps) {
  const isConflicted = brief.conflicted;

  return (
    <Link href={`/stocks/${brief.symbol.toUpperCase()}`}>
      <Card
        interactive
        className={cn(
          "p-5 flex flex-col justify-between h-full group hover:border-gold-500/40 transition-all",
          className
        )}
      >
        <div>
          {/* Header row */}
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-3">
              <SymbolAvatar ticker={brief.symbol} size={32} />
              <div>
                <h3 className="font-mono font-bold text-base text-foreground group-hover:text-gold-300 transition-colors">
                  {brief.symbol}
                </h3>
                <span className="text-xs text-text-subtle uppercase">
                  {(brief as any).sector_group || (brief as any).sector || "Universe"}
                </span>
              </div>
            </div>

            <SignalBadge label={brief.label} size="sm" />
          </div>

          <p className="text-xs text-muted-foreground line-clamp-2 mt-2 leading-relaxed">
            {(brief as any).summary || "Quantitative consensus evaluated. Tap to read the full brief."}
          </p>
        </div>

        {/* Footer row */}
        <div className="flex items-center justify-between pt-4 mt-4 border-t border-border/50 text-[11px] text-text-subtle">
          <div className="flex items-center gap-2">
            <span>Confidence:</span>
            <span className="font-mono font-semibold text-foreground">
              {fmtPct(brief.confidence, 0)}
            </span>
            {isConflicted && (
              <span
                className="size-2 rounded-full bg-warning"
                title="Debate detected divergent specialist votes"
              />
            )}
          </div>

          <span className="font-mono">{fmtDate(brief.as_of)}</span>
        </div>
      </Card>
    </Link>
  );
}
