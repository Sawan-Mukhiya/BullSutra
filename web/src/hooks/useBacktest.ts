import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type {
  BacktestDetail,
  BacktestListItem,
  TradeOut,
  FoldOut,
  FoldsResponse,
  EquityResponse,
} from "@/types";

export function useBacktestList(offset = 0, limit = 20) {
  return useQuery({
    queryKey: qk.backtests(offset, limit),
    queryFn: async () => {
      const res = await api.GET("/api/v1/backtest", {
        params: {
          query: { offset, limit },
        },
      });
      return unwrap<{ items: BacktestListItem[]; total: number }>(res);
    },
    staleTime: 30 * 1000,
  });
}

export function useBacktest(id: string) {
  return useQuery({
    queryKey: qk.backtest(id),
    queryFn: async () => {
      const res = await api.GET("/api/v1/backtest/{backtest_id}", {
        params: {
          path: { backtest_id: id },
        },
      });
      return unwrap<BacktestDetail>(res);
    },
    enabled: Boolean(id),
    staleTime: 30 * 1000,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 3000 : false;
    },
  });
}

export function useBacktestEquity(id: string, strategies?: string[]) {
  return useQuery({
    queryKey: qk.equity(id, strategies),
    queryFn: async () => {
      const res = await api.GET("/api/v1/backtest/{backtest_id}/equity", {
        params: {
          path: { backtest_id: id },
          query: { strategies: strategies?.join(",") },
        },
      });
      const data = unwrap<EquityResponse>(res);
      const seriesMap = data.series || {};

      // Transform into date-indexed rows
      const datesSet = new Set<string>();
      for (const points of Object.values(seriesMap)) {
        for (const p of points) {
          datesSet.add(p.date);
        }
      }

      const sortedDates = Array.from(datesSet).sort();
      const rows = sortedDates.map((d) => {
        const row: Record<string, any> = { date: d };
        for (const [strat, points] of Object.entries(seriesMap)) {
          const pt = points.find((p) => p.date === d);
          if (pt) {
            row[strat] = pt.equity;
            row[`${strat}_dd`] = pt.drawdown;
            if (strat === "full") row.drawdown = pt.drawdown;
          }
        }
        return row;
      });

      return rows as Array<{ date: string; [strategy: string]: any }>;
    },
    enabled: Boolean(id),
    staleTime: 5 * 60 * 1000,
  });
}

export function useBacktestTrades(id: string, strategy?: string, offset = 0, limit = 50) {
  return useQuery({
    queryKey: qk.trades(id, strategy, offset, limit),
    queryFn: async () => {
      const res = await api.GET("/api/v1/backtest/{backtest_id}/trades", {
        params: {
          path: { backtest_id: id },
          query: { strategy, offset, limit },
        },
      });
      return unwrap<{ items: TradeOut[]; total: number }>(res);
    },
    enabled: Boolean(id),
    staleTime: 5 * 60 * 1000,
  });
}

export function useBacktestFolds(id: string) {
  return useQuery({
    queryKey: qk.folds(id),
    queryFn: async () => {
      const res = await api.GET("/api/v1/backtest/{backtest_id}/folds", {
        params: {
          path: { backtest_id: id },
        },
      });
      const data = unwrap<FoldsResponse>(res);
      return data.items;
    },
    enabled: Boolean(id),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.POST("/api/v1/backtest", {
        body: payload,
      });
      return unwrap<{ backtest_id: string; job_id: string; status: string }>(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["backtests"] });
    },
  });
}
