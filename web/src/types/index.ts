import type { components } from "./api";

// Re-export generated OpenAPI schemas
export type ResearchBrief = components["schemas"]["ResearchBrief"];
export type AgentSignal = components["schemas"]["AgentSignal"];
export type Evidence = components["schemas"]["Evidence"];
export type Debate = components["schemas"]["Debate"];
export type Consensus = components["schemas"]["Consensus"];
export type BriefSummary = components["schemas"]["BriefSummary"];
export type SecuritySummary = components["schemas"]["SecuritySummary"];
export type SecurityDetail = components["schemas"]["SecurityDetail"];
export type Candle = components["schemas"]["Candle"];
export type OhlcvResponse = components["schemas"]["OhlcvResponse"];
export type IndicatorsResponse = components["schemas"]["IndicatorsResponse"];
export type BacktestDetail = components["schemas"]["BacktestDetail"];
export type BacktestListItem = components["schemas"]["BacktestListItem"];
export type StrategyResult = components["schemas"]["StrategyResult"];
export type TradeOut = components["schemas"]["TradeOut"];
export type FoldOut = components["schemas"]["FoldOut"];
export type FoldsResponse = components["schemas"]["FoldsResponse"];
export type EquityResponse = components["schemas"]["EquityResponse"];
export type EquityPoint = components["schemas"]["EquityPoint"];
export type JobOut = components["schemas"]["JobOut"];
export type UploadOut = components["schemas"]["UploadOut"];
export type AdminStatsResponse = components["schemas"]["AdminStatsResponse"];
export type WeightsOut = components["schemas"]["WeightsOut"];
export type CalibrationOut = components["schemas"]["CalibrationOut"];

// UI specific contracts
export type VerdictLabel = "BUY" | "HOLD" | "SELL" | "BULLISH" | "NEUTRAL" | "BEARISH";

export interface Quote {
  ticker: string;
  ltp: number;
  changeAbs: number;
  changePct: number;
  open: number;
  high: number;
  low: number;
  prevClose: number;
  volume: number;
  turnover: number;
  week52High?: number;
  week52Low?: number;
  updatedAt: string;
}

export interface Verdict {
  label: "Bullish" | "Neutral" | "Bearish";
  confidence: number;
  summary: string;
  generatedAt: string;
}

export interface Regime {
  label: string;
  dailyLimitPct: number;
  circuitRules: string[];
  status: "Open" | "Closed" | "Pre Open";
  closesAt?: string;
}

export interface JobEvent {
  event: string;
  seq: number;
  data: {
    job_id?: string;
    node?: string;
    value?: number;
    phase?: string;
    status?: string;
    score?: number;
    confidence?: number;
    error?: string;
    label?: string;
    brief_id?: string;
    [key: string]: unknown;
  };
}

export interface UserSession {
  authenticated: boolean;
  user?: {
    id: string;
    email: string;
    role: "admin" | "user";
  };
}
