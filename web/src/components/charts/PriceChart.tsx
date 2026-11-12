"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, LineData, HistogramData } from "lightweight-charts";
import { useTheme } from "next-themes";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { useOhlcv, useIndicators } from "@/hooks/useSecurity";
import { fmtNpr, fmtDate, fmtVolume, fmtSignedPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface PriceChartProps {
  symbol: string;
  asOf?: string;
  signalLabel?: string;
  className?: string;
}

const RANGES = ["3M", "6M", "1Y", "3Y", "ALL"] as const;
type Range = (typeof RANGES)[number];

export function PriceChart({
  symbol,
  asOf,
  signalLabel,
  className,
}: PriceChartProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);

  const [range, setRange] = useState<Range>("1Y");
  const [adjusted, setAdjusted] = useState(true);
  const [showSma20, setShowSma20] = useState(true);
  const [showSma50, setShowSma50] = useState(true);
  const [showSma200, setShowSma200] = useState(false);
  const [lowerPane, setLowerPane] = useState<"volume" | "rsi">("volume");

  // Hover legend state
  const [legend, setLegend] = useState<{
    time?: string | null;
    open?: number | null;
    high?: number | null;
    low?: number | null;
    close?: number | null;
    volume?: number | null;
    changePct?: number | null;
  }>({});

  // Compute start date based on range
  const startDate = useMemo(() => {
    if (range === "ALL") return undefined;
    const now = new Date();
    const months = range === "3M" ? 3 : range === "6M" ? 6 : range === "1Y" ? 12 : 36;
    now.setMonth(now.getMonth() - months);
    return now.toISOString().split("T")[0];
  }, [range]);

  const { data: candles, isLoading, isError, refetch } = useOhlcv(
    symbol,
    startDate,
    undefined,
    adjusted
  );

  const neededIndicators = useMemo(() => {
    const list: string[] = [];
    if (showSma20) list.push("sma20");
    if (showSma50) list.push("sma50");
    if (showSma200) list.push("sma200");
    if (lowerPane === "rsi") list.push("rsi");
    return list;
  }, [showSma20, showSma50, showSma200, lowerPane]);

  const { data: indicators } = useIndicators(symbol, neededIndicators, startDate);

  useEffect(() => {
    if (!chartContainerRef.current || !candles || candles.length === 0) return;

    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
      chartInstanceRef.current = null;
    }

    const container = chartContainerRef.current;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: 420,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: isDark ? "#A9AFBC" : "#4A5160",
        fontFamily: "var(--font-mono)",
      },
      grid: {
        vertLines: { color: isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(20, 20, 30, 0.05)" },
        horzLines: { color: isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(20, 20, 30, 0.05)" },
      },
      crosshair: {
        vertLine: { color: isDark ? "rgba(212, 175, 55, 0.4)" : "rgba(184, 147, 43, 0.4)", width: 1, style: 2 },
        horzLine: { color: isDark ? "rgba(212, 175, 55, 0.4)" : "rgba(184, 147, 43, 0.4)", width: 1, style: 2 },
      },
      timeScale: {
        borderColor: isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(20, 20, 30, 0.09)",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartInstanceRef.current = chart;

    // 1. Candlestick Series
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#22C58B",
      downColor: "#F0506E",
      borderUpColor: "#22C58B",
      borderDownColor: "#F0506E",
      wickUpColor: "#22C58B",
      wickDownColor: "#F0506E",
    });

    const candleData: CandlestickData[] = candles.map((c) => {
      const open = c.open ?? c.close;
      return {
        time: c.date as any,
        open,
        high: c.high ?? Math.max(open, c.close),
        low: c.low ?? Math.min(open, c.close),
        close: c.close,
      };
    });
    candleSeries.setData(candleData);

    // 2. Volume Series (histogram at bottom of main pane)
    if (lowerPane === "volume") {
      const volumeSeries = chart.addHistogramSeries({
        color: "#64748B",
        priceFormat: { type: "volume" },
        priceScaleId: "", // overlay
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      const volumeData: HistogramData[] = candles.map((c) => ({
        time: c.date as any,
        value: c.volume,
        color: c.close >= (c.open ?? c.close) ? "rgba(34, 197, 139, 0.35)" : "rgba(240, 80, 110, 0.35)",
      }));
      volumeSeries.setData(volumeData);
    }

    // 3. Moving Average Overlays
    if (showSma20 && indicators?.sma20) {
      const sma20Series = chart.addLineSeries({
        color: "#D4AF37",
        lineWidth: 1,
        title: "SMA20",
      });
      sma20Series.setData(indicators.sma20.map((d) => ({ time: d.date as any, value: d.value })));
    }

    if (showSma50 && indicators?.sma50) {
      const sma50Series = chart.addLineSeries({
        color: "#5B8CFF",
        lineWidth: 1,
        title: "SMA50",
      });
      sma50Series.setData(indicators.sma50.map((d) => ({ time: d.date as any, value: d.value })));
    }

    if (showSma200 && indicators?.sma200) {
      const sma200Series = chart.addLineSeries({
        color: "#9B7BFF",
        lineWidth: 1,
        title: "SMA200",
      });
      sma200Series.setData(indicators.sma200.map((d) => ({ time: d.date as any, value: d.value })));
    }

    // 4. Marker for As-Of signal
    if (asOf && signalLabel) {
      const isBuy = signalLabel.toUpperCase().includes("BUY");
      const isSell = signalLabel.toUpperCase().includes("SELL");

      candleSeries.setMarkers([
        {
          time: asOf as any,
          position: isBuy ? "belowBar" : isSell ? "aboveBar" : "inBar",
          color: isBuy ? "#22C58B" : isSell ? "#F0506E" : "#D4AF37",
          shape: isBuy ? "arrowUp" : isSell ? "arrowDown" : "circle",
          text: `Verdict: ${signalLabel}`,
        },
      ]);
    }

    // Crosshair move listener for live legend
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData) {
        // Fallback to last candle
        const last = candles[candles.length - 1];
        if (last) {
          const chg = last.open ? ((last.close - last.open) / last.open) * 100 : 0;
          setLegend({
            time: last.date,
            open: last.open,
            high: last.high,
            low: last.low,
            close: last.close,
            volume: last.volume,
            changePct: chg,
          });
        }
        return;
      }

      const cData = param.seriesData.get(candleSeries) as any;
      if (cData) {
        const chg = cData.open ? ((cData.close - cData.open) / cData.open) * 100 : 0;
        setLegend({
          time: String(param.time),
          open: cData.open,
          high: cData.high,
          low: cData.low,
          close: cData.close,
          changePct: chg,
        });
      }
    });

    // Default to last candle initially
    const last = candles[candles.length - 1];
    if (last) {
      setLegend({
        time: last.date,
        open: last.open,
        high: last.high,
        low: last.low,
        close: last.close,
        volume: last.volume,
        changePct: last.open ? ((last.close - last.open) / last.open) * 100 : 0,
      });
    }

    // ResizeObserver
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0] && chartInstanceRef.current) {
        chartInstanceRef.current.applyOptions({
          width: entries[0].contentRect.width,
        });
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartInstanceRef.current = null;
    };
  }, [candles, indicators, isDark, lowerPane, showSma20, showSma50, showSma200, asOf, signalLabel]);

  return (
    <Card className={cn("p-5 flex flex-col justify-between overflow-hidden relative", className)}>
      {/* Chart Toolbar Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border/60">
        {/* Timeframe Range Selector */}
        <div className="flex items-center gap-1 p-1 rounded-lg bg-secondary">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={cn(
                "px-3 py-1 text-xs font-semibold rounded-md transition-all",
                range === r
                  ? "bg-card text-foreground border border-gold-500/40 shadow-sm"
                  : "text-text-subtle hover:text-foreground"
              )}
            >
              {r}
            </button>
          ))}
        </div>

        {/* Indicator Toggles */}
        <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-xs font-medium">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <span className="text-text-subtle">Adj</span>
            <Switch checked={adjusted} onCheckedChange={setAdjusted} />
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer">
            <span className="text-[#D4AF37]">SMA20</span>
            <input
              type="checkbox"
              checked={showSma20}
              onChange={(e) => setShowSma20(e.target.checked)}
              className="accent-[#D4AF37] size-3.5 rounded"
            />
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer">
            <span className="text-[#5B8CFF]">SMA50</span>
            <input
              type="checkbox"
              checked={showSma50}
              onChange={(e) => setShowSma50(e.target.checked)}
              className="accent-[#5B8CFF] size-3.5 rounded"
            />
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer">
            <span className="text-[#9B7BFF]">SMA200</span>
            <input
              type="checkbox"
              checked={showSma200}
              onChange={(e) => setShowSma200(e.target.checked)}
              className="accent-[#9B7BFF] size-3.5 rounded"
            />
          </label>
        </div>
      </div>

      {/* Crosshair Legend Banner */}
      <div className="flex flex-wrap items-center gap-4 py-2.5 text-xs font-mono border-b border-border/40 text-text-subtle">
        <span>Date: <strong className="text-foreground">{legend.time ? fmtDate(legend.time) : "—"}</strong></span>
        <span>O: <strong className="text-foreground">{fmtNpr(legend.open)}</strong></span>
        <span>H: <strong className="text-foreground">{fmtNpr(legend.high)}</strong></span>
        <span>L: <strong className="text-foreground">{fmtNpr(legend.low)}</strong></span>
        <span>C: <strong className="text-foreground">{fmtNpr(legend.close)}</strong></span>
        {legend.volume && (
          <span>Vol: <strong className="text-foreground">{fmtVolume(legend.volume)}</strong></span>
        )}
        {legend.changePct !== undefined && legend.changePct !== null && (
          <span>
            Chg:{" "}
            <strong className={legend.changePct >= 0 ? "text-gain" : "text-loss"}>
              {fmtSignedPct(legend.changePct)}
            </strong>
          </span>
        )}
      </div>

      {/* Main Canvas Area */}
      <div className="relative min-h-[420px] w-full pt-2">
        {isLoading && (
          <div className="absolute inset-0 flex flex-col gap-2 items-center justify-center bg-card/60 z-20">
            <Skeleton className="w-full h-80 rounded-lg" />
            <span className="text-xs text-text-subtle font-mono">Loading OHLCV candles...</span>
          </div>
        )}

        {isError && (
          <div className="absolute inset-0 flex items-center justify-center z-20">
            <ErrorState
              title="Price Data Unavailable"
              description="Could not load price history for this symbol and timeframe."
              onRetry={refetch}
            />
          </div>
        )}

        <div ref={chartContainerRef} className="w-full h-[420px]" />
      </div>
    </Card>
  );
}
