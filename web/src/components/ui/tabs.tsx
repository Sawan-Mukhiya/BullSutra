import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List> & { variant?: "segmented" | "underline" }
>(({ className, variant = "segmented", ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      variant === "segmented" &&
        "inline-flex h-11 items-center justify-center rounded-[12px] bg-secondary p-1 text-muted-foreground",
      variant === "underline" &&
        "inline-flex h-12 items-center gap-6 border-b border-border bg-transparent text-muted-foreground",
      className
    )}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger> & { variant?: "segmented" | "underline" }
>(({ className, variant = "segmented", ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
      variant === "segmented" &&
        "rounded-[8px] px-3.5 py-1.5 data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:border data-[state=active]:border-gold-500/30 data-[state=active]:shadow-sm",
      variant === "underline" &&
        "relative h-12 rounded-none px-2 text-muted-foreground hover:text-foreground data-[state=active]:text-foreground data-[state=active]:after:absolute data-[state=active]:after:bottom-0 data-[state=active]:after:left-0 data-[state=active]:after:right-0 data-[state=active]:after:h-[2px] data-[state=active]:after:bg-gold-500",
      className
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-4 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      className
    )}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
