"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  CandlestickChart,
  Search,
  Briefcase,
  FlaskConical,
} from "lucide-react";
import { GlobalSearch } from "./GlobalSearch";
import { cn } from "@/lib/utils";

export function BottomTabBar() {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);

  const tabs = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Markets", href: "/markets", icon: CandlestickChart },
    { label: "Search", action: () => setSearchOpen(true), icon: Search },
    { label: "Backtest", href: "/backtests", icon: FlaskConical },
    { label: "Portfolio", href: "/portfolio", icon: Briefcase },
  ];

  return (
    <>
      <nav className="fixed bottom-0 inset-x-0 z-40 h-[68px] bg-bg-raised/90 backdrop-blur-xl border-t border-border flex items-center justify-around md:hidden pb-[env(safe-area-inset-bottom)]">
        {tabs.map((tab, idx) => {
          const Icon = tab.icon;
          const isActive = tab.href && (pathname === tab.href || pathname.startsWith(tab.href + "/"));

          if (tab.action) {
            return (
              <button
                key={idx}
                onClick={tab.action}
                className="flex flex-col items-center justify-center flex-1 py-1 text-muted-foreground hover:text-foreground transition-colors"
              >
                <Icon className="size-5 mb-1" />
                <span className="text-[10px] font-medium">{tab.label}</span>
              </button>
            );
          }

          return (
            <Link
              key={idx}
              href={tab.href!}
              className={cn(
                "relative flex flex-col items-center justify-center flex-1 py-1 transition-colors",
                isActive ? "text-gold-500 font-semibold" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {isActive && (
                <span className="absolute top-0 w-8 h-[2px] rounded-full bg-gold-gradient" />
              )}
              <Icon className="size-5 mb-1" />
              <span className="text-[10px] font-medium">{tab.label}</span>
            </Link>
          );
        })}
      </nav>

      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </>
  );
}
