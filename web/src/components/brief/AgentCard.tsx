import React from "react";
import { Newspaper, Landmark, Activity, ShieldAlert, AlertTriangle, ExternalLink } from "lucide-react";
import { Card } from "@/components/ui/card";
import { ScoreBar } from "@/components/common/ScoreBar";
import { fmtScore, fmtPct } from "@/lib/format";
import { AGENTS, FLAG_LABELS } from "@/lib/constants";
import type { AgentSignal } from "@/types";
import { cn } from "@/lib/utils";

const AGENT_ICONS = {
  news: Newspaper,
  fundamentals: Landmark,
  technicals: Activity,
  risk: ShieldAlert,
};

export interface AgentCardProps {
  signal?: AgentSignal | null;
  agentKey: "news" | "fundamentals" | "technicals" | "risk";
  weight?: number;
  className?: string;
}

export function AgentCard({
  signal,
  agentKey,
  weight,
  className,
}: AgentCardProps) {
  const meta = AGENTS[agentKey];
  const Icon = AGENT_ICONS[agentKey];

  if (!signal) {
    return (
      <Card className={cn("p-5 border-l-4 border-l-border opacity-70", className)}>
        <div className="flex items-center gap-3">
          <Icon className="size-5 text-text-subtle" />
          <span className="font-semibold text-sm">{meta.label}</span>
        </div>
        <p className="text-xs text-text-subtle mt-4">Agent signal not available for this session.</p>
      </Card>
    );
  }

  const isLowConfidence = signal.confidence < 0.2;

  return (
    <Card
      className={cn(
        "p-5 flex flex-col justify-between border-l-[3.5px] transition-all",
        className
      )}
      style={{ borderLeftColor: meta.color }}
    >
      <div>
        {/* Header */}
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2.5">
            <div
              className="size-8 rounded-full flex items-center justify-center shrink-0"
              style={{ backgroundColor: `${meta.color}22` }}
            >
              <Icon className="size-4" style={{ color: meta.color }} />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-foreground">{meta.label}</h4>
              <span className="text-[11px] text-text-subtle">
                Confidence {fmtPct(signal.confidence, 0)}
              </span>
            </div>
          </div>

          <div className="text-right flex items-center gap-2">
            {weight !== undefined && (
              <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-secondary text-text-subtle">
                Weight {weight.toFixed(2)}×
              </span>
            )}
            <span className="font-mono text-base font-bold text-foreground num">
              {fmtScore(signal.score)}
            </span>
          </div>
        </div>

        {/* Score Bar */}
        <div className="mb-4">
          <ScoreBar score={signal.score} kind="signed" showValue={false} />
        </div>

        {/* Low Confidence Banner */}
        {isLowConfidence && (
          <div className="flex items-center gap-2 p-2 rounded bg-secondary/70 text-[11px] text-text-subtle mb-3">
            <AlertTriangle className="size-3.5 text-warning shrink-0" />
            <span>Low confidence: this specialist had sparse data.</span>
          </div>
        )}

        {/* Flags Chips */}
        {signal.flags && signal.flags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {signal.flags.map((flag) => (
              <span
                key={flag}
                className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-secondary text-text-subtle border border-border"
              >
                {FLAG_LABELS[flag] || flag}
              </span>
            ))}
          </div>
        )}

        {/* Narrative */}
        <div className="text-xs text-muted-foreground leading-relaxed mb-4">
          {signal.narrative ? (
            <p>{signal.narrative}</p>
          ) : (
            <p className="italic text-text-subtle">Narrative unavailable.</p>
          )}
        </div>
      </div>

      {/* Drivers List */}
      {signal.drivers && signal.drivers.length > 0 && (
        <div className="pt-3 border-t border-border/60">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-text-subtle block mb-1.5">
            Key Drivers
          </span>
          <div className="space-y-1">
            {signal.drivers.slice(0, 3).map((driver, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground truncate max-w-[200px]" title={driver.note}>
                  {driver.note}
                </span>
                <span className="font-mono font-medium text-foreground ml-2 shrink-0">
                  {driver.value !== undefined ? String(driver.value) : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

export function RiskAgentCard({
  signal,
  className,
}: {
  signal?: AgentSignal | null;
  className?: string;
}) {
  const meta = AGENTS.risk;
  const Icon = AGENT_ICONS.risk;

  if (!signal) {
    return (
      <Card className={cn("p-5 border-l-4 border-l-loss opacity-70", className)}>
        <div className="flex items-center gap-3">
          <Icon className="size-5 text-loss" />
          <span className="font-semibold text-sm">Risk Specialist</span>
        </div>
        <p className="text-xs text-text-subtle mt-4">Risk evaluation not available.</p>
      </Card>
    );
  }

  const components = (signal.meta?.components as Record<string, number>) || {};

  return (
    <Card
      className={cn(
        "p-5 flex flex-col justify-between border-l-[3.5px] border-l-loss",
        className
      )}
    >
      <div>
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-full bg-loss/15 flex items-center justify-center shrink-0">
              <Icon className="size-4 text-loss" />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-foreground">Risk Specialist</h4>
              <span className="text-[11px] text-text-subtle">
                Confidence {fmtPct(signal.confidence, 0)}
              </span>
            </div>
          </div>

          <div className="text-right">
            <span className="font-mono text-base font-bold text-loss num">
              {signal.score.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Risk Score Bar */}
        <div className="mb-4">
          <ScoreBar score={signal.score} kind="risk" showValue={false} />
        </div>

        {/* Risk Components Breakdown */}
        {Object.keys(components).length > 0 && (
          <div className="space-y-2 mb-4 bg-secondary/30 p-2.5 rounded-lg border border-border/60">
            {Object.entries(components).map(([k, val]) => (
              <div key={k} className="flex items-center justify-between text-[11px]">
                <span className="text-text-subtle capitalize">{k.replace("_", " ")}</span>
                <span className="font-mono font-medium">{val?.toFixed?.(2) ?? val}</span>
              </div>
            ))}
          </div>
        )}

        {/* Narrative */}
        <p className="text-xs text-muted-foreground leading-relaxed mb-4">
          {signal.narrative || "Risk metrics within standard thresholds."}
        </p>
      </div>

      {/* Risks List */}
      {signal.risks && signal.risks.length > 0 && (
        <div className="pt-3 border-t border-border/60">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-loss block mb-1.5">
            Specific Risk Factors
          </span>
          <ul className="space-y-1">
            {signal.risks.map((risk, idx) => (
              <li key={idx} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <AlertTriangle className="size-3 text-loss shrink-0 mt-0.5" />
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
