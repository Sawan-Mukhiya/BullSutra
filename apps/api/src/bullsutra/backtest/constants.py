"""Backtest constants and labels."""

STRATEGY_KEYS = [
    "bh_nepse_index",
    "bh_equal_weight",
    "news_only",
    "fund_only",
    "tech_only",
    "consensus_basic",
    "consensus_weighted",
    "consensus_debate",
    "full",
]

STRATEGY_LABELS = {
    "bh_nepse_index": "Buy and hold (NEPSE index)",
    "bh_equal_weight": "Buy and hold (equal weight)",
    "news_only": "News only",
    "fund_only": "Fundamentals only",
    "tech_only": "Technicals only",
    "consensus_basic": "Consensus, equal weights",
    "consensus_weighted": "Consensus, fitted weights",
    "consensus_debate": "Consensus + debate",
    "full": "BullSutra (full system)",
}

BENCHMARK_KEYS = {"bh_nepse_index", "bh_equal_weight"}

METRIC_KEYS = [
    "final_equity",
    "total_return",
    "cagr",
    "volatility",
    "sharpe",
    "sortino",
    "max_drawdown",
    "calmar",
    "exposure",
    "turnover",
    "n_trades",
    "trade_win_rate",
    "avg_trade_return",
    "profit_factor",
    "avg_holding_days",
    "signal_hit_rate",
    "n_signals",
]
