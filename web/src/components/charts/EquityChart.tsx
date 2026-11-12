"use client";

import React, { useState, useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { useTheme } from "next-themes";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { STRATEGY_LABELS, STRATEGY_COLORS } from "@/lib/constants";
import { fmtNpr, fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface EquityChartProps {
  series: Array<{ date: string; [strategy: string]: any }>;
  availableStrategies?: string[];
  className?: string;
}

export function EquityChart({
  series = [],
  availableStrategies = ["full", "bh_equal_weight", "bh_nepse_index", "consensus_weighted"],
  className,
}: EquityChartProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([
    "full",
    "bh_equal_weight",
    "bh_nepse_index",
  ]);
  const [logScale, setLogScale] = useState(false);

  const toggleStrategy = (strat: string) => {
    setSelectedStrategies((prev) =>
      prev.includes(strat) ? prev.filter((s) => s !== strat) : [...prev, strat]
    );
  };

  const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(20, 20, 30, 0.06)";
  const textColor = isDark ? "#A9AFBC" : "#4A5160";

  return (
    <Card className={cn("p-5 space-y-4", className)}>
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border/60">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-text-subtle">
            Strategies:
          </span>
          {availableStrategies.map((strat) => {
            const isChecked = selectedStrategies.includes(strat);
            const color = STRATEGY_COLORS[strat] || "#A9AFBC";

            return (
              <button
                key={strat}
                onClick={() => toggleStrategy(strat)}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium border transition-all",
                  isChecked
                    ? "bg-card border-border shadow-sm text-foreground"
                    : "opacity-40 border-transparent text-text-subtle hover:opacity-75"
                )}
              >
                <span
                  className="size-2 rounded-full shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span>{STRATEGY_LABELS[strat] || strat}</span>
              </button>
            );
          })}
        </div>

        <label className="flex items-center gap-2 text-xs font-medium cursor-pointer text-text-subtle">
          <span>Logarithmic Scale</span>
          <Switch checked={logScale} onCheckedChange={setLogScale} />
        </label>
      </div>

      {/* Chart Canvas */}
      <div className="h-[380px] w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
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
              scale={logScale ? "log" : "auto"}
              domain={["auto", "auto"]}
              stroke={textColor}
              fontSize={11}
              fontFamily="var(--font-mono)"
              tickLine={false}
              tickFormatter={(v) => fmtNpr(v, true)}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload) return null;
                return (
                  <div className="glass p-3 rounded-lg text-xs space-y-1.5 shadow-xl border border-border">
                    <span className="font-mono text-text-subtle block border-b border-border/50 pb-1">
                      {fmtDate(label)}
                    </span>
                    {payload
                      .slice()
                      .sort((a, b) => Number(b.value) - Number(a.value))
                      .map((entry) => (
                        <div key={entry.name} className="flex items-center justify-between gap-4 font-mono">
                          <span className="flex items-center gap-1.5" style={{ color: entry.color }}>
                            <span className="size-1.5 rounded-full" style={{ backgroundColor: entry.color }} />
                            <span>{STRATEGY_LABELS[entry.name as string] || entry.name}</span>
                          </span>
                          <span className="font-semibold text-foreground">
                            {fmtNpr(Number(entry.value))}
                          </span>
                        </div>
                      ))}
                  </div>
                );
              }}
            />
            {selectedStrategies.map((strat) => {
              const color = STRATEGY_COLORS[strat] || "#A9AFBC";
              const isFull = strat === "full";

              return (
                <Line
                  key={strat}
                  type="monotone"
                  dataKey={strat}
                  name={strat}
                  stroke={color}
                  strokeWidth={isFull ? 2.5 : 1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
