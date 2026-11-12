"""Causality and truncation invariance tests for numeric specialist agents."""
import random
import numpy as np
import pandas as pd
import pytest

from bullsutra.agents.specialists.technicals import technicals_series
from bullsutra.agents.specialists.risk import risk_series

def _generate_synthetic_prices(n: int = 600, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    
    # Random walk close
    rets = rng.normal(0.0005, 0.02, size=n)
    close = 100.0 * np.exp(np.cumsum(rets))
    high = close * (1.0 + rng.uniform(0.0, 0.02, size=n))
    low = close * (1.0 - rng.uniform(0.0, 0.02, size=n))
    open_p = low + (high - low) * rng.uniform(0.1, 0.9, size=n)
    volume = rng.integers(1000, 50000, size=n).astype(float)
    turnover = close * volume

    df = pd.DataFrame({
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "raw_open": open_p,
        "raw_high": high,
        "raw_low": low,
        "raw_close": close,
        "volume": volume,
        "turnover": turnover,
        "adj_factor": np.ones(n),
    }, index=dates)
    df.index.name = "date"
    return df

def test_technicals_causality_truncation_invariance():
    """Technicals score and confidence at date t must be identical whether computed on prices[:t] or full prices."""
    prices = _generate_synthetic_prices(600, seed=123)
    full_res = technicals_series(prices)

    # Sample 20 random points between bar 220 and 599
    rng = random.Random(999)
    test_indices = rng.sample(range(220, 600), 20)

    for idx in test_indices:
        sub_prices = prices.iloc[: idx + 1]
        sub_res = technicals_series(sub_prices)
        
        expected_score = full_res["score"].iloc[idx]
        actual_score = sub_res["score"].iloc[-1]
        expected_conf = full_res["confidence"].iloc[idx]
        actual_conf = sub_res["confidence"].iloc[-1]

        assert abs(actual_score - expected_score) < 1e-9, f"Technicals score mismatch at idx {idx}: {actual_score} vs {expected_score}"
        assert abs(actual_conf - expected_conf) < 1e-9, f"Technicals confidence mismatch at idx {idx}: {actual_conf} vs {expected_conf}"

def test_risk_causality_truncation_invariance():
    """Risk components, score, and confidence at date t must be identical whether computed on prices[:t] or full prices."""
    prices = _generate_synthetic_prices(600, seed=456)
    full_res = risk_series(prices)

    rng = random.Random(888)
    test_indices = rng.sample(range(100, 600), 20)

    for idx in test_indices:
        sub_prices = prices.iloc[: idx + 1]
        sub_res = risk_series(sub_prices)

        for col in ["score", "confidence", "c_vol", "c_dd", "c_liq", "c_circ", "c_gap"]:
            expected = full_res[col].iloc[idx]
            actual = sub_res[col].iloc[-1]
            assert abs(actual - expected) < 1e-9, f"Risk {col} mismatch at idx {idx}: {actual} vs {expected}"
