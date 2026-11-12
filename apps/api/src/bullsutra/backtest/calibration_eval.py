"""Calibration evaluation for backtest out-of-sample periods."""
from typing import Dict, List, Any
import numpy as np
import pandas as pd

from bullsutra.agents.calibration.isotonic import reliability_bins

def evaluate_calibration(eval_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate raw vs calibrated confidence reliability on test window BUY/SELL signals."""
    if not eval_rows:
        return {"brier_raw": None, "brier_calibrated": None, "bins_raw": [], "bins_calibrated": [], "n": 0}

    df = pd.DataFrame(eval_rows)
    df = df[df["hit"].notna()]
    n = len(df)
    if n == 0:
        return {"brier_raw": None, "brier_calibrated": None, "bins_raw": [], "bins_calibrated": [], "n": 0}

    p_raw = df["raw_confidence"].astype(float).values
    p_cal = df["calibrated_confidence"].astype(float).values
    hits = df["hit"].astype(float).values

    brier_raw = float(np.mean((p_raw - hits) ** 2))
    brier_cal = float(np.mean((p_cal - hits) ** 2))

    bins_raw = reliability_bins(list(p_raw), list(hits))
    bins_cal = reliability_bins(list(p_cal), list(hits))

    return {
        "brier_raw": round(brier_raw, 4),
        "brier_calibrated": round(brier_cal, 4),
        "bins_raw": bins_raw,
        "bins_calibrated": bins_cal,
        "n": n,
    }
