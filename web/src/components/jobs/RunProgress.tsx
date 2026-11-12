"use client";

import React, { useEffect, useState } from "react";
import { Check, Loader2, X, Minus, Clock, CheckCircle2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { useJobEvents, NodeStatus } from "@/hooks/useJobEvents";
import { cn } from "@/lib/utils";

export interface RunProgressProps {
  jobId: string;
  kind?: "research" | "backtest";
  onFinished?: (result: any) => void;
  className?: string;
}

const RESEARCH_STEPS = [
  { id: "load_context", label: "Load Market Data & Historical Financials" },
  { id: "specialists", label: "Specialists Parallel Analysis (News, Fund, Tech, Risk)", isGroup: true },
  { id: "collect", label: "Collect & Standardize Agent Voters" },
  { id: "debate", label: "Cross-Examination & Multi-Agent Debate" },
  { id: "consensus", label: "Deterministic Voter Consensus Engine" },
  { id: "calibrate", label: "Isotonic Regression Hit-Rate Calibration" },
  { id: "write_brief", label: "Regex-Guarded Synthesis & Narrative Guardrail" },
  { id: "persist", label: "Persist Brief & Audit Record" },
];

export function RunProgress({
  jobId,
  kind = "research",
  onFinished,
  className,
}: RunProgressProps) {
  const { status, progress, phase, nodes, nodeResults, result, error } = useJobEvents(jobId);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (status === "succeeded" && result && onFinished) {
      onFinished(result);
    }
  }, [status, result, onFinished]);

  useEffect(() => {
    if (status !== "running" && status !== "connecting") return;
    const interval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [status]);

  const getStatusIcon = (st?: NodeStatus) => {
    switch (st) {
      case "running":
        return <Loader2 className="size-4 animate-spin text-gold-500" />;
      case "done":
        return <Check className="size-4 text-gain" />;
      case "failed":
        return <X className="size-4 text-loss" />;
      case "skipped":
        return <Minus className="size-4 text-text-subtle" />;
      default:
        return <div className="size-2 rounded-full bg-border" />;
    }
  };

  return (
    <Card featured className={cn("p-6 space-y-6 max-w-2xl mx-auto", className)}>
      <div className="flex items-center justify-between pb-4 border-b border-border/80">
        <div>
          <h3 className="font-display font-semibold text-lg text-foreground">
            {kind === "research" ? "Executing Multi-Agent Research Graph" : "Running Walk-Forward Simulation"}
          </h3>
          <p className="text-xs text-text-subtle font-mono mt-0.5">
            Job ID: {jobId}
          </p>
        </div>

        <div className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground">
          <Clock className="size-3.5 text-gold-500" />
          <span>{elapsed}s elapsed</span>
        </div>
      </div>

      {/* Main Progress Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-subtle capitalize">{phase || status}...</span>
          <span className="font-mono font-semibold">{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} />
      </div>

      {/* Stepper Rows for Research Graph */}
      {kind === "research" && (
        <div className="space-y-2 pt-2">
          {RESEARCH_STEPS.map((step) => {
            let stepStatus: NodeStatus = "pending";
            let detailText = "";

            if (step.isGroup) {
              const groupNodes = ["news", "fundamentals", "technicals", "risk"];
              const allDone = groupNodes.every((n) => nodes[n] === "done");
              const anyRunning = groupNodes.some((n) => nodes[n] === "running");
              const anyFailed = groupNodes.some((n) => nodes[n] === "failed");

              if (allDone) stepStatus = "done";
              else if (anyRunning) stepStatus = "running";
              else if (anyFailed) stepStatus = "failed";

              const doneCount = groupNodes.filter((n) => nodes[n] === "done").length;
              detailText = `${doneCount}/4 completed`;
            } else {
              stepStatus = nodes[step.id] || "pending";
              if (step.id === "debate" && nodes.consensus && !nodes.debate) {
                stepStatus = "skipped";
                detailText = "Agreement formed; debate skipped";
              }
            }

            return (
              <div
                key={step.id}
                className={cn(
                  "flex items-center justify-between p-2.5 rounded-lg border text-xs transition-colors",
                  stepStatus === "running"
                    ? "bg-accent/40 border-gold-500/40 text-foreground font-medium"
                    : stepStatus === "done"
                    ? "bg-secondary/30 border-border/50 text-foreground"
                    : "bg-transparent border-transparent text-text-subtle opacity-60"
                )}
              >
                <div className="flex items-center gap-3">
                  <div className="size-6 rounded-full bg-secondary flex items-center justify-center shrink-0">
                    {getStatusIcon(stepStatus)}
                  </div>
                  <span>{step.label}</span>
                </div>

                {detailText && (
                  <span className="font-mono text-[11px] text-text-subtle">
                    {detailText}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Terminal Error Banner */}
      {status === "failed" && (
        <div className="p-3.5 rounded-lg bg-loss/15 border border-loss/40 text-loss text-xs space-y-1">
          <strong className="block font-semibold">Execution Failed:</strong>
          <p>{error || "Unknown graph execution error occurred."}</p>
        </div>
      )}

      {/* Completion Banner */}
      {status === "succeeded" && (
        <div className="p-4 rounded-lg bg-gain/15 border border-gain/40 text-gain text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-4 shrink-0" />
            <span className="font-semibold">Execution completed successfully.</span>
          </div>
          {result?.label && (
            <span className="font-mono font-bold uppercase tracking-wider">
              Verdict: {result.label} ({Math.round((result.confidence || 0) * 100)}%)
            </span>
          )}
        </div>
      )}
    </Card>
  );
}
