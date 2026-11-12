"use client";

import React, { use, useState } from "react";
import Link from "next/link";
import {
  FlaskConical,
  Download,
  Calendar,
  AlertTriangle,
  Info,
  ChevronRight,
  TrendingUp,
  Percent,
  Layers,
  ArrowUpDown,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { DisclaimerBar } from "@/components/common/DisclaimerBar";
import { StatCard } from "@/components/common/StatCard";
import { DeltaChip } from "@/components/common/DeltaChip";
import { EquityChart } from "@/components/charts/EquityChart";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { ReliabilityChart } from "@/components/charts/ReliabilityChart";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import {
  useBacktest,
  useBacktestEquity,
  useBacktestTrades,
  useBacktestFolds,
} from "@/hooks/useBacktest";
import { STRATEGY_LABELS, STRATEGY_COLORS } from "@/lib/constants";
import { fmtDate, fmtPct, fmtNum, fmtNpr } from "@/lib/format";

export default function BacktestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [selectedTradeStrategy, setSelectedTradeStrategy] = useState("full");
  const [tradesPage, setTradesPage] = useState(0);

  const { data: backtest, isLoading, isError, refetch } = useBacktest(id);
  const { data: equityData = [] } = useBacktestEquity(id);
  const { data: tradesData } = useBacktestTrades(id, selectedTradeStrategy, tradesPage * 50, 50);
  const { data: foldsData = [] } = useBacktestFolds(id);

  if (isLoading) {
    return (
      <AppShell>
        <div className="space-y-6">
          <Skeleton className="h-8 w-64" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-32 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-96 rounded-xl" />
        </div>
      </AppShell>
    );
  }

  if (isError || !backtest) {
    return (
      <AppShell>
        <ErrorState
          title="Backtest Not Found"
          description={`Could not retrieve backtest record ${id}.`}
          onRetry={refetch}
        />
      </AppShell>
    );
  }

  const stratFull = backtest.strategies?.find((s) => s.strategy_key === "full");
  const stratBh = backtest.strategies?.find((s) => s.strategy_key === "bh_equal_weight");
  const stratFullMetrics = (stratFull?.metrics || {}) as Record<string, any>;
  const stratBhMetrics = (stratBh?.metrics || {}) as Record<string, any>;
  const bootstrap = (stratFull?.bootstrap || stratFullMetrics.bootstrap) as
    | { estimate: number; ci_low: number; ci_high: number; p_value: number }
    | undefined;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-text-subtle font-medium">
          <Link href="/backtests" className="hover:text-foreground transition-colors">
            Backtests
          </Link>
          <ChevronRight className="size-3.5" />
          <span className="font-mono text-foreground font-semibold">{backtest.name || id}</span>
        </div>

        <DisclaimerBar />

        {/* Backtest Header Card */}
        <div className="glass-featured p-6 lg:p-8 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                {backtest.name}
              </h1>
              <Badge variant="gold" className="text-xs uppercase">
                {backtest.status}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground font-mono">
              Created {fmtDate(backtest.created_at)} • Rolling 40-Stock Universe Folds
            </p>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={`/api/proxy/api/v1/exports/backtest/${id}/trades.csv`}
              download
              className="inline-flex items-center gap-2 h-10 px-4 rounded-lg border border-border bg-secondary text-xs font-semibold text-foreground hover:bg-secondary/80 transition-colors"
            >
              <Download className="size-4 text-gold-500" />
              <span>Export Trades CSV</span>
            </a>
          </div>
        </div>

        {/* 7 Interactive Tabs */}
        <Tabs defaultValue="overview" className="w-full space-y-6">
          <TabsList variant="underline" className="w-full overflow-x-auto no-scrollbar">
            <TabsTrigger variant="underline" value="overview">1. Overview</TabsTrigger>
            <TabsTrigger variant="underline" value="ablation">2. Strategy Ablation</TabsTrigger>
            <TabsTrigger variant="underline" value="trades">3. Executed Trades</TabsTrigger>
            <TabsTrigger variant="underline" value="folds">4. Walk-Forward Folds</TabsTrigger>
            <TabsTrigger variant="underline" value="persymbol">5. By Stock</TabsTrigger>
            <TabsTrigger variant="underline" value="calibration">6. Calibration</TabsTrigger>
            <TabsTrigger variant="underline" value="limits">7. Method & Limitations</TabsTrigger>
          </TabsList>

          {/* TAB 1: OVERVIEW */}
          <TabsContent value="overview" className="space-y-6 mt-0">
            {/* 4 MetricCards comparing Full vs B&H */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
              <StatCard
                label="CAGR (Annualized)"
                value={fmtPct(stratFullMetrics.cagr, 1)}
                delta={
                  typeof stratFullMetrics.cagr === "number" && typeof stratBhMetrics.cagr === "number"
                    ? stratFullMetrics.cagr - stratBhMetrics.cagr
                    : null
                }
                footnote={`Buy & Hold: ${fmtPct(stratBhMetrics.cagr, 1)}`}
              />

              <StatCard
                label="Sharpe Ratio"
                value={fmtNum(stratFullMetrics.sharpe, 2)}
                delta={
                  typeof stratFullMetrics.sharpe === "number" && typeof stratBhMetrics.sharpe === "number"
                    ? stratFullMetrics.sharpe - stratBhMetrics.sharpe
                    : null
                }
                footnote={`Buy & Hold: ${fmtNum(stratBhMetrics.sharpe, 2)}`}
              />

              <StatCard
                label="Max Drawdown"
                value={fmtPct(stratFullMetrics.max_drawdown, 1)}
                footnote={`Buy & Hold: ${fmtPct(stratBhMetrics.max_drawdown, 1)}`}
              />

              <StatCard
                label="Total Return"
                value={fmtPct(stratFullMetrics.total_return, 1)}
                footnote={`Net of all broker & SEBON fees`}
              />
            </div>

            {/* Statistical Significance Statement Card */}
            {bootstrap && (
              <Card className="p-5 border-l-4 border-l-gold-500 bg-accent/20">
                <div className="flex items-start gap-3">
                  <Info className="size-5 text-gold-500 shrink-0 mt-0.5" />
                  <div className="space-y-1 text-xs">
                    <strong className="text-foreground text-sm font-semibold font-display">
                      Paired Block Bootstrap Hypothesis Test (10-Day Blocks)
                    </strong>
                    <p className="text-muted-foreground leading-relaxed">
                      Sharpe difference vs Buy & Hold:{" "}
                      <span className="font-mono font-bold text-foreground">
                        {bootstrap.estimate > 0 ? `+${bootstrap.estimate.toFixed(2)}` : bootstrap.estimate.toFixed(2)}
                      </span>{" "}
                      (95% Confidence Interval:{" "}
                      <span className="font-mono font-bold text-foreground">
                        {bootstrap.ci_low.toFixed(2)} to {bootstrap.ci_high.toFixed(2)}
                      </span>
                      ), p-value = <span className="font-mono font-bold text-foreground">{bootstrap.p_value.toFixed(4)}</span>.
                    </p>
                    <p className="text-gold-500 font-medium">
                      {bootstrap.ci_low > 0
                        ? "Statistically significant outperformance at the 95% level."
                        : "Difference is within standard empirical noise bounds."}
                    </p>
                  </div>
                </div>
              </Card>
            )}

            {/* Equity Curve Line Chart */}
            <EquityChart series={equityData} />

            {/* Drawdown Profile Area Chart */}
            <DrawdownChart series={equityData} />
          </TabsContent>

          {/* TAB 2: ABLATION TABLE */}
          <TabsContent value="ablation" className="space-y-4 mt-0">
            <Card className="p-0 overflow-hidden">
              <Table>
                <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
                  <TableRow>
                    <TableHead className="pl-6">Strategy</TableHead>
                    <TableHead className="text-right">CAGR</TableHead>
                    <TableHead className="text-right">Total Return</TableHead>
                    <TableHead className="text-right">Sharpe</TableHead>
                    <TableHead className="text-right">Sortino</TableHead>
                    <TableHead className="text-right">Max DD</TableHead>
                    <TableHead className="text-right">Calmar</TableHead>
                    <TableHead className="text-right">Trades</TableHead>
                    <TableHead className="text-right pr-6">Win Rate</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {backtest.strategies?.map((strat) => {
                    const m = (strat.metrics || {}) as Record<string, any>;
                    const isFull = strat.strategy_key === "full";
                    const isBenchmark = strat.strategy_key.startsWith("bh_");

                    return (
                      <TableRow
                        key={strat.strategy_key}
                        className={isFull ? "bg-accent/30 font-semibold" : "hover:bg-white/[0.03]"}
                      >
                        <TableCell className="pl-6 font-mono text-xs">
                          <div className="flex items-center gap-2">
                            <span
                              className="size-2 rounded-full shrink-0"
                              style={{ backgroundColor: STRATEGY_COLORS[strat.strategy_key] || "#64748B" }}
                            />
                            <span>{STRATEGY_LABELS[strat.strategy_key] || strat.label || strat.strategy_key}</span>
                            {isFull && <Badge variant="gold" className="text-[9px] h-4">Top</Badge>}
                            {isBenchmark && <Badge variant="outline" className="text-[9px] h-4">B&H</Badge>}
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-gain">{fmtPct(m.cagr, 1)}</TableCell>
                        <TableCell className="text-right font-mono text-xs">{fmtPct(m.total_return, 1)}</TableCell>
                        <TableCell className="text-right font-mono text-xs font-bold text-gold-500">{fmtNum(m.sharpe, 2)}</TableCell>
                        <TableCell className="text-right font-mono text-xs">{fmtNum(m.sortino, 2)}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-loss">{fmtPct(m.max_drawdown, 1)}</TableCell>
                        <TableCell className="text-right font-mono text-xs">{fmtNum(m.calmar, 2)}</TableCell>
                        <TableCell className="text-right font-mono text-xs">{m.trade_count !== undefined ? String(m.trade_count) : "—"}</TableCell>
                        <TableCell className="text-right pr-6 font-mono text-xs">{fmtPct(m.win_rate, 1)}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Card>
          </TabsContent>

          {/* TAB 3: EXECUTED TRADES */}
          <TabsContent value="trades" className="space-y-4 mt-0">
            <Card className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-text-subtle uppercase">Strategy:</span>
                <select
                  value={selectedTradeStrategy}
                  onChange={(e) => {
                    setSelectedTradeStrategy(e.target.value);
                    setTradesPage(0);
                  }}
                  className="h-9 px-3 rounded-md bg-secondary border border-border text-xs font-mono font-medium outline-none"
                >
                  {backtest.strategies?.map((s) => (
                    <option key={s.strategy_key} value={s.strategy_key}>
                      {STRATEGY_LABELS[s.strategy_key] || s.label || s.strategy_key}
                    </option>
                  ))}
                </select>
              </div>

              <span className="text-xs font-mono text-text-subtle">
                Total trades: {tradesData?.total ?? 0}
              </span>
            </Card>

            <Card className="p-0 overflow-hidden">
              <Table>
                <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
                  <TableRow>
                    <TableHead className="pl-6">Symbol</TableHead>
                    <TableHead>Entry Date</TableHead>
                    <TableHead>Exit Date</TableHead>
                    <TableHead className="text-right">Entry (NPR)</TableHead>
                    <TableHead className="text-right">Exit (NPR)</TableHead>
                    <TableHead className="text-right">Shares</TableHead>
                    <TableHead className="text-right">Net PnL</TableHead>
                    <TableHead className="text-right">Return %</TableHead>
                    <TableHead className="text-right pr-6">Exit Reason</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {tradesData?.items?.map((t, idx) => (
                    <TableRow key={idx} className="hover:bg-white/[0.03]">
                      <TableCell className="pl-6 font-mono font-bold text-xs">{t.symbol}</TableCell>
                      <TableCell className="font-mono text-xs text-text-subtle">{fmtDate(t.entry_date)}</TableCell>
                      <TableCell className="font-mono text-xs text-text-subtle">{fmtDate(t.exit_date)}</TableCell>
                      <TableCell className="text-right font-mono text-xs">{fmtNpr(t.entry_price)}</TableCell>
                      <TableCell className="text-right font-mono text-xs">{fmtNpr(t.exit_price)}</TableCell>
                      <TableCell className="text-right font-mono text-xs">{t.shares?.toLocaleString()}</TableCell>
                      <TableCell className={`text-right font-mono text-xs font-semibold ${t.net_pnl >= 0 ? "text-gain" : "text-loss"}`}>
                        {fmtNpr(t.net_pnl)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        <DeltaChip value={t.return_pct} size="sm" />
                      </TableCell>
                      <TableCell className="text-right pr-6 text-xs text-text-subtle capitalize">
                        {t.exit_reason || "Signal exit"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          </TabsContent>

          {/* TAB 4: WALK-FORWARD FOLDS */}
          <TabsContent value="folds" className="space-y-4 mt-0">
            <Card className="p-0 overflow-hidden">
              <Table>
                <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
                  <TableRow>
                    <TableHead className="pl-6">Fold</TableHead>
                    <TableHead>Train Period</TableHead>
                    <TableHead>Test Period</TableHead>
                    <TableHead className="text-right">Calibrated Samples</TableHead>
                    <TableHead className="text-right">Train Hit Rate</TableHead>
                    <TableHead className="text-right pr-6">Weights (News/Fund/Tech)</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {foldsData.map((f) => {
                    const fm = (f.metrics || {}) as Record<string, any>;
                    const fw = (f.weights || {}) as Record<string, any>;
                    return (
                      <TableRow key={f.fold_idx} className="hover:bg-white/[0.03]">
                        <TableCell className="pl-6 font-mono font-bold text-xs">Fold #{f.fold_idx}</TableCell>
                        <TableCell className="font-mono text-xs text-text-subtle">
                          {fmtDate(f.train_start)} → {fmtDate(f.train_end)}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-foreground font-medium">
                          {fmtDate(f.test_start)} → {fmtDate(f.test_end)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">{fm.calibration_samples ?? "—"}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-gain">{fmtPct(fm.train_hit_rate ?? fm.hit_rate, 1)}</TableCell>
                        <TableCell className="text-right pr-6 font-mono text-xs">
                          {fw.news !== undefined
                            ? `${Number(fw.news).toFixed(2)} / ${Number(fw.fundamentals).toFixed(2)} / ${Number(fw.technicals).toFixed(2)}`
                            : "—"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Card>
          </TabsContent>

          {/* TAB 5: BY STOCK */}
          <TabsContent value="persymbol" className="space-y-4 mt-0">
            <Card className="p-0 overflow-hidden">
              <Table>
                <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
                  <TableRow>
                    <TableHead className="pl-6">Symbol</TableHead>
                    <TableHead className="text-right">Trades</TableHead>
                    <TableHead className="text-right">Net PnL (NPR)</TableHead>
                    <TableHead className="text-right">Win Rate</TableHead>
                    <TableHead className="text-right">Strategy Return</TableHead>
                    <TableHead className="text-right pr-6">Buy & Hold Return</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {Object.entries((stratFullMetrics.per_symbol as Record<string, any>) || {}).map(
                    ([sym, val]) => (
                      <TableRow key={sym} className="hover:bg-white/[0.03]">
                        <TableCell className="pl-6 font-mono font-bold text-xs">{sym}</TableCell>
                        <TableCell className="text-right font-mono text-xs">{val.trades ?? 0}</TableCell>
                        <TableCell className={`text-right font-mono text-xs font-bold ${val.net_pnl >= 0 ? "text-gain" : "text-loss"}`}>
                          {fmtNpr(val.net_pnl)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">{fmtPct(val.win_rate, 1)}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-gain">{fmtPct(val.return_pct, 1)}</TableCell>
                        <TableCell className="text-right pr-6 font-mono text-xs text-text-subtle">
                          {fmtPct(val.bh_return_pct, 1)}
                        </TableCell>
                      </TableRow>
                    )
                  )}
                </TableBody>
              </Table>
            </Card>
          </TabsContent>

          {/* TAB 6: CALIBRATION */}
          <TabsContent value="calibration" className="space-y-6 mt-0">
            <ReliabilityChart
              binsCalibrated={stratFullMetrics.calibration?.bins}
              brierCal={stratFullMetrics.calibration?.brier_score}
            />
          </TabsContent>

          {/* TAB 7: METHOD & LIMITATIONS */}
          <TabsContent value="limits" className="space-y-6 mt-0">
            <Card className="p-6 space-y-4 border-l-4 border-l-warning">
              <h3 className="font-display font-semibold text-lg text-foreground">
                Statistical Assumptions & NEPSE Structural Limitations
              </h3>
              <ul className="space-y-2.5 text-xs text-muted-foreground leading-relaxed">
                <li className="flex items-start gap-2">
                  <span className="size-1.5 rounded-full bg-gold-500 shrink-0 mt-1.5" />
                  <span><strong>Limited NEPSE History:</strong> Sparse fundamental reports prior to modern reporting mandates mean wider confidence intervals.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="size-1.5 rounded-full bg-gold-500 shrink-0 mt-1.5" />
                  <span><strong>Cost Model Invariants:</strong> Results model exact broker commission tiers (0.27% - 0.40%), 0.015% SEBON fee, flat Rs. 25 DP fee, and applicable CGT.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="size-1.5 rounded-full bg-gold-500 shrink-0 mt-1.5" />
                  <span><strong>Cash Exit Discipline:</strong> Strict long-only cash exit modeling; retail short selling is strictly prohibited under NEPSE regulations.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="size-1.5 rounded-full bg-gold-500 shrink-0 mt-1.5" />
                  <span><strong>Zero Lookahead Guarantee:</strong> Every signal fold enforces strict <code>usable_from &lt;= as_of</code> point-in-time discipline. Past backtest returns do not guarantee future performance.</span>
                </li>
              </ul>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  );
}
