import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[14px] text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-500/40 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-gold-gradient text-primary-foreground shadow-md hover:brightness-110 active:brightness-95",
        destructive:
          "bg-loss text-white shadow-sm hover:brightness-110 active:brightness-95",
        outline:
          "border border-gold-500/40 bg-transparent text-gold-300 hover:bg-gold-500/10 active:bg-gold-500/20",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost:
          "text-muted-foreground hover:bg-white/5 dark:hover:bg-white/5 hover:text-foreground",
        link: "text-gold-300 underline-offset-4 hover:underline",
      },
      size: {
        default: "h-11 px-5 py-2",
        sm: "h-9 rounded-[10px] px-3 text-xs",
        lg: "h-12 rounded-[16px] px-8 text-base",
        icon: "size-10 rounded-[12px]",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        aria-busy={loading}
        {...props}
      >
        {loading && <Loader2 className="animate-spin size-4 mr-1.5" />}
        {children}
      </Comp>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
