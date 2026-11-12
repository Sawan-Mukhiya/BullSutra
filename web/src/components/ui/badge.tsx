import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border border-transparent bg-primary text-primary-foreground",
        secondary:
          "border border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border border-transparent bg-destructive text-destructive-foreground",
        outline: "border border-border text-foreground",
        gain: "border border-gain/30 bg-gain/15 text-gain",
        loss: "border border-loss/30 bg-loss/15 text-loss",
        neutral: "border border-neutral/30 bg-neutral/15 text-neutral",
        info: "border border-info/30 bg-info/15 text-info",
        warning: "border border-warning/30 bg-warning/15 text-warning",
        violet: "border border-violet/30 bg-violet/15 text-violet",
        teal: "border border-teal/30 bg-teal/15 text-teal",
        gold: "border border-gold-500/40 bg-gold-500/15 text-gold-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
