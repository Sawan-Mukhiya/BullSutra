"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  CandlestickChart,
  FlaskConical,
  Briefcase,
  Newspaper,
  Settings2,
  ShieldCheck,
  Sparkles,
  PlusCircle,
  Database,
  UploadCloud,
  Key,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSession } from "@/hooks/useSession";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Markets", href: "/markets", icon: CandlestickChart },
  { label: "Backtest", href: "/backtests", icon: FlaskConical },
  { label: "Portfolio", href: "/portfolio", icon: Briefcase },
  { label: "News Feed", href: "/news", icon: Newspaper },
  { label: "Settings", href: "/settings", icon: Settings2 },
];

const ADMIN_ITEMS = [
  { label: "Overview", href: "/admin", icon: ShieldCheck },
  { label: "Run Agents", href: "/admin/runs", icon: Sparkles },
  { label: "New Backtest", href: "/admin/backtests/new", icon: PlusCircle },
  { label: "Data Pipelines", href: "/admin/pipelines", icon: Database },
  { label: "Upload Wizard", href: "/admin/uploads", icon: UploadCloud },
  { label: "API Keys", href: "/admin/api-keys", icon: Key },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();

  const isAdmin = session?.authenticated;

  return (
    <aside className="fixed left-0 top-0 bottom-0 z-30 hidden md:flex flex-col w-[76px] lg:w-[264px] bg-bg-raised border-r border-border py-6 px-3 lg:px-4 transition-all">
      {/* Brand Monogram & Wordmark */}
      <div className="h-10 mb-8 flex items-center gap-3 px-2">
        <Link href="/" className="flex items-center gap-3">
          <div className="size-9 rounded-full bg-gold-gradient flex items-center justify-center shrink-0 shadow-sm">
            <svg viewBox="0 0 24 24" className="size-5 fill-primary-foreground stroke-primary-foreground stroke-[1.5]">
              <path d="M4 18 C4 18 8 16 12 10 C16 4 20 4 20 4 M20 4 L16 8 M20 4 L20 9" />
            </svg>
          </div>
          <span className="hidden lg:inline font-display text-xl font-bold tracking-tight">
            Bull<span className="text-gold-500">Sutra</span>
          </span>
        </Link>
      </div>

      {/* Primary Navigation */}
      <div className="flex-1 overflow-y-auto thin-scrollbar space-y-6">
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "relative flex items-center gap-3 h-11 px-3 rounded-md text-sm font-medium transition-colors",
                  isActive
                    ? "text-accent-foreground bg-accent"
                    : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
                )}
                title={item.label}
              >
                {isActive && (
                  <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r-full bg-gold-gradient" />
                )}
                <Icon className="size-5 shrink-0" />
                <span className="hidden lg:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Admin Navigation Group */}
        {isAdmin && (
          <div className="pt-4 border-t border-border/60">
            <span className="hidden lg:block px-3 text-[11px] font-semibold uppercase tracking-wider text-text-subtle mb-2">
              Admin Workspace
            </span>
            <nav className="space-y-1">
              {ADMIN_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "relative flex items-center gap-3 h-10 px-3 rounded-md text-sm font-medium transition-colors",
                      isActive
                        ? "text-accent-foreground bg-accent"
                        : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
                    )}
                    title={item.label}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-gold-gradient" />
                    )}
                    <Icon className="size-4 shrink-0 text-gold-500" />
                    <span className="hidden lg:inline">{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        )}
      </div>

      {/* Bottom Market Status Mini Widget */}
      <div className="hidden lg:block pt-4 border-t border-border/60">
        <div className="glass p-3 rounded-lg text-xs space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-text-subtle font-medium">NEPSE Benchmark</span>
            <span className="size-2 rounded-full bg-gain animate-pulse" />
          </div>
          <div className="flex items-baseline justify-between font-mono font-semibold">
            <span>2,712.40</span>
            <span className="text-gain text-[11px]">+0.82%</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
