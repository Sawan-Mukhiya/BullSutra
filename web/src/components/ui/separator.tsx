import * as React from "react";
import * as SeparatorPrimitive from "@radix-ui/react-separator";
import { cn } from "@/lib/utils";

const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root> & { gold?: boolean }
>(
  (
    { className, orientation = "horizontal", decorative = true, gold = false, ...props },
    ref
  ) => (
    <SeparatorPrimitive.Root
      ref={ref}
      decorative={decorative}
      orientation={orientation}
      className={cn(
        gold
          ? "hairline-gold"
          : "shrink-0 bg-border",
        orientation === "horizontal"
          ? gold ? "h-[1px] w-full" : "h-[1px] w-full"
          : "h-full w-[1px]",
        className
      )}
      {...props}
    />
  )
);
Separator.displayName = SeparatorPrimitive.Root.displayName;

export { Separator };
