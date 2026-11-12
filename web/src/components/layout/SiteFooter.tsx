import React from "react";
import Link from "next/link";
import { DISCLAIMER, APP_NAME } from "@/lib/constants";

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-bg-raised/40 backdrop-blur-md mt-16 transition-colors">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <span className="font-display text-xl font-bold tracking-tight">
                Bull<span className="text-gold-500">Sutra</span>
              </span>
            </div>
            <p className="text-sm text-muted-foreground max-w-md leading-relaxed">
              Multi-Agent Quantitative Stock Research & Walk-Forward Backtesting for the Nepal Stock Exchange (NEPSE).
            </p>
          </div>

          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground mb-3 font-display">
              Research & Models
            </h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link href="/dashboard" className="hover:text-foreground transition-colors">
                  Market Dashboard
                </Link>
              </li>
              <li>
                <Link href="/markets" className="hover:text-foreground transition-colors">
                  Securities Screener
                </Link>
              </li>
              <li>
                <Link href="/backtests" className="hover:text-foreground transition-colors">
                  Walk-Forward Backtests
                </Link>
              </li>
              <li>
                <Link href="/stocks/NABIL" className="hover:text-foreground transition-colors">
                  Sample Brief: NABIL
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground mb-3 font-display">
              System & Platform
            </h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link href="/login" className="hover:text-foreground transition-colors">
                  Admin Sign In
                </Link>
              </li>
              <li>
                <Link href="/admin/pipelines" className="hover:text-foreground transition-colors">
                  Data Pipelines
                </Link>
              </li>
              <li>
                <a
                  href="/templates/fundamentals_template.csv"
                  download
                  className="hover:text-foreground transition-colors"
                >
                  Fundamentals CSV Template
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Disclaimer Block */}
        <div className="border-t border-border/60 pt-6">
          <p className="text-xs text-text-subtle leading-relaxed text-justify sm:text-left">
            <strong className="text-muted-foreground font-semibold">Regulatory & Risk Notice: </strong>
            {DISCLAIMER}
          </p>
          <div className="mt-4 flex flex-col sm:flex-row items-center justify-between text-xs text-text-subtle gap-2">
            <span>© {new Date().getFullYear()} {APP_NAME}. All rights reserved.</span>
            <span>Modeled on NEPSE 2026 Structural Reforms & Slabs</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
