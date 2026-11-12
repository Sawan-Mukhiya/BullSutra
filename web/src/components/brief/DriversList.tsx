import React from "react";
import { ExternalLink, FileText, Database, Newspaper } from "lucide-react";
import { AGENTS, AgentKey } from "@/lib/constants";
import { fmtDate } from "@/lib/format";
import type { Evidence } from "@/types";
import { cn } from "@/lib/utils";

export function DriversList({
  drivers = [],
  className,
}: {
  drivers?: Evidence[];
  className?: string;
}) {
  if (!drivers || drivers.length === 0) {
    return <p className="text-xs text-text-subtle">No key drivers recorded.</p>;
  }

  return (
    <ol className={cn("space-y-2.5", className)}>
      {drivers.slice(0, 5).map((driver, idx) => {
        const agentMeta = AGENTS[driver.kind as AgentKey];
        const dotColor = agentMeta ? agentMeta.color : "#D4AF37";

        return (
          <li
            key={idx}
            className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-secondary/30 border border-border/50 hover:bg-secondary/50 transition-colors"
          >
            <div className="flex items-center gap-2.5 min-w-0 pr-2">
              <span
                className="size-2 rounded-full shrink-0"
                style={{ backgroundColor: dotColor }}
              />
              <span className="font-semibold text-text-subtle w-4 shrink-0">{idx + 1}.</span>
              <span className="text-foreground truncate" title={driver.note}>
                {driver.note}
              </span>
            </div>
            {driver.value !== undefined && (
              <span className="font-mono font-semibold text-foreground shrink-0 ml-2">
                {String(driver.value)}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function SourcesList({
  sources = [],
  className,
}: {
  sources?: any[];
  className?: string;
}) {
  if (!sources || sources.length === 0) {
    return <p className="text-xs text-text-subtle">No explicit source citations.</p>;
  }

  return (
    <div className={cn("space-y-3", className)}>
      {sources.map((src, idx) => {
        const kind = src.type || src.kind;
        const title = src.label || src.title;
        const date = src.published_at || src.reported_at || src.date;

        const Icon =
          kind === "news"
            ? Newspaper
            : kind === "fundamental" || kind === "fundamentals"
            ? FileText
            : Database;

        return (
          <div
            key={idx}
            className="flex items-center justify-between p-2.5 rounded-lg border border-border/60 bg-secondary/20 text-xs"
          >
            <div className="flex items-center gap-2.5 min-w-0 pr-2">
              <Icon className="size-4 shrink-0 text-gold-500" />
              <div className="truncate">
                {src.url ? (
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-foreground hover:text-gold-300 hover:underline inline-flex items-center gap-1 truncate"
                  >
                    <span>{title}</span>
                    <ExternalLink className="size-3 shrink-0" />
                  </a>
                ) : (
                  <span className="font-medium text-foreground">{title}</span>
                )}
                <span className="text-[11px] text-text-subtle block">
                  {src.source || "NEPSE Primary Record"}
                </span>
              </div>
            </div>

            {date && (
              <span className="text-[11px] text-text-subtle shrink-0 ml-2 font-mono">
                {fmtDate(date)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
