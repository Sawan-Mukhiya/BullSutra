"use client";

import React from "react";
import { Database, Play, CheckCircle2, RefreshCw, Newspaper, Activity, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useRunPipeline, useJobs } from "@/hooks/useAdmin";
import { fmtDateTime } from "@/lib/format";

const PIPELINES = [
  {
    id: "eod_prices",
    name: "Ingest End-of-Day Prices",
    icon: Database,
    description: "Fetches latest trading day OHLCV bars, adjustments, and sector indices.",
  },
  {
    id: "news_scrape",
    name: "Scrape Financial Portals",
    icon: Newspaper,
    description: "Fetches latest articles from Sharesansar, Bizshala, and official company announcements.",
  },
  {
    id: "news_score",
    name: "Compute News Sentiment",
    icon: Activity,
    description: "Processes unscored articles through exponential decay sentiment analyzer.",
  },
  {
    id: "signals_daily",
    name: "Precompute Daily Signals",
    icon: SlidersHorizontal,
    description: "Evaluates causal technical and fundamental indicator series across the 40-stock universe.",
  },
  {
    id: "weights_update",
    name: "Update Calibration & Hit-Rates",
    icon: RefreshCw,
    description: "Evaluates 10-day forward return hit-rates and updates dynamic specialist weights.",
  },
];

export default function AdminPipelinesPage() {
  const runPipeline = useRunPipeline();
  const { data: recentJobs } = useJobs(undefined, undefined, 0, 10);

  const handleRun = async (pipelineId: string, name: string) => {
    try {
      const res = await runPipeline.mutateAsync({ name: pipelineId });
      toast.success(`Pipeline triggered: ${name} (Job: ${res.job_id.slice(0, 8)})`);
    } catch (err: any) {
      toast.error(err?.message || `Failed to trigger ${name}`);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          Data Pipelines & ETL Triggers
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Manually trigger scheduled data ingestion, sentiment scoring, and empirical weight calibration jobs.
        </p>
      </div>

      {/* Pipelines Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {PIPELINES.map((p) => {
          const Icon = p.icon;
          return (
            <Card key={p.id} className="p-6 flex flex-col justify-between space-y-4 hover:border-gold-500/40 transition-colors">
              <div className="space-y-3">
                <div className="size-10 rounded-lg bg-accent flex items-center justify-center text-gold-500">
                  <Icon className="size-5" />
                </div>
                <h3 className="font-display font-semibold text-base text-foreground">
                  {p.name}
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {p.description}
                </p>
              </div>

              <div className="pt-4 border-t border-border/60">
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full gap-2 text-xs"
                  onClick={() => handleRun(p.id, p.name)}
                  loading={runPipeline.isPending}
                >
                  <Play className="size-3.5 text-gold-500" />
                  <span>Execute Pipeline</span>
                </Button>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Recent Pipeline Jobs */}
      <div className="space-y-4 pt-4">
        <h2 className="font-display text-lg font-bold text-foreground">
          Recent Pipeline Execution History
        </h2>

        <Card className="p-0 overflow-hidden">
          <Table>
            <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
              <TableRow>
                <TableHead className="pl-6">Job ID</TableHead>
                <TableHead>Kind</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead className="text-right">Elapsed</TableHead>
                <TableHead className="text-right pr-6">Result</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {recentJobs?.items?.map((job) => (
                <TableRow key={job.id} className="hover:bg-white/[0.03]">
                  <TableCell className="pl-6 font-mono text-xs text-text-subtle">
                    {job.id.slice(0, 10)}...
                  </TableCell>
                  <TableCell className="font-medium text-xs capitalize text-foreground">
                    {job.kind}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        job.status === "succeeded"
                          ? "gain"
                          : job.status === "failed"
                          ? "loss"
                          : "neutral"
                      }
                      className="text-[10px] capitalize"
                    >
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
                    {job.status === "succeeded" ? "Completed" : job.error || "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
