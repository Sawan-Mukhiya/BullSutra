import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { SecurityDetail, SecuritySummary, Candle, OhlcvResponse, IndicatorsResponse } from "@/types";

export function useSecurity(symbol: string) {
  return useQuery({
    queryKey: qk.security(symbol),
    queryFn: async () => {
      const res = await api.GET("/api/v1/securities/{symbol}", {
        params: {
          path: { symbol: symbol.toUpperCase() },
        },
      });
      return unwrap<SecurityDetail>(res);
    },
    enabled: Boolean(symbol),
    staleTime: 5 * 60 * 1000,
  });
}

export function useSecuritySearch(q: string, limit = 8) {
  return useQuery({
    queryKey: qk.search(q),
    queryFn: async () => {
      const res = await api.GET("/api/v1/securities", {
        params: {
          query: {
            q: q.trim() || undefined,
            limit,
          },
        },
      });
      return unwrap<{ items: SecuritySummary[]; total: number }>(res);
    },
    staleTime: 60 * 1000,
  });
}

export function useOhlcv(symbol: string, start?: string, end?: string, adjusted = true) {
  return useQuery({
    queryKey: qk.ohlcv(symbol, start, end, adjusted),
    queryFn: async () => {
      const res = await api.GET("/api/v1/securities/{symbol}/ohlcv", {
        params: {
          path: { symbol: symbol.toUpperCase() },
          query: {
            start,
            end,
            adjusted,
          },
        },
      });
      const data = unwrap<OhlcvResponse>(res);
      return data.candles;
    },
    enabled: Boolean(symbol),
    staleTime: 5 * 60 * 1000,
  });
}

export function useIndicators(symbol: string, names?: string[], start?: string, end?: string) {
  return useQuery({
    queryKey: qk.indicators(symbol, names, start, end),
    queryFn: async () => {
      const res = await api.GET("/api/v1/securities/{symbol}/indicators", {
        params: {
          path: { symbol: symbol.toUpperCase() },
          query: {
            names: names?.join(","),
            start,
            end,
          },
        },
      });
      const data = unwrap<IndicatorsResponse>(res);
      return data.series as Record<string, Array<{ date: string; value: number }>>;
    },
    enabled: Boolean(symbol && names && names.length > 0),
    staleTime: 5 * 60 * 1000,
  });
}
