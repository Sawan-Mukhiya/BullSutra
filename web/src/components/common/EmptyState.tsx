import React from "react";
import { FolderSearch, LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon: Icon = FolderSearch,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-14 px-4 text-center rounded-xl",
        className
      )}
    >
      <div className="size-16 rounded-full bg-accent/60 border border-gold-500/30 flex items-center justify-center text-gold-500 mb-4 shadow-sm">
        <Icon className="size-8" />
      </div>
      <h3 className="text-xl font-semibold font-display text-foreground">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm mt-1.5 leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <Button onClick={onAction} className="mt-6" variant="default">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
