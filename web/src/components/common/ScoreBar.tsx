import React from "react";
import { fmtScore, fmtNum } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface ScoreBarProps {
  score: number;
  min?: number;
  max?: number;
  kind?: "signed" | "risk";
  showValue?: boolean;
  className?: string;
}

export function ScoreBar({
  score,
  min = -1,
  max = 1,
  kind = "signed",
  showValue = true,
  className,
}: ScoreBarProps) {
  if (kind === "signed") {
    const clamped = Math.max(-1, Math.min(1, score));
    const isPositive = clamped >= 0;
    const widthPct = Math.abs(clamped) * 50; // 0 to 50% from center

    return (
      <div className={cn("flex items-center gap-3 w-full", className)}>
        <div className="relative h-2 flex-1 rounded-full bg-secondary overflow-hidden">
          {/* Center line */}
          <div className="absolute left-1/2 top-0 bottom-0 w-[1.5px] bg-border z-10" />

          {/* Bar fill */}
          {isPositive ? (
            <div
              className="absolute left-1/2 top-0 bottom-0 bg-gain rounded-r-full transition-all duration-500"
              style={{ width: `${widthPct}%` }}
            />
          ) : (
            <div
              className="absolute top-0 bottom-0 bg-loss rounded-l-full transition-all duration-500"
              style={{
                left: `${50 - widthPct}%`,
                width: `${widthPct}%`,
              }}
            />
          )}
        </div>
        {showValue && (
          <span className="num text-xs font-semibold text-foreground w-12 text-right">
            {fmtScore(score)}
          </span>
        )}
      </div>
    );
  }

  // Risk variant: 0 to 1
  const clamped = Math.max(0, Math.min(1, score));
  const widthPct = clamped * 100;

  return (
    <div className={cn("flex items-center gap-3 w-full", className)}>
      <div className="relative h-2 flex-1 rounded-full bg-secondary overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-gain via-warning to-loss"
          style={{ width: `${widthPct}%` }}
        />
      </div>
      {showValue && (
        <span className="num text-xs font-semibold text-foreground w-12 text-right">
          {fmtNum(score, 2)}
        </span>
      )}
    </div>
  );
}
