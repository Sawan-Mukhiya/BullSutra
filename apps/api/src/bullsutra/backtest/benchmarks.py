"""Benchmark portfolio simulations."""
import math
from datetime import date
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

from bullsutra.core.constants import get_circuit_limit_pct
from bullsutra.backtest.config import BacktestConfig
from bullsutra.backtest.costs import trade_cost, capital_gains_tax, MIN_LOT
from bullsutra.backtest.engine import EngineResult, Trade, Position

def simulate_bh_equal_weight(
    prices_long: pd.DataFrame,
    dates: List[date],
    cfg: BacktestConfig,
    symbol_map: Dict[int, str],
) -> EngineResult:
    """Buy and hold equal weight across eligible universe on first test date."""
    if not dates:
        return EngineResult(equity=pd.DataFrame(), trades=[], turnover_value=0.0)

    # Price lookup: (security_id, date) -> row
    lookup: Dict[Tuple[int, date], Dict[str, Any]] = {}
    sec_ids_set = set()
    for _, r in prices_long.iterrows():
        sec_id = int(r["security_id"])
        sec_ids_set.add(sec_id)
        d = r["date"] if isinstance(r["date"], date) else r["date"].date()
        lookup[(sec_id, d)] = {
            "raw_open": float(r["raw_open"]),
            "raw_close": float(r["raw_close"]),
            "prev_close": float(r.get("prev_close_exchange", r.get("prev_close", r["raw_close"]))),
            "volume": float(r.get("volume", 0.0)),
            "adj_factor": float(r.get("adj_factor", 1.0)),
        }

    first_date = dates[0]
    circuit_limit = get_circuit_limit_pct(first_date)

    # Eligible universe on first_date
    eligible = []
    for s_id in sec_ids_set:
        bar = lookup.get((s_id, first_date))
        if bar and bar["volume"] > 0:
            raw_p = bar["raw_open"] if cfg.execution == "next_open" else bar["raw_close"]
            prev_p = bar["prev_close"]
            if raw_p < prev_p * (1.0 + circuit_limit) - 0.01:
                eligible.append((s_id, raw_p, bar["adj_factor"]))

    cash = float(cfg.initial_capital)
    positions: Dict[int, Position] = {}
    turnover_value = 0.0

    if eligible:
        alloc_per_sec = cash / len(eligible)
        for s_id, raw_p, adj_f in eligible:
            fill = raw_p * (1.0 + cfg.slippage_bps / 10000.0)
            shares = math.floor(alloc_per_sec / (fill * (1.0 + 0.0040 + 0.00015)))
            while shares > 0 and (shares * fill + trade_cost(shares * fill)) > cash:
                shares -= 1
            if shares >= MIN_LOT:
                trade_val = shares * fill
                turnover_value += trade_val
                cost = trade_cost(trade_val)
                cash -= (trade_val + cost)
                positions[s_id] = Position(
                    security_id=s_id,
                    entry_date=first_date,
                    entry_price=round(fill, 4),
                    units=shares / adj_f,
                    entry_cost=cost,
                    entry_value=trade_val,
                )

    equity_records = []
    last_known_close: Dict[int, float] = {}

    for d in dates:
        port_val = 0.0
        for s_id, pos in positions.items():
            bar = lookup.get((s_id, d))
            if bar and bar["raw_close"] > 0:
                last_known_close[s_id] = bar["raw_close"]
                close_p = bar["raw_close"]
                adj_f = bar["adj_factor"]
            else:
                close_p = last_known_close.get(s_id, pos.entry_price)
                adj_f = 1.0
            shares_held = math.floor(pos.units * adj_f)
            port_val += shares_held * close_p

        eq_close = cash + port_val
        exp = port_val / eq_close if eq_close > 0 else 0.0
        equity_records.append({
            "date": d,
            "equity": round(eq_close, 2),
            "exposure": round(exp, 4),
        })

    # Liquidate at end of test
    trades = []
    if dates and positions:
        last_date = dates[-1]
        for s_id, pos in positions.items():
            bar = lookup.get((s_id, last_date))
            exit_p = bar["raw_close"] if bar else last_known_close.get(s_id, pos.entry_price)
            adj_f = bar["adj_factor"] if bar else 1.0
            qty = math.floor(pos.units * adj_f)
            trade_val = qty * exit_p
            turnover_value += trade_val
            cost = trade_cost(trade_val)
            proceeds = trade_val - cost
            gain = (trade_val - cost) - (pos.entry_value + pos.entry_cost)
            tax = capital_gains_tax(gain, (last_date - pos.entry_date).days) if cfg.apply_taxes else 0.0
            cash += (proceeds - tax)
            net_pnl = proceeds - tax - (pos.entry_value + pos.entry_cost)
            trades.append(Trade(
                security_id=s_id,
                symbol=symbol_map.get(s_id, f"SEC_{s_id}"),
                entry_date=pos.entry_date,
                exit_date=last_date,
                entry_price=pos.entry_price,
                exit_price=round(exit_p, 4),
                shares=qty,
                entry_cost=round(pos.entry_cost, 2),
                exit_cost=round(cost, 2),
                tax=round(tax, 2),
                net_pnl=round(net_pnl, 2),
                return_pct=round(net_pnl / (pos.entry_value + pos.entry_cost), 6) if (pos.entry_value + pos.entry_cost) > 0 else 0.0,
                holding_days=(last_date - pos.entry_date).days,
                exit_reason="end_of_test",
            ))
        equity_records[-1]["equity"] = round(cash, 2)
        equity_records[-1]["exposure"] = 0.0

    eq_df = pd.DataFrame(equity_records)
    if not eq_df.empty:
        cummax = eq_df["equity"].cummax()
        eq_df["drawdown"] = ((eq_df["equity"] - cummax) / cummax).round(4)
    else:
        eq_df = pd.DataFrame(columns=["date", "equity", "exposure", "drawdown"])

    return EngineResult(equity=eq_df, trades=trades, turnover_value=turnover_value)

def simulate_bh_nepse_index(
    index_df: pd.DataFrame,
    dates: List[date],
    initial_capital: float = 1_000_000.0,
) -> Optional[EngineResult]:
    """Buy and hold NEPSE index benchmark if coverage >= 95%."""
    if index_df.empty or not dates:
        return None

    # Filter index_df to dates
    idx_map = {}
    for idx_row in index_df.itertuples():
        d = getattr(idx_row, "date", getattr(idx_row, "Index", None))
        if hasattr(d, "date"):
            d = d.date()
        idx_map[d] = float(getattr(idx_row, "close", 0.0))

    # Check 95% coverage
    covered = [d for d in dates if d in idx_map]
    if len(covered) / len(dates) < 0.95:
        return None

    first_d = covered[0]
    first_close = idx_map[first_d]
    if first_close <= 0:
        return None

    records = []
    curr_close = first_close
    for d in dates:
        if d in idx_map:
            curr_close = idx_map[d]
        eq = initial_capital * (curr_close / first_close)
        records.append({
            "date": d,
            "equity": round(eq, 2),
            "exposure": 1.0,
        })

    eq_df = pd.DataFrame(records)
    cummax = eq_df["equity"].cummax()
    eq_df["drawdown"] = ((eq_df["equity"] - cummax) / cummax).round(4)

    return EngineResult(equity=eq_df, trades=[], turnover_value=0.0)
