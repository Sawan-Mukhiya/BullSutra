"""Tests for walk-forward folds, embargo, and fitting cutoff leakage."""
from datetime import date, timedelta
import pandas as pd
import pytest

from bullsutra.backtest.config import BacktestConfig
from bullsutra.backtest.folds import make_folds, Fold
from bullsutra.agents.calibration.weights import fit_weights

def test_make_folds_embargo_and_contiguity():
    # 1200 business days
    dates = [date(2022, 1, 1) + timedelta(days=i) for i in range(1200)]
    cfg = BacktestConfig(
        train_days=750,
        test_days=120,
        step_days=120,
        embargo_days=10,
    )

    folds = make_folds(dates, cfg, first_signal_idx=0)
    assert len(folds) >= 2

    for i, f in enumerate(folds):
        # L7: Embargo check
        # test_start must be >= train_end + 10 trading days
        train_end_idx = dates.index(f.train_end)
        test_start_idx = dates.index(f.test_start)
        assert test_start_idx - train_end_idx > cfg.embargo_days

        # Contiguity check: fold i test_end + 1 day == fold i+1 test_start
        if i + 1 < len(folds):
            next_f = folds[i + 1]
            curr_end_idx = dates.index(f.test_end)
            next_start_idx = dates.index(next_f.test_start)
            assert next_start_idx == curr_end_idx + 1

def test_fold_fitting_cutoff_leakage_l6():
    """fit_weights with cutoff ignores outcomes realized after cutoff."""
    cutoff = date(2025, 6, 1)
    
    # Outcomes realized <= cutoff
    outcomes_valid = pd.DataFrame([
        {"agent": "technicals", "realized_on": date(2025, 5, 1), "hit": True},
        {"agent": "technicals", "realized_on": date(2025, 5, 15), "hit": True},
    ] * 30)

    # Outcome realized AFTER cutoff
    outcome_future = pd.DataFrame([
        {"agent": "technicals", "realized_on": date(2025, 6, 2), "hit": False},
    ] * 50)

    combined = pd.concat([outcomes_valid, outcome_future], ignore_index=True)

    w1, m1 = fit_weights(outcomes_valid, cutoff=cutoff)
    w2, m2 = fit_weights(combined, cutoff=cutoff)

    # Must be identical!
    assert w1 == w2
    assert m1["hit_rates"]["technicals"] == m2["hit_rates"]["technicals"]
