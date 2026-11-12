"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2 } from "lucide-react";
import { Command } from "cmdk";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useSecuritySearch } from "@/hooks/useSecurity";
import { SymbolAvatar } from "@/components/common/SymbolAvatar";
import { Badge } from "@/components/ui/badge";
import { fmtNpr } from "@/lib/format";

export interface GlobalSearchProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function GlobalSearch({ open, onOpenChange }: GlobalSearchProps) {
  const router = useRouter();
  const [query, setQuery] = React.useState("");
  const { data, isLoading } = useSecuritySearch(query, 10);

  const handleSelect = (symbol: string) => {
    onOpenChange(false);
    setQuery("");
    router.push(`/stocks/${symbol.toUpperCase()}`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="p-0 overflow-hidden max-w-xl border border-gold-500/30 glass-featured">
        <Command className="w-full bg-transparent">
          <div className="flex items-center border-b border-border px-4 pr-12 h-14">
            <Search className="size-5 shrink-0 text-text-subtle mr-3" />
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder="Search NEPSE symbol or company (e.g. NABIL, NICA)..."
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-text-subtle text-foreground"
            />
            {isLoading && <Loader2 className="size-4 animate-spin text-gold-500 ml-2" />}
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2 thin-scrollbar">
            <Command.Empty className="py-8 text-center text-sm text-text-subtle">
              No securities found matching &ldquo;{query}&rdquo;
            </Command.Empty>

            <Command.Group heading="Securities" className="px-2 text-xs font-semibold text-text-subtle uppercase tracking-wider mb-1">
              {data?.items?.map((item) => (
                <Command.Item
                  key={item.symbol}
                  value={`${item.symbol} ${item.name}`}
                  onSelect={() => handleSelect(item.symbol)}
                  className="flex items-center justify-between p-2.5 rounded-lg hover:bg-white/5 cursor-pointer data-[selected=true]:bg-accent/40 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <SymbolAvatar ticker={item.symbol} size={32} />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-sm text-foreground">
                          {item.symbol}
                        </span>
                        {item.in_universe && (
                          <Badge variant="gold" className="text-[9px] h-4 px-1.5">
                            Universe 40
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-text-subtle truncate max-w-xs sm:max-w-md">
                        {item.name}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-xs uppercase text-text-subtle font-medium">
                      {item.sector_group}
                    </span>
                    {item.last_close && (
                      <p className="font-mono text-xs font-medium text-foreground">
                        {fmtNpr(item.last_close)}
                      </p>
                    )}
                  </div>
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>

          <div className="flex items-center justify-between border-t border-border px-4 py-2 text-[11px] text-text-subtle bg-secondary/30">
            <span>Navigation: Arrow keys to move, Enter to view stock</span>
            <span>Esc to close</span>
          </div>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
