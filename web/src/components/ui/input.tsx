import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-11 w-full rounded-[10px] border border-border bg-input px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-text-subtle focus-visible:outline-none focus-visible:border-gold-500/60 focus-visible:ring-4 focus-visible:ring-gold-500/20 disabled:cursor-not-allowed disabled:opacity-50 transition-all",
          error && "border-loss focus-visible:border-loss focus-visible:ring-loss/20",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
