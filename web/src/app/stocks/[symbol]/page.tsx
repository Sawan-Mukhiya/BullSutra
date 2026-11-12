"use client";

import React, { use } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Sparkles, AlertTriangle, ShieldCheck, FileText, ChevronRight } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { BriefHeader } from "@/components/brief/BriefHeader";
import { BriefSummaryCard } from "@/components/brief/BriefSummaryCard";
import { AgentCard, RiskAgentCard } from "@/components/brief/AgentCard";
import { DebateTimeline } from "@/components/brief/DebateTimeline";
import { RiskFlags } from "@/components/brief/RiskFlags";
import { DriversList, SourcesList } from "@/components/brief/DriversList";
import { MetaPanel } from "@/components/brief/MetaPanel";
import { PriceChart } from "@/components/charts/PriceChart";
import { DisclaimerBar } from "@/components/common/DisclaimerBar";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useSecurity } from "@/hooks/useSecurity";
import { useBrief, useBriefHistory } from "@/hooks/useBrief";
import { useSession } from "@/hooks/useSession";

export default function StockBriefPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  return (
    <React.Suspense
      fallback={
        <AppShell>
          <div className="space-y-6 animate-pulse">
            <div className="h-28 rounded-xl bg-card/40" />
            <div className="h-96 rounded-xl bg-card/40" />
          </div>
        </AppShell>
      }
    >
      <StockBriefPageContent params={params} />
    </React.Suspense>
  );
}

function StockBriefPageContent({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol: rawSymbol } = use(params);
  const symbol = rawSymbol.toUpperCase();
  const searchParams = useSearchParams();
  const asOf = searchParams.get("as_of") || undefined;

  const { data: session } = useSession();
  const { data: security, isLoading: secLoading } = useSecurity(symbol);
  const { data: history = [] } = useBriefHistory(symbol);
  const {
    data: brief,
    isLoading: briefLoading,
    isError: briefError,
    refetch: refetchBrief,
  } = useBrief(symbol, asOf);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center gap-2 text-xs text-text-subtle font-medium">
          <Link href="/markets" className="hover:text-foreground transition-colors">
            Markets
          </Link>
          <ChevronRight className="size-3.5" />
          <span className="font-mono text-foreground font-semibold">{symbol}</span>
          {asOf && (
            <>
              <ChevronRight className="size-3.5" />
              <span className="font-mono text-gold-500">As-Of: {asOf}</span>
            </>
          )}
        </div>

        {/* Regulatory Disclaimer Bar */}
        <DisclaimerBar />

        {/* Stock Header Band */}
        <BriefHeader
          symbol={symbol}
          security={security}
          briefId={brief?.id}
          history={history}
          currentAsOf={asOf}
        />

        {/* Main Content Layout (Grid: Main Column + Sticky Side Column) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left / Main Column (8 cols) */}
          <div className="lg:col-span-8 space-y-8">
            {/* Interactive Candlestick Price Chart */}
            <PriceChart
              symbol={symbol}
              asOf={brief?.as_of}
              signalLabel={brief?.signal?.label}
            />

            {/* Brief Loading Skeleton */}
            {briefLoading && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[...Array(4)].map((_, i) => (
                    <Skeleton key={i} className="h-64 rounded-xl" />
                  ))}
                </div>
                <Skeleton className="h-48 rounded-xl" />
              </div>
            )}

            {/* Brief Error / Not Found State */}
            {!briefLoading && (briefError || !brief) && (
              <EmptyState
                icon={FileText}
                title={`No research brief yet for ${symbol}`}
                description="Specialist agents have not synthesized a consensus brief for this symbol yet, or the symbol is outside the primary 40-stock universe cohort."
                actionLabel={session?.authenticated ? "Run Multi-Agent Graph" : undefined}
                onAction={
                  session?.authenticated
                    ? () => {
                        window.location.href = `/admin/runs?symbol=${symbol}`;
                      }
                    : undefined
                }
              />
            )}

            {/* Brief Rendered Content */}
            {!briefLoading && brief && (
              <>
                {/* 1. Specialist Agents Cards Grid (2x2) */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="font-display text-xl font-bold text-foreground">
                      Specialist Agent Signals
                    </h2>
                    <span className="text-xs text-text-subtle font-mono">
                      Dynamic Hit-Rate Weighted
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <AgentCard
                      agentKey="news"
                      signal={brief.agents?.news}
                      weight={brief.meta?.weights?.news}
                    />
                    <AgentCard
                      agentKey="fundamentals"
                      signal={brief.agents?.fundamentals}
                      weight={brief.meta?.weights?.fundamentals}
                    />
                    <AgentCard
                      agentKey="technicals"
                      signal={brief.agents?.technicals}
                      weight={brief.meta?.weights?.technicals}
                    />
                    <RiskAgentCard signal={brief.agents?.risk} />
                  </div>
                </div>

                {/* 2. Debate & Cross-Examination Protocol */}
                <div className="space-y-4">
                  <h2 className="font-display text-xl font-bold text-foreground">
                    Agent Debate Protocol
                  </h2>
                  <DebateTimeline debate={brief.debate} />
                </div>

                {/* 3. Risk Flags & Drivers Section */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {/* Risk Flags */}
                  <Card className="p-6 space-y-4">
                    <h3 className="font-display font-semibold text-base text-foreground">
                      Identified Risk Flags
                    </h3>
                    <RiskFlags
                      flags={brief.risks?.map((r: any) =>
                        typeof r === "string"
                          ? { code: r, message: r, severity: "medium" }
                          : r
                      )}
                    />
                  </Card>

                  {/* Key Drivers */}
                  <Card className="p-6 space-y-4">
                    <h3 className="font-display font-semibold text-base text-foreground">
                      Consensus Key Drivers
                    </h3>
                    <DriversList drivers={brief.drivers} />
                  </Card>
                </div>

                {/* 4. Sources Citations */}
                <Card className="p-6 space-y-4">
                  <h3 className="font-display font-semibold text-base text-foreground">
                    Attributed Sources & Data Proof
                  </h3>
                  <SourcesList sources={brief.sources} />
                </Card>

                {/* 5. System Provenance & Weights Meta Panel */}
                <MetaPanel meta={brief.meta as any} />
              </>
            )}
          </div>

          {/* Right / Sticky Side Column (4 cols) */}
          <div className="lg:col-span-4 space-y-6">
            <BriefSummaryCard brief={brief} />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
