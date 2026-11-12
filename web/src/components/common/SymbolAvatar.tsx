import React from "react";
import { cn } from "@/lib/utils";

export interface SymbolAvatarProps {
  ticker: string;
  initials?: string;
  size?: 24 | 32 | 40 | 56;
  className?: string;
}

export function SymbolAvatar({
  ticker,
  initials,
  size = 32,
  className,
}: SymbolAvatarProps) {
  const displayInitials =
    initials ||
    (ticker.length <= 3
      ? ticker
      : ticker.slice(0, 2).toUpperCase());

  const sizeClass = {
    24: "size-6 text-[10px]",
    32: "size-8 text-xs",
    40: "size-10 text-sm",
    56: "size-14 text-lg",
  }[size];

  return (
    <div
      className={cn(
        "rounded-full bg-secondary border border-gold-500/40 flex items-center justify-center font-display font-semibold select-none shrink-0 shadow-sm text-gold-500 dark:text-gold-300",
        sizeClass,
        className
      )}
      title={ticker}
    >
      {displayInitials}
    </div>
  );
}
