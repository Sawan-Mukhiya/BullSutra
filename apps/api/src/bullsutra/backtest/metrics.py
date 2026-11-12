"""Quantitative performance metrics computation for backtests."""
import math
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from bullsutra.core.constants import TRADING_DAYS_PER_YEAR
from bullsutra.backtest.engine import Trade

def compute_metrics(
    equity_series: pd.Series,
    exposure_series: pd.Series,
    initial_capital: float,
    rf_annual: float,
    trades: List[Trade],
    turnover_value: float,
    is_benchmark: bool = False,
    signal_hit_rate: Optional[float] = None,
    n_signals: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate portfolio performance metrics adhering to specification."""
    if equity_series.empty or initial_capital <= 0:
        return {}

    e_0 = float(initial_capital)
    e_t = float(equity_series.iloc[-1])
    total_return = (e_t / e_0) - 1.0

    t_days = len(equity_series)
    years = t_days / float(TRADING_DAYS_PER_YEAR)
    cagr = ((e_t / e_0) ** (1.0 / years)) - 1.0 if years >= 0.25 else None

    # Daily returns
    # r_t = E_t / E_{t-1} - 1 (first return uses E_0)
    prev_equity = pd.concat([pd.Series([e_0]), equity_series.iloc[:-1].reset_index(drop=True)])
    r = (equity_series.values / prev_equity.values) - 1.0

    # Volatility
    vol = float(np.std(r, ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR)) if len(r) > 1 else 0.0

    # Sharpe & Sortino
    rf_d = ((1.0 + rf_annual) ** (1.0 / TRADING_DAYS_PER_YEAR)) - 1.0
    excess_r = r - rf_d
    excess_std = float(np.std(excess_r, ddof=1)) if len(excess_r) > 1 else 0.0

    if excess_std > 0:
        sharpe = float(np.mean(excess_r) / excess_std * math.sqrt(TRADING_DAYS_PER_YEAR))
    else:
        sharpe = 0.0

    downside = np.minimum(excess_r, 0.0)
    downside_var = float(np.mean(downside ** 2))
    if downside_var > 0:
        sortino = float(np.mean(excess_r) / math.sqrt(downside_var) * math.sqrt(TRADING_DAYS_PER_YEAR))
    else:
        sortino = None

    # Max Drawdown
    cummax = np.maximum.accumulate(equity_series.values)
    dd_array = (equity_series.values - cummax) / cummax
    max_dd = float(np.min(dd_array)) if len(dd_array) > 0 else 0.0

    # Calmar
    if cagr is not None and max_dd < 0:
        calmar = cagr / abs(max_dd)
    else:
        calmar = None

    exposure = float(np.mean(exposure_series.values)) if not exposure_series.empty else 0.0
    mean_eq = float(np.mean(equity_series.values)) if not equity_series.empty else e_0
    turnover = (turnover_value / mean_eq / years) if (mean_eq > 0 and years > 0) else 0.0

    res: Dict[str, Any] = {
        "final_equity": round(e_t, 2),
        "total_return": round(total_return, 4),
        "cagr": round(cagr, 4) if cagr is not None else None,
        "volatility": round(vol, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4) if sortino is not None else None,
        "max_drawdown": round(max_dd, 4),
        "calmar": round(calmar, 4) if calmar is not None else None,
        "exposure": round(exposure, 4),
        "turnover": round(turnover, 4),
        "signal_hit_rate": round(signal_hit_rate, 4) if signal_hit_rate is not None else None,
        "n_signals": n_signals,
    }

    if is_benchmark:
        res["n_trades"] = None
        res["trade_win_rate"] = None
        res["avg_trade_return"] = None
        res["profit_factor"] = None
        res["avg_holding_days"] = None
    else:
        n_trades = len(trades)
        res["n_trades"] = n_trades
        if n_trades > 0:
            wins = sum(1 for tr in trades if tr.net_pnl > 0)
            res["trade_win_rate"] = round(wins / n_trades, 4)
            res["avg_trade_return"] = round(float(np.mean([tr.return_pct for tr in trades])), 4)
            pos_pnl = sum(tr.net_pnl for tr in trades if tr.net_pnl > 0)
            neg_pnl = sum(abs(tr.net_pnl) for tr in trades if tr.net_pnl < 0)
            res["profit_factor"] = round(pos_pnl / neg_pnl, 4) if neg_pnl > 0 else None
            res["avg_holding_days"] = round(float(np.mean([tr.holding_days for tr in trades])), 1)
        else:
            res["trade_win_rate"] = None
            res["avg_trade_return"] = None
            res["profit_factor"] = None
            res["avg_holding_days"] = None

    return res
