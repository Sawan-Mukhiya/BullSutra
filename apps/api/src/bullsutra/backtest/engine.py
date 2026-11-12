"""Walk-forward portfolio simulation engine for NEPSE."""
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Any, Set
import numpy as np
import pandas as pd

from bullsutra.core.constants import get_circuit_limit_pct
from bullsutra.backtest.config import BacktestConfig
from bullsutra.backtest.costs import trade_cost, capital_gains_tax, MIN_LOT
from bullsutra.backtest.strategies import Decider, Decision

@dataclass
class Position:
    security_id: int
    entry_date: date
    entry_price: float
    units: float               # shares / adj_factor at entry
    entry_cost: float
    entry_value: float

@dataclass
class Order:
    security_id: int
    side: str                  # "BUY" or "SELL"
    score: float = 0.0
    multiplier: float = 1.0
    exit_reason: str = "signal"

@dataclass
class Trade:
    security_id: int
    symbol: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    shares: int
    entry_cost: float
    exit_cost: float
    tax: float
    net_pnl: float
    return_pct: float
    holding_days: int
    exit_reason: str

@dataclass
class EngineResult:
    equity: pd.DataFrame       # columns: date, equity, exposure, drawdown
    trades: List[Trade]
    turnover_value: float

class PortfolioEngine:
    def __init__(
        self,
        prices_long: pd.DataFrame,
        dates: List[date],
        decider: Decider,
        cfg: BacktestConfig,
        symbol_map: Dict[int, str],
        delisted_on: Optional[Dict[int, date]] = None,
        folds_map: Optional[Dict[date, Dict[str, Any]]] = None,
    ):
        self.prices_long = prices_long
        self.dates = dates
        self.decider = decider
        self.cfg = cfg
        self.symbol_map = symbol_map
        self.delisted_on = delisted_on or {}
        self.folds_map = folds_map or {}

        # Fast price lookup: (security_id, date) -> row dict
        self._price_lookup: Dict[Tuple[int, date], Dict[str, Any]] = {}
        for _, r in prices_long.iterrows():
            sec_id = int(r["security_id"])
            d = r["date"] if isinstance(r["date"], date) else r["date"].date()
            self._price_lookup[(sec_id, d)] = {
                "raw_open": float(r["raw_open"]),
                "raw_high": float(r.get("raw_high", r["raw_open"])),
                "raw_low": float(r.get("raw_low", r["raw_close"])),
                "raw_close": float(r["raw_close"]),
                "prev_close": float(r.get("prev_close_exchange", r.get("prev_close", r["raw_close"]))),
                "volume": float(r.get("volume", 0.0)),
                "adj_factor": float(r.get("adj_factor", 1.0)),
            }

    def simulate(self, decisions_by_date: Dict[date, Dict[int, Decision]]) -> EngineResult:
        cash: float = float(self.cfg.initial_capital)
        positions: Dict[int, Position] = {}
        pending_sells: List[Order] = []
        pending_buys: List[Order] = []
        trades: List[Trade] = []
        equity_records: List[Dict[str, Any]] = []
        turnover_value: float = 0.0

        last_known_close: Dict[int, float] = {}

        for d in self.dates:
            # 0. Fold boundary update
            if d in self.folds_map:
                self.decider.set_fold(self.folds_map[d])

            circuit_limit = get_circuit_limit_pct(d)

            # 1. Execute Pending Orders
            # A. Execute Pending Sells
            remaining_sells: List[Order] = []
            for order in pending_sells:
                sec_id = order.security_id
                if sec_id not in positions:
                    continue
                pos = positions[sec_id]
                bar = self._price_lookup.get((sec_id, d))
                
                # Check tradability
                if bar is None or bar["volume"] <= 0:
                    remaining_sells.append(order)
                    continue

                raw_price = bar["raw_open"] if self.cfg.execution == "next_open" else bar["raw_close"]
                prev_close = bar["prev_close"]

                # Check limit-down circuit block
                if raw_price <= prev_close * (1.0 - circuit_limit) + 0.01:
                    remaining_sells.append(order)
                    continue

                # Execute Sell
                fill = raw_price * (1.0 - self.cfg.slippage_bps / 10000.0)
                adj_fac = bar["adj_factor"]
                qty = math.floor(pos.units * adj_fac)
                
                if qty <= 0:
                    del positions[sec_id]
                    continue

                trade_val = qty * fill
                turnover_value += trade_val
                cost = trade_cost(trade_val)
                proceeds = trade_val - cost
                
                gain = (trade_val - cost) - (pos.entry_value + pos.entry_cost)
                holding_days = (d - pos.entry_date).days
                tax = capital_gains_tax(gain, holding_days) if self.cfg.apply_taxes else 0.0
                
                cash += (proceeds - tax)
                net_pnl = proceeds - tax - (pos.entry_value + pos.entry_cost)
                cost_basis = pos.entry_value + pos.entry_cost
                ret_pct = net_pnl / cost_basis if cost_basis > 0 else 0.0

                trades.append(Trade(
                    security_id=sec_id,
                    symbol=self.symbol_map.get(sec_id, f"SEC_{sec_id}"),
                    entry_date=pos.entry_date,
                    exit_date=d,
                    entry_price=pos.entry_price,
                    exit_price=round(fill, 4),
                    shares=qty,
                    entry_cost=round(pos.entry_cost, 2),
                    exit_cost=round(cost, 2),
                    tax=round(tax, 2),
                    net_pnl=round(net_pnl, 2),
                    return_pct=round(ret_pct, 6),
                    holding_days=holding_days,
                    exit_reason=order.exit_reason,
                ))
                del positions[sec_id]

            pending_sells = remaining_sells

            # B. Execute Pending Buys
            # Calculate open equity for position sizing
            open_pos_val = 0.0
            for s_id, p in positions.items():
                s_bar = self._price_lookup.get((s_id, d))
                curr_p = s_bar["raw_open"] if (s_bar and s_bar["raw_open"] > 0) else last_known_close.get(s_id, p.entry_price)
                adj_f = s_bar["adj_factor"] if s_bar else 1.0
                open_pos_val += math.floor(p.units * adj_f) * curr_p
            equity_open = cash + open_pos_val

            for order in pending_buys:
                sec_id = order.security_id
                if sec_id in positions or cash <= 0:
                    continue

                bar = self._price_lookup.get((sec_id, d))
                if bar is None or bar["volume"] <= 0:
                    continue

                raw_price = bar["raw_open"] if self.cfg.execution == "next_open" else bar["raw_close"]
                prev_close = bar["prev_close"]

                # Check limit-up circuit block
                if raw_price >= prev_close * (1.0 + circuit_limit) - 0.01:
                    continue

                fill = raw_price * (1.0 + self.cfg.slippage_bps / 10000.0)
                if fill <= 0:
                    continue

                target_val = (equity_open / self.cfg.max_positions) * order.multiplier
                budget = min(target_val, cash)
                
                # Sizing with fee buffer
                shares = math.floor(budget / (fill * (1.0 + 0.0040 + 0.00015)))
                while shares > 0 and (shares * fill + trade_cost(shares * fill)) > cash:
                    shares -= 1

                if shares < MIN_LOT:
                    continue

                trade_val = shares * fill
                turnover_value += trade_val
                cost = trade_cost(trade_val)
                cash -= (trade_val + cost)

                adj_fac = bar["adj_factor"]
                positions[sec_id] = Position(
                    security_id=sec_id,
                    entry_date=d,
                    entry_price=round(fill, 4),
                    units=shares / adj_fac,
                    entry_cost=cost,
                    entry_value=trade_val,
                )

            # Buy orders do not carry over
            pending_buys = []

            # 2. Check Delisting
            for sec_id in list(positions.keys()):
                delist_date = self.delisted_on.get(sec_id)
                if delist_date and d >= delist_date:
                    pos = positions[sec_id]
                    bar = self._price_lookup.get((sec_id, d))
                    exit_p = bar["raw_close"] if bar else last_known_close.get(sec_id, pos.entry_price)
                    adj_fac = bar["adj_factor"] if bar else 1.0
                    qty = math.floor(pos.units * adj_fac)
                    trade_val = qty * exit_p
                    cost = trade_cost(trade_val)
                    proceeds = trade_val - cost
                    gain = (trade_val - cost) - (pos.entry_value + pos.entry_cost)
                    holding_days = (d - pos.entry_date).days
                    tax = capital_gains_tax(gain, holding_days) if self.cfg.apply_taxes else 0.0
                    cash += (proceeds - tax)
                    net_pnl = proceeds - tax - (pos.entry_value + pos.entry_cost)
                    trades.append(Trade(
                        security_id=sec_id,
                        symbol=self.symbol_map.get(sec_id, f"SEC_{sec_id}"),
                        entry_date=pos.entry_date,
                        exit_date=d,
                        entry_price=pos.entry_price,
                        exit_price=round(exit_p, 4),
                        shares=qty,
                        entry_cost=round(pos.entry_cost, 2),
                        exit_cost=round(cost, 2),
                        tax=round(tax, 2),
                        net_pnl=round(net_pnl, 2),
                        return_pct=round(net_pnl / (pos.entry_value + pos.entry_cost), 6) if (pos.entry_value + pos.entry_cost) > 0 else 0.0,
                        holding_days=holding_days,
                        exit_reason="delisted",
                    ))
                    del positions[sec_id]

            # 3. Update last known close & Mark to Market at Close
            portfolio_val = 0.0
            for sec_id, pos in positions.items():
                bar = self._price_lookup.get((sec_id, d))
                if bar is not None and bar["raw_close"] > 0:
                    last_known_close[sec_id] = bar["raw_close"]
                    close_p = bar["raw_close"]
                    adj_fac = bar["adj_factor"]
                else:
                    close_p = last_known_close.get(sec_id, pos.entry_price)
                    adj_fac = 1.0
                shares_held = math.floor(pos.units * adj_fac)
                portfolio_val += shares_held * close_p

            equity_close = cash + portfolio_val
            exposure = portfolio_val / equity_close if equity_close > 0 else 0.0
            equity_records.append({
                "date": d,
                "equity": round(equity_close, 2),
                "exposure": round(exposure, 4),
            })

            # 4. Check Optional Stop Loss
            if self.cfg.stop_loss_pct is not None:
                for sec_id, pos in positions.items():
                    bar = self._price_lookup.get((sec_id, d))
                    if bar and bar["raw_close"] <= pos.entry_price * (1.0 - self.cfg.stop_loss_pct):
                        if not any(o.security_id == sec_id for o in pending_sells):
                            pending_sells.append(Order(security_id=sec_id, side="SELL", exit_reason="stop_loss"))

            # 5. Create Orders for Next Day from Decisions on Date d
            day_decisions = decisions_by_date.get(d, {})
            # A. Evaluate Held Positions for Exit
            for sec_id in positions.keys():
                dec = day_decisions.get(sec_id)
                if dec and dec.label == "SELL":
                    if not any(o.security_id == sec_id for o in pending_sells):
                        pending_sells.append(Order(security_id=sec_id, side="SELL", exit_reason="signal"))

            # B. Evaluate BUY Candidates
            selling_sec_ids = {o.security_id for o in pending_sells}
            held_not_selling = sum(1 for s_id in positions if s_id not in selling_sec_ids)
            available_slots = self.cfg.max_positions - held_not_selling

            if available_slots > 0:
                buy_candidates: List[Tuple[float, int, Order]] = []
                for sec_id, dec in day_decisions.items():
                    if sec_id in positions or sec_id in selling_sec_ids:
                        continue
                    if dec.label == "BUY":
                        # For full strategy: calibrated_conf >= min_calibrated_confidence
                        if self.decider.key == "full":
                            conf = dec.calibrated_conf or 0.0
                            if conf < self.cfg.min_calibrated_confidence:
                                continue
                        buy_candidates.append((
                            dec.score,
                            sec_id,
                            Order(security_id=sec_id, side="BUY", score=dec.score, multiplier=dec.multiplier),
                        ))

                # Sort by score descending, ties by security_id ascending
                buy_candidates.sort(key=lambda x: (-x[0], x[1]))
                for cand in buy_candidates[:available_slots]:
                    pending_buys.append(cand[2])

        # 6. End of Test: Force-liquidate all open positions at last date's close
        if self.dates and positions:
            last_date = self.dates[-1]
            for sec_id, pos in list(positions.items()):
                bar = self._price_lookup.get((sec_id, last_date))
                exit_p = bar["raw_close"] if bar else last_known_close.get(sec_id, pos.entry_price)
                adj_fac = bar["adj_factor"] if bar else 1.0
                qty = math.floor(pos.units * adj_fac)
                trade_val = qty * exit_p
                turnover_value += trade_val
                cost = trade_cost(trade_val)
                proceeds = trade_val - cost
                gain = (trade_val - cost) - (pos.entry_value + pos.entry_cost)
                holding_days = (last_date - pos.entry_date).days
                tax = capital_gains_tax(gain, holding_days) if self.cfg.apply_taxes else 0.0
                cash += (proceeds - tax)
                net_pnl = proceeds - tax - (pos.entry_value + pos.entry_cost)
                trades.append(Trade(
                    security_id=sec_id,
                    symbol=self.symbol_map.get(sec_id, f"SEC_{sec_id}"),
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
                    holding_days=holding_days,
                    exit_reason="end_of_test",
                ))
            equity_records[-1]["equity"] = round(cash, 2)
            equity_records[-1]["exposure"] = 0.0

        # Build equity curve dataframe
        eq_df = pd.DataFrame(equity_records)
        if not eq_df.empty:
            cummax = eq_df["equity"].cummax()
            eq_df["drawdown"] = ((eq_df["equity"] - cummax) / cummax).round(4)
        else:
            eq_df = pd.DataFrame(columns=["date", "equity", "exposure", "drawdown"])

        return EngineResult(equity=eq_df, trades=trades, turnover_value=turnover_value)
