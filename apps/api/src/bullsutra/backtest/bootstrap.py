"""Paired circular block bootstrap for strategy significance testing."""
import math
from typing import Dict, Any
import numpy as np

from bullsutra.core.constants import TRADING_DAYS_PER_YEAR

def _calc_sharpe(r: np.ndarray, rf_d: float) -> float:
    ex = r - rf_d
    std = float(np.std(ex, ddof=1))
    if std > 0:
        return float(np.mean(ex) / std * math.sqrt(TRADING_DAYS_PER_YEAR))
    return 0.0

def paired_block_bootstrap(
    r_strategy: np.ndarray,
    r_bench: np.ndarray,
    n: int = 2000,
    block: int = 10,
    rf_annual: float = 0.05,
    seed: int = 42,
) -> Dict[str, Any]:
    """Paired circular block bootstrap comparing strategy to benchmark returns."""
    T = len(r_strategy)
    if T == 0 or len(r_bench) != T or T < block:
        return {}

    rf_d = ((1.0 + rf_annual) ** (1.0 / TRADING_DAYS_PER_YEAR)) - 1.0

    orig_sharpe_s = _calc_sharpe(r_strategy, rf_d)
    orig_sharpe_b = _calc_sharpe(r_bench, rf_d)
    orig_diff = orig_sharpe_s - orig_sharpe_b
    orig_excess = float(np.mean(r_strategy - r_bench) * TRADING_DAYS_PER_YEAR)

    rng = np.random.default_rng(seed)

    boot_sharpe_s = np.empty(n)
    boot_diff = np.empty(n)
    boot_excess = np.empty(n)

    # Number of blocks needed
    k = int(math.ceil(T / block))

    for i in range(n):
        # Draw random block starts in [0, T)
        starts = rng.integers(0, T, size=k)
        # Generate block indices with circular wrap modulo T
        indices = np.concatenate([np.arange(st, st + block) % T for st in starts])[:T]

        s_sample = r_strategy[indices]
        b_sample = r_bench[indices]

        sh_s = _calc_sharpe(s_sample, rf_d)
        sh_b = _calc_sharpe(b_sample, rf_d)

        boot_sharpe_s[i] = sh_s
        boot_diff[i] = sh_s - sh_b
        boot_excess[i] = float(np.mean(s_sample - b_sample) * TRADING_DAYS_PER_YEAR)

    p_value = float(np.mean(boot_diff <= 0.0))

    return {
        "vs": "bh_equal_weight",
        "n": n,
        "block": block,
        "sharpe": {
            "estimate": round(orig_sharpe_s, 4),
            "ci_low": round(float(np.percentile(boot_sharpe_s, 2.5)), 4),
            "ci_high": round(float(np.percentile(boot_sharpe_s, 97.5)), 4),
        },
        "sharpe_diff": {
            "estimate": round(orig_diff, 4),
            "ci_low": round(float(np.percentile(boot_diff, 2.5)), 4),
            "ci_high": round(float(np.percentile(boot_diff, 97.5)), 4),
            "p_value": round(p_value, 4),
        },
        "excess_return_annual": {
            "estimate": round(orig_excess, 4),
            "ci_low": round(float(np.percentile(boot_excess, 2.5)), 4),
            "ci_high": round(float(np.percentile(boot_excess, 97.5)), 4),
        },
    }
