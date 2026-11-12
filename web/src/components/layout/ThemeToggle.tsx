"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <Button variant="ghost" size="icon" className={className} aria-label="Toggle theme" />;
  }

  const isDark = theme === "dark";

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={className}
      aria-label="Toggle theme"
      aria-pressed={isDark}
    >
      {isDark ? (
        <Sun className="size-5 text-gold-300 transition-transform duration-250 hover:rotate-45" />
      ) : (
        <Moon className="size-5 text-muted-foreground transition-transform duration-250 hover:-rotate-12" />
      )}
    </Button>
  );
}
