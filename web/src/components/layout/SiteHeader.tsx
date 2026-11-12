"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "./ThemeToggle";
import { GlobalSearch } from "./GlobalSearch";
import { MarketStatusPill } from "./MarketStatusPill";
import { useSession } from "@/hooks/useSession";

export function SiteHeader() {
  const [searchOpen, setSearchOpen] = useState(false);
  const { data: session } = useSession();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <header className="sticky top-0 z-40 h-[72px] bg-background/80 backdrop-blur-xl border-b border-border transition-colors">
      <div className="max-w-[1440px] mx-auto h-full px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4">
        {/* Brand Logo */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="size-9 rounded-full bg-gold-gradient flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform">
              <svg viewBox="0 0 24 24" className="size-5 fill-primary-foreground stroke-primary-foreground stroke-[1.5]">
                <path d="M4 18 C4 18 8 16 12 10 C16 4 20 4 20 4 M20 4 L16 8 M20 4 L20 9" />
              </svg>
            </div>
            <span className="font-display text-2xl font-bold tracking-tight">
              Bull<span className="text-gold-500">Sutra</span>
            </span>
          </Link>

          <MarketStatusPill className="hidden md:inline-flex" />
        </div>

        {/* Navigation Links */}
        <nav className="hidden lg:flex items-center gap-6 text-sm font-medium text-muted-foreground">
          <Link href="/dashboard" className="hover:text-foreground transition-colors">
            Dashboard
          </Link>
          <Link href="/markets" className="hover:text-foreground transition-colors">
            Markets
          </Link>
          <Link href="/backtests" className="hover:text-foreground transition-colors">
            Backtest
          </Link>
          <Link href="/#agents" className="hover:text-foreground transition-colors">
            Specialists
          </Link>
        </nav>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {/* Quick Search Button */}
          <button
            onClick={() => setSearchOpen(true)}
            className="flex items-center gap-2.5 h-10 px-3.5 rounded-full border border-border bg-secondary/50 text-text-subtle text-xs hover:border-gold-500/40 transition-colors"
          >
            <Search className="size-4" />
            <span className="hidden sm:inline">Search symbol...</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-background/60 rounded border border-border">
              ⌘K
            </kbd>
          </button>

          <ThemeToggle />

          {session?.authenticated ? (
            <Link href="/admin">
              <Button size="sm" variant="default">
                Admin Area
              </Button>
            </Link>
          ) : (
            <div className="flex items-center gap-2">
              <Link href="/login">
                <Button size="sm" variant="ghost" className="text-xs">
                  Log in
                </Button>
              </Link>
              <Link href="/signup">
                <Button size="sm" variant="outline" className="text-xs border-gold-500/40 text-gold-500 hover:bg-gold-500/10">
                  Sign up
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button size="sm" variant="default" className="hidden sm:inline-flex text-xs">
                  Explore App
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>

      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </header>
  );
}
