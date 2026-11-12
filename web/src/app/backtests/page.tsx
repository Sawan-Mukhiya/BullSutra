"use client";

import React from "react";
import Link from "next/link";
import { FlaskConical, PlusCircle, ArrowUpRight, TrendingUp, CheckCircle2 } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { useBacktestList } from "@/hooks/useBacktest";
import { useSession } from "@/hooks/useSession";
import { fmtDate, fmtPct, fmtNum } from "@/lib/format";

export default function BacktestsPage() {
  const { data: session } = useSession();
  const { data, isLoading, isError, refetch } = useBacktestList(0, 20);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Walk-Forward Backtests
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              Rigorous out-of-sample simulation across rolling train/test folds with empirical NEPSE cost model.
            </p>
          </div>

          {session?.authenticated && (
            <Link href="/admin/backtests/new">
              <Button size="sm" variant="default" className="gap-2">
                <PlusCircle className="size-4" />
                <span>New Backtest Run</span>
              </Button>
            </Link>
          )}
        </div>

        {/* Backtests List Table */}
        <Card className="p-0 overflow-hidden">
          <Table>
            <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
              <TableRow>
                <TableHead className="pl-6">Backtest Run</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Sharpe Ratio (BullSutra vs B&H)</TableHead>
                <TableHead className="text-right">CAGR (BullSutra vs B&H)</TableHead>
                <TableHead className="text-right pr-6">Action</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {isLoading ? (
                [...Array(6)].map((_, i) => (
                  <TableRow key={i}>
                    <TableCell className="pl-6"><Skeleton className="w-48 h-5" /></TableCell>
                    <TableCell><Skeleton className="w-16 h-5 rounded-full" /></TableCell>
                    <TableCell><Skeleton className="w-24 h-4" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="w-28 h-4 ml-auto" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="w-28 h-4 ml-auto" /></TableCell>
                    <TableCell className="text-right pr-6"><Skeleton className="w-16 h-8 ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : isError ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-48 text-center">
                    <ErrorState
                      description="Failed to load backtests history."
                      onRetry={refetch}
                    />
                  </TableCell>
                </TableRow>
              ) : !data?.items || data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-64 text-center">
                    <EmptyState
                      icon={FlaskConical}
                      title="No backtests found"
                      description="No simulation runs have been recorded in the database yet."
                      actionLabel={session?.authenticated ? "Create First Backtest" : undefined}
                      onAction={
                        session?.authenticated
                          ? () => {
                              window.location.href = "/admin/backtests/new";
                            }
                          : undefined
                      }
                    />
                  </TableCell>
                </TableRow>
              ) : (
                data.items.map((item) => {
                  const summary = (item.summary || {}) as Record<string, any>;
                  const fullSharpe = summary.full?.sharpe;
                  const bhSharpe = summary.bh_equal_weight?.sharpe;
                  const fullCagr = summary.full?.cagr;
                  const bhCagr = summary.bh_equal_weight?.cagr;

                  const statusVariant =
                    item.status === "succeeded"
                      ? "gain"
                      : item.status === "failed"
                      ? "loss"
                      : item.status === "running"
                      ? "info"
                      : "neutral";

                  return (
                    <TableRow key={item.id} className="hover:bg-white/[0.03]">
                      <TableCell className="pl-6 font-medium">
                        <Link
                          href={`/backtests/${item.id}`}
                          className="font-mono font-semibold text-foreground hover:text-gold-300 transition-colors"
                        >
                          {item.name || `Simulation ${item.id.slice(0, 8)}`}
                        </Link>
                      </TableCell>

                      <TableCell>
                        <Badge variant={statusVariant} className="capitalize text-[10px]">
                          {item.status}
                        </Badge>
                      </TableCell>

                      <TableCell className="text-xs text-text-subtle font-mono">
                        {fmtDate(item.created_at)}
                      </TableCell>

                      <TableCell className="text-right font-mono text-xs">
                        {fullSharpe !== undefined && bhSharpe !== undefined ? (
                          <div className="flex items-center justify-end gap-1.5 font-bold">
                            <span className="text-gold-500">{fmtNum(fullSharpe, 2)}</span>
                            <span className="text-text-subtle font-normal">vs</span>
                            <span className="text-muted-foreground">{fmtNum(bhSharpe, 2)}</span>
                          </div>
                        ) : (
                          "—"
                        )}
                      </TableCell>

                      <TableCell className="text-right font-mono text-xs">
                        {fullCagr !== undefined && bhCagr !== undefined ? (
                          <div className="flex items-center justify-end gap-1.5 font-bold">
                            <span className="text-gain">{fmtPct(fullCagr, 1)}</span>
                            <span className="text-text-subtle font-normal">vs</span>
                            <span className="text-muted-foreground">{fmtPct(bhCagr, 1)}</span>
                          </div>
                        ) : (
                          "—"
                        )}
                      </TableCell>

                      <TableCell className="text-right pr-6">
                        <Link href={`/backtests/${item.id}`}>
                          <Button size="sm" variant="outline" className="h-8 px-2.5 text-xs gap-1">
                            <span>Inspect</span>
                            <ArrowUpRight className="size-3" />
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </Card>
      </div>
    </AppShell>
  );
}
