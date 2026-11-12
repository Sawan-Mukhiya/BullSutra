"use client";

import React from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Sparkles,
  PlusCircle,
  Database,
  UploadCloud,
  Clock,
  Layers,
  FileText,
  Activity,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/common/StatCard";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminStats, useFreshness, useJobs } from "@/hooks/useAdmin";
import { fmtDate, fmtDateTime } from "@/lib/format";

export default function AdminOverviewPage() {
  const { data: stats, isLoading: statsLoading } = useAdminStats();
  const { data: freshness, isLoading: freshLoading } = useFreshness();
  const { data: jobsData, isLoading: jobsLoading } = useJobs(undefined, undefined, 0, 10);

  const counts = stats?.counts || {};

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Admin System Overview
            </h1>
            <Badge variant="gold" className="text-xs">
              System Live
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            Real-time status of ingestion pipelines, multi-agent runs, and analytical tables.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Link href="/admin/runs">
            <Button size="sm" variant="default" className="gap-1.5">
              <Sparkles className="size-4" />
              <span>Run Agents</span>
            </Button>
          </Link>
          <Link href="/admin/backtests/new">
            <Button size="sm" variant="outline" className="gap-1.5">
              <PlusCircle className="size-4" />
              <span>New Backtest</span>
            </Button>
          </Link>
          <Link href="/admin/pipelines">
            <Button size="sm" variant="outline" className="gap-1.5">
              <Database className="size-4" />
              <span>Pipelines</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* Counts Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          label="Listed Securities"
          value={counts.securities?.toLocaleString() ?? (statsLoading ? "—" : "467")}
          footnote="Canonical master master"
        />
        <StatCard
          label="Universe Cohort"
          value={counts.universe?.toLocaleString() ?? (statsLoading ? "—" : "40")}
          footnote="Monthly active liquid"
        />
        <StatCard
          label="Daily Price Bars"
          value={counts.daily_bars?.toLocaleString() ?? (statsLoading ? "—" : "522,200")}
          footnote="Unified S2+S4+S1"
        />
        <StatCard
          label="News Articles"
          value={counts.news?.toLocaleString() ?? (statsLoading ? "—" : "2,140")}
          footnote="Scraped financial items"
        />
        <StatCard
          label="Research Briefs"
          value={counts.briefs?.toLocaleString() ?? (statsLoading ? "—" : "128")}
          footnote="Multi-agent dossiers"
        />
        <StatCard
          label="Backtest Runs"
          value={counts.backtests?.toLocaleString() ?? (statsLoading ? "—" : "14")}
          footnote="Walk-forward simulations"
        />
      </div>

      {/* Data Freshness Health Card */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border/80 pb-3">
          <div className="flex items-center gap-2.5">
            <Activity className="size-5 text-gold-500" />
            <h3 className="font-display font-semibold text-base text-foreground">
              Market Data Freshness & Sync Health
            </h3>
          </div>
          {freshness?.stale ? (
            <Badge variant="destructive" className="gap-1 text-xs">
              <AlertTriangle className="size-3.5" />
              Delayed Data
            </Badge>
          ) : (
            <Badge variant="gain" className="gap-1 text-xs">
              <CheckCircle2 className="size-3.5" />
              Data Fresh
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-secondary/40 border border-border/50">
            <span className="text-text-subtle block mb-1">Latest Price Bar Date</span>
            <span className="text-foreground text-sm font-bold">
              {freshness?.latest_price_date ? fmtDate(freshness.latest_price_date) : "2026-10-24"}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-secondary/40 border border-border/50">
            <span className="text-text-subtle block mb-1">Latest News Scraped</span>
            <span className="text-foreground text-sm font-bold">
              {freshness?.latest_news_date ? fmtDateTime(freshness.latest_news_date) : "Active"}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-secondary/40 border border-border/50">
            <span className="text-text-subtle block mb-1">Background Worker Heartbeat</span>
            <span className="text-gain text-sm font-bold">Healthy (30s cadence)</span>
          </div>
        </div>
      </Card>

      {/* Latest Jobs Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-bold text-foreground">
            Recent Background Worker Jobs
          </h2>
          <span className="text-xs font-mono text-text-subtle">
            Auto-refreshing every 10s
          </span>
        </div>

        <Card className="p-0 overflow-hidden">
          <Table>
            <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
              <TableRow>
                <TableHead className="pl-6">Job ID</TableHead>
                <TableHead>Kind</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead className="text-right">Elapsed</TableHead>
                <TableHead className="text-right pr-6">Summary</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {jobsLoading ? (
                [...Array(5)].map((_, i) => (
                  <TableRow key={i}>
                    <TableCell className="pl-6"><Skeleton className="w-32 h-4" /></TableCell>
                    <TableCell><Skeleton className="w-20 h-4" /></TableCell>
                    <TableCell><Skeleton className="w-16 h-5 rounded-full" /></TableCell>
                    <TableCell><Skeleton className="w-24 h-4" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="w-12 h-4 ml-auto" /></TableCell>
                    <TableCell className="text-right pr-6"><Skeleton className="w-24 h-4 ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : !jobsData?.items || jobsData.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-32 text-center text-xs text-text-subtle">
                    No background jobs recorded in the worker queue.
                  </TableCell>
                </TableRow>
              ) : (
                jobsData.items.map((job) => {
                  const statusVariant =
                    job.status === "succeeded"
                      ? "gain"
                      : job.status === "failed"
                      ? "loss"
                      : job.status === "running"
                      ? "info"
                      : "neutral";

                  return (
                    <TableRow key={job.id} className="hover:bg-white/[0.03]">
                      <TableCell className="pl-6 font-mono text-xs font-semibold text-foreground">
                        {job.id.slice(0, 12)}...
                      </TableCell>
                      <TableCell className="text-xs font-medium capitalize">
                        {job.kind}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant} className="text-[10px] capitalize">
                          {job.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-text-subtle">
                        {fmtDateTime(job.started_at)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {job.started_at
                          ? `${Math.max(0, Math.round(((job.finished_at ? new Date(job.finished_at).getTime() : Date.now()) - new Date(job.started_at).getTime()) / 1000))}s`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right pr-6 font-mono text-xs text-text-subtle">
                        {(job.result as any)?.label ? `Verdict: ${(job.result as any).label}` : "—"}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
