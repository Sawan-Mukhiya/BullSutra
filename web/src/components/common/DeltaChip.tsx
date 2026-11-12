import React from "react";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { fmtSignedPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface DeltaChipProps {
  value: number | null | undefined;
  abs?: number | null;
  size?: "sm" | "md";
  showIcon?: boolean;
  className?: string;
}

export function DeltaChip({
  value,
  abs,
  size = "sm",
  showIcon = true,
  className,
}: DeltaChipProps) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="text-text-subtle text-xs">—</span>;
  }

  const isPositive = value > 0;
  const isNegative = value < 0;
  const isZero = !isPositive && !isNegative;

  const Icon = isPositive ? ArrowUpRight : isNegative ? ArrowDownRight : Minus;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-mono font-medium",
        size === "sm" ? "h-6 px-2 text-xs" : "h-7 px-2.5 text-sm",
        isPositive && "bg-gain/15 text-gain border border-gain/30",
        isNegative && "bg-loss/15 text-loss border border-loss/30",
        isZero && "bg-neutral/15 text-neutral border border-neutral/30",
        className
      )}
    >
      {showIcon && <Icon className={size === "sm" ? "size-3" : "size-3.5"} />}
      <span>{fmtSignedPct(value)}</span>
      {abs !== undefined && abs !== null && (
        <span className="opacity-75 text-[10px] ml-0.5">
          ({abs > 0 ? `+${abs}` : abs})
        </span>
      )}
    </span>
  );
}
