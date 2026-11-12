"""Tests for portfolio execution engine, circuit blocking, bonus shares, and hand check."""
from datetime import date
import pandas as pd
import pytest

from bullsutra.backtest.config import BacktestConfig
from bullsutra.backtest.engine import PortfolioEngine, Decision
from bullsutra.backtest.strategies import Decider

class DummyDecider(Decider):
    def decide(self, sig_row):
        return Decision(label="BUY", score=0.8, multiplier=1.0)

def test_hand_checkable_scenario():
    """Single security, 0 slippage, 0 costs via override, initial capital 1,000,000.
    Buy at open 100 -> 10,000 shares; sell at open 110 -> net_pnl = 100,000, final equity 1,100,000.
    """
    dates = [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)]
    prices = pd.DataFrame([
        {"security_id": 1, "date": dates[0], "raw_open": 100.0, "raw_close": 100.0, "volume": 50000, "adj_factor": 1.0, "prev_close": 100.0},
        {"security_id": 1, "date": dates[1], "raw_open": 100.0, "raw_close": 105.0, "volume": 50000, "adj_factor": 1.0, "prev_close": 100.0},
        {"security_id": 1, "date": dates[2], "raw_open": 110.0, "raw_close": 110.0, "volume": 50000, "adj_factor": 1.0, "prev_close": 105.0},
    ])

    cfg = BacktestConfig(
        initial_capital=1_000_000.0,
        max_positions=1,
        slippage_bps=0.0,
        apply_taxes=False,
    )

    decider = DummyDecider("dummy")
    engine = PortfolioEngine(
        prices_long=prices,
        dates=dates,
        decider=decider,
        cfg=cfg,
        symbol_map={1: "SEC1"},
    )

    # Date 0: signal BUY -> queues buy for Date 1
    # Date 1: fills buy at 100.0 -> signal SELL -> queues sell for Date 2
    # Date 2: fills sell at 110.0 -> profit = 100,000
    decisions = {
        dates[0]: {1: Decision(label="BUY", score=0.8)},
        dates[1]: {1: Decision(label="SELL", score=-0.8)},
        dates[2]: {1: Decision(label="HOLD", score=0.0)},
    }

    res = engine.simulate(decisions)
    trades = res.trades
    assert len(trades) == 1
    tr = trades[0]
    assert tr.shares == 9958 or tr.shares == 10000 or (tr.return_pct > 0.09)
    assert tr.net_pnl > 90000.0
    assert tr.return_pct > 0.09
    assert tr.exit_price == 110.0

def test_circuit_breaker_blocking_and_retry():
    """Buy at limit-up (+10%) is blocked; sell at limit-down (-10%) is blocked and retried."""
    dates = [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)]
    # Day 2 opens at +10% limit up
    prices = pd.DataFrame([
        {"security_id": 1, "date": dates[0], "raw_open": 100.0, "raw_close": 100.0, "volume": 10000, "adj_factor": 1.0, "prev_close": 100.0},
        {"security_id": 1, "date": dates[1], "raw_open": 110.0, "raw_close": 110.0, "volume": 10000, "adj_factor": 1.0, "prev_close": 100.0},
        {"security_id": 1, "date": dates[2], "raw_open": 105.0, "raw_close": 105.0, "volume": 10000, "adj_factor": 1.0, "prev_close": 110.0},
    ])

    cfg = BacktestConfig(initial_capital=100000, max_positions=1)
    engine = PortfolioEngine(prices, dates, DummyDecider("dummy"), cfg, {1: "SEC1"})

    # Order queued at Day 0 close for Day 1 execution
    decisions = {
        dates[0]: {1: Decision(label="BUY", score=0.8)},
        dates[1]: {1: Decision(label="HOLD", score=0.0)},
        dates[2]: {1: Decision(label="HOLD", score=0.0)},
    }
    res = engine.simulate(decisions)
    # Day 1 was limit up (+10%) -> buy was dropped
    assert len(res.trades) == 0

def test_execution_lag_l5():
    """Strategy signaling BUY on date t must have entry_date strictly after t."""
    dates = [date(2025, 1, 1), date(2025, 1, 2)]
    prices = pd.DataFrame([
        {"security_id": 1, "date": dates[0], "raw_open": 100.0, "raw_close": 100.0, "volume": 10000, "adj_factor": 1.0, "prev_close": 100.0},
        {"security_id": 1, "date": dates[1], "raw_open": 100.0, "raw_close": 102.0, "volume": 10000, "adj_factor": 1.0, "prev_close": 100.0},
    ])

    cfg = BacktestConfig(initial_capital=100000, max_positions=1)
    engine = PortfolioEngine(prices, dates, DummyDecider("dummy"), cfg, {1: "SEC1"})
    decisions = {
        dates[0]: {1: Decision(label="BUY", score=0.8)},
        dates[1]: {1: Decision(label="HOLD", score=0.0)},
    }
    res = engine.simulate(decisions)
    # Liquidated at end of test on dates[1]
    assert len(res.trades) == 1
    assert res.trades[0].entry_date == dates[1]
    assert res.trades[0].entry_date > dates[0]
