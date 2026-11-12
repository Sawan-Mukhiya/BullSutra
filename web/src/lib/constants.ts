export const APP_NAME = "BullSutra";

export const DISCLAIMER =
  "BullSutra is a quantitative research and backtesting platform for educational and informational purposes only. It is not an investment advisor, broker, or financial institution, and nothing produced by BullSutra constitutes investment, legal, or tax advice. Nepal Stock Exchange (NEPSE) investments carry substantial risk, including the loss of principal. Always consult a licensed SEBON investment advisor before making financial decisions.";

export const AGENTS = {
  news: {
    label: "News",
    icon: "Newspaper",
    color: "#8B5CF6",
    tailwindColor: "info",
    description: "Scrapes and evaluates sentiment from Nepali financial portals with exponential decay.",
  },
  fundamentals: {
    label: "Fundamentals",
    icon: "Landmark",
    color: "#0EA5E9",
    tailwindColor: "violet",
    description: "Evaluates point-in-time quarterly financials, ROE, P/E, P/B, and sector-specific metrics.",
  },
  technicals: {
    label: "Technicals",
    icon: "Activity",
    color: "#F59E0B",
    tailwindColor: "teal",
    description: "Analyzes causal moving averages, Donchian channels, RSI momentum, and volume surges.",
  },
  risk: {
    label: "Risk",
    icon: "ShieldAlert",
    color: "#EF4444",
    tailwindColor: "warning",
    description: "Monitors volatility, liquidity turnover, circuit limit proximity, and broker concentration.",
  },
} as const;

export type AgentKey = keyof typeof AGENTS;

export const STRATEGY_LABELS: Record<string, string> = {
  bh_nepse_index: "NEPSE Index Buy & Hold",
  bh_equal_weight: "Equal-Weight Buy & Hold",
  news_only: "News Specialist Only",
  fund_only: "Fundamentals Specialist Only",
  tech_only: "Technicals Specialist Only",
  consensus_basic: "Unweighted Consensus",
  consensus_weighted: "Dynamic-Weighted Consensus",
  consensus_debate: "Debate-Adjusted Consensus",
  full: "BullSutra Full Walk-Forward",
};

export const STRATEGY_COLORS: Record<string, string> = {
  bh_nepse_index: "#94a3b8",
  bh_equal_weight: "#64748b",
  news_only: "#a78bfa",
  fund_only: "#38bdf8",
  tech_only: "#fbbf24",
  consensus_basic: "#34d399",
  consensus_weighted: "#10b981",
  consensus_debate: "#059669",
  full: "#D4AF37", // BullSutra Champagne Gold for top strategy
};

export const SECTOR_GROUP_LABELS: Record<string, string> = {
  all: "All Sectors",
  bank: "Commercial & Dev Banks",
  hydro: "Hydropower",
  insurance: "Life & Non-Life Insurance",
  other: "Manufacturing, Hotels & Others",
};

export const FLAG_LABELS: Record<string, string> = {
  insufficient_history: "Not enough price history",
  no_news: "No recent news coverage",
  no_fundamentals: "No fundamentals report on file",
  agent_error: "Specialist computation warning",
  insufficient_signal: "Not enough decisive signal",
  risk_damped: "Buy signal reduced by elevated risk",
  illiquid_no_buy: "Too illiquid to enter position",
  conflict_hold: "Agents conflicted: held in neutral",
};
