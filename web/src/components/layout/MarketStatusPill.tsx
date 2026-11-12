import React from "react";
import { cn } from "@/lib/utils";

export interface MarketStatusPillProps {
  status?: "Open" | "Closed" | "Pre Open";
  closesAt?: string;
  className?: string;
}

export function MarketStatusPill({
  status = "Closed",
  closesAt = "15:00 NPT",
  className,
}: MarketStatusPillProps) {
  const isOpen = status === "Open";
  const isPreOpen = status === "Pre Open";

  return (
    <div
      title={isOpen ? `Closes at ${closesAt}` : "NEPSE Trading hours: Sun-Thu 11:00 - 15:00 NPT"}
      className={cn(
        "inline-flex items-center gap-2 h-8 px-3 rounded-full text-xs font-medium border select-none transition-colors",
        isOpen && "bg-gain/15 text-gain border-gain/30",
        isPreOpen && "bg-warning/15 text-warning border-warning/30",
        !isOpen && !isPreOpen && "bg-neutral/15 text-neutral border-neutral/30",
        className
      )}
    >
      <span
        className={cn(
          "size-2 rounded-full",
          isOpen && "bg-gain animate-pulse",
          isPreOpen && "bg-warning",
          !isOpen && !isPreOpen && "bg-neutral"
        )}
      />
      <span>{isOpen ? "Market Open" : isPreOpen ? "Pre Open" : "Market Closed"}</span>
    </div>
  );
}
