"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  TrendingUp,
  ArrowRight,
  ShieldCheck,
  Newspaper,
  Landmark,
  Activity,
  ShieldAlert,
  Search,
  Sparkles,
  BarChart3,
  Scale,
} from "lucide-react";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { GlobalSearch } from "@/components/layout/GlobalSearch";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SignalBadge } from "@/components/common/SignalBadge";
import { ConfidenceGauge } from "@/components/common/ConfidenceGauge";
import { AGENTS } from "@/lib/constants";

const SAMPLE_TICKERS = [
  { symbol: "NEPSE", price: "2,712.40", chg: "+0.82%" },
  { symbol: "NABIL", price: "1,245.50", chg: "+1.20%" },
  { symbol: "NICA", price: "782.00", chg: "-0.45%" },
  { symbol: "CIT", price: "2,410.00", chg: "+2.15%" },
  { symbol: "GBIME", price: "348.00", chg: "+0.28%" },
  { symbol: "CHCL", price: "512.00", chg: "+3.40%" },
  { symbol: "SHIVM", price: "490.50", chg: "-1.10%" },
  { symbol: "HDL", price: "1,890.00", chg: "+0.90%" },
  { symbol: "NLIC", price: "730.00", chg: "-0.65%" },
];

export default function LandingPage() {
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background flex flex-col selection:bg-gold-500/20">
      <SiteHeader />

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 lg:pt-24 lg:pb-32 grid-texture">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-12 gap-12 items-center">
            {/* Left Hero Text Column */}
            <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
              <div className="inline-flex items-center gap-2 rounded-full border border-gold-500/40 bg-accent px-3.5 py-1 text-xs text-accent-foreground font-medium">
                <Sparkles className="size-3.5 text-gold-500" />
                <span>Engineered for the Nepal Stock Exchange (NEPSE)</span>
              </div>

              <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-balance leading-[1.15]">
                Research the Nepal market with{" "}
                <span className="text-gold-gradient">four specialist minds</span>, one verdict.
              </h1>

              <p className="text-base sm:text-lg text-muted-foreground max-w-2xl leading-relaxed">
                Deterministic specialist agents evaluate news sentiment, causal fundamentals, technical momentum, and broker concentration risk. They debate and cross-examine to produce calibrated consensus research.
              </p>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
                <Link href="/dashboard" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full gap-2 text-base font-semibold">
                    <span>Enter Market Dashboard</span>
                    <ArrowRight className="size-4" />
                  </Button>
                </Link>

                <button
                  onClick={() => setSearchOpen(true)}
                  className="w-full sm:w-auto flex items-center justify-center gap-2 h-12 px-6 rounded-[16px] border border-border bg-secondary text-sm font-semibold text-foreground hover:border-gold-500/40 hover:bg-secondary/80 transition-all"
                >
                  <Search className="size-4 text-gold-500" />
                  <span>Search Stocks (Cmd+K)</span>
                </button>
              </div>

              {/* Trust Badges */}
              <div className="pt-4 flex flex-wrap items-center justify-center lg:justify-start gap-6 text-xs text-text-subtle">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="size-4 text-gain" />
                  <span>Zero LLM Hallucinated Math</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Scale className="size-4 text-gold-500" />
                  <span>Multi-Agent Debate Protocol</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <BarChart3 className="size-4 text-info" />
                  <span>Walk-Forward Backtested</span>
                </div>
              </div>
            </div>

            {/* Right Interactive Preview Stack */}
            <div className="lg:col-span-5 relative flex justify-center">
              <div className="w-full max-w-md space-y-4">
                <Card featured className="p-6 relative rotate-[-1deg] shadow-2xl hover:rotate-0 transition-transform duration-300">
                  <div className="flex items-center justify-between border-b border-border/80 pb-4 mb-4">
                    <div className="flex items-center gap-3">
                      <div className="size-10 rounded-full bg-secondary border border-gold-500/40 flex items-center justify-center font-display font-bold text-gold-500">
                        NB
                      </div>
                      <div>
                        <h3 className="font-mono font-bold text-lg">NABIL</h3>
                        <span className="text-xs text-text-subtle">Nabil Bank Limited</span>
                      </div>
                    </div>
                    <SignalBadge label="BULLISH" size="sm" />
                  </div>

                  <div className="flex items-center justify-between my-4">
                    <div>
                      <span className="text-xs text-text-subtle uppercase block">Consensus Score</span>
                      <span className="font-mono text-2xl font-bold text-gain">+0.68</span>
                    </div>
                    <ConfidenceGauge value={0.78} size="sm" label="Confidence" />
                  </div>

                  {/* Specialist Chips */}
                  <div className="grid grid-cols-2 gap-2 pt-3 border-t border-border/60 text-xs">
                    <div className="flex items-center justify-between p-2 rounded bg-secondary/50">
                      <span className="text-info font-medium">News</span>
                      <span className="font-mono font-bold">+0.74</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded bg-secondary/50">
                      <span className="text-violet font-medium">Fundamentals</span>
                      <span className="font-mono font-bold">+0.81</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded bg-secondary/50">
                      <span className="text-teal font-medium">Technicals</span>
                      <span className="font-mono font-bold">+0.52</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded bg-secondary/50">
                      <span className="text-warning font-medium">Risk Score</span>
                      <span className="font-mono font-bold text-gain">0.24</span>
                    </div>
                  </div>

                  <Link href="/stocks/NABIL" className="block mt-4">
                    <Button variant="outline" size="sm" className="w-full text-xs">
                      Inspect Full NABIL Research Dossier →
                    </Button>
                  </Link>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Infinite Ticker Tape */}
      <div className="border-y border-border bg-bg-raised/70 backdrop-blur-md h-12 overflow-hidden flex items-center">
        <div className="animate-marquee gap-10 pl-6">
          {[...SAMPLE_TICKERS, ...SAMPLE_TICKERS, ...SAMPLE_TICKERS].map((t, idx) => (
            <div key={idx} className="flex items-center gap-2 text-xs font-mono shrink-0">
              <span className="font-bold text-foreground">{t.symbol}</span>
              <span className="text-muted-foreground">{t.price}</span>
              <span className={t.chg.startsWith("+") ? "text-gain font-semibold" : "text-loss font-semibold"}>
                {t.chg}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Stats Proof Strip */}
      <section className="py-16 bg-secondary/20 border-b border-border">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 text-center">
            <Card className="p-6">
              <span className="font-mono text-3xl sm:text-4xl font-bold text-gold-500 block">4</span>
              <span className="text-xs uppercase font-semibold text-text-subtle tracking-wider mt-2 block">
                Independent Specialists
              </span>
              <p className="text-xs text-muted-foreground mt-1">News, Fundamentals, Technicals, Risk</p>
            </Card>

            <Card className="p-6">
              <span className="font-mono text-3xl sm:text-4xl font-bold text-gold-500 block">40</span>
              <span className="text-xs uppercase font-semibold text-text-subtle tracking-wider mt-2 block">
                Point-in-Time Universe
              </span>
              <p className="text-xs text-muted-foreground mt-1">Liquid monthly NEPSE cohorts</p>
            </Card>

            <Card className="p-6">
              <span className="font-mono text-3xl sm:text-4xl font-bold text-gold-500 block">100%</span>
              <span className="text-xs uppercase font-semibold text-text-subtle tracking-wider mt-2 block">
                Deterministic Quant
              </span>
              <p className="text-xs text-muted-foreground mt-1">Pure math; zero hallucinated metrics</p>
            </Card>

            <Card className="p-6">
              <span className="font-mono text-3xl sm:text-4xl font-bold text-gold-500 block">0.40%</span>
              <span className="text-xs uppercase font-semibold text-text-subtle tracking-wider mt-2 block">
                Realistic Cost Model
              </span>
              <p className="text-xs text-muted-foreground mt-1">Broker slabs, SEBON fees, DP & CGT</p>
            </Card>
          </div>
        </div>
      </section>

      {/* Meet the Specialist Agents */}
      <section id="agents" className="py-20 lg:py-28">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <div className="hairline-gold w-16 mx-auto mb-4" />
            <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">
              Four Specialists. Rigorous Cross-Examination.
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
              No single algorithm possesses a complete market perspective. BullSutra divides analytical responsibility into four deterministic roles.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* News Agent */}
            <Card className="p-6 border-t-4 border-t-info hover:-translate-y-1 transition-transform flex flex-col justify-between">
              <div className="space-y-4">
                <div className="size-12 rounded-xl bg-info/15 flex items-center justify-center text-info">
                  <Newspaper className="size-6" />
                </div>
                <h3 className="font-display font-semibold text-lg text-foreground">News Specialist</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Aggregates headlines and announcements from Nepali financial portals. Applies 5-day exponential decay half-life and prior shrinkage.
                </p>
              </div>
              <div className="pt-6 border-t border-border/60 text-[11px] font-mono text-text-subtle">
                Attributes direct article URLs
              </div>
            </Card>

            {/* Fundamentals Agent */}
            <Card className="p-6 border-t-4 border-t-violet hover:-translate-y-1 transition-transform flex flex-col justify-between">
              <div className="space-y-4">
                <div className="size-12 rounded-xl bg-violet/15 flex items-center justify-center text-violet">
                  <Landmark className="size-6" />
                </div>
                <h3 className="font-display font-semibold text-lg text-foreground">Fundamentals Specialist</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Calculates point-in-time quarterly ROE, P/E, P/B, and EPS growth. Applies sector-specific scoring models and bank NPL penalties.
                </p>
              </div>
              <div className="pt-6 border-t border-border/60 text-[11px] font-mono text-text-subtle">
                Enforces usable_from causality
              </div>
            </Card>

            {/* Technicals Agent */}
            <Card className="p-6 border-t-4 border-t-teal hover:-translate-y-1 transition-transform flex flex-col justify-between">
              <div className="space-y-4">
                <div className="size-12 rounded-xl bg-teal/15 flex items-center justify-center text-teal">
                  <Activity className="size-6" />
                </div>
                <h3 className="font-display font-semibold text-lg text-foreground">Technicals Specialist</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Vectorized moving averages (SMA50/200), MACD line crosses, Donchian channel breakouts, and RSI momentum with overbought penalty.
                </p>
              </div>
              <div className="pt-6 border-t border-border/60 text-[11px] font-mono text-text-subtle">
                Zero lookahead bias
              </div>
            </Card>

            {/* Risk Agent */}
            <Card className="p-6 border-t-4 border-t-warning hover:-translate-y-1 transition-transform flex flex-col justify-between">
              <div className="space-y-4">
                <div className="size-12 rounded-xl bg-warning/15 flex items-center justify-center text-warning">
                  <ShieldAlert className="size-6" />
                </div>
                <h3 className="font-display font-semibold text-lg text-foreground">Risk Specialist</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Computes 30-day volatility, rolling drawdowns, turnover liquidity, circuit limit proximity, and broker HHI floorsheet concentration.
                </p>
              </div>
              <div className="pt-6 border-t border-border/60 text-[11px] font-mono text-text-subtle">
                Holds absolute veto power
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Footer Section */}
      <section className="py-20 bg-secondary/30 border-t border-border">
        <div className="max-w-4xl mx-auto px-4 text-center space-y-6">
          <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">
            Ready to explore verified NEPSE research?
          </h2>
          <p className="text-muted-foreground text-sm sm:text-base max-w-xl mx-auto">
            Review live research briefs, inspect the walk-forward backtesting ledger, or run specialist consensus for any listed company.
          </p>
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/dashboard">
              <Button size="lg" className="w-full sm:w-auto">
                Explore Market Dashboard
              </Button>
            </Link>
            <Link href="/backtests">
              <Button size="lg" variant="outline" className="w-full sm:w-auto">
                Review Backtests
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </div>
  );
}
