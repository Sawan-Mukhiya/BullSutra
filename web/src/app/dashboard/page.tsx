"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  Search,
  Sparkles,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Layers,
  Scale,
  ShieldCheck,
  Clock,
  Gauge,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { GlobalSearch } from "@/components/layout/GlobalSearch";
import { StatCard } from "@/components/common/StatCard";
import { BriefCard } from "@/components/brief/BriefCard";
import { MarketStatusPill } from "@/components/layout/MarketStatusPill";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { useLatestBriefs } from "@/hooks/useBrief";
import { useFreshness } from "@/hooks/useAdmin";
import { fmtDate } from "@/lib/format";

const SECTORS = [
  { key: "all", label: "All Sectors" },
  { key: "bank", label: "Banks & Finance" },
  { key: "hydro", label: "Hydropower" },
  { key: "insurance", label: "Insurance" },
  { key: "other", label: "Others" },
];

export default function DashboardPage() {
  const [searchOpen, setSearchOpen] = useState(false);
  const [selectedSector, setSelectedSector] = useState("all");
  const [signalFilter, setSignalFilter] = useState<"ALL" | "BUY" | "HOLD" | "SELL">("ALL");

  const { data: briefsData, isLoading, isError, refetch } = useLatestBriefs(0, 40);
  const { data: freshness } = useFreshness();

  // Filter briefs client-side
  const filteredBriefs = useMemo(() => {
    if (!briefsData?.items) return [];
    return briefsData.items.filter((b) => {
      const bSector = (b as any).sector_group || (b as any).sector;
      const matchSector =
        selectedSector === "all" ||
        (bSector && bSector.toLowerCase() === selectedSector.toLowerCase());

      const matchSignal =
        signalFilter === "ALL" ||
        b.label?.toUpperCase() === signalFilter;

      return matchSector && matchSignal;
    });
  }, [briefsData, selectedSector, signalFilter]);

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Top Greeting & Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                Market Research Dashboard
              </h1>
              <MarketStatusPill status="Open" />
            </div>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              Data synchronized as of{" "}
              <strong className="text-foreground font-mono">
                {freshness?.latest_price_date ? fmtDate(freshness.latest_price_date) : "Latest Session"}
              </strong>
              {freshness?.stale && (
                <Badge variant="destructive" className="ml-2 text-[10px] py-0 px-1.5">
                  Delayed
                </Badge>
              )}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setSearchOpen(true)}
              className="flex items-center gap-2 h-10 px-4 rounded-lg bg-secondary border border-border text-xs text-text-subtle hover:border-gold-500/40 transition-colors"
            >
              <Search className="size-3.5 text-gold-500" />
              <span>Search any stock...</span>
              <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-card rounded border border-border">
                ⌘K
              </kbd>
            </button>

            <Link href="/backtests">
              <Button size="sm" variant="outline" className="hidden sm:inline-flex">
                Backtest Ledger
              </Button>
            </Link>
          </div>
        </div>

        {/* Index Strip (4 StatCards) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <StatCard
            label="NEPSE Benchmark"
            value="2,712.40"
            delta={0.82}
            deltaAbs={22.14}
            footnote="Official Index Close"
          />

          <StatCard
            label="Total Turnover"
            value="Rs. 3.42 Cr"
            delta={14.5}
            footnote="Active market session aggregate"
          />

          <StatCard
            label="Traded Volume"
            value="8.92M"
            delta={-2.1}
            footnote="Unified multi-source shares traded"
          />

          <Card className="p-5 flex flex-col justify-between min-h-[120px]">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-text-subtle">
                Market Breadth
              </span>
              <span className="text-[10px] font-mono text-gain font-semibold">142 Adv / 61 Dec</span>
            </div>

            <div className="my-2">
              <div className="flex items-baseline justify-between text-xs font-mono font-bold mb-1.5">
                <span className="text-gain flex items-center gap-1">
                  <TrendingUp className="size-3" /> 142
                </span>
                <span className="text-text-subtle">12 Unch</span>
                <span className="text-loss flex items-center gap-1">
                  <TrendingDown className="size-3" /> 61
                </span>
              </div>
              <div className="h-2 rounded-full overflow-hidden flex gap-1 bg-secondary">
                <div className="bg-gain rounded-l-full" style={{ width: "66%" }} />
                <div className="bg-text-subtle" style={{ width: "6%" }} />
                <div className="bg-loss rounded-r-full" style={{ width: "28%" }} />
              </div>
            </div>

            <span className="text-[11px] text-muted-foreground line-clamp-1">
              Bullish advance/decline ratio 2.33:1
            </span>
          </Card>
        </div>

        {/* Market Structure & Rules Banner */}
        <Card className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-secondary/30">
          <div className="flex items-center gap-3">
            <div className="size-9 rounded-full bg-accent flex items-center justify-center text-gold-500 shrink-0">
              <Gauge className="size-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-foreground">
                NEPSE 2026 Structural Regime Rules
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5">
                Standard trading days (Sunday to Thursday, 11:00 - 15:00 NPT) with ±10% daily circuit limit execution blocks.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Badge variant="gold" className="text-xs">
              Long-Only Cash Exit
            </Badge>
            <Badge variant="outline" className="text-xs">
              4-Tier Broker Slab
            </Badge>
          </div>
        </Card>

        {/* Latest Research Briefs Grid Section */}
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
            <div>
              <h2 className="font-display text-xl font-bold text-foreground">
                Latest Specialist Research Briefs
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Cross-examined consensus briefs produced by the four-agent deterministic pipeline.
              </p>
            </div>

            {/* Filter Controls */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Sector Filter Chips */}
              <div className="flex items-center gap-1 p-1 rounded-lg bg-secondary/60">
                {SECTORS.map((sec) => (
                  <button
                    key={sec.key}
                    onClick={() => setSelectedSector(sec.key)}
                    className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                      selectedSector === sec.key
                        ? "bg-card text-foreground border border-gold-500/40 shadow-sm"
                        : "text-text-subtle hover:text-foreground"
                    }`}
                  >
                    {sec.label}
                  </button>
                ))}
              </div>

              {/* Signal Filter Toggle */}
              <div className="flex items-center gap-1 p-1 rounded-lg bg-secondary/60 text-xs font-mono">
                {(["ALL", "BUY", "HOLD", "SELL"] as const).map((sig) => (
                  <button
                    key={sig}
                    onClick={() => setSignalFilter(sig)}
                    className={`px-2.5 py-1 rounded-md font-semibold transition-colors ${
                      signalFilter === sig
                        ? sig === "BUY"
                          ? "bg-gain/20 text-gain border border-gain/40"
                          : sig === "SELL"
                          ? "bg-loss/20 text-loss border border-loss/40"
                          : "bg-card text-foreground border border-gold-500/40"
                        : "text-text-subtle hover:text-foreground"
                    }`}
                  >
                    {sig}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Grid of Brief Cards */}
          {isLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {[...Array(8)].map((_, i) => (
                <Card key={i} className="p-5 h-48 space-y-4">
                  <div className="flex justify-between items-center">
                    <Skeleton className="size-8 rounded-full" />
                    <Skeleton className="w-16 h-6 rounded-full" />
                  </div>
                  <Skeleton className="w-3/4 h-4 rounded" />
                  <Skeleton className="w-full h-12 rounded" />
                  <Skeleton className="w-1/2 h-3 rounded" />
                </Card>
              ))}
            </div>
          )}

          {isError && (
            <ErrorState
              title="Could not load research briefs"
              description="Failed to fetch briefs from the API service. Please verify that the backend is active."
              onRetry={refetch}
            />
          )}

          {!isLoading && !isError && filteredBriefs.length === 0 && (
            <EmptyState
              title="No briefs matching criteria"
              description="No research briefs matched the selected sector or signal filters. Try clearing filters or run the research agents for universe stocks."
              actionLabel="Clear Filters"
              onAction={() => {
                setSelectedSector("all");
                setSignalFilter("ALL");
              }}
            />
          )}

          {!isLoading && !isError && filteredBriefs.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredBriefs.map((brief) => (
                <BriefCard key={brief.id} brief={brief} />
              ))}
            </div>
          )}
        </div>
      </div>

      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </AppShell>
  );
}
