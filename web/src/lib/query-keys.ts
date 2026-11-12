export const qk = {
  brief: (symbol: string, asOf?: string) => ["brief", symbol.toUpperCase(), asOf ?? "latest"] as const,
  briefHistory: (symbol: string) => ["briefHistory", symbol.toUpperCase()] as const,
  latestBriefs: (offset = 0, limit = 40) => ["latestBriefs", offset, limit] as const,
  security: (symbol: string) => ["security", symbol.toUpperCase()] as const,
  search: (q: string) => ["search", q] as const,
  ohlcv: (symbol: string, start?: string, end?: string, adjusted = true) =>
    ["ohlcv", symbol.toUpperCase(), start ?? "all", end ?? "latest", adjusted] as const,
  indicators: (symbol: string, names?: string[], start?: string, end?: string) =>
    ["indicators", symbol.toUpperCase(), (names ?? []).sort().join(","), start ?? "all", end ?? "latest"] as const,
  backtests: (offset = 0, limit = 20) => ["backtests", offset, limit] as const,
  backtest: (id: string) => ["backtest", id] as const,
  equity: (id: string, strategies?: string[]) =>
    ["equity", id, (strategies ?? []).sort().join(",")] as const,
  trades: (id: string, strategy?: string, offset = 0, limit = 50) =>
    ["trades", id, strategy ?? "full", offset, limit] as const,
  folds: (id: string) => ["folds", id] as const,
  job: (id: string) => ["job", id] as const,
  jobs: (kind?: string, status?: string, offset = 0, limit = 20) =>
    ["jobs", kind ?? "all", status ?? "all", offset, limit] as const,
  session: () => ["session"] as const,
  adminStats: () => ["adminStats"] as const,
  freshness: () => ["freshness"] as const,
  weights: () => ["weights"] as const,
  calibration: () => ["calibration"] as const,
};
