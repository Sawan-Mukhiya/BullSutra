"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { Search, Filter, ExternalLink, ArrowUpDown } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { SymbolAvatar } from "@/components/common/SymbolAvatar";
import { DeltaChip } from "@/components/common/DeltaChip";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { useSecuritySearch } from "@/hooks/useSecurity";
import { fmtNpr } from "@/lib/format";

const SECTORS = [
  { key: "all", label: "All Companies" },
  { key: "bank", label: "Banking & Finance" },
  { key: "hydro", label: "Hydropower" },
  { key: "insurance", label: "Insurance" },
  { key: "other", label: "Manufacturing & Others" },
];

export default function MarketsPage() {
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("all");
  const [universeOnly, setUniverseOnly] = useState(false);
  const [sortField, setSortField] = useState<"symbol" | "last_close" | "change_pct">("symbol");
  const [sortAsc, setSortAsc] = useState(true);

  const { data, isLoading } = useSecuritySearch(query, 200);

  const handleSort = (field: "symbol" | "last_close" | "change_pct") => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false); // default desc for numeric
    }
  };

  const filteredItems = useMemo(() => {
    if (!data?.items) return [];
    return data.items
      .filter((s) => {
        const matchSector =
          sector === "all" || s.sector_group?.toLowerCase() === sector.toLowerCase();
        const matchUniverse = !universeOnly || s.in_universe;
        return matchSector && matchUniverse;
      })
      .sort((a, b) => {
        let valA: any = a[sortField];
        let valB: any = b[sortField];
        if (valA === undefined || valA === null) valA = 0;
        if (valB === undefined || valB === null) valB = 0;

        if (typeof valA === "string") {
          return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return sortAsc ? valA - valB : valB - valA;
      });
  }, [data, sector, universeOnly, sortField, sortAsc]);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Title & Stats */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              NEPSE Securities Screener
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              Explore 250+ listed NEPSE symbols with real-time valuation, sector categorization, and universe status.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-text-subtle">
              Showing {filteredItems.length} companies
            </span>
          </div>
        </div>

        {/* Toolbar & Filters */}
        <Card className="p-4 sm:p-5 space-y-4">
          <div className="flex flex-col sm:flex-row items-center gap-3 justify-between">
            {/* Search Input */}
            <div className="relative w-full sm:max-w-md">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-text-subtle" />
              <Input
                placeholder="Search symbol or company name..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-10 h-10 text-xs"
              />
            </div>

            {/* Universe Only Toggle */}
            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <button
                onClick={() => setUniverseOnly(!universeOnly)}
                className={`h-9 px-3 rounded-lg text-xs font-medium border transition-colors ${
                  universeOnly
                    ? "bg-accent border-gold-500/50 text-accent-foreground"
                    : "bg-secondary/40 border-border text-text-subtle hover:text-foreground"
                }`}
              >
                Universe 40 Only
              </button>
            </div>
          </div>

          {/* Sector Filter Chips */}
          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1">
            {SECTORS.map((sec) => (
              <button
                key={sec.key}
                onClick={() => setSector(sec.key)}
                className={`h-8 px-3.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors border ${
                  sector === sec.key
                    ? "bg-card border-gold-500/50 text-foreground shadow-sm"
                    : "bg-secondary/40 border-border text-text-subtle hover:text-foreground"
                }`}
              >
                {sec.label}
              </button>
            ))}
          </div>
        </Card>

        {/* Securities DataTable */}
        <Card className="p-0 overflow-hidden">
          <Table>
            <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
              <TableRow>
                <TableHead
                  onClick={() => handleSort("symbol")}
                  className="cursor-pointer hover:text-foreground pl-6"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Symbol & Company</span>
                    <ArrowUpDown className="size-3" />
                  </div>
                </TableHead>
                <TableHead>Sector</TableHead>
                <TableHead
                  onClick={() => handleSort("last_close")}
                  className="cursor-pointer hover:text-foreground text-right"
                >
                  <div className="flex items-center justify-end gap-1.5">
                    <span>Last Close</span>
                    <ArrowUpDown className="size-3" />
                  </div>
                </TableHead>
                <TableHead
                  onClick={() => handleSort("change_pct")}
                  className="cursor-pointer hover:text-foreground text-right"
                >
                  <div className="flex items-center justify-end gap-1.5">
                    <span>Change %</span>
                    <ArrowUpDown className="size-3" />
                  </div>
                </TableHead>
                <TableHead className="text-center">Universe</TableHead>
                <TableHead className="text-right pr-6">Action</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {isLoading ? (
                [...Array(10)].map((_, i) => (
                  <TableRow key={i}>
                    <TableCell className="pl-6">
                      <div className="flex items-center gap-3">
                        <Skeleton className="size-8 rounded-full" />
                        <div className="space-y-1">
                          <Skeleton className="w-16 h-4" />
                          <Skeleton className="w-32 h-3" />
                        </div>
                      </div>
                    </TableCell>
                    <TableCell><Skeleton className="w-20 h-4" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="w-16 h-4 ml-auto" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="w-14 h-4 ml-auto" /></TableCell>
                    <TableCell className="text-center"><Skeleton className="w-16 h-4 mx-auto" /></TableCell>
                    <TableCell className="text-right pr-6"><Skeleton className="w-12 h-6 ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : filteredItems.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-64 text-center">
                    <EmptyState
                      title="No companies match filters"
                      description="Try clearing your search query or switching sector filters."
                      actionLabel="Reset Filters"
                      onAction={() => {
                        setQuery("");
                        setSector("all");
                        setUniverseOnly(false);
                      }}
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredItems.map((sec) => (
                  <TableRow key={sec.symbol} className="hover:bg-white/[0.03]">
                    {/* Symbol & Company Name */}
                    <TableCell className="pl-6">
                      <Link
                        href={`/stocks/${sec.symbol.toUpperCase()}`}
                        className="flex items-center gap-3 group"
                      >
                        <SymbolAvatar ticker={sec.symbol} size={32} />
                        <div>
                          <div className="font-mono font-bold text-sm text-foreground group-hover:text-gold-300 transition-colors">
                            {sec.symbol}
                          </div>
                          <p className="text-xs text-text-subtle truncate max-w-xs sm:max-w-sm">
                            {sec.name}
                          </p>
                        </div>
                      </Link>
                    </TableCell>

                    {/* Sector */}
                    <TableCell>
                      <Badge variant="outline" className="text-[11px] capitalize">
                        {sec.sector_group || "Universe"}
                      </Badge>
                    </TableCell>

                    {/* Last Close */}
                    <TableCell className="text-right font-mono font-semibold text-sm num">
                      {fmtNpr(sec.last_close)}
                    </TableCell>

                    {/* Change % */}
                    <TableCell className="text-right">
                      <DeltaChip value={sec.change_pct} size="sm" />
                    </TableCell>

                    {/* In Universe */}
                    <TableCell className="text-center">
                      {sec.in_universe ? (
                        <Badge variant="gold" className="text-[10px] px-2 py-0.5">
                          Universe 40
                        </Badge>
                      ) : (
                        <span className="text-[11px] text-text-subtle font-mono">External</span>
                      )}
                    </TableCell>

                    {/* Action */}
                    <TableCell className="text-right pr-6">
                      <Link href={`/stocks/${sec.symbol.toUpperCase()}`}>
                        <Button size="sm" variant="outline" className="h-8 px-2.5 text-xs gap-1">
                          <span>Brief</span>
                          <ExternalLink className="size-3" />
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Card>
      </div>
    </AppShell>
  );
}
