"use client";

import React, { useState } from "react";
import { ChevronDown, SlidersHorizontal, Cpu, GitCommit } from "lucide-react";
import { Card } from "@/components/ui/card";
import { fmtDateTime, fmtDate } from "@/lib/format";
import { AGENTS, AgentKey } from "@/lib/constants";
import { cn } from "@/lib/utils";

export interface MetaPanelProps {
  meta?: {
    weights?: Record<string, number>;
    graph_version?: string;
    logic_version?: string;
    prompt_version?: string;
    llm_model?: string | null;
    price_date?: string;
    news_cutoff?: string;
    generated_at?: string;
    [key: string]: unknown;
  } | null;
  className?: string;
}

export function MetaPanel({ meta, className }: MetaPanelProps) {
  const [open, setOpen] = useState(false);

  if (!meta) return null;

  return (
    <Card className={cn("overflow-hidden transition-all", className)}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full p-4 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <SlidersHorizontal className="size-4 text-gold-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
            System Provenance & Model Weights
          </span>
        </div>
        <ChevronDown
          className={cn(
            "size-4 text-text-subtle transition-transform duration-200",
            open && "rotate-180"
          )}
        />
      </button>

      {open && (
        <div className="p-5 pt-0 border-t border-border/60 space-y-5 text-xs text-muted-foreground">
          {/* Dynamic Specialist Weights */}
          {meta.weights && (
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-text-subtle block mb-2">
                Empirical Hit-Rate Weights
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {Object.entries(meta.weights).map(([agent, w]) => {
                  const agentMeta = AGENTS[agent as AgentKey];
                  return (
                    <div
                      key={agent}
                      className="p-2.5 rounded-lg bg-secondary/50 border border-border/50"
                    >
                      <span className="block text-text-subtle capitalize mb-1">
                        {agentMeta?.label || agent}
                      </span>
                      <span className="font-mono font-bold text-sm text-foreground">
                        {Number(w).toFixed(2)}×
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Model & Ingestion Metadata */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div className="flex items-center justify-between py-1 border-b border-border/40">
              <span className="flex items-center gap-1.5">
                <Cpu className="size-3.5 text-text-subtle" />
                <span>Synthesis Engine:</span>
              </span>
              <span className="font-mono text-foreground">{meta.llm_model || "Deterministic Math Only"}</span>
            </div>

            <div className="flex items-center justify-between py-1 border-b border-border/40">
              <span className="flex items-center gap-1.5">
                <GitCommit className="size-3.5 text-text-subtle" />
                <span>Pipeline Version:</span>
              </span>
              <span className="font-mono text-foreground">
                v{meta.graph_version || "1.0.0"}
              </span>
            </div>

            <div className="flex items-center justify-between py-1 border-b border-border/40">
              <span>Price As-Of:</span>
              <span className="font-mono text-foreground">{fmtDate(meta.price_date)}</span>
            </div>

            <div className="flex items-center justify-between py-1 border-b border-border/40">
              <span>News Cutoff:</span>
              <span className="font-mono text-foreground">{fmtDateTime(meta.news_cutoff)}</span>
            </div>
          </div>

          <div className="text-[11px] text-text-subtle text-right">
            Generated at: {fmtDateTime(meta.generated_at)}
          </div>
        </div>
      )}
    </Card>
  );
}
