"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { Sparkles, ArrowRight, CheckCircle2, History } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { RunProgress } from "@/components/jobs/RunProgress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useRunAgents, useJobs } from "@/hooks/useAdmin";
import { fmtDateTime } from "@/lib/format";

export default function AdminRunsPage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-xs font-mono text-text-subtle">Loading runner...</div>}>
      <AdminRunsPageContent />
    </React.Suspense>
  );
}

function AdminRunsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const defaultSymbol = searchParams.get("symbol") || "";

  const [symbol, setSymbol] = useState(defaultSymbol);
  const [asOf, setAsOf] = useState("");
  const [useLlm, setUseLlm] = useState(true);
  const [force, setForce] = useState(false);

  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [finishedBrief, setFinishedBrief] = useState<any | null>(null);

  const runAgents = useRunAgents();
  const { data: recentRuns } = useJobs("research", undefined, 0, 10);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol.trim()) {
      toast.error("Please enter a stock symbol");
      return;
    }

    setFinishedBrief(null);
    setActiveJobId(null);

    try {
      const res = await runAgents.mutateAsync({
        symbol: symbol.trim().toUpperCase(),
        as_of: asOf || undefined,
        use_llm: useLlm,
        force,
      });

      if (res.status === "cached") {
        toast.info("Recent cached brief found for this date", {
          action: {
            label: "Open Brief",
            onClick: () => router.push(`/stocks/${symbol.toUpperCase()}`),
          },
        });
        setFinishedBrief({ cached: true, symbol: symbol.toUpperCase() });
      } else if (res.job_id) {
        setActiveJobId(res.job_id);
        toast.success(`Multi-agent research job queued: ${res.job_id.slice(0, 8)}`);
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to trigger research graph");
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          Execute Multi-Agent Research Graph
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Trigger the full 11-node LangGraph pipeline (News, Fundamentals, Technicals, Risk, Debate, Consensus, Calibration, Synthesis).
        </p>
      </div>

      {/* Main Execution Form */}
      <Card featured className="p-6 lg:p-8 max-w-2xl mx-auto space-y-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Stock Symbol
              </label>
              <Input
                placeholder="e.g. NABIL, NICA, CIT"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="font-mono text-sm"
                required
              />
              <p className="text-[11px] text-text-subtle">
                Any active NEPSE symbol with price data (Universe 40 stocks have automated daily briefs).
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                As-Of Date (Optional)
              </label>
              <Input
                type="date"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
                className="font-mono text-sm"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-border/60">
            <label className="flex items-center gap-2.5 cursor-pointer text-xs font-medium">
              <Switch checked={useLlm} onCheckedChange={setUseLlm} />
              <span>Enable Regex-Guarded Narrative Synthesis</span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer text-xs font-medium">
              <Switch checked={force} onCheckedChange={setForce} />
              <span className="text-text-subtle">Force Recalculate (Bypass Cache)</span>
            </label>
          </div>

          <Button
            type="submit"
            size="lg"
            className="w-full gap-2 text-sm font-semibold"
            loading={runAgents.isPending}
          >
            <Sparkles className="size-4" />
            <span>Launch Multi-Agent Research Graph</span>
          </Button>
        </form>
      </Card>

      {/* Live SSE Execution Stepper */}
      {activeJobId && (
        <RunProgress
          jobId={activeJobId}
          kind="research"
          onFinished={(res) => setFinishedBrief(res)}
        />
      )}

      {/* Finished Success Card */}
      {finishedBrief && (
        <Card className="p-6 max-w-2xl mx-auto border-2 border-gain/40 bg-gain/5 flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-5 text-gain" />
              <h4 className="font-semibold text-foreground">Research Brief Dossier Ready</h4>
            </div>
            <p className="text-xs text-muted-foreground">
              Consensus synthesized and stored in PostgreSQL.
            </p>
          </div>

          <Link href={`/stocks/${symbol.toUpperCase()}`}>
            <Button size="sm" variant="default" className="gap-1.5">
              <span>View Dossier</span>
              <ArrowRight className="size-4" />
            </Button>
          </Link>
        </Card>
      )}

      {/* Recent Research Runs */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center gap-2">
          <History className="size-4 text-gold-500" />
          <h2 className="font-display text-lg font-bold text-foreground">
            Recent Research Executions
          </h2>
        </div>

        <Card className="p-0 overflow-hidden">
          <Table>
            <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
              <TableRow>
                <TableHead className="pl-6">Job ID</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Time</TableHead>
                <TableHead className="text-right">Elapsed</TableHead>
                <TableHead className="text-right pr-6">Action</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {recentRuns?.items?.map((run) => (
                <TableRow key={run.id} className="hover:bg-white/[0.03]">
                  <TableCell className="pl-6 font-mono text-xs text-text-subtle">
                    {run.id.slice(0, 10)}...
                  </TableCell>
                  <TableCell className="font-mono font-bold text-xs text-foreground">
                    {String((run.payload as any)?.symbol || "—")}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        run.status === "succeeded"
                          ? "gain"
                          : run.status === "failed"
                          ? "loss"
                          : "neutral"
                      }
                      className="text-[10px] capitalize"
                    >
                      {run.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-text-subtle">
                    {fmtDateTime(run.started_at)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    {run.started_at
                      ? `${Math.max(0, Math.round(((run.finished_at ? new Date(run.finished_at).getTime() : Date.now()) - new Date(run.started_at).getTime()) / 1000))}s`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-right pr-6">
                    {Boolean((run.payload as any)?.symbol) && (
                      <Link href={`/stocks/${String((run.payload as any).symbol)}`}>
                        <Button size="sm" variant="ghost" className="h-7 text-xs">
                          Inspect
                        </Button>
                      </Link>
                    )}
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
