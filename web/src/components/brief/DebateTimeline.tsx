import React from "react";
import { CheckCircle2, Scale, ArrowRight, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fmtScore, fmtPct } from "@/lib/format";
import type { Debate } from "@/types";
import { cn } from "@/lib/utils";

export interface DebateTimelineProps {
  debate?: Debate | null;
  conflicted?: boolean;
  className?: string;
}

export function DebateTimeline({
  debate,
  conflicted = false,
  className,
}: DebateTimelineProps) {
  if (!debate) {
    return (
      <Card className={cn("p-6", className)}>
        <p className="text-sm text-text-subtle">No debate protocol record found.</p>
      </Card>
    );
  }

  if (!debate.triggered) {
    return (
      <Card className={cn("p-6 border border-gain/30 bg-gain/5", className)}>
        <div className="flex items-center gap-3">
          <CheckCircle2 className="size-5 text-gain shrink-0" />
          <div>
            <h4 className="font-semibold text-sm text-foreground">
              Consensus Formed Without Debate
            </h4>
            <p className="text-xs text-muted-foreground mt-0.5">
              Specialist agents independently agreed with low initial disagreement (
              {debate.initial_disagreement?.toFixed(2) ?? "0.00"}). Cross-examination was not required.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn("p-6 space-y-6", className)}>
      <div className="flex items-center justify-between border-b border-border/80 pb-4">
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-full bg-accent flex items-center justify-center">
            <Scale className="size-4 text-gold-500" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-base text-foreground">
              Specialist Debate & Cross-Examination
            </h3>
            <p className="text-xs text-text-subtle">
              Initial disagreement: {debate.initial_disagreement?.toFixed(2)} → Final:{" "}
              {debate.final_disagreement?.toFixed(2)}
            </p>
          </div>
        </div>

        {conflicted && (
          <Badge variant="warning" className="gap-1">
            <AlertCircle className="size-3" />
            Conflicted Signal
          </Badge>
        )}
      </div>

      {/* Summary Narrative Quote */}
      {debate.summary && (
        <blockquote className="border-l-[3px] border-gold-500 bg-accent/40 pl-4 py-2.5 rounded-r-md text-xs italic text-foreground leading-relaxed">
          &ldquo;{debate.summary}&rdquo;
        </blockquote>
      )}

      {/* Cross-Check Rules */}
      {debate.cross_checks && debate.cross_checks.length > 0 && (
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-text-subtle block mb-2">
            Applied Risk Cross-Checks
          </span>
          <div className="space-y-1.5">
            {debate.cross_checks.map((cc, idx) => (
              <div
                key={idx}
                className="text-xs p-2 rounded bg-secondary/50 border border-border/60 text-muted-foreground flex items-start gap-2"
              >
                <span className="font-mono text-gold-500 font-semibold">{cc.rule}:</span>
                <span>{cc.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debate Rounds */}
      {debate.rounds && debate.rounds.length > 0 && (
        <div className="space-y-4">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-text-subtle block">
            Rounds Progression
          </span>

          <div className="space-y-3">
            {debate.rounds.map((round) => (
              <div
                key={round.round}
                className="p-3.5 rounded-lg border border-border/80 bg-secondary/20 space-y-2.5"
              >
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-foreground">Round {round.round}</span>
                  <span className="text-text-subtle text-[11px]">
                    Disagreement: {round.disagreement_before.toFixed(2)} →{" "}
                    {round.disagreement_after.toFixed(2)}
                  </span>
                </div>

                {/* Per Agent Score adjustments */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {round.revisions?.map((adj) => (
                    <div
                      key={adj.agent}
                      className="flex items-center justify-between p-2 rounded bg-card/60 border border-border/40"
                    >
                      <span className="capitalize font-medium text-foreground">{adj.agent}</span>
                      <div className="flex items-center gap-1.5 font-mono text-[11px]">
                        <span>{fmtScore(adj.score_before)}</span>
                        <ArrowRight className="size-3 text-text-subtle" />
                        <span className="font-bold text-foreground">
                          {fmtScore(adj.score_after)}
                        </span>
                        <span className="text-text-subtle ml-1">
                          ({fmtPct(adj.confidence_after, 0)})
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
