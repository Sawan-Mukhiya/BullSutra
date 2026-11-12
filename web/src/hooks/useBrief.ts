import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { ResearchBrief, BriefSummary } from "@/types";

export function useBrief(symbol: string, asOf?: string) {
  return useQuery({
    queryKey: qk.brief(symbol, asOf),
    queryFn: async () => {
      const res = await api.GET("/api/v1/research/{symbol}", {
        params: {
          path: { symbol: symbol.toUpperCase() },
          query: asOf ? { as_of: asOf } : undefined,
        },
      });
      return unwrap<ResearchBrief>(res);
    },
    enabled: Boolean(symbol),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useBriefHistory(symbol: string) {
  return useQuery({
    queryKey: qk.briefHistory(symbol),
    queryFn: async () => {
      const res = await api.GET("/api/v1/research/{symbol}/history", {
        params: {
          path: { symbol: symbol.toUpperCase() },
        },
      });
      const data = unwrap<Record<string, BriefSummary[]>>(res);
      const list = Object.values(data)[0] || [];
      const dates = list.map((b) => b.as_of).filter(Boolean);
      return Array.from(new Set(dates));
    },
    enabled: Boolean(symbol),
    staleTime: 5 * 60 * 1000,
  });
}

export function useLatestBriefs(offset = 0, limit = 40) {
  return useQuery({
    queryKey: qk.latestBriefs(offset, limit),
    queryFn: async () => {
      const res = await api.GET("/api/v1/research", {
        params: {
          query: { offset, limit },
        },
      });
      return unwrap<{ items: BriefSummary[]; total: number }>(res);
    },
    staleTime: 60 * 1000,
  });
}
