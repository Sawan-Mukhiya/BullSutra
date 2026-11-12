"""Tests for quantitative metrics and paired block bootstrap."""
import numpy as np
import pandas as pd
import pytest

from bullsutra.backtest.metrics import compute_metrics
from bullsutra.backtest.bootstrap import paired_block_bootstrap
from bullsutra.backtest.engine import Trade

def test_metrics_max_drawdown_and_cagr():
    # Equity curve [100, 120, 90, 110] -> max drawdown is (90 - 120)/120 = -0.25 (-25%)
    eq = pd.Series([100.0, 120.0, 90.0, 110.0])
    exp = pd.Series([1.0, 1.0, 1.0, 1.0])
    metrics = compute_metrics(
        equity_series=eq,
        exposure_series=exp,
        initial_capital=100.0,
        rf_annual=0.05,
        trades=[],
        turnover_value=0.0,
    )

    assert metrics["max_drawdown"] == -0.25
    assert metrics["total_return"] == 0.10

def test_paired_block_bootstrap_identical_returns():
    """Identical strategy and benchmark return series must give sharpe_diff == 0."""
    rng = np.random.default_rng(42)
    r = rng.normal(0.001, 0.02, size=300)

    res = paired_block_bootstrap(
        r_strategy=r,
        r_bench=r,
        n=500,
        block=10,
        rf_annual=0.05,
        seed=42,
    )

    assert res["sharpe_diff"]["estimate"] == 0.0
    # 95% CI must contain 0
    assert res["sharpe_diff"]["ci_low"] <= 0.0 <= res["sharpe_diff"]["ci_high"]
    assert res["excess_return_annual"]["estimate"] == 0.0
