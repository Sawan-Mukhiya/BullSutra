"use client";

import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { useTheme } from "next-themes";
import { Card } from "@/components/ui/card";
import { fmtDate, fmtPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface DrawdownChartProps {
  series: Array<{ date: string; full?: number; bh_equal_weight?: number; [k: string]: any }>;
  className?: string;
}

export function DrawdownChart({ series = [], className }: DrawdownChartProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(20, 20, 30, 0.06)";
  const textColor = isDark ? "#A9AFBC" : "#4A5160";

  return (
    <Card className={cn("p-5 space-y-4", className)}>
      <div className="flex items-center justify-between pb-3 border-b border-border/60">
        <span className="text-xs font-semibold uppercase tracking-wider text-text-subtle">
          Rolling Drawdown Profile
        </span>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="flex items-center gap-1.5 text-loss">
            <span className="size-2 rounded-full bg-loss" />
            <span>BullSutra Full</span>
          </span>
          <span className="flex items-center gap-1.5 text-text-subtle">
            <span className="size-2 rounded-full bg-slate-500" />
            <span>Equal-Weight B&H</span>
          </span>
        </div>
      </div>

      <div className="h-[220px] w-full pt-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="drawdownFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#F0506E" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#F0506E" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
            <XAxis
              dataKey="date"
              stroke={textColor}
              fontSize={11}
              fontFamily="var(--font-mono)"
              tickLine={false}
              tickFormatter={(d) => fmtDate(d)}
            />
            <YAxis
              domain={["auto", 0]}
              stroke={textColor}
              fontSize={11}
              fontFamily="var(--font-mono)"
              tickLine={false}
              tickFormatter={(v) => fmtPct(v, 0)}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload) return null;
                return (
                  <div className="glass p-3 rounded-lg text-xs space-y-1 shadow-xl border border-border">
                    <span className="font-mono text-text-subtle block border-b border-border/50 pb-1">
                      {fmtDate(label)}
                    </span>
                    {payload.map((entry) => (
                      <div key={entry.name} className="flex items-center justify-between gap-4 font-mono">
                        <span style={{ color: entry.color }}>
                          {entry.name === "full" ? "BullSutra" : "Buy & Hold"}:
                        </span>
                        <span className="font-bold text-foreground">
                          {fmtPct(Number(entry.value), 2)}
                        </span>
                      </div>
                    ))}
                  </div>
                );
              }}
            />
            <Area
              type="monotone"
              dataKey="full"
              name="full"
              stroke="#F0506E"
              strokeWidth={1.5}
              fill="url(#drawdownFill)"
            />
            <Area
              type="monotone"
              dataKey="bh_equal_weight"
              name="bh_equal_weight"
              stroke="#64748B"
              strokeWidth={1}
              fill="transparent"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
