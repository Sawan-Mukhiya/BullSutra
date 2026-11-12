import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface ErrorStateProps {
  title?: string;
  description: string;
  onRetry?: () => void;
  variant?: "card" | "inline";
  className?: string;
}

export function ErrorState({
  title = "Failed to load data",
  description,
  onRetry,
  variant = "card",
  className,
}: ErrorStateProps) {
  if (variant === "inline") {
    return (
      <div
        role="alert"
        className={cn(
          "flex items-center justify-between gap-3 p-3.5 rounded-lg bg-loss/10 border border-loss/30 text-loss text-sm",
          className
        )}
      >
        <div className="flex items-center gap-2.5">
          <AlertTriangle className="size-4 shrink-0 text-loss" />
          <span>{description}</span>
        </div>
        {onRetry && (
          <Button
            size="sm"
            variant="ghost"
            onClick={onRetry}
            className="text-loss hover:bg-loss/15 h-8 px-2.5"
          >
            <RefreshCw className="size-3.5 mr-1" />
            Retry
          </Button>
        )}
      </div>
    );
  }

  return (
    <div
      role="alert"
      className={cn(
        "glass flex flex-col items-center justify-center p-8 text-center rounded-xl",
        className
      )}
    >
      <div className="size-14 rounded-full bg-loss/15 border border-loss/30 flex items-center justify-center text-loss mb-4">
        <AlertTriangle className="size-7" />
      </div>
      <h3 className="text-lg font-semibold text-foreground font-display">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm mt-1 mb-6 leading-relaxed">
        {description}
      </p>
      {onRetry && (
        <Button onClick={onRetry} variant="outline" className="border-loss/40 text-loss hover:bg-loss/10">
          <RefreshCw className="size-4 mr-2" />
          Try again
        </Button>
      )}
    </div>
  );
}
