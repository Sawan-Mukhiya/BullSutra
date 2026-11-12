import React from "react";
import { Card } from "@/components/ui/card";
import { DeltaChip } from "./DeltaChip";
import { cn } from "@/lib/utils";

export interface StatCardProps {
  label: string;
  value: string | number;
  delta?: number | null;
  deltaAbs?: number | null;
  footnote?: string;
  loading?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function StatCard({
  label,
  value,
  delta,
  deltaAbs,
  footnote,
  loading = false,
  className,
  children,
}: StatCardProps) {
  return (
    <Card className={cn("p-5 flex flex-col justify-between min-h-[120px]", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-text-subtle">
          {label}
        </span>
        {delta !== undefined && delta !== null && (
          <DeltaChip value={delta} abs={deltaAbs} size="sm" />
        )}
      </div>

      <div className="mt-2 flex items-baseline justify-between gap-4">
        <span className="text-2xl sm:text-3xl font-mono font-semibold tracking-tight text-foreground num">
          {value}
        </span>
        {children}
      </div>

      {footnote && (
        <span className="text-[11px] text-muted-foreground mt-2 line-clamp-1">
          {footnote}
        </span>
      )}
    </Card>
  );
}
