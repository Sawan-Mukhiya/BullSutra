"use client";

import React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Sparkles, Calendar, Gauge } from "lucide-react";
import { SymbolAvatar } from "@/components/common/SymbolAvatar";
import { DeltaChip } from "@/components/common/DeltaChip";
import { ExportMenu } from "./ExportMenu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fmtNpr, fmtDate } from "@/lib/format";
import { useSession } from "@/hooks/useSession";
import type { SecurityDetail } from "@/types";

export interface BriefHeaderProps {
  symbol: string;
  security?: SecurityDetail | null;
  briefId?: string;
  history?: string[];
  currentAsOf?: string;
}

export function BriefHeader({
  symbol,
  security,
  briefId,
  history = [],
  currentAsOf,
}: BriefHeaderProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: session } = useSession();

  const uniqueHistory = React.useMemo(
    () => Array.from(new Set(history.filter(Boolean))),
    [history]
  );

  const handleDateChange = (date: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("as_of", date);
    router.push(`/stocks/${symbol.toUpperCase()}?${params.toString()}`);
  };

  const ltp = security?.last_close;
  const changePct = security?.change_pct;

  return (
    <div className="glass-featured p-6 lg:p-8 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
      {/* Identity & Company Info */}
      <div className="flex items-start gap-4 sm:gap-5">
        <SymbolAvatar ticker={symbol} size={56} className="mt-1" />
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="font-mono text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              {symbol}
            </h1>
            <Badge variant="outline" className="text-xs uppercase">
              {security?.sector_group || "NEPSE Universe"}
            </Badge>
            <Badge variant="gold" className="text-xs gap-1">
              <Gauge className="size-3" />
              ±10% Daily Band
            </Badge>
          </div>
          <p className="text-sm sm:text-base text-muted-foreground font-medium">
            {security?.name || `${symbol} Listed Company Ltd.`}
          </p>
        </div>
      </div>

      {/* Price & Actions Row */}
      <div className="flex flex-wrap items-center gap-4 sm:gap-6">
        {/* Real-time / Last Traded Price */}
        {ltp !== undefined && ltp !== null && (
          <div className="space-y-1 text-left lg:text-right">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-text-subtle block">
              Last Close
            </span>
            <div className="flex items-center gap-3">
              <span className="font-mono text-2xl sm:text-3xl font-bold text-foreground num">
                {fmtNpr(ltp)}
              </span>
              <DeltaChip value={changePct} size="md" />
            </div>
          </div>
        )}

        {/* As-Of History Selector */}
        {uniqueHistory.length > 0 && (
          <div className="space-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-text-subtle block">
              Historical As-Of
            </span>
            <Select value={currentAsOf || uniqueHistory[0]} onValueChange={handleDateChange}>
              <SelectTrigger className="w-44 h-10 text-xs font-mono">
                <Calendar className="size-3.5 mr-2 text-gold-500" />
                <SelectValue placeholder="Select date" />
              </SelectTrigger>
              <SelectContent>
                {uniqueHistory.map((date) => (
                  <SelectItem key={date} value={date} className="font-mono text-xs">
                    {fmtDate(date)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Export and Admin Run */}
        <div className="flex items-center gap-2 pt-2 sm:pt-0">
          {briefId && <ExportMenu briefId={briefId} />}

          {session?.authenticated && (
            <Link href={`/admin/runs?symbol=${symbol}`}>
              <Button size="sm" variant="default" className="gap-1.5">
                <Sparkles className="size-3.5" />
                <span>Run Agents</span>
              </Button>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
