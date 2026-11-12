import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SignalBadgeProps {
  label: string | null | undefined;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function SignalBadge({ label, size = "md", className }: SignalBadgeProps) {
  const norm = (label || "HOLD").toUpperCase();
  const isBuy = norm === "BUY" || norm === "BULLISH";
  const isSell = norm === "SELL" || norm === "BEARISH";
  const isHold = !isBuy && !isSell;

  const Icon = isBuy ? TrendingUp : isSell ? TrendingDown : Minus;

  const textLabel = isBuy ? "BULLISH" : isSell ? "BEARISH" : "NEUTRAL";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold uppercase tracking-wider transition-colors",
        size === "sm" && "h-6 px-2.5 text-[10px]",
        size === "md" && "h-7 px-3 text-xs",
        size === "lg" && "h-9 px-4 text-sm font-bold tracking-widest",
        isBuy && "bg-gain/15 text-gain border border-gain/30",
        isSell && "bg-loss/15 text-loss border border-loss/30",
        isHold && "bg-neutral/15 text-neutral border border-neutral/30",
        className
      )}
    >
      <Icon className={cn(size === "sm" ? "size-3" : size === "lg" ? "size-4" : "size-3.5")} />
      <span>{textLabel}</span>
    </span>
  );
}
