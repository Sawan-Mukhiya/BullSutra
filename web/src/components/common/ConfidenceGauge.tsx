import React from "react";
import { cn } from "@/lib/utils";

export interface ConfidenceGaugeProps {
  value: number; // 0 to 1 or 0 to 100
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function ConfidenceGauge({
  value,
  label = "Calibrated confidence",
  size = "md",
  className,
}: ConfidenceGaugeProps) {
  // Normalize to 0-1
  const norm = value > 1 ? Math.min(100, Math.max(0, value)) / 100 : Math.min(1, Math.max(0, value));
  const pct = Math.round(norm * 100);

  // Band calculations
  let bandColor = "text-slate-400";
  let strokeColor = "#94a3b8";
  let bandLabel = "Low";

  if (norm >= 0.67) {
    bandColor = "text-gain";
    strokeColor = "#22C58B";
    bandLabel = "High";
  } else if (norm >= 0.34) {
    bandColor = "text-info";
    strokeColor = "#5B8CFF";
    bandLabel = "Moderate";
  }

  // Length of semicircle with r=50 is PI * 50 = 157.08
  const dashLength = 157.08;
  const dashOffset = dashLength * (1 - norm);

  const dimensions = {
    sm: "w-24 h-16",
    md: "w-36 h-24",
    lg: "w-48 h-32",
  }[size];

  return (
    <div
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-label={label}
      className={cn("flex flex-col items-center justify-center text-center", className)}
    >
      <div className={cn("relative flex items-center justify-center", dimensions)}>
        <svg viewBox="0 0 120 72" className="w-full h-full overflow-visible">
          {/* Background track */}
          <path
            d="M10 62 A50 50 0 0 1 110 62"
            fill="none"
            stroke="currentColor"
            strokeWidth="10"
            strokeLinecap="round"
            className="text-border/70"
          />

          {/* Foreground colored arc */}
          <path
            d="M10 62 A50 50 0 0 1 110 62"
            fill="none"
            stroke={strokeColor}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={dashLength}
            strokeDashoffset={dashOffset}
            style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.2, 0.8, 0.2, 1)" }}
          />

          {/* Center percentage and band */}
          <text
            x="60"
            y="48"
            textAnchor="middle"
            className="fill-foreground font-mono font-bold text-[22px] tracking-tight"
          >
            {pct}%
          </text>
          <text
            x="60"
            y="62"
            textAnchor="middle"
            className="fill-text-subtle text-[9px] uppercase font-semibold tracking-wider"
          >
            {bandLabel}
          </text>
        </svg>
      </div>
      {label && <span className="mt-1 text-[11px] font-medium text-text-subtle uppercase tracking-wider">{label}</span>}
    </div>
  );
}
