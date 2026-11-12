"use client";

import React, { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Client runtime error boundary caught:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center">
      <div className="size-20 rounded-full bg-loss/15 border border-loss/30 flex items-center justify-center text-loss mb-6">
        <AlertTriangle className="size-10" />
      </div>

      <h1 className="font-display text-3xl font-bold tracking-tight text-foreground">
        Application Error
      </h1>

      <p className="text-sm text-muted-foreground max-w-md mt-2 mb-8 leading-relaxed">
        {error.message || "An unexpected error occurred while rendering the user interface."}
      </p>

      <Button onClick={reset} variant="default" className="gap-2">
        <RefreshCw className="size-4" />
        <span>Reload Interface</span>
      </Button>
    </div>
  );
}
