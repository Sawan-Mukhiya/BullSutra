import React from "react";
import { fmtDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface SourceStampProps {
  updatedAt?: string | null;
  source?: string;
  className?: string;
}

export function SourceStamp({
  updatedAt,
  source = "NEPSE Official EOD Data",
  className,
}: SourceStampProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 text-[11px] text-text-subtle",
        className
      )}
    >
      <span className="size-1.5 rounded-full bg-gold-500 shrink-0" />
      <span>
        As of {updatedAt ? fmtDateTime(updatedAt) : "Latest Session"}. Source: {source}
      </span>
    </div>
  );
}
