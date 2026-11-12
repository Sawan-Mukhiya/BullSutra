"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Search, LogOut, User as UserIcon } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { MarketStatusPill } from "./MarketStatusPill";
import { GlobalSearch } from "./GlobalSearch";
import { useSession, useLogout } from "@/hooks/useSession";
import { Button } from "@/components/ui/button";

export function TopBar() {
  const [searchOpen, setSearchOpen] = useState(false);
  const { data: session } = useSession();
  const logout = useLogout();

  return (
    <header className="sticky top-0 z-30 h-[72px] bg-bg-raised/80 backdrop-blur-xl border-b border-border transition-colors">
      <div className="h-full px-4 sm:px-6 flex items-center justify-between gap-4">
        {/* Search Bar Trigger */}
        <div className="flex-1 max-w-xl">
          <button
            onClick={() => setSearchOpen(true)}
            className="flex items-center justify-between w-full h-11 px-4 rounded-lg bg-secondary/60 border border-border text-sm text-text-subtle hover:border-gold-500/40 hover:bg-secondary/80 transition-all text-left"
          >
            <div className="flex items-center gap-2.5">
              <Search className="size-4" />
              <span>Search stocks (e.g. NABIL, CIT, CHCL)...</span>
            </div>
            <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono bg-card rounded border border-border text-foreground font-semibold">
              Ctrl K
            </kbd>
          </button>
        </div>

        {/* Right Status & Actions */}
        <div className="flex items-center gap-3">
          <MarketStatusPill className="hidden sm:inline-flex" />

          <ThemeToggle />

          {session?.authenticated ? (
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline-block text-xs font-mono font-medium text-text-subtle px-2 py-1 rounded bg-secondary">
                {session.user?.email || "Admin"}
              </span>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => logout.mutate()}
                title="Log out"
                aria-label="Log out"
              >
                <LogOut className="size-4 text-text-subtle hover:text-loss" />
              </Button>
            </div>
          ) : (
            <Link href="/login">
              <Button size="sm" variant="outline">
                <UserIcon className="size-3.5 mr-1.5" />
                Sign in
              </Button>
            </Link>
          )}
        </div>
      </div>

      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </header>
  );
}
