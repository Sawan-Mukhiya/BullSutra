"use client";

import React from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { useTheme } from "next-themes";
import { Card } from "@/components/ui/card";
import { fmtPct, fmtNum } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface ReliabilityBin {
  bin_center: number;
  predicted: number;
  observed: number;
  count: number;
}

export interface ReliabilityChartProps {
  binsRaw?: ReliabilityBin[];
  binsCalibrated?: ReliabilityBin[];
  brierRaw?: number;
  brierCal?: number;
  sampleCount?: number;
  className?: string;
}

export function ReliabilityChart({
  binsRaw = [],
  binsCalibrated = [],
  brierRaw,
  brierCal,
  sampleCount,
  className,
}: ReliabilityChartProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  const chartData = (binsCalibrated.length > 0 ? binsCalibrated : binsRaw).map((b, idx) => ({
    predicted: b.predicted ?? b.bin_center,
    observedCalibrated: b.observed,
    observedRaw: binsRaw[idx]?.observed ?? b.observed,
    count: b.count,
  }));

  const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(20, 20, 30, 0.06)";
  const textColor = isDark ? "#A9AFBC" : "#4A5160";

  return (
    <Card className={cn("p-5 space-y-4", className)}>
      <div className="flex flex-wrap items-center justify-between gap-4 pb-3 border-b border-border/60">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-subtle">
            Empirical Reliability & Calibration
          </h4>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Non-parametric Isotonic Regression mapped against 10-day forward return win rate.
          </p>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          {brierCal !== undefined && (
            <span className="px-2 py-0.5 rounded bg-accent text-accent-foreground">
              Brier Score: {fmtNum(brierCal, 4)}
            </span>
          )}
          {sampleCount !== undefined && (
            <span className="text-text-subtle">N = {sampleCount}</span>
          )}
        </div>
      </div>

      <div className="h-[280px] w-full pt-1">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis
              dataKey="predicted"
              type="number"
              domain={[0, 1]}
              stroke={textColor}
              fontSize={11}
              fontFamily="var(--font-mono)"
              tickFormatter={(v) => fmtPct(v, 0)}
              label={{ value: "Predicted Probability", position: "insideBottom", offset: -5, fill: textColor, fontSize: 10 }}
            />
            <YAxis
              domain={[0, 1]}
              stroke={textColor}
              fontSize={11}
              fontFamily="var(--font-mono)"
              tickFormatter={(v) => fmtPct(v, 0)}
              label={{ value: "Observed Win Rate", angle: -90, position: "insideLeft", fill: textColor, fontSize: 10 }}
            />
            {/* 45-degree diagonal: perfect calibration */}
            <ReferenceLine
              segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
              stroke="#64748B"
              strokeDasharray="4 4"
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || payload.length === 0) return null;
                const d = payload[0].payload;
                return (
                  <div className="glass p-2.5 rounded-lg text-xs font-mono space-y-1 border border-border">
                    <p className="text-text-subtle">Predicted: {fmtPct(d.predicted, 1)}</p>
                    <p className="text-gold-500 font-semibold">Observed: {fmtPct(d.observedCalibrated, 1)}</p>
                    <p className="text-[11px] text-muted-foreground">Sample Size: {d.count}</p>
                  </div>
                );
              }}
            />
            <Line
              type="monotone"
              dataKey="observedCalibrated"
              stroke="#D4AF37"
              strokeWidth={2}
              dot={{ r: 4, fill: "#D4AF37" }}
              name="Calibrated"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
