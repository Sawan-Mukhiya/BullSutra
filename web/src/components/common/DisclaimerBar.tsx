import React from "react";
import { Info } from "lucide-react";
import { DISCLAIMER } from "@/lib/constants";
import { cn } from "@/lib/utils";

export function DisclaimerBar({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 p-3.5 rounded-lg border border-border/80 bg-secondary/40 text-xs text-muted-foreground leading-relaxed",
        className
      )}
    >
      <Info className="size-4 shrink-0 text-gold-500 mt-0.5" />
      <div>
        <strong className="text-foreground font-semibold">Research Output: </strong>
        {DISCLAIMER}
      </div>
    </div>
  );
}
