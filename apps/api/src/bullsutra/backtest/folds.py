"""Walk-forward fold generator for backtesting."""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from bullsutra.core.constants import REGIME_3_START
from bullsutra.backtest.config import BacktestConfig

@dataclass
class Fold:
    idx: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    spans_regime_change: bool = False

def make_folds(
    dates: List[date],
    cfg: BacktestConfig,
    first_signal_idx: int = 0,
) -> List[Fold]:
    """Generate rolling walk-forward train/test folds with embargo and regime tracking."""
    if not dates:
        return []

    # Filter dates by cfg start_date and end_date if specified
    filtered_dates = [
        d for d in dates
        if (cfg.start_date is None or d >= cfg.start_date)
        and (cfg.end_date is None or d <= cfg.end_date)
    ]
    if len(filtered_dates) < (cfg.train_days + cfg.embargo_days + 20):
        return []

    train_days = cfg.train_days
    test_days = cfg.test_days
    step_days = cfg.step_days
    embargo_days = cfg.embargo_days

    first_test_idx = first_signal_idx + train_days + embargo_days
    last_idx = len(filtered_dates) - 1

    folds: List[Fold] = []
    k = 0

    while True:
        test_start_idx = first_test_idx + k * step_days
        if test_start_idx > last_idx:
            break

        test_end_idx = min(test_start_idx + test_days - 1, last_idx)
        # Drop a final fold with fewer than 20 test days
        if (test_end_idx - test_start_idx + 1) < 20:
            break

        train_end_idx = test_start_idx - embargo_days - 1
        train_start_idx = train_end_idx - train_days + 1

        if train_start_idx < 0:
            k += 1
            continue

        train_start = filtered_dates[train_start_idx]
        train_end = filtered_dates[train_end_idx]
        test_start = filtered_dates[test_start_idx]
        test_end = filtered_dates[test_end_idx]

        # Spans regime change if crossing 2026-04-20
        spans_regime = (train_start <= REGIME_3_START <= test_end)

        folds.append(Fold(
            idx=k,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            spans_regime_change=spans_regime,
        ))
        k += 1

    return folds
