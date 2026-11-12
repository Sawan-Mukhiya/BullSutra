import React from "react";
import Link from "next/link";
import { FolderSearch, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center">
      <div className="size-20 rounded-full bg-accent flex items-center justify-center text-gold-500 mb-6 shadow-md">
        <FolderSearch className="size-10" />
      </div>

      <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
        Resource Not Found
      </h1>

      <p className="text-sm text-muted-foreground max-w-md mt-2 mb-8 leading-relaxed">
        The requested stock symbol, research brief, or analytical route could not be found in the BullSutra database.
      </p>

      <div className="flex items-center gap-3">
        <Link href="/dashboard">
          <Button variant="default" className="gap-2">
            <ArrowLeft className="size-4" />
            <span>Return to Dashboard</span>
          </Button>
        </Link>
        <Link href="/markets">
          <Button variant="outline">
            Browse All Stocks
          </Button>
        </Link>
      </div>
    </div>
  );
}
